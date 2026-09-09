import numpy as np
import pandas as pd
from src.events import align_day_zero, event_variables


def test_close_cutoff_utc_dst_and_weekend():
    calendar = pd.to_datetime(["2025-07-03", "2025-07-07", "2025-07-08"])
    # July 3 closes at 13:00 Eastern; July 4 and the weekend are absent.
    assert align_day_zero("2025-07-03", "2025-07-03T16:59:59Z", calendar)[0] == calendar[0]
    assert align_day_zero("2025-07-03", "2025-07-03T17:00:00Z", calendar) == (calendar[1], True)
    assert pd.isna(align_day_zero("2025-07-03", None, calendar)[0])


def test_filing_date_is_lower_bound():
    calendar = pd.bdate_range("2025-01-02", periods=10)
    assert align_day_zero("2025-01-06", "2025-01-03T18:00:00Z", calendar)[0] == pd.Timestamp("2025-01-06")


def test_event_window_compounding_and_no_fill():
    cal = pd.bdate_range("2024-01-01", periods=160)
    p = pd.Series(10*1.01**np.arange(160), index=cal)
    b = pd.Series(100*1.002**np.arange(160), index=cal)
    v = pd.Series(1000., index=cal)
    f = {"filing_date": cal[80], "acceptance_datetime": str(cal[80].date())+"T15:00:00Z"}
    got = event_variables(f,p,p,v,b,1000)
    assert got["valid_history"] and got["complete_windows"]
    assert np.isclose(got["event_excess"],1.01**4-1.002**4)
    assert np.isclose(got["pre_excess"],1.01**55-1.002**55)
    assert got["post_vol"] < 1e-12
    p.iloc[90] = np.nan
    assert not event_variables(f,p,p,v,b,1000)["complete_windows"]


def test_missing_benchmark_does_not_shorten_calendar():
    cal = pd.bdate_range("2024-01-01", periods=160)
    p = pd.Series(10*1.01**np.arange(160),index=cal)
    b = pd.Series(100.,index=cal)
    b.iloc[81] = np.nan
    f = {"filing_date":cal[80],"acceptance_datetime":str(cal[80].date())+"T15:00:00Z"}
    assert not event_variables(f,p,p,p,b,1000)["complete_windows"]


def test_sixty_after_passes_history_but_not_complete_volatility_window():
    cal = pd.bdate_range("2024-01-01", periods=141)
    p = pd.Series(10*1.01**np.arange(141),index=cal)
    f = {"filing_date":cal[80],"acceptance_datetime":str(cal[80].date())+"T15:00:00Z"}
    out = event_variables(f,p,p,p,p,1000)
    assert out["valid_history"]
    assert not out["complete_windows"]


def test_recent_filing_return_is_available_without_future_volatility():
    cal = pd.bdate_range("2024-01-01", periods=100)
    p = pd.Series(10*1.01**np.arange(100), index=cal)
    f = {"filing_date":cal[80],"acceptance_datetime":str(cal[80].date())+"T15:00:00Z"}
    out = event_variables(f,p,p,p,p,1000)
    assert out["valid_pre_history"] and out["complete_return"]
    assert np.isfinite(out["event_excess"])
    assert not out["complete_volatility"] and np.isnan(out["post_vol"])
