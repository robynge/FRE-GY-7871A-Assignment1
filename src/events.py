"""Trading-day alignment and strictly observed event windows."""
import numpy as np
import pandas as pd


def align_day_zero(filing_date, acceptance_datetime, calendar):
    calendar = pd.DatetimeIndex(calendar).normalize().sort_values().unique()
    filing_date = pd.Timestamp(filing_date).normalize().tz_localize(None)
    accepted = pd.to_datetime(acceptance_datetime, utc=True, errors="coerce")
    if pd.isna(accepted):
        return pd.NaT, False
    eastern = accepted.tz_convert("America/New_York")
    accepted_date = eastern.normalize().tz_localize(None)
    if eastern.hour >= 16:
        accepted_date += pd.Timedelta(days=1)
    target = max(filing_date, accepted_date)
    idx = calendar.searchsorted(target)
    naive = calendar.searchsorted(filing_date)
    if idx >= len(calendar):
        return pd.NaT, False
    return calendar[idx], bool(naive < len(calendar) and calendar[idx] != calendar[naive])


def event_variables(filing, adjusted, nominal, volume, benchmark, shares=np.nan, calendar=None):
    calendar = pd.DatetimeIndex(calendar if calendar is not None else benchmark.index)
    day0, moved = align_day_zero(filing["filing_date"], filing["acceptance_datetime"], calendar)
    out = {"day0": day0, "day0_moved": moved, "valid_day0_price": False,
           "valid_history": False, "complete_windows": False}
    if pd.isna(day0):
        return out
    p = adjusted.reindex(calendar)
    nominal = nominal.reindex(calendar)
    volume = volume.reindex(calendar)
    r = p.pct_change(fill_method=None)
    b = benchmark.reindex(calendar)
    t = calendar.get_loc(day0)
    if t < 1:
        return out
    price = nominal.iloc[t-1]
    out["price_minus1"] = price
    out["valid_day0_price"] = bool(pd.notna(price) and price >= 3)
    if t < 61:
        return out
    # Require all 60 preceding returns; at least 60 among the 63 following
    # sessions, then separately demand every observation used by each window.
    out["valid_history"] = bool(r.iloc[t-60:t].notna().sum() >= 60 and
                                 r.iloc[t+1:t+64].notna().sum() >= 60)
    if t + 63 >= len(calendar):
        return out
    pre = r.iloc[t-60:t-5]
    post = r.iloc[t+4:t+64]
    event = r.iloc[t:t+4]
    benchmark_ok = b.iloc[t-61:t+64].notna().all()
    out["complete_windows"] = bool(pre.notna().all() and post.notna().all() and
                                    event.notna().all() and len(post) == 60 and benchmark_ok)
    if not out["complete_windows"]:
        return out
    dv = (nominal * volume).iloc[t-60:t-5]
    log_dv = np.log(dv.mean()) if dv.notna().all() and (dv > 0).all() else np.nan
    out.update({
        "pre_vol": pre.std(ddof=1) * np.sqrt(252),
        "post_vol": post.std(ddof=1) * np.sqrt(252),
        "event_excess": p.iloc[t+3]/p.iloc[t-1] - b.iloc[t+3]/b.iloc[t-1],
        "pre_excess": p.iloc[t-6]/p.iloc[t-61] - b.iloc[t-6]/b.iloc[t-61],
        "log_dollar_volume": log_dv,
        "log_size": np.log(price * shares) if pd.notna(shares) and shares > 0 and price > 0 else np.nan,
        "shares_outstanding": shares,
    })
    return out
