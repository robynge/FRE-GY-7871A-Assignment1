"""Offline coverage for tagged cover-page share extraction."""
import math
import pytest
from src.shares import extract_cover_shares


def context(cid, when="2025-01-20", member=None, axis="us-gaap:StatementClassOfStockAxis"):
    dim = f'<xbrli:segment><xbrldi:explicitMember dimension="{axis}">{member}</xbrldi:explicitMember></xbrli:segment>' if member else ""
    return f'<xbrli:context id="{cid}"><xbrli:entity>{dim}</xbrli:entity><xbrli:period><xbrli:instant>{when}</xbrli:instant></xbrli:period></xbrli:context>'


def fact(cid, value="1,234", extra="", name="dei:EntityCommonStockSharesOutstanding"):
    return f'<ix:nonFraction name="{name}" contextRef="{cid}" {extra}>{value}</ix:nonFraction>'


def extract(html):
    return extract_cover_shares(html, "2025-02-01")


def test_single_aggregate_and_repeated_context_are_not_double_counted():
    got = extract(context("a") + fact("a") + fact("a"))
    assert got["shares_outstanding"] == 1234
    assert got["shares_as_of"] == "2025-01-20"
    assert got["shares_status"] == "matched_html_aggregate"
    assert got["share_classes"] == []


def test_sum_stock_classes_deduplicating_equivalent_contexts():
    html = context("a", member="us-gaap:CommonClassAMember") + context("a2", member="us-gaap:CommonClassAMember")
    html += context("b", member="us-gaap:CommonClassBMember") + fact("a", "100") + fact("a2", "100") + fact("b", "25")
    got = extract(html)
    assert got["shares_outstanding"] == 125
    assert got["shares_status"] == "matched_html_classes"
    assert len(got["share_classes"]) == 2


def test_aggregate_preferred_to_class_sum():
    got = extract(context("all") + context("a", member="ClassA") + fact("all", "500") + fact("a", "100"))
    assert got["shares_outstanding"] == 500
    assert got["shares_status"] == "matched_html_aggregate"


@pytest.mark.parametrize("value,extra,expected", [
    ("1,234.5", 'format="ixt:num-dot-decimal" scale="3"', 1234500),
    ("1.234,5", 'format="ixt:num-comma-decimal" scale="3"', 1234500),
    ("1\u00a0234", 'format="ixt:num-space-dot"', 1234),
    ("123400", 'scale="-2"', 1234),
])
def test_numeric_transformations(value, extra, expected):
    assert extract(context("a") + fact("a", value, extra))["shares_outstanding"] == expected


@pytest.mark.parametrize("value,extra", [("123", 'sign="-"'), ("123", 'xsi:nil="true"'),
    ("1,23", ''), ("bad", ''), ("123", 'format="ixt:unsupported"'), ("1.23", '')])
def test_invalid_values_never_become_counts(value, extra):
    assert math.isnan(extract(context("a") + fact("a", value, extra))["shares_outstanding"])


def test_latest_nonfuture_instant_is_selected():
    html = context("old", "2024-12-31") + fact("old", "100")
    html += context("new") + fact("new", "200") + context("future", "2025-02-02") + fact("future", "300")
    assert extract(html)["shares_outstanding"] == 200


def test_stock_classes_must_have_same_latest_date():
    html = context("a", "2025-01-20", "ClassA") + fact("a", "100")
    html += context("b", "2025-01-19", "ClassB") + fact("b", "20")
    got = extract(html)
    assert math.isnan(got["shares_outstanding"])
    assert got["shares_status"] == "inconsistent_class_dates"


@pytest.mark.parametrize("member", [None, "ClassA"])
def test_conflicting_same_date_facts_are_missing(member):
    got = extract(context("a", member=member) + fact("a", "100") + fact("a", "101"))
    assert math.isnan(got["shares_outstanding"])
    assert got["shares_status"] == "ambiguous_cover_page_fact"


def test_other_dimensions_rejected_without_partial_class_sum():
    html = context("a", member="ClassA") + fact("a", "100")
    html += context("segment", member="US", axis="acme:GeographyAxis") + fact("segment", "20")
    got = extract(html)
    assert math.isnan(got["shares_outstanding"])
    assert got["shares_status"] == "unsupported_or_missing_context"


def test_untagged_numbers_and_weighted_averages_never_used():
    html = '<p>Shares outstanding: 123456</p>' + context("a")
    html += fact("a", "200", name="us-gaap:WeightedAverageNumberOfSharesOutstandingBasic")
    assert math.isnan(extract(html)["shares_outstanding"])


def test_invalid_date_and_duration_context_rejected():
    assert extract_cover_shares('', 'not a date')["shares_status"] == "invalid_filing_date"
    html = context("a").replace('<xbrli:instant>2025-01-20</xbrli:instant>', '<xbrli:startDate>2024-01-01</xbrli:startDate><xbrli:endDate>2024-12-31</xbrli:endDate>') + fact("a")
    assert math.isnan(extract(html)["shares_outstanding"])
