"""Trading-day alignment and independently observed event windows."""
from functools import lru_cache
import numpy as np
import pandas as pd
import pandas_market_calendars as mcal


@lru_cache(maxsize=16)
def _session_closes(year):
    schedule = mcal.get_calendar('NYSE').schedule(f'{year}-01-01', f'{year}-12-31')
    return schedule.market_close


def align_day_zero(filing_date, acceptance_datetime, calendar):
    calendar = pd.DatetimeIndex(calendar).normalize().sort_values().unique()
    filing_date = pd.Timestamp(filing_date).normalize().tz_localize(None)
    accepted = pd.to_datetime(acceptance_datetime, utc=True, errors='coerce')
    if pd.isna(accepted):
        return pd.NaT, False
    eastern = accepted.tz_convert('America/New_York')
    accepted_date = eastern.normalize().tz_localize(None)
    close = _session_closes(eastern.year).get(accepted_date)
    if close is not None and accepted >= close:
        accepted_date += pd.Timedelta(days=1)
    target = max(filing_date, accepted_date)
    idx, naive = calendar.searchsorted(target), calendar.searchsorted(filing_date)
    if idx >= len(calendar):
        return pd.NaT, False
    return calendar[idx], bool(naive < len(calendar) and calendar[idx] != calendar[naive])


def event_variables(filing, adjusted, nominal, volume, benchmark, shares=np.nan, calendar=None):
    calendar = pd.DatetimeIndex(calendar if calendar is not None else benchmark.index)
    day0, moved = align_day_zero(filing['filing_date'], filing['acceptance_datetime'], calendar)
    out = dict(day0=day0, day0_moved=moved, valid_day0_price=False,
               valid_history=False, valid_pre_history=False, complete_windows=False,
               complete_return=False, complete_volatility=False, shares_outstanding=shares,
               pre_vol=np.nan, post_vol=np.nan, event_excess=np.nan, pre_excess=np.nan,
               log_size=np.nan, log_dollar_volume=np.nan)
    if pd.isna(day0):
        return out
    p, nominal, volume, b = [s.reindex(calendar) for s in (adjusted, nominal, volume, benchmark)]
    r = p.pct_change(fill_method=None)
    t = calendar.get_loc(day0)
    if t < 1:
        return out
    price = nominal.iloc[t-1]
    out['price_minus1'] = price
    out['valid_day0_price'] = bool(pd.notna(price) and price >= 3)
    if pd.notna(shares) and shares > 0 and price > 0:
        out['log_size'] = np.log(price * shares)
    if t < 61:
        return out
    out['valid_pre_history'] = bool(r.iloc[t-60:t].notna().sum() == 60)
    out['valid_history'] = bool(out['valid_pre_history'] and r.iloc[t+1:t+64].notna().sum() >= 60)
    pre = r.iloc[t-60:t-5]
    pre_benchmark_ok = b.iloc[t-61:t-5].notna().all()
    if len(pre) == 55 and pre.notna().all():
        out['pre_vol'] = pre.std(ddof=1) * np.sqrt(252)
    if pre_benchmark_ok and p.iloc[[t-61,t-6]].notna().all():
        out['pre_excess'] = p.iloc[t-6]/p.iloc[t-61] - b.iloc[t-6]/b.iloc[t-61]
    dv = (nominal * volume).iloc[t-60:t-5]
    if len(dv) == 55 and dv.notna().all() and (dv > 0).all():
        out['log_dollar_volume'] = np.log(dv.mean())
    if t + 3 < len(calendar):
        event_ok = r.iloc[t:t+4].notna().all() and b.iloc[t-1:t+4].notna().all()
        out['complete_return'] = bool(event_ok)
        if event_ok:
            out['event_excess'] = p.iloc[t+3]/p.iloc[t-1] - b.iloc[t+3]/b.iloc[t-1]
    if t + 63 < len(calendar):
        post = r.iloc[t+4:t+64]
        out['complete_volatility'] = bool(pre.notna().all() and len(post) == 60 and post.notna().all())
        if out['complete_volatility']:
            out['post_vol'] = post.std(ddof=1) * np.sqrt(252)
        out['complete_windows'] = bool(out['complete_volatility'] and out['complete_return']
                                       and b.iloc[t-61:t+64].notna().all())
    return out
