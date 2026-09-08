"""Offline integration checks for acquisition integrity and filter ordering."""
import numpy as np
import pandas as pd
import pytest

from src import analysis


@pytest.fixture
def sample_files(tmp_path, monkeypatch):
    paths = {}
    for name in ("INTERIM_DIR", "PRICE_DIR", "UNIVERSE_DIR", "OUTPUT_DIR"):
        paths[name] = tmp_path / name.lower()
        paths[name].mkdir()
        monkeypatch.setattr(analysis, name, paths[name])
    monkeypatch.setattr(analysis, "ROOT", tmp_path)
    return paths


def filing(accession, cik="0000000001", ticker="AAA", when="2024-01-16", status="parsed", form="10-K"):
    return {"accession": accession, "cik": cik, "ticker": ticker, "filing_date": when,
            "acceptance_datetime": when + "T15:00:00Z", "status": status,
            "form": form, "n_words": 2500}


def write_inputs(paths, records, expected):
    pd.DataFrame(records).to_csv(paths["INTERIM_DIR"] / "filings_manifest.csv", index=False)
    pd.DataFrame([
        {"cik": cik, "status": "domestic_filer", "n_10k": count, "n_10q": 0}
        for cik, count in expected.items()
    ]).to_csv(paths["UNIVERSE_DIR"] / "universe.csv", index=False)


def write_market(paths, records, low_price_date=None):
    # Actual event calculations run against a deterministic exchange calendar.
    calendar = analysis.mcal.get_calendar("NYSE").valid_days("2020-09-01", "2026-04-30").tz_localize(None)
    tickers = sorted({r["ticker"] for r in records}) + ["SPY"]
    levels = 10 * np.exp(.0002 * np.arange(len(calendar)))
    prices = pd.DataFrame({ticker: levels for ticker in tickers}, index=calendar)
    nominal = prices.copy()
    if low_price_date:
        nominal.loc[pd.Timestamp(low_price_date), "AAA"] = 2.0
    prices.to_csv(paths["PRICE_DIR"] / "prices.csv")
    nominal.to_csv(paths["PRICE_DIR"] / "nominal_close.csv")
    pd.DataFrame(1000., index=calendar, columns=tickers).to_csv(paths["PRICE_DIR"] / "volume.csv")
    pd.DataFrame([
        {"accession": r["accession"], "cik": r["cik"], "shares_outstanding": 1000000}
        for r in records
    ]).to_csv(paths["PRICE_DIR"] / "shares.csv", index=False)


def no_market_read(*args, **kwargs):
    pytest.fail("An incomplete acquisition must be rejected before market analysis")


def test_missing_original_filing_blocks_partial_corpus(sample_files, monkeypatch):
    write_inputs(sample_files, [filing("kept")], {"0000000001": 2})
    monkeypatch.setattr(analysis, "_prices", no_market_read)
    with pytest.raises(RuntimeError, match="all expected original filings"):
        analysis.construct_sample()


@pytest.mark.parametrize("status", ["download_failed", "not_attempted", "listing_failed"])
def test_acquisition_failure_cannot_be_treated_as_parse_exclusion(sample_files, monkeypatch, status):
    records = [filing("kept"), filing("failed", status=status)]
    write_inputs(sample_files, records, {"0000000001": 2})
    monkeypatch.setattr(analysis, "_prices", no_market_read)
    with pytest.raises(RuntimeError, match="Acquisition is incomplete"):
        analysis.construct_sample()


def test_later_eligible_filing_does_not_replace_earlier_ineligible_filing(sample_files):
    # AAA's first filing fails the $3 test; its later filing would pass.
    # BBB provides a valid observation so the final sample remains nonempty.
    records = [filing("aaa-early"), filing("aaa-later", when="2024-02-15"),
               filing("bbb", cik="0000000002", ticker="BBB", when="2024-03-15")]
    write_inputs(sample_files, records, {"0000000001": 2, "0000000002": 1})
    write_market(sample_files, records, low_price_date="2024-01-12")
    sample, waterfall, audit = analysis.construct_sample()
    assert sample.accession.tolist() == ["bbb"]
    assert audit["final_companies"] == 1
    by_filter = waterfall.set_index("filter")
    assert by_filter.loc["Earliest company filing each quarter", "removed"] == 1
    assert by_filter.loc["Usable day 0 and prior price at least $3", "removed"] == 1
    assert by_filter.loc["Usable day 0 and prior price at least $3", "remaining"] == 1
    # Prove the later filing is independently eligible, rather than merely
    # assuming why it disappeared from the first construction.
    replacement = records[1:]
    write_inputs(sample_files, replacement, {"0000000001": 1, "0000000002": 1})
    later_sample, _, _ = analysis.construct_sample()
    assert set(later_sample.accession) == {"aaa-later", "bbb"}


def test_completed_acquisition_allows_parse_failure_and_amendment_exclusions(sample_files):
    records = [filing("kept"), filing("parse-error", status="parse_failed"),
               filing("amended", status="amendment", form="10-K/A")]
    write_inputs(sample_files, records, {"0000000001": 2})
    write_market(sample_files, records)
    sample, waterfall, audit = analysis.construct_sample()
    assert sample.accession.tolist() == ["kept"]
    assert audit["expected_original_filings"] == 2
    assert audit["parse_failures"] == 1
    assert audit["amendments"] == 1
    assert waterfall.loc[waterfall["filter"].eq("Remove amendments and parse failures"), "removed"].item() == 2
