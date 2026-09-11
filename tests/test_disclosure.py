"""Language-versus-composition decomposition of filing-to-filing tone changes."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.disclosure import (  # noqa: E402
    build_panel, decompose, decomposition_summary, outcome_by_transition,
    switch_events,
)


def sections(rows):
    """Build a sections frame from (ticker, form, date, mode, risk_w, body_w, s_risk, s_body)."""
    records = []
    for ticker, form, date, mode, risk_w, body_w, s_risk, s_body in rows:
        total = risk_w + body_w
        share = risk_w / total
        records.append({
            "accession": f"{ticker}-{date}", "cik": ticker.lower().zfill(10),
            "ticker": ticker, "form": form, "filing_date": date,
            "quarter": str(pd.Period(pd.Timestamp(date), freq="Q")),
            "group": "ARK", "risk_found": True, "risk_mode": mode,
            "n_words": total, "risk_words": risk_w, "body_words": body_w,
            "risk_share": share,
            "Negative_prop_total": share * s_risk + (1 - share) * s_body,
            "Negative_prop_risk": s_risk, "Negative_prop_body": s_body,
            "Uncertainty_prop_total": share * s_risk + (1 - share) * s_body,
            "Uncertainty_prop_risk": s_risk, "Uncertainty_prop_body": s_body,
        })
    return pd.DataFrame(records)


class DecompositionTests(unittest.TestCase):

    def test_the_two_parts_add_up_exactly(self):
        rng = np.random.default_rng(0)
        rows = []
        for i in range(40):
            rows.append(("AAA", "10-Q", f"202{i // 4 % 5}-{i % 4 * 3 + 1:02d}-15", "full",
                         int(rng.integers(50, 40000)), int(rng.integers(5000, 60000)),
                         float(rng.uniform(0.005, 0.05)), float(rng.uniform(0.005, 0.05))))
        panel = decompose(build_panel(sections(rows)), "Negative")
        self.assertGreater(len(panel), 30)
        np.testing.assert_allclose(panel.Negative_residual, 0, atol=1e-15)

    def test_dropping_the_risk_section_shows_up_as_composition(self):
        # Identical writing in both parts; only the amount of risk text changes.
        rows = [("AAA", "10-Q", "2024-05-01", "full", 40000, 20000, 0.04, 0.01),
                ("AAA", "10-Q", "2024-08-01", "reference_only", 60, 20000, 0.04, 0.01)]
        panel = decompose(build_panel(sections(rows)), "Negative")
        row = panel.iloc[0]
        self.assertEqual(row.transition, "to_reference")
        self.assertLess(row.Negative_change, 0)
        self.assertAlmostEqual(row.Negative_language, 0, places=12)
        self.assertAlmostEqual(row.Negative_composition, row.Negative_change, places=12)

    def test_rewriting_the_body_shows_up_as_language(self):
        # Same section lengths; the body itself becomes more negative.
        rows = [("AAA", "10-Q", "2024-05-01", "full", 10000, 20000, 0.04, 0.010),
                ("AAA", "10-Q", "2024-08-01", "full", 10000, 20000, 0.04, 0.020)]
        panel = decompose(build_panel(sections(rows)), "Negative")
        row = panel.iloc[0]
        self.assertEqual(row.transition, "stays_full")
        self.assertAlmostEqual(row.Negative_composition, 0, places=12)
        self.assertAlmostEqual(row.Negative_language, row.Negative_change, places=12)

    def test_first_filing_of_each_company_has_no_predecessor(self):
        rows = [("AAA", "10-Q", "2024-05-01", "full", 100, 900, 0.04, 0.01),
                ("AAA", "10-Q", "2024-08-01", "full", 100, 900, 0.04, 0.01),
                ("BBB", "10-Q", "2024-08-01", "full", 100, 900, 0.04, 0.01)]
        panel = build_panel(sections(rows))
        self.assertEqual(len(panel), 1)
        self.assertEqual(panel.iloc[0].ticker, "AAA")

    def test_forms_are_never_compared_with_each_other(self):
        rows = [("AAA", "10-K", "2024-02-01", "full", 40000, 20000, 0.04, 0.01),
                ("AAA", "10-Q", "2024-05-01", "reference_only", 60, 20000, 0.04, 0.01)]
        self.assertTrue(build_panel(sections(rows)).empty)

    def test_switch_events_keep_only_changes_of_mode(self):
        rows = [("AAA", "10-Q", "2024-02-01", "full", 40000, 20000, 0.04, 0.01),
                ("AAA", "10-Q", "2024-05-01", "reference_only", 60, 20000, 0.04, 0.01),
                ("AAA", "10-Q", "2024-08-01", "reference_only", 60, 20000, 0.04, 0.01),
                ("AAA", "10-Q", "2024-11-01", "full", 40000, 20000, 0.04, 0.01)]
        events = switch_events(build_panel(sections(rows)))
        self.assertEqual(events.transition.tolist(), ["to_reference", "to_full"])

    def test_outcome_summary_requires_the_market_column(self):
        panel = build_panel(sections(
            [("AAA", "10-Q", "2024-05-01", "full", 100, 900, 0.04, 0.01),
             ("AAA", "10-Q", "2024-08-01", "full", 100, 900, 0.04, 0.01)]))
        with self.assertRaises(KeyError):
            outcome_by_transition(panel, "event_excess")
        panel["event_excess"] = [0.02]
        self.assertEqual(outcome_by_transition(panel, "event_excess").iloc[0]["n"], 1)

    def test_summary_reports_a_negligible_residual(self):
        rng = np.random.default_rng(7)
        rows = [("AAA", "10-Q", f"2024-{i % 4 * 3 + 1:02d}-15",
                 "full" if i % 2 else "reference_only",
                 int(rng.integers(50, 40000)), int(rng.integers(5000, 60000)),
                 float(rng.uniform(0.005, 0.05)), float(rng.uniform(0.005, 0.05)))
                for i in range(8)]
        summary = decomposition_summary(build_panel(sections(rows)))
        self.assertTrue((summary.max_abs_residual_pp < 1e-12).all())


if __name__ == "__main__":
    unittest.main()


class FocalGuardTests(unittest.TestCase):
    """A dummy identified by a couple of rows must not return an estimate."""

    def frame(self, n_treated, n=200):
        rng = np.random.default_rng(3)
        data = pd.DataFrame({
            "y": rng.normal(size=n),
            "switched": [1.0] * n_treated + [0.0] * (n - n_treated),
            "log_size": rng.normal(size=n),
            "log_dollar_volume": rng.normal(size=n),
            "pre_excess": rng.normal(size=n),
            "cik": [f"{i % 20:010d}" for i in range(n)],
            "quarter": [f"202{i % 5}Q{i % 4 + 1}" for i in range(n)],
            "form": "10-Q",
        })
        return data

    def test_a_dummy_with_one_treated_row_is_refused(self):
        from src.regressions import CONTROLS, focal_test
        row = focal_test(self.frame(1), "y", "switched", CONTROLS, form=False)
        self.assertEqual(row["n_treated"], 1)
        self.assertTrue(np.isnan(row["coef"]))
        self.assertIn("smaller_group", row["status"])

    def test_a_dummy_with_enough_treated_rows_is_estimated(self):
        from src.regressions import CONTROLS, focal_test
        row = focal_test(self.frame(60), "y", "switched", CONTROLS, form=False)
        self.assertEqual(row["n_treated"], 60)
        self.assertEqual(row["status"], "ok")
        self.assertTrue(np.isfinite(row["coef"]))

    def test_a_continuous_regressor_reports_no_treated_count(self):
        from src.regressions import CONTROLS, focal_test
        data = self.frame(60)
        data["switched"] = np.random.default_rng(1).normal(size=len(data))
        row = focal_test(data, "y", "switched", CONTROLS, form=False)
        self.assertTrue(np.isnan(row["n_treated"]))
        self.assertEqual(row["status"], "ok")
