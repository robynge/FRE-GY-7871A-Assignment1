"""Compare six ARK holdings snapshots at security level, with six fetches at most.

Uses cached CSVs on reruns. Ticker or CUSIP matches indicate overlap, not a
corporate-action-adjusted issuer history. No missing holding is called a failure.
"""
from __future__ import annotations
import json
from pathlib import Path
import re
import subprocess
import sys
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import ARK_FUNDS, DATA, OUTPUT_DIR, UNIVERSE_DIR

DATE = "2021-05-06"
REPOSITORY = "robynge/ark-routine"
CACHE = DATA / "survivorship" / DATE


def normalize_ticker(value: str) -> str:
    parts = str(value).strip().upper().split()
    if len(parts) == 2 and parts[1] in {"UQ", "UW", "UN", "US", "UA", "UP"}:
        return parts[0].replace(".", "-")
    return " ".join(parts).replace(".", "-")


def load_positions(path: Path, default_fund: str = "") -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str).fillna("")
    frame.columns = [c.strip().lower() for c in frame.columns]
    if "fund" not in frame:
        frame["fund"] = default_fund
    valid = (frame["ticker"].str.strip().ne("")
             & pd.to_datetime(frame["date"], format="%m/%d/%Y", errors="coerce").notna()
             & frame["fund"].isin(ARK_FUNDS))
    frame = frame.loc[valid].copy()
    frame["normalized_ticker"] = frame["ticker"].map(normalize_ticker)
    frame["normalized_cusip"] = frame["cusip"].str.upper().str.replace(r"\s+", "", regex=True)
    # Missing or placeholder identifiers cannot establish an identity match.
    frame.loc[~frame.normalized_cusip.str.fullmatch(r"[A-Z0-9*@#]{9}"), "normalized_cusip"] = ""
    return frame


def compare(early: pd.DataFrame, current: pd.DataFrame) -> dict:
    tickers = set(current.normalized_ticker) - {""}
    cusips = set(current.normalized_cusip) - {""}
    early = early.copy()
    early["cusip_match"] = early.normalized_cusip.ne("") & early.normalized_cusip.isin(cusips)
    early["ticker_match"] = early.normalized_ticker.isin(tickers)
    early["matched"] = early.cusip_match | early.ticker_match
    early["security_key"] = early.apply(lambda r: "CUSIP:" + r.normalized_cusip if r.normalized_cusip else "TICKER:" + r.normalized_ticker, axis=1)
    security_matches = early.groupby("security_key").matched.any()
    early_cusips = set(early.normalized_cusip) - {""}
    absent = early[~early.matched].drop_duplicates("security_key")
    renamed = early[early.cusip_match & ~early.ticker_match].drop_duplicates("security_key")
    return {
        "early_snapshot_date": DATE,
        "early_holding_dates": sorted(early.date.unique().tolist()),
        "comparison_holding_dates": sorted(current.date.unique().tolist()),
        "source": f"https://github.com/{REPOSITORY}/tree/main/data/holdings/2021/{DATE}",
        "funds": ARK_FUNDS,
        "early_positions": len(early),
        "early_unique_tickers": early.normalized_ticker.nunique(),
        "early_unique_cusips": len(early_cusips),
        "early_unique_security_keys": len(security_matches),
        "matched_positions": int(early.matched.sum()),
        "absent_positions": int((~early.matched).sum()),
        "matched_security_keys": int(security_matches.sum()),
        "absent_security_keys": int((~security_matches).sum()),
        "cusips_present_in_comparison": len(early_cusips & cusips),
        "cusips_absent_in_comparison": len(early_cusips - cusips),
        "cusip_matched_with_different_ticker": renamed[["ticker", "company", "cusip"]].to_dict("records"),
        "absent_securities": absent[["ticker", "company", "cusip"]].to_dict("records"),
        "method": "Overlap means matching normalized ticker OR exact valid CUSIP across any of the six funds. Unique security keys use CUSIP where available and normalized ticker otherwise.",
        "limitations": "Security-level snapshot comparison, not proven company exits. Ticker reuse can create false matches; CUSIP changes or both identifiers changing can create false absences. Share classes, funds and other securities may be counted separately. Absence does not imply company failure, and does not date any sale.",
    }


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    frames = []
    # Exactly one fetch per missing fund; no retries, search, or expanded crawl.
    for fund in ARK_FUNDS:
        name = f"{fund}_Holdings_{DATE}.csv"
        path = CACHE / name
        if not path.exists():
            endpoint = f"repos/{REPOSITORY}/contents/data/holdings/2021/{DATE}/{name}?ref=main"
            result = subprocess.run(["gh", "api", endpoint, "-H", "Accept: application/vnd.github.raw+json"], check=True, capture_output=True)
            path.write_bytes(result.stdout)
        frame = load_positions(path, fund)
        if frame.empty:
            raise ValueError(f"No usable holdings in {name}")
        frames.append(frame)
    early = pd.concat(frames, ignore_index=True)
    current = load_positions(UNIVERSE_DIR / "ark_holdings_raw.csv")
    result = compare(early, current)
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "survivorship.json").write_text(json.dumps(result, indent=2))
    note = (f"# Holdings overlap\n\n"
            f"The six ARK funds held {result['early_positions']} ticker-bearing positions on "
            f"{', '.join(result['early_holding_dates'])}, representing {result['early_unique_cusips']} distinct valid CUSIPs "
            f"and {result['early_unique_security_keys']} security identifiers. Relative to holdings dated "
            f"{', '.join(result['comparison_holding_dates'])}, {result['matched_security_keys']} security identifiers match "
            f"and {result['absent_security_keys']} are absent using ticker-or-CUSIP matching. At the fund-position level, "
            f"{result['matched_positions']} match and {result['absent_positions']} are absent.\n\n"
            f"Exact CUSIP comparison: {result['cusips_present_in_comparison']} remain present and "
            f"{result['cusips_absent_in_comparison']} are absent. "
            f"{len(result['cusip_matched_with_different_ticker'])} security identifiers match by CUSIP despite a different ticker.\n\n"
            f"{result['method']} {result['limitations']}\n\n"
            f"Source: [ARK historical holdings]({result['source']}).\n")
    (OUTPUT_DIR / "survivorship.md").write_text(note)
    print(note)


if __name__ == "__main__":
    main()
