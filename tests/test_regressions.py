"""Regression design and inference checks on a known synthetic panel."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm, t as student_t

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.regressions import outcome_tests, trend_tests


@pytest.fixture
def panel():
    rng = np.random.default_rng(138)
    rows = []
    for firm in range(12):
        for q in range(20):
            pre = rng.uniform(.1, .5)
            negative = .03 + .002 * q / 4 + rng.normal(0, .008)
            uncertainty = .02 + .001 * q / 4 + rng.normal(0, .006)
            row = dict(cik=str(firm), quarter=f"{2021 + q // 4}Q{q % 4 + 1}",
                       form="10-K" if (firm + q) % 4 == 0 else "10-Q",
                       time_years=q / 4, Negative_prop=negative,
                       Negative_tfidf=negative * 2 + rng.normal(0, .001),
                       Uncertainty_prop=uncertainty,
                       Uncertainty_tfidf=uncertainty * 3 + rng.normal(0, .001),
                       pre_vol=pre, post_vol=.2 + .5 * pre + uncertainty + rng.normal(0, .06),
                       event_excess=-2 * negative + rng.normal(0, .03),
                       log_size=rng.normal(22, 1), log_dollar_volume=rng.normal(17, 1),
                       pre_excess=rng.normal(0, .1))
            row.update({f"season{s}": int(q % 4 + 1 == s) for s in range(1, 5)})
            rows.append(row)
    return pd.DataFrame(rows)


def test_trends_are_identifiable_and_two_way_uses_min_clusters(panel):
    result = trend_tests(panel)
    assert len(result) == 16
    assert set(result.status) == {"ok"}
    two_way = result[result.inference.eq("firm_quarter_cluster")]
    assert (two_way.df_inference == 11).all()
    assert (two_way.fixed_effects == "cik").all()
    assert (two_way.firm_clusters == 12).all()
    assert (two_way.quarter_clusters == 20).all()
    first = two_way.iloc[0]
    assert first.p == pytest.approx(2 * student_t.sf(abs(first.t), 11))
    assert first.mde80 == pytest.approx((student_t.ppf(.975, 11) + norm.ppf(.8)) * first.se)
    aggregate = result[result.model.eq("aggregate_trend")]
    assert (aggregate.n == 20).all()
    assert set(aggregate.inference) == {"OLS", "HAC4"}
    shuffled = trend_tests(panel.sample(frac=1, random_state=42))
    np.testing.assert_allclose(aggregate.coef, shuffled[shuffled.model.eq("aggregate_trend")].coef)
    np.testing.assert_allclose(aggregate.se, shuffled[shuffled.model.eq("aggregate_trend")].se)


def test_prevol_comparison_holds_sample_fixed(panel):
    panel.loc[0, "pre_vol"] = np.nan
    result = outcome_tests(panel)
    assert len(result) == 12
    assert (result.n == 239).all()
    vol = result[result.outcome.eq("post_vol")]
    assert set(vol.measure) == {"Uncertainty_prop", "Uncertainty_tfidf"}
    assert (vol.groupby(["measure", "inference"]).n.nunique() == 1).all()
    assert (result.fixed_effects == "cik,quarter").all()
    assert result[result.model.eq("filing_return")].controls.str.contains("pre_vol").all()
    assert set(result[result.model.eq("filing_return")].measure) == {"Negative_prop", "Negative_tfidf"}


def test_single_form_omits_constant_form_dummy(panel):
    panel["form"] = "10-Q"
    result = pd.concat([trend_tests(panel), outcome_tests(panel)])
    assert not result.form_control.any()
    assert not result.status.eq("rank_deficient").any()


def test_insufficient_panel_is_reported_without_crashing(panel):
    result = trend_tests(panel.iloc[:1])
    assert (result.status == "insufficient_data").all()
    assert result.coef.isna().all()


def test_stable_firm_filing_season_keeps_identified_time_slope():
    rows = []
    for firm in range(12):
        season = firm % 4 + 1
        for year in range(5):
            time = year + (season - 1) / 4
            tone = .03 + .001 * firm + (.002 + .0001 * (firm - 5.5)) * time
            row = dict(cik=str(firm), quarter=f"{2021 + year}Q{season}",
                       form="10-K", time_years=time)
            row.update({f"season{s}": int(s == season) for s in [2, 3, 4]})
            row.update({name: tone for name in ["Negative_prop", "Uncertainty_prop",
                        "Negative_tfidf", "Uncertainty_tfidf"]})
            rows.append(row)
    result = trend_tests(pd.DataFrame(rows))
    within = result[result.model.eq("within_firm_trend")]
    assert set(within.status) == {"ok"}
    assert (within.design_rank == 13).all()
    assert within.dropped_nuisance.str.len().gt(0).all()
    np.testing.assert_allclose(within.coef, .002, atol=1e-12)


def test_focal_absorbed_by_firm_effects_is_not_identified(panel):
    panel["time_years"] = panel.cik.astype(float)
    result = trend_tests(panel)
    within = result[result.model.eq("within_firm_trend")]
    assert set(within.status) == {"focal_not_identified"}
    assert within.coef.isna().all()
