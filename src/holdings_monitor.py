"""Current-security holdings histories with observed-date quarterly denominators."""
from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

import numpy as np
import pandas as pd

FUNDS = ['ARKK', 'ARKQ', 'ARKW', 'ARKF', 'ARKG', 'ARKX']


def normalize_ticker(value):
    value = str(value or '').strip().upper()
    value = re.sub(r'\s+(?:US|UN|UW|UQ|UF|UA)(?:\s+EQUITY)?$', '', value)
    return value.replace('.', '-')


def clean_holdings(frame):
    d = frame.rename(columns={'weight (%)': 'weight', 'shares': 'shares_held',
                              'market value ($)': 'market_value'}).copy().fillna('')
    for c in ['ticker', 'cusip', 'company']:
        d[c] = d.get(c, pd.Series('', index=d.index)).astype(str).str.strip()
    d['normalized_ticker'] = d.ticker.map(normalize_ticker)
    d['normalized_cusip'] = d.cusip.str.upper().str.replace(r'\s+', '', regex=True)
    # Source identifiers can be CUSIPs, SEDOLs or private-security identifiers.
    d['security_key'] = np.where(d.normalized_cusip.ne(''), 'ID:' + d.normalized_cusip,
                                np.where(d.normalized_ticker.ne(''), 'TICKER:' + d.normalized_ticker,
                                         'NAME:' + d.company.str.upper()))
    d = d[d.company.ne('') | d.normalized_ticker.ne('') | d.normalized_cusip.ne('')].copy()
    d['date'] = pd.to_datetime(d.date, format='mixed', errors='coerce').dt.normalize()
    if d.date.isna().any():
        raise ValueError('Holding rows contain invalid dates')
    for c in ['weight', 'shares_held', 'market_value']:
        raw = d.get(c, pd.Series('', index=d.index)).astype(str).str.replace(r'[$,%\s]', '', regex=True)
        d[c] = pd.to_numeric(raw, errors='coerce')
    if d.weight.isna().any():
        raise ValueError('Holding rows contain missing or invalid weights')
    d['held'] = d[['weight', 'shares_held', 'market_value']].fillna(0).ne(0).any(axis=1)
    return d


def build_holdings_monitor(latest, history, as_of, calendar):
    as_of = pd.Timestamp(as_of).normalize()
    latest, history = clean_holdings(latest), clean_holdings(history)
    if not latest.date.eq(as_of).all():
        raise ValueError('Every latest holding must carry the requested observation date')
    funds = sorted(latest.fund.unique())
    if set(funds) != set(history.fund.unique()):
        raise ValueError('Latest and historical fund coverage differ')
    history = history[history.date.le(as_of)].copy()
    history['identifier_match_method'] = 'Exact source identifier'
    repairs = []
    ticker_ids = latest[latest.normalized_ticker.ne('')].groupby('normalized_ticker').normalized_cusip.unique()
    for ticker, ids in ticker_ids.items():
        ids = [i for i in ids if i]
        if len(ids) != 1:
            continue
        target = ids[0]
        mask = history.normalized_ticker.eq(ticker)
        for raw in history.loc[mask, 'normalized_cusip'].unique():
            if not raw or raw == target:
                continue
            reason = None
            if target.isdigit() and len(target) == 9 and raw.isdigit() and len(raw) < 9 and raw.zfill(9) == target:
                reason = 'Restored leading zeros; exact current identifier and ticker match'
            elif re.fullmatch(r'\d+(?:\.\d+)?E[+-]?\d+', raw) and re.fullmatch(r'0*\d+E\d+', target):
                try:
                    if Decimal(raw) == Decimal(target):
                        reason = 'Exact decimal equivalence of an identifier misread as scientific notation; unique current ticker/identifier'
                except InvalidOperation:
                    pass
            if reason:
                selected = mask & history.normalized_cusip.eq(raw)
                repairs.append({'normalized_ticker': ticker, 'raw_identifier': raw, 'matched_identifier': target,
                                'rows': int(selected.sum()), 'method': reason})
                history.loc[selected, 'normalized_cusip'] = target
                history.loc[selected, 'security_key'] = 'ID:' + target
                history.loc[selected, 'identifier_match_method'] = reason
        observed_ids = set(history.loc[mask & history.normalized_cusip.ne(''), 'normalized_cusip'])
        missing = mask & history.normalized_cusip.eq('')
        if missing.any() and observed_ids == {target}:
            reason = 'Missing source identifier; unique current ticker and no conflicting observed historical identifier; provisional ticker match'
            repairs.append({'normalized_ticker': ticker, 'raw_identifier': '', 'matched_identifier': target,
                            'rows': int(missing.sum()), 'method': reason})
            history.loc[missing, 'security_key'] = 'ID:' + target
            history.loc[missing, 'identifier_match_method'] = reason
    # The current official snapshot wins the date/fund collision as a whole file.
    history = pd.concat([history[~history.date.eq(as_of)], latest], ignore_index=True)
    calendar = pd.DatetimeIndex(calendar).normalize().sort_values().unique()
    nontrading = history.loc[~history.date.isin(calendar), ['date', 'fund']].drop_duplicates()
    history = history[history.date.isin(calendar)].copy()
    latest = latest[latest.held].copy()
    metadata_rows = latest.sort_values(['security_key', 'fund']).drop_duplicates('security_key')
    identities = metadata_rows.set_index('security_key')
    keys = list(identities.index)
    current = latest.groupby(['security_key', 'fund'], as_index=False).agg(
        date=('date', 'first'), company=('company', 'first'), ticker=('ticker', 'first'),
        normalized_ticker=('normalized_ticker', 'first'), cusip=('cusip', 'first'),
        normalized_cusip=('normalized_cusip', 'first'), current_weight_pct=('weight', 'sum'),
        shares_held=('shares_held', 'sum'), market_value=('market_value', 'sum'))
    current['security_status'] = np.where(current.normalized_ticker.eq(''),
        'No public ticker supplied; private, cash or other security requires classification',
        'Ticker supplied; SEC filing eligibility determined separately')
    # Exact identifiers preserve renamings without silently joining reused tickers.
    conflicts = []
    for key, row in identities.iterrows():
        if not row.normalized_ticker:
            continue
        conflict = history[history.normalized_ticker.eq(row.normalized_ticker) & history.security_key.ne(key)]
        for old_key, g in conflict.groupby('security_key'):
            conflicts.append({'security_key': key, 'normalized_ticker': row.normalized_ticker,
                'current_cusip': row.normalized_cusip, 'unlinked_historical_key': old_key,
                'historical_tickers': '|'.join(sorted(set(g.ticker))),
                'historical_company_examples': '|'.join(g.company.drop_duplicates().head(4)),
                'first_date': g.date.min(), 'last_date': g.date.max(), 'rows': len(g),
                'reason': 'Same ticker with a different or absent source identifier; not linked without corporate-action evidence'})
    quarterly, entries, coverage = [], [], []
    for fund in funds:
        fd = history[history.fund.eq(fund)]
        dates = pd.DatetimeIndex(sorted(fd.date.unique()))
        if len(dates) == 0:
            raise ValueError(f'No trading-day snapshots for {fund}')
        weights = fd[fd.security_key.isin(keys)].groupby(['date', 'security_key']).weight.sum().unstack()
        weights = weights.reindex(index=dates, columns=keys).fillna(0)
        presence = fd[fd.held & fd.security_key.isin(keys)].groupby(['date', 'security_key']).size().unstack()
        presence = presence.reindex(index=dates, columns=keys).fillna(0).gt(0)
        unresolved_dates = {}
        for key in keys:
            ticker = identities.loc[key, 'normalized_ticker']
            conflict_dates = fd.loc[fd.normalized_ticker.eq(ticker) & fd.security_key.ne(key), 'date'] if ticker else []
            unresolved_dates[key] = pd.DatetimeIndex(conflict_dates).unique()
        for quarter in dates.to_period('Q').unique():
            qdates = dates[dates.to_period('Q') == quarter]
            full = calendar[(calendar >= quarter.start_time.normalize()) &
                            (calendar <= min(quarter.end_time.normalize(), as_of))]
            expected = full[full >= dates[0]]
            coverage_row = {'fund': fund, 'quarter': str(quarter), 'quarter_start': quarter.start_time.normalize(),
                'quarter_end': quarter.end_time.normalize(), 'first_snapshot_date': qdates.min(),
                'last_snapshot_date': qdates.max(), 'observed_snapshot_days': len(qdates),
                'expected_sessions_in_coverage_window': len(expected),
                'missing_snapshot_days': len(expected.difference(qdates)),
                'coverage_fraction': len(qdates) / len(expected) if len(expected) else None,
                'partial_current_quarter': as_of < quarter.end_time.normalize(),
                'partial_archive_start_quarter': dates[0] > quarter.start_time.normalize() and str(dates[0].to_period('Q')) == str(quarter)}
            coverage.append(coverage_row)
            for key in keys:
                vals = weights.loc[qdates, key]
                unresolved_days = len(qdates.intersection(unresolved_dates[key]))
                quarterly.append({'security_key': key, 'normalized_ticker': identities.loc[key, 'normalized_ticker'],
                    'normalized_cusip': identities.loc[key, 'normalized_cusip'], 'fund': fund,
                    'quarter': str(quarter), 'average_weight_pct': None if unresolved_days else float(vals.mean()),
                    'matched_only_average_weight_pct': float(vals.mean()),
                    'unresolved_identity_days': unresolved_days, 'unresolved_identity': unresolved_days > 0,
                    'held_snapshot_days': int(presence.loc[qdates, key].sum()),
                    'observed_snapshot_days': len(qdates), 'sum_daily_weight_pct': float(vals.sum()),
                    'last_observed_weight_pct': float(vals.iloc[-1]),
                    'missing_snapshot_days': coverage_row['missing_snapshot_days'],
                    'partial_current_quarter': coverage_row['partial_current_quarter'],
                    'partial_archive_start_quarter': coverage_row['partial_archive_start_quarter']})
        for key in keys:
            held = presence[key].to_numpy()
            positions = np.flatnonzero(held)
            first = int(positions[0]) if len(positions) else None
            last_spell = None
            if len(positions) and held[-1]:
                last_spell = len(held) - 1
                while last_spell > 0 and held[last_spell - 1]:
                    last_spell -= 1
            gap_days = None
            if last_spell is not None:
                span = calendar[(calendar >= dates[last_spell]) & (calendar <= dates[-1])]
                gap_days = len(span.difference(dates))
            related = fd[fd.security_key.eq(key)]
            entries.append({'security_key': key, 'normalized_ticker': identities.loc[key, 'normalized_ticker'],
                'normalized_cusip': identities.loc[key, 'normalized_cusip'], 'fund': fund,
                'fund_history_first_date': dates[0], 'fund_history_last_date': dates[-1],
                'first_observed_holding_date': dates[first] if first is not None else None,
                'first_entry_left_censored': first == 0 if first is not None else None,
                'last_observed_absence_before_first_entry': dates[first-1] if first is not None and first > 0 else None,
                'latest_observed_spell_entry_date': dates[last_spell] if last_spell is not None else None,
                'latest_spell_left_censored': last_spell == 0 if last_spell is not None else None,
                'last_observed_absence_before_latest_spell': dates[last_spell-1] if last_spell is not None and last_spell > 0 else None,
                'unobserved_sessions_in_latest_spell': gap_days,
                'held_on_latest_snapshot': bool(held[-1]),
                'historical_ticker_aliases': '|'.join(sorted(set(related.normalized_ticker) - {''})),
                'identifier_match_methods': '|'.join(sorted(set(related.identifier_match_method.dropna()))),
                'has_provisional_ticker_matches': bool(related.identifier_match_method.fillna('').str.contains('provisional').any()),
                'identity_conflict_requires_review': any(c['security_key'] == key for c in conflicts),
                'entry_date_interpretation': 'First observed holding of this source security identifier; not an exact trade date or proof of continuous operating-company identity'})
    totals = history.groupby(['fund', 'date']).weight.sum()
    totals = totals[(totals < 95) | (totals > 105)]
    return {'metadata': {'as_of_date': as_of, 'funds': funds, 'current_securities': len(keys),
        'current_fund_positions': len(current), 'weight_unit': 'Percentage of each ETF net assets; 1 means 1%',
        'quarterly_mean_rule': 'Sum weights on all observed trading snapshots divided by all observed fund snapshots in the quarter; confirmed absence is zero; missing snapshot dates are not filled. If any same-ticker unlinked-identifier observation occurs in a security/fund quarter, average_weight_pct is null because exposure is unresolved. matched_only_average_weight_pct and sum_daily_weight_pct describe only matched records and are not complete exposure measures in those quarters.',
        'identity_rule': 'Exact source identifier, documented lossless format repairs, or flagged provisional matching when identifiers are missing and the normalized ticker has one current identifier and no historical identifier conflict. Different nonempty identifiers are not merged solely by ticker.',
        'entry_rule': 'First observed holding; left-censored at first fund archive date. Latest spell is continuous only across observed snapshots, not across unobserved dates.',
        'source_coverage': 'Bloomberg backfill before 2021-05-06 and selected gap dates; blog archive through 2026-04-28; official ARK files thereafter. See source README for limitations.',
        'nontrading_snapshot_dates_removed': len(nontrading),
        'outlying_fund_snapshot_totals': [{'fund': fund, 'date': day, 'total_weight_pct': weight} for (fund, day), weight in totals.items()],
        'identity_conflicts': len(conflicts)}, 'latest_holdings': current.to_dict('records'),
        'quarterly_weights': quarterly, 'entry_dates': entries, 'fund_quarter_coverage': coverage,
        'identity_conflicts': conflicts, 'identifier_repairs': repairs}


def save_holdings_monitor(data, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    def encode(value):
        if isinstance(value, pd.Timestamp):
            return value.date().isoformat()
        if isinstance(value, np.generic):
            return value.item()
        raise TypeError(type(value).__name__)
    payload = json.loads(json.dumps(data, default=encode, allow_nan=False))
    (output_dir / 'data.json').write_text(json.dumps(payload, indent=2) + '\n')
    for key, rows in payload.items():
        if isinstance(rows, list):
            pd.DataFrame(rows).to_csv(output_dir / f'{key}.csv', index=False)
