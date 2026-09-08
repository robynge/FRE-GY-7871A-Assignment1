"""Regression tests for company identity and sample attrition bookkeeping."""
import importlib.util
from pathlib import Path
import unittest
import pandas as pd

spec = importlib.util.spec_from_file_location("universe", Path(__file__).resolve().parents[1] / "scripts/01_build_universe.py")
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)


class UniverseTests(unittest.TestCase):
    def holdings(self, pairs):
        return pd.DataFrame([dict(ticker=t, company=n, fund="ARKK", date="09/04/2026") for t,n in pairs])

    def test_security_exclusions_and_unresolved_are_preserved(self):
        x = self.holdings([("ARKY", "ARK ETF"), ("MYSTERY", "UNIDENTIFIED COMPANY"),
                           ("4689", "LY CORP"), ("", "CASH"), ("SPCX", "SPACE EXPLORATION TECHN-CL A")])
        c = u.build_candidates(x, {"ARKY": "1"})
        self.assertEqual(c.position_count.sum(), len(x))
        status = c.set_index("raw_ticker").status.to_dict()
        self.assertEqual(status["ARKY"], "non_company_security")
        self.assertEqual(status["MYSTERY"], "unresolved_identifier")
        self.assertEqual(status["SPCX"], "unresolved_identifier")
        self.assertEqual(status["4689"], "foreign_local_listing")

    def test_foreign_ticker_collisions_do_not_assign_us_ciks(self):
        x = self.holdings([("AIR", "AIRBUS SE"), ("DSY", "DISCOVERY LTD"), ("DSY FP", "DASSAULT SYSTEMES SE")])
        c = u.build_candidates(x, {"AIR": "1750", "DSY": "99"})
        self.assertTrue(c.cik.eq("").all())
        self.assertEqual(len(c), 3)
        self.assertEqual(u.clean_ticker("RKLB UQ"), "RKLB")
        self.assertIsNone(u.clean_ticker("DSY FP"))
        self.assertIsNone(u.clean_ticker(float("nan")))

    def test_share_classes_query_once_and_no_filings_remain_visible(self):
        x = self.holdings([("GOOG", "ALPHABET CL C"), ("GOOGL", "ALPHABET CL A"), ("NEW", "NEW CORP")])
        c = u.build_candidates(x, {"GOOG": "1", "GOOGL": "1", "NEW": "2"})
        class Client:
            calls = []
            def list_filings(self, cik, *args):
                self.calls.append(cik)
                return pd.DataFrame([dict(form="10-K", company="ALPHABET")]) if cik.endswith("1") else pd.DataFrame()
        client = Client()
        result = u.build_universe(c, client)
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(len(result), 2)
        self.assertEqual(result.set_index("ticker").loc["GOOG", "tickers"], "GOOG|GOOGL")
        self.assertEqual(result.set_index("ticker").loc["NEW", "status"], "no_10x_filings")

    def test_report_history_distinguishes_foreign_and_recent_issuers(self):
        foreign = pd.DataFrame([dict(form="20-F", filingDate="2024-03-01")])
        self.assertEqual(u.classify_no10x(foreign)[0], "foreign_reporting_forms")
        recent = pd.DataFrame([dict(form="S-1", filingDate="2024-03-01"),
                               dict(form="10-Q", filingDate="2026-05-08")])
        category, reason = u.classify_no10x(recent)
        self.assertEqual(category, "first_10x_after_sample")
        self.assertIn("2026-05-08", reason)
        self.assertEqual(u.classify_no10x(pd.DataFrame())[0], "no_report_evidence")

    def test_comparison_excludes_untickered_and_footer_rows(self):
        x = self.holdings([("TSLA", "TESLA"), ("", "CASH"), ("BAD", "FOOTER")])
        x.loc[2, "date"] = "Legal disclaimer"
        self.assertEqual(u.comparison_positions(x).ticker.tolist(), ["TSLA"])

    def test_failed_lookup_is_not_reported_as_no_filings(self):
        class Client:
            def list_filings(self, *args):
                raise RuntimeError("unavailable")
        c = u.build_candidates(self.holdings([("ABC", "ABC CORP")]), {"ABC":"3"})
        self.assertEqual(u.build_universe(c, Client()).iloc[0].status, "lookup_error")

if __name__ == "__main__":
    unittest.main()
