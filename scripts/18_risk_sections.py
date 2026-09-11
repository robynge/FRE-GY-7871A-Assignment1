"""Split every filing into its risk-factor section and the rest of the document.

A filer who replaces the risk factors with a pointer to the annual report prints
fewer uncertainty words without having become more certain. Measuring the two
parts separately is what makes that distinguishable from a change in tone.

Proportional scores only. Equation (1) weights are fitted across a corpus and a
weighted sum over part of a document is not the part of the weighted sum over
all of it, so the section decomposition is defined on word shares, where the
parts do add up.

Writes data/interim/risk_sections.csv, one row per parsed filing.
"""
from __future__ import annotations

import gzip
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import INTERIM_DIR, ROOT, UNIVERSE_DIR, holdings_group
from src.lexicons import load_all
from src.parse import tokenize
from src.risk_section import (
    REFERENCE_ONLY_MAX_WORDS, classify_disclosure_mode, find_risk_section,
)

OUT_PATH = INTERIM_DIR / "risk_sections.csv"
CATEGORIES = ["Negative", "Uncertainty"]


def shares(tokens: list[str], lexicons: dict[str, set]) -> dict[str, float]:
    """Category word share of these tokens; NaN when there are no tokens."""
    if not tokens:
        return {c: float("nan") for c in CATEGORIES}
    counts = Counter(tokens)
    total = len(tokens)
    return {c: sum(n for w, n in counts.items() if w in lexicons[c]) / total
            for c in CATEGORIES}


def main() -> int:
    lexicons = {c: v for c, v in load_all().items() if c in CATEGORIES}
    meta = pd.read_csv(INTERIM_DIR / "filings_meta.csv", dtype={"cik": str})
    universe = pd.read_csv(UNIVERSE_DIR / "universe.csv", dtype={"cik": str})
    group = {str(r.cik).zfill(10): holdings_group(r.funds) for r in universe.itertuples()}

    rows = []
    for position, filing in enumerate(meta.itertuples(), 1):
        with gzip.open(ROOT / filing.text_path, "rt", encoding="utf-8") as handle:
            text = handle.read()
        span = find_risk_section(text)
        if span:
            section_text, body_text = text[span[0]:span[1]], text[:span[0]] + " " + text[span[1]:]
        else:
            section_text, body_text = "", text
        section, body = tokenize(section_text), tokenize(body_text)
        whole = section + body
        section_shares, body_shares, whole_shares = (
            shares(section, lexicons), shares(body, lexicons), shares(whole, lexicons))
        rows.append({
            "accession": filing.accession, "cik": str(filing.cik).zfill(10),
            "ticker": filing.ticker, "form": filing.form,
            "filing_date": filing.filing_date,
            "quarter": str(pd.Period(pd.Timestamp(filing.filing_date), freq="Q")),
            "group": group.get(str(filing.cik).zfill(10), "UNKNOWN"),
            "risk_found": span is not None,
            "risk_mode": classify_disclosure_mode(section_text),
            "n_words": len(whole), "risk_words": len(section), "body_words": len(body),
            "risk_share": len(section) / len(whole) if whole else float("nan"),
            **{f"{c}_prop_total": whole_shares[c] for c in CATEGORIES},
            **{f"{c}_prop_risk": section_shares[c] for c in CATEGORIES},
            **{f"{c}_prop_body": body_shares[c] for c in CATEGORIES},
        })
        if position % 250 == 0:
            print(f"  {position}/{len(meta)} filings split", flush=True)

    out = pd.DataFrame(rows)
    out.to_csv(OUT_PATH, index=False)
    print(f"\nWrote {len(out)} rows to {OUT_PATH}")
    print(f"Reference-only word ceiling: {REFERENCE_ONLY_MAX_WORDS} words")
    print("\nDisclosure mode by form:")
    print(pd.crosstab(out.form, out.risk_mode).to_string())
    print("\nSection words by mode:")
    print(out.groupby("risk_mode").risk_words.describe()[["count", "min", "50%", "max"]].to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
