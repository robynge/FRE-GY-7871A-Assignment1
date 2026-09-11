"""What a change of disclosure practice does to the tone measures, and to the stock.

Three questions, in order:

1. How common is it? Shares of quarterly reports in each disclosure mode, by
   group and year.
2. What does it do to the measures? The language / composition split, reported
   next to the change in the filing excluding Item 1A, which is the statistic
   free of the pointer-density problem.
3. Does the market react, and does removing the section improve the measure?
   Filing-window excess return and following-quarter volatility on switch
   indicators, and the volatility test rerun with the risk-section-excluded
   uncertainty measure in place of the whole-document one.

Switches are not randomly assigned. A company that stops restating its risk
factors may differ in other ways, so these are conditional associations with
firm and quarter effects, not the effect of the disclosure choice itself.

    python scripts/20_disclosure_outcomes.py --run all
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import INTERIM_DIR, OUTPUT_DIR
from src.disclosure import (
    CATEGORIES, build_panel, decompose, decomposition_summary, mode_counts,
    outcome_by_transition, switch_events,
)
from src.regressions import CONTROLS, focal_test

PANEL_COLUMNS = [
    "accession", "group", "risk_mode", "prev_mode", "transition", "risk_share",
    "prev_risk_share", "risk_words", "prev_risk_words", "risk_words_change",
    "quarters_apart",
] + [f"{c}_prop_{p}" for c in CATEGORIES for p in ("total", "risk", "body")] \
  + [f"{c}_{p}" for c in CATEGORIES
     for p in ("change", "body_change", "language", "composition")]


def merged_sections(sample: pd.DataFrame, sections: pd.DataFrame) -> pd.DataFrame:
    """Market sample plus this filing's section split, for every located filing.

    The whole-filing and excluding-Item-1A measures need no predecessor, so
    they are estimated on every filing with a located section rather than on
    the transition panel, which drops each company's first filing.
    """
    columns = ["accession", "group", "risk_mode", "risk_share", "risk_words"] + \
              [f"{c}_prop_{p}" for c in CATEGORIES for p in ("total", "risk", "body")]
    located = sections[sections.risk_found]
    out = sample.merge(located[columns], on="accession", how="inner", validate="one_to_one")
    out["prints_risk_factors"] = out.risk_mode.isin(["full", "partial_update"]).astype(float)
    return out


def merged(sample: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    """Market sample plus this filing's section split and transition."""
    columns = [c for c in PANEL_COLUMNS if c in panel.columns]
    out = sample.merge(panel[columns], on="accession", how="inner", validate="one_to_one")
    out["to_reference"] = out.transition.eq("to_reference").astype(float)
    out["to_full"] = out.transition.eq("to_full").astype(float)
    out["prints_risk_factors"] = out.risk_mode.isin(["full", "partial_update"]).astype(float)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", default="all", help="outputs/<run> holding the market samples")
    args = parser.parse_args()
    run = OUTPUT_DIR / args.run
    out = run / "disclosure"
    out.mkdir(parents=True, exist_ok=True)

    sections = pd.read_csv(INTERIM_DIR / "risk_sections.csv", dtype={"cik": str})
    # Everything written under outputs/<run> describes that run's text sample:
    # the filings behind Tables 2 to 4, one per company per quarter.
    text_sample = pd.read_csv(run / "text_sample.csv", dtype={"cik": str})
    sections = sections[sections.accession.isin(text_sample.accession)].copy()
    panel = build_panel(sections)
    for category in CATEGORIES:
        panel = decompose(panel, category)
    quarterly = panel[panel.form.eq("10-Q")]

    mode_counts(sections).to_csv(out / "mode_shares.csv")
    decomposition_summary(quarterly).to_csv(out / "decomposition.csv", index=False)
    by_group = pd.concat(
        [decomposition_summary(g).assign(group=name)
         for name, g in quarterly.groupby("group")], ignore_index=True)
    by_group.to_csv(out / "decomposition_by_group.csv", index=False)

    volatility = merged(pd.read_csv(run / "volatility_sample.csv"), panel)
    returns = merged(pd.read_csv(run / "return_sample.csv"), panel)
    volatility_m = merged_sections(pd.read_csv(run / "volatility_sample.csv"), sections)
    returns_m = merged_sections(pd.read_csv(run / "return_sample.csv"), sections)
    switch_events(panel).to_csv(out / "switch_events.csv", index=False)

    descriptive = []
    for name, sample, outcome in [("filing_return", returns, "event_excess"),
                                  ("post_volatility", volatility, "post_vol"),
                                  ("volatility_change", volatility, "vol_change")]:
        if outcome == "vol_change":
            sample = sample.assign(vol_change=sample.post_vol - sample.pre_vol)
        descriptive.append(outcome_by_transition(sample, outcome).assign(outcome=name))
    pd.concat(descriptive, ignore_index=True).to_csv(out / "switch_outcomes.csv", index=False)

    rows = []
    for label in ["All", "10-K", "10-Q"]:
        pooled = label == "All"
        vol = volatility if pooled else volatility[volatility.form.eq(label)]
        ret = returns if pooled else returns[returns.form.eq(label)]
        for focal in ["to_reference", "to_full", "prints_risk_factors"]:
            rows.append({**focal_test(ret, "event_excess", focal, CONTROLS + ["pre_vol"],
                                      form=pooled, model="filing_return"), "sample": label})
            rows.append({**focal_test(vol, "post_vol", focal, CONTROLS + ["pre_vol"],
                                      form=pooled, model="volatility_with_prevol"),
                         "sample": label})
        # Does excluding the risk section leave a measure that predicts better?
        # Estimated on every located filing, not only those with a predecessor.
        vol_m = volatility_m if pooled else volatility_m[volatility_m.form.eq(label)]
        ret_m = returns_m if pooled else returns_m[returns_m.form.eq(label)]
        for measure in ["Uncertainty_prop_total", "Uncertainty_prop_body"]:
            for pre in [False, True]:
                rows.append({**focal_test(
                    vol_m, "post_vol", measure, CONTROLS + (["pre_vol"] if pre else []),
                    form=pooled,
                    model="volatility_with_prevol" if pre else "volatility_without_prevol"),
                    "sample": label})
        for measure in ["Negative_prop_total", "Negative_prop_body"]:
            rows.append({**focal_test(ret_m, "event_excess", measure, CONTROLS + ["pre_vol"],
                                      form=pooled, model="filing_return"), "sample": label})
    estimates = pd.DataFrame(rows)
    # A coefficient per unit of a word share is not readable; scale to one
    # standard deviation of the regressor in its own estimation sample.
    spreads = {}
    for measure in ["Uncertainty_prop_total", "Uncertainty_prop_body"]:
        spreads[measure] = volatility_m[measure].std()
    for measure in ["Negative_prop_total", "Negative_prop_body"]:
        spreads[measure] = returns_m[measure].std()
    estimates["effect_1sd"] = estimates.coef * estimates.measure.map(spreads).fillna(1.0)
    estimates["mde80_1sd"] = estimates.mde80 * estimates.measure.map(spreads).fillna(1.0)
    estimates.to_csv(out / "switch_regressions.csv", index=False)

    print(f"Wrote disclosure exhibits to {out}")
    print(f"\nPaired filings: {len(panel)} ({len(quarterly)} quarterly), "
          f"{panel.cik.nunique()} companies")
    print(f"Switches: {int(quarterly.transition.eq('to_reference').sum())} to reference, "
          f"{int(quarterly.transition.eq('to_full').sum())} to full")
    print(f"Matched to market outcomes: {len(returns)} return, {len(volatility)} volatility")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
