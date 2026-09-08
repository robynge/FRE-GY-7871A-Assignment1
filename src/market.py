"""Yahoo market histories with separate return and nominal-price series.

Yahoo Close and Volume are split-adjusted. Adj Close additionally adjusts for
cash distributions. Reverse *subsequent* splits for historical nominal prices
and share volumes; retain actions through retrieval date, even after sample end.
See https://github.com/ranaroussi/yfinance/issues/1749 and
https://help.yahoo.com/kb/SLN28256.html for price conventions. Volume
convention is also exercised by yfinance/tests/test_price_repair.py upstream.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .config import PRICE_DIR

FILES = {
    "prices": "prices.csv", "nominal_close": "nominal_close.csv",
    "volume": "volume.csv", "split_adjusted_close": "split_adjusted_close.csv",
    "split_adjusted_volume": "split_adjusted_volume.csv",
    "dividends": "dividends.csv", "splits": "stock_splits.csv",
}


def reconstruct_nominal(close, volume, splits):
    """Undo future splits, excluding the current day's already-effective split."""
    ratios = splits.reindex_like(close).fillna(0).replace(0, 1)
    factor = ratios.iloc[::-1].cumprod().iloc[::-1] / ratios
    return close * factor, volume / factor


def download_market_data(tickers, start, end, cache_dir=None):
    """Return a bundle for [start, end); actions include dates through retrieval.

    A manifest records request coverage, retrieval date, and ticker coverage.
    Legacy caches without a manifest are refreshed. Missing histories remain
    missing; no price or volume is carried across a gap.
    """
    import yfinance as yf

    directory = Path(cache_dir or PRICE_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    tickers = sorted(set(tickers))
    if not tickers or pd.Timestamp(start) >= pd.Timestamp(end):
        raise ValueError("Nonempty tickers and start < end are required")
    today = pd.Timestamp.now(tz="America/New_York").date().isoformat()
    manifest = directory / "market_coverage.json"
    if manifest.exists() and all((directory / f).exists() for f in FILES.values()):
        info = json.loads(manifest.read_text())
        if (info.get("schema") == 2 and info.get("retrieved_date") == today
                and info["start"] <= start and info["end"] >= end
                and set(tickers) <= set(info["tickers"])):
            bundle = {k: pd.read_csv(directory / f, index_col=0, parse_dates=True)
                      for k, f in FILES.items()}
            if all(set(tickers) <= set(frame.columns) for frame in bundle.values()):
                return {k: frame.reindex(columns=tickers) if k in {"dividends", "splits"}
                        else frame.loc[(frame.index >= start) & (frame.index < end), tickers]
                        for k, frame in bundle.items()}

    # Download beyond sample end: a later split also changes Yahoo's old closes.
    raw = yf.download(tickers=tickers, start=start, end=None, auto_adjust=False,
                      actions=True, progress=False, threads=True)
    if raw is None or raw.empty:
        raise RuntimeError("Yahoo returned no market history; cache not updated")
    def field(name, optional=False):
        if isinstance(raw.columns, pd.MultiIndex):
            if name not in raw.columns.get_level_values(0):
                if optional:
                    return pd.DataFrame(0.0, index=raw.index, columns=tickers)
                raise ValueError(f"Yahoo response lacks {name}")
            frame = raw[name].copy()
        else:
            if len(tickers) != 1:
                raise ValueError("Unlabelled multi-ticker Yahoo response")
            if name not in raw and optional:
                return pd.DataFrame(0.0, index=raw.index, columns=tickers)
            frame = raw[[name]].rename(columns={name: tickers[0]})
        frame.index = pd.DatetimeIndex(frame.index).tz_localize(None)
        return frame.reindex(columns=tickers).sort_index()

    close, volume = field("Close"), field("Volume")
    splits = field("Stock Splits")
    nominal, nominal_volume = reconstruct_nominal(close, volume, splits)
    bundle = dict(prices=field("Adj Close"), nominal_close=nominal,
                  volume=nominal_volume, split_adjusted_close=close,
                  split_adjusted_volume=volume, dividends=field("Dividends"), splits=splits)
    for key, frame in bundle.items():
        if key not in {"splits", "dividends"}:
            bundle[key] = frame.loc[(frame.index >= start) & (frame.index < end)]
        bundle[key].to_csv(directory / FILES[key])
    manifest.write_text(json.dumps({"schema": 2, "start": start, "end": end,
        "tickers": tickers, "retrieved_date": today,
        "actual_first": str(close.index.min()), "actual_last": str(close.index.max()),
        "ticker_coverage": {t: {"first": str(close[t].first_valid_index()),
            "last": str(close[t].last_valid_index()), "observations": int(close[t].notna().sum())}
            for t in tickers},
        "missing_tickers": [t for t in tickers if close[t].notna().sum() == 0]}, indent=2))
    return bundle


def download_prices(tickers, start, end, cache_path=None):
    """Daily distribution- and split-adjusted close for total-return windows."""
    path = Path(cache_path or PRICE_DIR / "prices.csv")
    result = download_market_data(tickers, start, end, path.parent)["prices"]
    if path.name != FILES["prices"]:
        result.to_csv(path)
    return result


def download_volume(tickers, start, end, cache_path=None):
    """Historical nominal share volume; multiply by nominal_close for dollars."""
    path = Path(cache_path or PRICE_DIR / "volume.csv")
    result = download_market_data(tickers, start, end, path.parent)["volume"]
    if path.name != FILES["volume"]:
        result.to_csv(path)
    return result
