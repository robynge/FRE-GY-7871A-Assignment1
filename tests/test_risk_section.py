"""Item 1A location and disclosure-mode classification.

Every fixture below is shortened from wording that occurs in this corpus. The
two boundary cases were both real defects: a contents line was accepted as a
heading, and the word "signature" inside bank risk factors ended the section
hundreds of thousands of characters early.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.parse import tokenize  # noqa: E402
from src.risk_section import (  # noqa: E402
    classify_disclosure_mode, describe_filing, extract_risk_section,
    find_risk_section,
)

CONTENTS = ("Part II - Other Information 42 Item 1. Legal Proceedings 43 "
            "Item 1A. Risk Factors 43 Item 2. Unregistered Sales of Equity Securities 43 ")


class RiskSectionTests(unittest.TestCase):

    def test_contents_line_is_not_the_heading(self):
        text = (CONTENTS + "These examples are not exhaustive. ITEM 1A. RISK FACTORS "
                "Investing in our Class A common stock involves a high degree of risk. "
                "Item 2. Unregistered Sales of Equity Securities None.")
        section = extract_risk_section(text)
        self.assertTrue(section.startswith("Investing in our Class A"))
        self.assertNotIn("Legal Proceedings", section)

    def test_reference_back_to_the_annual_report_does_not_hide_the_heading(self):
        # The pointer that follows the heading names Item 1A again, one clause later.
        text = (CONTENTS + "These examples are not exhaustive. ITEM 1A. RISK FACTORS "
                "There have been no material changes to the risk factors disclosed in "
                "Part I, Item 1A. “Risk Factors” of our Annual Report on Form 10-K. "
                "Item 2. Unregistered Sales of Equity Securities None.")
        self.assertEqual(classify_disclosure_mode(extract_risk_section(text)), "reference_only")

    def test_cross_reference_is_not_treated_as_the_heading(self):
        text = ("For more information, see Part II, Item 1A. Risk Factors of this "
                "Quarterly Report on Form 10-Q. We hold liquid assets.")
        self.assertIsNone(find_risk_section(text))
        self.assertEqual(extract_risk_section(text), "")

    def test_the_word_signature_does_not_end_the_section(self):
        body = ("closures of Silicon Valley Bank, Signature Bank, and First Republic Bank "
                "reduced deposits. Borrowers may challenge the electronic signature on "
                "loan documents. ") * 3
        text = ("Item 1A. Risk Factors Investing in our common stock involves risk. " + body
                + "Item 1B. Unresolved Staff Comments None.")
        section = extract_risk_section(text)
        self.assertIn("First Republic", section)
        self.assertIn("electronic signature", section)
        self.assertNotIn("Unresolved Staff Comments", section)

    def test_citation_of_a_later_item_does_not_end_the_section(self):
        text = ("Item 1A. Risk Factors We face litigation described in Item 3. Legal "
                "Proceedings of this report, which could harm us. "
                "Item 3. Legal Proceedings See Note 12.")
        section = extract_risk_section(text)
        self.assertIn("which could harm us", section)
        self.assertNotIn("See Note 12", section)

    def test_partial_update_is_distinguished_from_a_bare_pointer(self):
        pointer = ("Item 1A. Risk Factors There have been no material changes to our risk "
                   "factors previously disclosed in our Annual Report. Item 5. Other Information")
        partial = ("Item 1A. Risk Factors There are no material changes from the risk factors "
                   "set forth in our 2024 Annual Report on Form 10-K except as set forth below. "
                   "Our banking licence may be withdrawn. Item 5. Other Information")
        self.assertEqual(classify_disclosure_mode(extract_risk_section(pointer)), "reference_only")
        self.assertEqual(classify_disclosure_mode(extract_risk_section(partial)), "partial_update")

    def test_full_restatement_is_labelled_full(self):
        restated = ("Our revenue may decline if customers reduce spending. Competition "
                    "in our markets is intense and may increase. ") * 60  # ~1,000 words
        text = ("Item 1A. Risk Factors You should carefully consider the risks described "
                "below. " + restated + "Item 2. Unregistered Sales of Equity Securities")
        section = extract_risk_section(text)
        self.assertGreater(len(tokenize(section)), 400)
        self.assertEqual(classify_disclosure_mode(section), "full")

    def test_a_long_section_that_claims_no_change_is_a_partial_update(self):
        # Claiming nothing changed and then printing a thousand words is an update.
        updates = "Our banking licence may be withdrawn by the regulator. " * 130
        text = ("Item 1A. Risk Factors There have been no material changes to the risk "
                "factors disclosed in our Annual Report. " + updates
                + "Item 5. Other Information")
        section = extract_risk_section(text)
        self.assertGreater(len(tokenize(section)), 400)
        self.assertEqual(classify_disclosure_mode(section), "partial_update")

    def test_a_pointer_without_a_no_change_claim_is_still_a_reference(self):
        text = ("Item 1A. Risk Factors Our operations and financial results are subject "
                "to various risks and uncertainties, including those described in Part I, "
                "Item 1A of our Annual Report on Form 10-K for the year ended December 31, "
                "2025, which could adversely affect our business. "
                "Item 2. Unregistered Sales of Equity Securities")
        self.assertEqual(classify_disclosure_mode(extract_risk_section(text)), "reference_only")

    def test_a_section_that_says_nothing_is_omitted_not_full(self):
        text = ("Item 1A. Risk Factors Not applicable. "
                "Item 2. Unregistered Sales of Equity Securities")
        self.assertEqual(classify_disclosure_mode(extract_risk_section(text)), "omitted")

    def test_a_cross_reference_index_is_not_the_heading(self):
        # Intel closes its 10-K with an index of form items and page ranges.
        text = ("Cross-Reference Index Item 1. Business Pages 3 - 20 "
                "Item 1A. Risk Factors Pages 48 - 62 "
                "Item 1B. Unresolved Staff Comments None Item 2. Properties Page 63")
        self.assertIsNone(find_risk_section(text))

    def test_absent_section_reports_not_found_without_raising(self):
        result = describe_filing("This quarterly report contains no risk factor heading at all.")
        self.assertFalse(result["risk_found"])
        self.assertEqual(result["risk_mode"], "not_found")
        self.assertEqual(result["risk_words"], 0)
        self.assertGreater(result["body_words"], 0)

    def test_body_and_section_words_partition_the_filing(self):
        text = ("Alpha beta gamma delta. Item 1A. Risk Factors You should consider the "
                "risks described below carefully. Item 5. Other Information None here.")
        result = describe_filing(text)
        self.assertGreater(result["risk_words"], 0)
        self.assertGreater(result["body_words"], 0)

        self.assertEqual(result["risk_words"] + result["body_words"], len(tokenize(text)))


if __name__ == "__main__":
    unittest.main()
