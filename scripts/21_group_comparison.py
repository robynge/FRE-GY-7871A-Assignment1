"""ARK holdings against the Nasdaq-100, tested on one pooled sample.

Two separate regressions, one per group, cannot establish that the groups
differ: a significant slope in one and an insignificant slope in the other is
not a difference between them. Every comparison here is therefore a single
regression on the pooled sample with an index indicator, and the difference is
read off that indicator or its interaction with time.

The pooled sample is the disjoint one. Twenty-two companies are held by an ARK
fund and are also index constituents; leaving them in both arms would put the
same filings on both sides of the difference. They are reported separately.

Equation (1) weights come from the pooled run, so weighted scores are on one
scale across both groups. Reading them from the per-group runs would compare
scores fitted on different corpora.

    python scripts/21_group_comparison.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.analysis import MEASURES
from src.config import INTERIM_DIR, OUTPUT_DIR, UNIVERSE_DIR, holdings_group
from src.regressions import CONTROLS, focal_test

OUT = OUTPUT_DIR / "comparison"
SEASONS = ["season2", "season3", "season4"]


def labelled(frame: pd.DataFrame) -> pd.DataFrame:
    universe = pd.read_csv(UNIVERSE_DIR / "universe.csv", dtype={"cik": str})
    label = {str(r.cik).zfill(10): holdings_group(r.funds) for r in universe.itertuples()}
    out = frame.copy()
    out["group"] = out.cik.astype(str).str.zfill(10).map(label)
    out["is_ndx"] = out.group.eq("NDX").astype(float)
    return out


def levels(data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (group, form), part in data.groupby(["group", "form"]):
        for measure in MEASURES:
            scale = 100 if measure.endswith("prop") else 1
            series = part[measure] * scale
            rows.append({"group": group, "form": form, "measure": measure,
                         "n": len(part), "companies": part.cik.nunique(),
                         "mean": series.mean(), "sd": series.std(),
                         "median": series.median()})
    return pd.DataFrame(rows)


def differences(disjoint: pd.DataFrame) -> pd.DataFrame:
    """Index-versus-ARK difference in level, and in annual trend, per measure."""
    rows = []
    for form in ["All", "10-K", "10-Q"]:
        part = disjoint if form == "All" else disjoint[disjoint.form.eq(form)]
        for measure in MEASURES:
            level = focal_test(part, measure, "is_ndx", SEASONS,
                               effects=("quarter",), form=(form == "All"),
                               model="level_difference")
            level.update(sample=form, measure_name=measure, term="is_ndx")
            rows.append(level)

            with_interaction = part.copy()
            with_interaction["ndx_x_time"] = with_interaction.is_ndx * with_interaction.time_years
            trend = focal_test(with_interaction, measure, "ndx_x_time",
                               ["is_ndx", "time_years"] + SEASONS,
                               effects=("quarter",), form=(form == "All"),
                               model="trend_difference")
            trend.update(sample=form, measure_name=measure, term="ndx_x_time")
            rows.append(trend)
    return pd.DataFrame(rows)


def differences_excluding_item_1a(disjoint: pd.DataFrame, sections: pd.DataFrame) -> pd.DataFrame:
    """The same group difference, measured on the filing without its risk factors.

    Run on the filings where the section was located, so the whole-filing and
    section-excluded columns describe one sample rather than two.
    """
    pairs = [("Negative_prop_total", "Negative_prop_body"),
             ("Uncertainty_prop_total", "Uncertainty_prop_body")]
    columns = ["accession", "risk_found"] + [c for pair in pairs for c in pair]
    data = disjoint.merge(sections[columns], on="accession", how="inner")
    data = data[data.risk_found].copy()
    rows = []
    for form in ["All", "10-K", "10-Q"]:
        part = data if form == "All" else data[data.form.eq(form)]
        if part.empty:
            continue
        for whole, body in pairs:
            for measure in (whole, body):
                row = focal_test(part, measure, "is_ndx", SEASONS,
                                 effects=("quarter",), form=(form == "All"),
                                 model="level_difference")
                row.update(sample=form, measure_name=measure,
                           scope="whole filing" if measure == whole else "excluding Item 1A",
                           category=whole.split("_")[0])
                rows.append(row)
    return pd.DataFrame(rows)


def disclosure_practice(sections: pd.DataFrame) -> pd.DataFrame:
    """How often each group replaces its quarterly risk factors with a pointer."""
    quarterly = sections[sections.form.eq("10-Q") & sections.risk_found].copy()
    quarterly["refers"] = quarterly.risk_mode.isin(["reference_only", "omitted"])
    rows = []
    for group, part in quarterly.groupby("group"):
        rows.append({"group": group, "filings": len(part), "companies": part.cik.nunique(),
                     "refers_pct": 100 * part.refers.mean(),
                     "median_risk_words": part.risk_words.median()})
    return pd.DataFrame(rows)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    pooled = labelled(pd.read_csv(OUTPUT_DIR / "all" / "text_sample.csv", dtype={"cik": str}))
    disjoint = pooled[pooled.group.isin(["ARK", "NDX"])].copy()

    sections = pd.read_csv(INTERIM_DIR / "risk_sections.csv", dtype={"cik": str})
    sections = sections[sections.accession.isin(pooled.accession)].copy()  # same filings as Tables 2 to 4
    levels(pooled).to_csv(OUT / "levels.csv", index=False)
    differences(disjoint).to_csv(OUT / "differences.csv", index=False)
    differences_excluding_item_1a(disjoint, sections).to_csv(
        OUT / "differences_excluding_item_1a.csv", index=False)
    disclosure_practice(sections).to_csv(OUT / "disclosure_practice.csv", index=False)

    counts = pooled.groupby("group").agg(filings=("accession", "size"),
                                         companies=("cik", "nunique"))
    counts.to_csv(OUT / "counts.csv")
    print(counts.to_string())
    print(f"\nPooled {len(pooled)} filings; disjoint test sample {len(disjoint)} "
          f"filings, {disjoint.cik.nunique()} companies")
    print(f"Wrote comparison exhibits to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
