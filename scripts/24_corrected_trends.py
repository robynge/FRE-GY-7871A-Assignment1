"""Does the language trend survive when the risk-factor section is taken out?

Table 4 measures tone over the whole filing. If the risk-factor section is
growing as a share of the document, a rising word share can be that and nothing
else. The same within-company trend specification is therefore run twice per
measure: once on the whole filing, once on the filing excluding Item 1A, on the
identical set of filings so that the two slopes are comparable.

Filings where no Item 1A heading was located are dropped from both, since a
sample that differs between the two columns would make the comparison useless.

    python scripts/24_corrected_trends.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import INTERIM_DIR, OUTPUT_DIR
from src.regressions import focal_test

SEASONS = ["season2", "season3", "season4"]
RUNS = ["course_ark_2021_2025", "ark", "ndx", "all"]
PAIRS = [("Negative_prop_total", "Negative_prop_body"),
         ("Uncertainty_prop_total", "Uncertainty_prop_body")]


def trend(data: pd.DataFrame, measure: str, pooled: bool) -> dict:
    return focal_test(data, measure, "time_years", SEASONS, effects=("cik",),
                      form=pooled, model="within_firm_trend")


def main() -> int:
    sections = pd.read_csv(INTERIM_DIR / "risk_sections.csv", dtype={"cik": str})
    columns = ["accession", "risk_found", "risk_share"] + [c for pair in PAIRS for c in pair]
    rows = []
    for run in RUNS:
        path = OUTPUT_DIR / run / "text_sample.csv"
        if not path.exists():
            continue
        sample = pd.read_csv(path, dtype={"cik": str})
        merged = sample.merge(sections[columns], on="accession", how="inner")
        merged = merged[merged.risk_found].copy()
        for label in ["All", "10-K", "10-Q"]:
            pooled = label == "All"
            part = merged if pooled else merged[merged.form.eq(label)]
            if part.empty:
                continue
            for whole, body in PAIRS:
                for measure in (whole, body):
                    row = trend(part, measure, pooled)
                    row.update(run=run, sample=label,
                               scope="whole filing" if measure == whole else "excluding Item 1A",
                               category=whole.split("_")[0])
                    rows.append(row)
            # Is the section itself growing? That is the mechanism, if any.
            share = trend(part, "risk_share", pooled)
            share.update(run=run, sample=label, scope="Item 1A share of words",
                         category="Section length")
            rows.append(share)

    out = pd.DataFrame(rows)
    target = OUTPUT_DIR / "comparison" / "corrected_trends.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(target, index=False)

    view = out[out.status.eq("ok")].copy()
    view["slope_pp_per_year"] = 100 * view.coef
    print(view[["run", "sample", "category", "scope", "n", "slope_pp_per_year", "p"]]
          .round(4).to_string(index=False))
    print(f"\nWrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
