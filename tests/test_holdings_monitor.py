import pandas as pd
import pytest

from src.holdings_monitor import build_holdings_monitor, normalize_ticker


def test_observed_date_denominator_zero_absences_gaps_and_identity():
    def row(day, ticker, cusip, weight):
        return dict(date=day, fund='ARKK', company=ticker, ticker=ticker, cusip=cusip, weight=weight)
    history = pd.DataFrame([row('2026-07-01', 'A', '111111111', 6),
        row('2026-07-02', 'B', '222222222', 10),
        row('2026-07-06', 'A OLD', '111111111', 3),
        row('2026-07-06', 'A', '333333333', 99)])
    latest = pd.DataFrame([row('2026-07-07', 'A', '111111111', 3)])
    calendar = pd.to_datetime(['2026-07-01', '2026-07-02', '2026-07-03', '2026-07-06', '2026-07-07'])
    data = build_holdings_monitor(latest, history, '2026-07-07', calendar)
    q = data['quarterly_weights'][0]
    assert q['average_weight_pct'] is None
    assert q['unresolved_identity'] and q['unresolved_identity_days'] == 1
    assert q['matched_only_average_weight_pct'] == pytest.approx((6 + 0 + 3 + 3) / 4)
    assert q['observed_snapshot_days'] == 4 and q['missing_snapshot_days'] == 1
    assert q['held_snapshot_days'] == 3 and q['partial_current_quarter']
    e = data['entry_dates'][0]
    assert e['first_entry_left_censored']
    assert e['latest_observed_spell_entry_date'] == pd.Timestamp('2026-07-06')
    assert e['last_observed_absence_before_latest_spell'] == pd.Timestamp('2026-07-02')
    assert e['identity_conflict_requires_review'] and len(data['identity_conflicts']) == 1
    assert 'A OLD' in e['historical_ticker_aliases']
    assert normalize_ticker('DKNG UW') == 'DKNG'


def test_missing_snapshots_do_not_imply_exit_or_zero_weight():
    frame = pd.DataFrame([dict(date=d, fund='ARKK', company='A', ticker='A', cusip='111111111', weight=w)
                          for d, w in [('2026-07-01', 2), ('2026-07-06', 4)]])
    data = build_holdings_monitor(frame.tail(1), frame, '2026-07-06',
                                  pd.to_datetime(['2026-07-01', '2026-07-02', '2026-07-06']))
    assert data['quarterly_weights'][0]['average_weight_pct'] == 3
    e = data['entry_dates'][0]
    assert e['latest_observed_spell_entry_date'] == pd.Timestamp('2026-07-01')
    assert e['unobserved_sessions_in_latest_spell'] == 1


def test_identifier_format_repair_and_flagged_missing_identifier():
    def rows(day, identifiers):
        return [dict(date=day, fund='ARKK', company=ticker, ticker=ticker, cusip=cusip, weight=2)
                for ticker, cusip in zip(['AMD', 'ABSI', 'ESLT', 'IONS'], identifiers)]
    old = pd.DataFrame(rows('2026-07-01', ['7903107', '9.10E+110', '', '4.62E+08']))
    current = pd.DataFrame(rows('2026-07-02', ['007903107', '00091E109', 'M3760D101', '462222100']))
    history = pd.concat([old, current], ignore_index=True)
    d = build_holdings_monitor(current, history, '2026-07-02', pd.to_datetime(['2026-07-01', '2026-07-02']))
    q = {r['normalized_ticker']: r for r in d['quarterly_weights']}
    assert all(q[t]['average_weight_pct'] == 2 for t in ['AMD', 'ABSI', 'ESLT'])
    assert q['IONS']['average_weight_pct'] is None  # An unresolved identifier is not zero exposure.
    assert q['IONS']['unresolved_identity_days'] == 1
    assert q['IONS']['matched_only_average_weight_pct'] == 1
    assert next(r for r in d['entry_dates'] if r['normalized_ticker'] == 'ESLT')['has_provisional_ticker_matches']
    assert len(d['identity_conflicts']) == 1
