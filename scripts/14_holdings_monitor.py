"""Build quarterly ETF weights for the securities held on the observation date."""
import sys
import subprocess
from pathlib import Path

import pandas as pd
import pandas_market_calendars as mcal

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import ROOT, AS_OF_DATE
from src.holdings_monitor import FUNDS, build_holdings_monitor, save_holdings_monitor


if __name__ == '__main__':
    source = ROOT / 'data/current_holdings'
    (source / 'history').mkdir(exist_ok=True)
    for fund in FUNDS:
        path = source / 'history' / f'{fund}.csv'
        if not path.exists():
            path.write_bytes(subprocess.check_output(['gh', 'api', f'repos/robynge/ark-routine/contents/data/consolidated/{fund}.csv?ref=main', '-H', 'Accept: application/vnd.github.raw+json']))
    latest = pd.concat([pd.read_csv(source / f'{f}_Holdings_{AS_OF_DATE}.csv', dtype=str) for f in FUNDS], ignore_index=True)
    history = pd.concat([pd.read_csv(source / 'history' / f'{f}.csv', dtype=str) for f in FUNDS], ignore_index=True)
    first = pd.to_datetime(history.date).min()
    calendar = mcal.get_calendar('NYSE').valid_days(first, AS_OF_DATE).tz_localize(None)
    data = build_holdings_monitor(latest, history, AS_OF_DATE, calendar)
    save_holdings_monitor(data, ROOT / 'outputs/current_holdings')
    print({k: v for k, v in data['metadata'].items() if k not in ['outlying_fund_snapshot_totals']})
