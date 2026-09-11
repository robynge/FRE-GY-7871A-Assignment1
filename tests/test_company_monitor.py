import pandas as pd
import pytest

from src.company_monitor import build_monitor


def filing(period, filed, negative=20, uncertainty=10, form="10-Q", acceptance=None, accession=None):
    return {"ticker": "TEST", "cik": "123", "company": "Test Company", "form": form,
            "filing_date": filed, "report_date": period,
            "acceptance_datetime": acceptance or filed + " 14:00:00+00:00",
            "accession": accession or filed + form, "doc_url": "https://www.sec.gov/example",
            "n_words": 2000, "Negative_prop": negative / 2000, "Uncertainty_prop": uncertainty / 2000}


def monitor(rows):
    universe = pd.DataFrame([{"ticker": "TEST", "tickers": "TEST", "cik": "123", "funds": "ARKK"}])
    return build_monitor(pd.DataFrame(rows), universe, "2026-09-09")


def test_anniversary_never_crosses_form_and_accepts_fiscal_week_shift():
    data = monitor([filing("2025-03-29", "2025-05-01", form="10-K"),
                    filing("2025-03-30", "2025-05-02"), filing("2026-03-31", "2026-05-01", negative=15)])
    latest = data["quarterly"][0]
    prior = data["history"][latest["latest_matched_history_index"]]
    assert prior["form"] == "10-Q"
    assert latest["latest_match_gap_days"] == 1
    assert latest["latest_delta_neg_pp"] == pytest.approx(-0.25)


@pytest.mark.parametrize("prior_date,matched", [("2025-02-14", True), ("2025-02-13", False), ("2025-05-15", True), ("2025-05-16", False)])
def test_anniversary_tolerance_is_inclusive(prior_date, matched):
    data = monitor([filing(prior_date, "2025-06-01"), filing("2026-03-31", "2026-05-01")])
    assert (data["quarterly"][0]["latest_matched_history_index"] is not None) == matched


def test_unpublished_prior_period_not_used():
    data = monitor([filing("2025-03-31", "2026-05-02"), filing("2026-03-31", "2026-05-01")])
    assert data["quarterly"][0]["latest_matched_history_index"] is None


def test_same_day_prior_requires_earlier_acceptance():
    first = filing("2025-03-31", "2026-05-01", acceptance="2026-05-01 18:00:00+00:00", accession="a")
    current = filing("2026-03-31", "2026-05-01", acceptance="2026-05-01 17:00:00+00:00", accession="b")
    assert monitor([first, current])["quarterly"][0]["latest_matched_history_index"] is None
    first["acceptance_datetime"] = "2026-05-01 16:00:00+00:00"
    assert monitor([first, current])["quarterly"][0]["latest_matched_history_index"] is not None


def test_latest_three_require_three_complete_pairs_and_zero_is_not_missing():
    rows = [filing("2024-09-30", "2024-11-01"), filing("2025-03-31", "2025-05-01"),
            filing("2025-06-30", "2025-08-01"), filing("2025-09-30", "2025-11-01"),
            filing("2026-03-31", "2026-05-01"), filing("2026-06-30", "2026-08-01")]
    full = monitor(rows)["quarterly"][0]
    assert full["trend_eligible"] and full["ranking_eligible"]
    assert full["recent_three_mean_delta_neg_pp"] == 0
    assert full["recent_three_neg_unchanged"] == 3
    assert full["rank_negative_improvement"] is None
    assert full["rank_uncertainty_rise"] is None
    missing = monitor(rows[1:])["quarterly"][0]
    assert missing["matched_latest_three"] == 2
    assert not missing["trend_eligible"]
    assert missing["recent_three_mean_delta_neg_pp"] is None


def test_earliest_original_is_canonical_and_counts_recover():
    first = filing("2025-03-31", "2025-05-01", negative=0)
    later = filing("2025-03-31", "2025-05-02", negative=10)
    data = monitor([later, first])
    assert len(data["history"]) == 1
    assert data["history"][0]["Negative_tokens"] == 0
    assert data["metadata"]["excluded_filings"] == 1
    assert not data["quarterly"][0]["fresh"]
    assert data["quarterly"][0]["rank_latest_uncertainty"] is None


def test_invalid_score_precision_rejected():
    row = filing("2026-06-30", "2026-08-01")
    row["Negative_prop"] = 0.01001
    with pytest.raises(ValueError, match="integer token counts"):
        monitor([row])


def test_noncurrent_company_is_excluded_even_if_cached_scores_exist():
    kept = filing("2026-06-30", "2026-08-01")
    sold = dict(kept, cik="999", ticker="SOLD", accession="sold")
    result = monitor([kept, sold])
    assert {r["ticker"] for r in result["history"]} == {"TEST"}
    assert result["metadata"]["exclusion_counts"]["Not held in the selected current company universe"] == 1
