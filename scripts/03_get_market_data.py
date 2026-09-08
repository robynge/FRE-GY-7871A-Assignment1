"""Download prices, volume and point-in-time shares outstanding.

    python scripts/03_get_market_data.py

Writes:
    data/prices/prices.csv   daily auto-adjusted closes, tickers in columns
    data/prices/nominal_close.csv historical nominal closes for price/size controls
    data/prices/volume.csv   daily nominal share volume
    data/prices/shares.csv   dei:EntityCommonStockSharesOutstanding, per filing
    data/prices/shares_missing.csv explicit missing/ambiguous/request-failure log

On shares outstanding. The cover page of every 10-K and 10-Q states the share
count as of a date shortly before filing, and EDGAR exposes it as the XBRL fact
dei:EntityCommonStockSharesOutstanding. That is a point-in-time number: it was
printed on the document you are scoring. Market cap built from today's share
count and a 2021 price is a look-ahead bug, and it is the most common one in
assignments like this.

Some filings will have no such fact. Leave those rows missing rather than filling
them forward from a later filing, and report how many you lost.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import (  # noqa: E402
    ALT_BENCHMARK, BENCHMARK, INTERIM_DIR, PRICE_DIR, SAMPLE_END, SAMPLE_START,
    SEC_USER_AGENT, VIX_TICKER, FILING_DIR,
)
from src.edgar import EdgarClient  # noqa: E402
from src.market import download_market_data  # noqa: E402
from src.shares import extract_cover_shares

FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

# Use the cover-page point-in-time count only. Weighted averages measure a
# different quantity and cannot substitute for shares outstanding.
SHARE_TAGS = [("dei", "EntityCommonStockSharesOutstanding")]
PRICE_START = "2020-09-01"
PRICE_END = "2026-05-01"  # exclusive; supports +63 sessions after December filings


def select_cover_shares(facts: dict, accession: str, filing_date) -> dict:
    """Match the scored filing; choose its latest non-future instant fact.

    Conflicting values on the selected date are ambiguous and remain missing.
    Never select an arbitrary company-facts array element or a weighted average.
    """
    date = pd.to_datetime(filing_date, errors="coerce")
    absent = {"shares_outstanding": float("nan"), "shares_as_of": None,
              "shares_tag": "dei:EntityCommonStockSharesOutstanding"}
    if pd.isna(date):
        return dict(absent, shares_status="invalid_filing_date")
    values = facts.get("dei", {}).get("EntityCommonStockSharesOutstanding", {}).get("units", {}).get("shares", [])
    valid = []
    for fact in values:
        if fact.get("accn") != accession:
            continue
        end = pd.to_datetime(fact.get("end"), errors="coerce")
        filed = pd.to_datetime(fact.get("filed"), errors="coerce")
        value = pd.to_numeric(fact.get("val"), errors="coerce")
        if (pd.isna(end) or end > date or pd.isna(value) or value <= 0
                or (pd.notna(filed) and filed > date)
                or fact.get("start") is not None):
            continue
        valid.append((end, float(value)))
    if not valid:
        return dict(absent, shares_status="missing_cover_page_fact")
    latest = max(end for end, value in valid)
    latest_values = {value for end, value in valid if end == latest}
    if len(latest_values) != 1:
        return dict(absent, shares_as_of=latest.date().isoformat(),
                    shares_status="ambiguous_cover_page_fact")
    return {"shares_outstanding": latest_values.pop(),
            "shares_as_of": latest.date().isoformat(),
            "shares_tag": "dei:EntityCommonStockSharesOutstanding",
            "shares_status": "matched"}


def get_shares(client: EdgarClient, meta: pd.DataFrame) -> pd.DataFrame:
    """One audited result per scored accession, including missing share counts."""
    rows = []
    prior_path = PRICE_DIR / "shares.csv"
    prior = pd.read_csv(prior_path).set_index("accession").to_dict("index") if prior_path.exists() else {}
    for i, (cik, company) in enumerate(meta.groupby("cik", sort=True), 1):
        error = None
        try:
            facts = client._get(FACTS_URL.format(cik=str(cik).zfill(10))).json().get("facts", {})
        except Exception as exc:  # retain failures explicitly instead of losing rows
            facts, error = {}, type(exc).__name__
        for filing in company.drop_duplicates("accession").itertuples():
            result = select_cover_shares(facts, filing.accession, filing.filing_date)
            if error:
                result["shares_status"] = "companyfacts_request_failed:" + error
            if result["shares_status"] != "matched":
                cached = prior.get(filing.accession, {})
                raw_path = FILING_DIR / (filing.accession.replace("-", "") + ".html")
                if (str(cached.get("shares_status", "")).startswith("matched_html")
                        and cached.get("extraction_version") == 1
                        and pd.to_datetime(cached.get("shares_as_of")) <= pd.to_datetime(filing.filing_date)):
                    result = cached
                elif raw_path.exists():
                    direct = extract_cover_shares(raw_path.read_text(encoding="utf-8", errors="replace"), filing.filing_date)
                    if direct["shares_status"].startswith("matched"):
                        result = direct
                        result["extraction_version"] = 1
            rows.append({**result, "cik": str(cik).zfill(10), "accession": filing.accession})
        if i % 20 == 0:
            print(f"  company facts: {i} companies...")
    columns = ["cik", "accession", "shares_outstanding", "shares_as_of", "shares_tag", "shares_status", "share_classes", "extraction_version"]
    result = pd.DataFrame(rows, columns=columns)
    print("  shares status: " + str(result["shares_status"].value_counts().to_dict()))
    return result


def main() -> int:
    meta = pd.read_csv(INTERIM_DIR / "filings_meta.csv", dtype={"cik": str})
    tickers = sorted(meta["ticker"].unique()) + [BENCHMARK, ALT_BENCHMARK, VIX_TICKER]
    print(f"{len(set(tickers))} tickers, {SAMPLE_START} to {SAMPLE_END}")

    bundle = download_market_data(tickers, PRICE_START, PRICE_END)
    px = bundle["prices"]
    print(f"prices:  {px.shape[0]} days x {px.shape[1]} tickers -> {PRICE_DIR / 'prices.csv'}")
    missing = [t for t in tickers if t not in px.columns or px[t].notna().sum() == 0]
    if missing:
        print(f"  no price history for: {missing}")

    vol = bundle["volume"]
    print(f"nominal closes: {PRICE_DIR / 'nominal_close.csv'}")
    print(f"volume:  {vol.shape[0]} days x {vol.shape[1]} tickers -> {PRICE_DIR / 'volume.csv'}")

    if VIX_TICKER in px.columns:
        print(f"VIX:     {px[VIX_TICKER].notna().sum()} days, mean "
              f"{px[VIX_TICKER].mean():.1f} (for the Figure 1 overlay)")

    client = EdgarClient(SEC_USER_AGENT or None)
    shares = get_shares(client, meta)
    shares.to_csv(PRICE_DIR / "shares.csv", index=False)
    matched_rows = shares["shares_status"].str.startswith("matched")
    shares.loc[~matched_rows].to_csv(PRICE_DIR / "shares_missing.csv", index=False)
    matched = meta["accession"].isin(shares.loc[matched_rows, "accession"]).mean()
    print(f"shares:  {len(shares)} facts -> {PRICE_DIR / 'shares.csv'} "
          f"({matched:.1%} of filings matched)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
