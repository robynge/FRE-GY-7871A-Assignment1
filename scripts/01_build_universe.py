"""Build unique SEC company universe and preserve a full holdings audit.

The default uses the dated current-holdings snapshot. --refresh stores a separate live
snapshot and never overwrites ark_holdings_raw.csv. Candidate exclusions are
company/security exclusions, not subsequent filing-level analysis filters.
"""
from __future__ import annotations
import argparse
import csv
import io
import hashlib
import json
import re
import sys
from pathlib import Path
import pandas as pd
import requests
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import (
    ARK_FUNDS, HOLDING_FUND_LABELS, SAMPLE_END, SAMPLE_START, SEC_USER_AGENT,
    UNIVERSE_DIR,
)
from src.edgar import EdgarClient

ARK_CSV_BASE = "https://assets.ark-funds.com/fund-documents/funds-etf-csv/"
ARK_CSV_NAMES = {
    "ARKK": "ARK_INNOVATION_ETF_ARKK_HOLDINGS.csv",
    "ARKQ": "ARK_AUTONOMOUS_TECH._&_ROBOTICS_ETF_ARKQ_HOLDINGS.csv",
    "ARKW": "ARK_NEXT_GENERATION_INTERNET_ETF_ARKW_HOLDINGS.csv",
    "ARKF": "ARK_FINTECH_INNOVATION_ETF_ARKF_HOLDINGS.csv",
    "ARKG": "ARK_GENOMIC_REVOLUTION_ETF_ARKG_HOLDINGS.csv",
    "ARKX": "ARK_SPACE_EXPLORATION_&_INNOVATION_ETF_ARKX_HOLDINGS.csv",
}
RAW_PATH = UNIVERSE_DIR / "ark_holdings_raw.csv"
OUT_PATH = UNIVERSE_DIR / "universe.csv"
# Ticker symbols are exchange-specific. These holding labels establish the
# identity of local foreign listings; never match AIR (Airbus) to AAR Corp.
FOREIGN_LOCAL = {("AIR", "AIRBUS"), ("HO", "THALES"), ("DSY", "DISCOVERY"),
                 ("ADYEN", "ADYEN")}


def refresh_holdings() -> pd.DataFrame:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (course assignment)"})
    frames = []
    for fund in ARK_FUNDS:
        resp = session.get(ARK_CSV_BASE + ARK_CSV_NAMES[fund], timeout=60)
        resp.raise_for_status()
        frame = pd.DataFrame(list(csv.DictReader(io.StringIO(resp.text))))
        frame = frame[frame["company"].fillna("").str.strip().ne("")]
        frame["fund"] = fund
        frames.append(frame)
    out = pd.concat(frames, ignore_index=True)
    out.to_csv(UNIVERSE_DIR / "ark_holdings_live.csv", index=False)
    return out


def clean_ticker(raw: str) -> str | None:
    """Normalize only known US Bloomberg exchange suffixes, never all suffixes."""
    if pd.isna(raw):
        return None
    parts = str(raw).strip().upper().split()
    if not parts or "/" in parts[0] or parts[0].isdigit():
        return None
    if len(parts) > 1 and parts[1] not in {"UQ", "UW", "UN", "US", "UA", "UP"}:
        return None
    return parts[0].replace(".", "-")


def build_candidates(raw: pd.DataFrame, cik_map: dict[str, str]) -> pd.DataFrame:
    records = []
    raw = raw.fillna("").copy()
    for (raw_ticker, name), group in raw.groupby(["ticker", "company"], dropna=False, sort=True):
        raw_ticker, name = str(raw_ticker).strip(), str(name).strip()
        ticker = clean_ticker(raw_ticker)
        status, reason, cik = "unresolved_identifier", "No matching SEC ticker; issuer type unconfirmed", ""
        if re.search(r"\b(ETF|CASH|TREASURY)\b", name.upper()):
            status, reason = "non_company_security", "Holding label identifies a fund, cash or Treasury security"
        elif any(raw_ticker == t and name.upper().startswith(n) for t, n in FOREIGN_LOCAL):
            status, reason = "foreign_local_listing", "Holding label and exchange-specific ticker identify local foreign listing"
        elif raw_ticker.isdigit() or (len(raw_ticker.split()) > 1 and ticker is None):
            status, reason = "foreign_local_listing", "Numeric listing or non-US Bloomberg exchange suffix"
        elif ticker and ticker in cik_map:
            cik = str(cik_map[ticker]).zfill(10)
            status, reason = "pending_filing_check", "SEC ticker-to-CIK match"
        records.append(dict(raw_ticker=raw_ticker, ticker=ticker or "", cik=cik, ark_name=name,
                            funds="|".join(sorted(set(group["fund"]))),
                            holdings_dates="|".join(sorted(set(group["date"]))),
                            position_count=len(group), status=status, exclusion_reason=reason))
    return pd.DataFrame(records)


def build_universe(candidates: pd.DataFrame, client) -> pd.DataFrame:
    records = []
    for cik, group in candidates[candidates["cik"].ne("")].groupby("cik", sort=True):
        tickers = sorted(set(group["ticker"]))
        record = dict(ticker=tickers[0], tickers="|".join(tickers), cik=cik, sec_name="",
                      ark_name="|".join(sorted(set(group["ark_name"]))),
                      funds="|".join(sorted({f for fs in group["funds"] for f in fs.split("|")})),
                      n_10k=0, n_10q=0, status="no_10x_filings", exclusion_reason="No 10-K/10-Q in sample window")
        try:
            filings = client.list_filings(cik, ["10-K", "10-Q"], SAMPLE_START, SAMPLE_END)
            if len(filings):
                record.update(n_10k=int(filings["form"].eq("10-K").sum()),
                              n_10q=int(filings["form"].eq("10-Q").sum()),
                              sec_name=filings["company"].iloc[0], status="domestic_filer", exclusion_reason="")
        except Exception as exc:
            record.update(status="lookup_error", exclusion_reason=f"{type(exc).__name__}: {exc}")
        records.append(record)
        print(f"  checked {len(records)} CIKs: {record['ticker']} {record['status']}", flush=True)
    columns = ["ticker", "tickers", "cik", "sec_name", "ark_name", "funds", "n_10k", "n_10q", "status", "exclusion_reason"]
    result = pd.DataFrame(records, columns=columns).sort_values("ticker")
    if hasattr(client, "cache_dir"):
        result = enrich_no10x(result, client.cache_dir)
    return result


def classify_no10x(history: pd.DataFrame) -> tuple[str, str]:
    """Use actual submission forms/dates; never infer private status from absence."""
    if history.empty or not {"form", "filingDate"}.issubset(history):
        return "no_report_evidence", "No 10-K/10-Q in sample; cached history supplies no report evidence"
    forms = history["form"].astype(str)
    dates = pd.to_datetime(history["filingDate"], errors="coerce")
    domestic = dates[forms.isin(["10-K", "10-Q"])].dropna()
    foreign = history[forms.isin(["20-F", "40-F"])]
    if not domestic.empty and domestic.min() > pd.Timestamp(SAMPLE_END):
        return "first_10x_after_sample", f"First observed 10-K/10-Q filed {domestic.min():%Y-%m-%d}, after sample end"
    if not foreign.empty:
        observed = "/".join(sorted(set(foreign["form"])))
        return "foreign_reporting_forms", f"{observed} reporting observed; no 10-K/10-Q in sample window"
    if not domestic.empty:
        return "10x_outside_sample", "10-K/10-Q observed only outside sample window"
    return "no_report_evidence", "No 10-K/10-Q or 20-F/40-F observed in cached submission history"


def enrich_no10x(universe: pd.DataFrame, cache_dir: Path) -> pd.DataFrame:
    """Read only cached SEC JSON. Never issue new network requests."""
    out = universe.copy()
    if "no10x_reason" not in out:
        out["no10x_reason"] = ""
    def read_json(url):
        path = Path(cache_dir) / "metadata" / (hashlib.sha256(url.encode()).hexdigest() + ".json")
        return json.loads(path.read_text()) if path.exists() else None
    for idx, row in out[out["status"].eq("no_10x_filings")].iterrows():
        payload = read_json(f"https://data.sec.gov/submissions/CIK{str(row['cik']).zfill(10)}.json")
        if payload is None:
            out.loc[idx, "no10x_reason"] = "metadata_not_cached"
            continue
        histories = [pd.DataFrame(payload.get("filings", {}).get("recent", {}))]
        missing_page = False
        for item in payload.get("filings", {}).get("files", []):
            page = read_json("https://data.sec.gov/submissions/" + item["name"])
            if page is None:
                missing_page = True
            else:
                histories.append(pd.DataFrame(page))
        histories = [f.dropna(axis=1, how="all") for f in histories if not f.empty]
        history = pd.concat(histories, ignore_index=True) if histories else pd.DataFrame()
        category, reason = classify_no10x(history)
        if missing_page:
            category, reason = "incomplete_cached_history", "Older submission page absent from cache; detailed exclusion unresolved"
        out.loc[idx, "no10x_reason"] = category
        out.loc[idx, "exclusion_reason"] = reason
        out.loc[idx, "sec_name"] = payload.get("name", "")
    return out


def comparison_positions(frame: pd.DataFrame) -> pd.DataFrame:
    """Exclude footer lines and positions without ticker on a consistent basis."""
    valid = (frame["fund"].isin(HOLDING_FUND_LABELS)
             & frame["ticker"].fillna("").str.strip().ne("")
             & pd.to_datetime(frame["date"], format="%m/%d/%Y", errors="coerce").notna())
    return frame[valid].copy()


def write_comparison(raw: pd.DataFrame) -> None:
    directory = UNIVERSE_DIR.parent / "holdings_comparison" / "2026-09-07"
    paths = sorted(directory.glob("*.csv"))
    if not paths:
        return
    other = pd.concat([pd.read_csv(p) for p in paths], ignore_index=True)
    raw = comparison_positions(raw)
    other = comparison_positions(other)
    a, b = set(raw["ticker"].dropna()), set(other["ticker"].dropna())
    text = ("# Holdings snapshot comparison\n\n"
            f"Teacher snapshot: {len(raw)} positions, {len(a)} distinct raw tickers; holding dates "
            f"{', '.join(sorted(raw['date'].dropna().unique()))}.\n\n"
            f"User snapshot: {len(other)} positions, {len(b)} distinct raw tickers; holding dates "
            f"{', '.join(sorted(other['date'].dropna().unique()))}.\n\n"
            f"Only in teacher snapshot: {', '.join(sorted(a-b)) or 'None'}.\n\n"
            f"Only in user snapshot: {', '.join(sorted(b-a)) or 'None'}.\n\n"
            "Raw ticker counts are not company counts. GOOG and GOOGL identify the same CIK; "
            "DSY and DSY FP identify different issuers. Holdings include funds and foreign local listings. "
            "The teacher snapshot defines the default sample and is retained unchanged. "
            "Company/security exclusions precede all filing-level filters. Unmatched identifiers "
            "remain unresolved rather than being assumed private or foreign. Absence of sample-window "
            "10-K/10-Q filings does not establish an issuer's nationality or private status.\n")
    output = UNIVERSE_DIR.parents[1] / "outputs" / "universe_comparison.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text)


CIK_OVERRIDES = {"SE": "0001703399", "KMTUY": "0000056594", "BYDDY": "0001445162"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="use separately saved live holdings")
    ap.add_argument("--holdings", type=Path, default=RAW_PATH,
                    help="dated holdings snapshot to build from; defaults to the ARK snapshot")
    args = ap.parse_args()
    raw_path = args.holdings
    if not args.refresh and not raw_path.exists():
        raise FileNotFoundError(f"Dated holdings snapshot missing: {raw_path}; use --refresh explicitly")
    raw = refresh_holdings() if args.refresh else pd.read_csv(raw_path)
    raw = comparison_positions(raw)
    raw.to_csv(UNIVERSE_DIR / "holdings_positions.csv", index=False)
    client = EdgarClient(SEC_USER_AGENT or None)
    cik_map = client.ticker_to_cik()
    cik_map.update(CIK_OVERRIDES)
    candidates = build_candidates(raw, cik_map)
    candidates.to_csv(UNIVERSE_DIR / "holdings_candidates.csv", index=False)
    universe = build_universe(candidates, client)
    universe.to_csv(OUT_PATH, index=False)
    for _, row in universe.iterrows():
        mask = candidates["cik"].eq(row["cik"])
        candidates.loc[mask, "status"] = row["status"]
        candidates.loc[mask, "exclusion_reason"] = row["exclusion_reason"]
        candidates.loc[mask, "no10x_reason"] = row.get("no10x_reason", "")
    candidates.to_csv(UNIVERSE_DIR / "holdings_candidates.csv", index=False)
    candidates[candidates["status"].ne("domestic_filer")].to_csv(UNIVERSE_DIR / "holdings_exclusions.csv", index=False)
    print(candidates.groupby("status").size().to_string())
    print(f"Unique CIK filers kept: {universe['status'].eq('domestic_filer').sum()}")
    return int(universe["status"].eq("lookup_error").any())


if __name__ == "__main__":
    raise SystemExit(main())
