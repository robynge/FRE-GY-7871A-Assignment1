"""Economic regression guards for nominal prices and point-in-time shares."""
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.market import download_market_data, reconstruct_nominal

spec = importlib.util.spec_from_file_location("get_market_script", ROOT / "scripts/03_get_market_data.py")
script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(script)


def test_split_reconstruction_preserves_dollar_turnover():
    index = pd.to_datetime(["2025-12-01", "2025-12-02", "2026-06-01"])
    close = pd.DataFrame({"A": [2., 2.5, 3.]}, index=index)
    volume = pd.DataFrame({"A": [100., 200., 300.]}, index=index)
    splits = pd.DataFrame({"A": [0., 2., 3.]}, index=index)
    nominal, nominal_volume = reconstruct_nominal(close, volume, splits)
    assert nominal["A"].tolist() == [12., 7.5, 3.]
    assert nominal_volume.loc[index[0], "A"] == pytest.approx(100 / 6)
    pd.testing.assert_frame_equal(nominal * nominal_volume, close * volume)


def test_download_extends_actions_and_invalidates_short_cache(tmp_path, monkeypatch):
    calls = []
    dates = pd.to_datetime(["2025-12-01", "2026-04-30", "2026-06-01"])
    def download(**kwargs):
        calls.append(kwargs)
        return pd.DataFrame({"Close": [2., 3., 4.], "Adj Close": [1.8, 2.9, 4.],
            "Volume": [100., 200., 300.], "Stock Splits": [0., 0., 2.],
            "Dividends": [0., 0.1, 0.]}, index=dates)
    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(download=download))
    first = download_market_data(["A"], "2025-12-01", "2026-03-31", tmp_path)
    assert first["nominal_close"].iloc[0, 0] == 4.
    assert first["prices"].iloc[0, 0] == 1.8
    assert calls[0]["end"] is None
    assert calls[0]["actions"] and not calls[0]["auto_adjust"]
    assert len(first["splits"]) == 3
    download_market_data(["A"], "2025-12-01", "2026-03-31", tmp_path)
    assert len(calls) == 1
    later = download_market_data(["A"], "2025-12-01", "2026-05-01", tmp_path)
    assert len(calls) == 2 and len(later["prices"]) == 2
    (tmp_path / "stock_splits.csv").unlink()
    download_market_data(["A"], "2025-12-01", "2026-05-01", tmp_path)
    assert len(calls) == 3


def test_reverse_split_and_missing_prices():
    close = pd.DataFrame({"A": [10., None, 10.]})
    volume = pd.DataFrame({"A": [100., None, 100.]})
    splits = pd.DataFrame({"A": [0., 0., 0.1]})
    nominal, vol = reconstruct_nominal(close, volume, splits)
    assert nominal.iloc[0, 0] == 1.
    assert vol.iloc[0, 0] == 1000.
    assert pd.isna(nominal.iloc[1, 0])


def facts(values):
    return {"dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": values}}}}


def test_shares_latest_date_not_array_order_or_future():
    values = [dict(accn="a", end="2025-02-01", val=200),
              dict(accn="a", end="2025-01-01", val=100),
              dict(accn="a", end="2025-04-01", val=300),
              dict(accn="b", end="2025-02-15", val=999)]
    for vals in [values, values[::-1]]:
        selected = script.select_cover_shares(facts(vals), "a", "2025-03-01")
        assert selected["shares_outstanding"] == 200
        assert selected["shares_as_of"] == "2025-02-01"


def test_shares_ambiguity_and_no_weighted_average_fallback():
    values = [dict(accn="a", end="2025-02-01", val=n) for n in (100, 200)]
    assert script.select_cover_shares(facts(values), "a", "2025-03-01")["shares_status"] == "ambiguous_cover_page_fact"
    weighted = {"us-gaap": {"WeightedAverageNumberOfDilutedSharesOutstanding": {"units": {"shares": values}}}}
    result = script.select_cover_shares(weighted, "a", "2025-03-01")
    assert pd.isna(result["shares_outstanding"])


def test_shares_failures_preserve_filing_rows():
    class FailedClient:
        def _get(self, url):
            raise RuntimeError("unavailable")
    meta = pd.DataFrame({"cik": ["1"], "accession": ["a"], "filing_date": ["2025-01-01"]})
    result = script.get_shares(FailedClient(), meta)
    assert result["accession"].tolist() == ["a"]
    assert result["shares_status"].iloc[0] == "companyfacts_request_failed:RuntimeError"
