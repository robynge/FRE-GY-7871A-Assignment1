"""Append the Nasdaq-100 constituents to the ARK holdings snapshot.

The universe builder reads one holdings file. The ARK snapshot comes from
00_get_holdings.py; the index list (rank, company, ticker, weight) was saved by
hand from slickcharts.com for the same date, since no script downloads it. Index
rows carry the fund label NDX and no share or value columns.

    python scripts/00_combine_holdings.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import UNIVERSE_DIR


def combine(ark: pd.DataFrame, index: pd.DataFrame) -> pd.DataFrame:
    rows = pd.DataFrame({
        "date": ark["date"].iloc[0], "fund": "NDX", "company": index["company"],
        "ticker": index["ticker"], "cusip": "", "shares": "", "market value ($)": "",
        "weight (%)": index["weight"]})
    return pd.concat([ark, rows[ark.columns]], ignore_index=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ark", type=Path, default=UNIVERSE_DIR / "ark_holdings_raw.csv")
    ap.add_argument("--index", type=Path, default=UNIVERSE_DIR / "ndx_holdings_raw.csv")
    ap.add_argument("--out", type=Path, default=UNIVERSE_DIR / "combined_holdings_raw.csv")
    args = ap.parse_args()
    out = combine(pd.read_csv(args.ark, dtype=str, keep_default_na=False),
                  pd.read_csv(args.index, dtype=str, keep_default_na=False))
    out.to_csv(args.out, index=False)
    print(f"Wrote {args.out}: {len(out)} positions, {out.fund.eq('NDX').sum()} index constituents")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
