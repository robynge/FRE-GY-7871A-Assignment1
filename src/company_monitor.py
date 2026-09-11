"""Company-level filing-language monitoring using same-form fiscal anniversaries."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

MIN_WORDS = {"10-K": 2000, "10-Q": 1000}
FRESHNESS_DAYS = {"10-K": 450, "10-Q": 210}
MATCH_TOLERANCE_DAYS = 45


def _clean(value):
    """Return strict JSON data, preserving missing values as null rather than zero."""
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if isinstance(value, np.generic):
        return _clean(value.item())
    if value is pd.NA or (isinstance(value, float) and np.isnan(value)):
        return None
    return value


def _published_before(prior, current):
    if prior["_filing"] != current["_filing"]:
        return prior["_filing"] < current["_filing"]
    return (pd.notna(prior["_accepted"]) and pd.notna(current["_accepted"])
            and prior["_accepted"] < current["_accepted"])


def prepare_history(scores, universe, as_of):
    """Validate scores and retain the earliest original filing for each period."""
    data = scores.copy()
    data["cik"] = data["cik"].astype(str).str.zfill(10)
    for field in ("report_date", "filing_date"):
        data["_" + field.split("_")[0]] = pd.to_datetime(data[field], errors="coerce").dt.normalize()
    data["_accepted"] = pd.to_datetime(data["acceptance_datetime"], errors="coerce", utc=True)
    as_of = pd.Timestamp(as_of).normalize()
    data["exclusion_reason"] = ""
    conditions = [
        (~data.cik.isin(universe.cik.astype(str).str.zfill(10)), "Not held in the selected current company universe"),
        (~data.form.isin(MIN_WORDS), "Not an original 10-K or 10-Q"),
        (data._filing.isna(), "Invalid filing date"),
        (data._report.isna(), "Invalid report date"),
        (data._filing.gt(as_of), "Filed after the observation cutoff"),
        (data._report.gt(data._filing), "Report period ends after filing date"),
        (data.n_words.lt(data.form.map(MIN_WORDS)), "Below minimum document length"),
        (~data.n_words.gt(0), "Missing or invalid document length"),
        (data[["Negative_prop", "Uncertainty_prop"]].isna().any(axis=1), "Missing tone score"),
    ]
    for condition, reason in conditions:
        data.loc[condition & data.exclusion_reason.eq(""), "exclusion_reason"] = reason
    eligible = data[data.exclusion_reason.eq("")].sort_values(
        ["_filing", "_accepted", "accession"], kind="stable", na_position="last")
    duplicate_indices = eligible.index[eligible.duplicated(["cik", "form", "report_date"], keep="first")]
    data.loc[duplicate_indices, "exclusion_reason"] = "Later original filing for the same company, form and report date"
    excluded = data[~data.exclusion_reason.eq("")].copy()
    data = data[data.exclusion_reason.eq("")].drop(columns="exclusion_reason")
    data = data.sort_values(["cik", "form", "_report", "_filing", "accession"], kind="stable").reset_index(drop=True)
    data["history_index"] = data.index
    mapping = universe.copy()
    mapping["cik"] = mapping["cik"].astype(str).str.zfill(10)
    if mapping.cik.duplicated().any():
        raise ValueError("Universe must contain one record per CIK")
    fund_map = mapping.set_index("cik").funds.to_dict()
    ticker_map = mapping.set_index("cik").tickers.to_dict()
    data["funds"] = data.cik.map(fund_map).fillna("")
    data["tickers"] = data.cik.map(ticker_map).fillna(data.ticker)
    precision_errors = {}
    for label in ("Negative", "Uncertainty"):
        proportions = data[label + "_prop"]
        if not proportions.between(0, 1).all():
            raise ValueError(f"{label} proportions must lie between zero and one")
        implied = proportions * data.n_words
        error = np.abs(implied - np.rint(implied))
        precision_errors[label] = float(error.max()) if len(error) else 0.0
        if (error > 1e-6).any():
            raise ValueError(f"{label} proportions do not recover integer token counts")
        data[label + "_tokens"] = np.rint(implied).astype(int)
        data[label + "_pct"] = proportions * 100
    excluded = excluded.drop(columns=[c for c in excluded if c.startswith("_")])
    return data, excluded, precision_errors


def match_anniversaries(history, tolerance_days=MATCH_TOLERANCE_DAYS):
    """Match only previously published, same-form periods near the prior year."""
    history = history.copy()
    for field in ("matched_history_index", "match_gap_days", "match_signed_gap_days", "delta_neg_pp", "delta_unc_pp"):
        history[field] = np.nan
    history["anniversary_target_date"] = None
    for (_, _), group in history.groupby(["cik", "form"], sort=False):
        records = group.to_dict("records")
        for current in records:
            idx = current["history_index"]
            target = current["_report"] - pd.DateOffset(years=1)
            history.at[idx, "anniversary_target_date"] = target.date().isoformat()
            candidates = [p for p in records if p["_report"] < current["_report"]
                          and abs((p["_report"] - target).days) <= tolerance_days
                          and _published_before(p, current)]
            if not candidates:
                continue
            prior = min(candidates, key=lambda p: (abs((p["_report"] - target).days), p["_report"], p["accession"]))
            signed_gap = (prior["_report"] - target).days
            history.at[idx, "matched_history_index"] = prior["history_index"]
            history.at[idx, "match_gap_days"] = abs(signed_gap)
            history.at[idx, "match_signed_gap_days"] = signed_gap
            history.at[idx, "delta_neg_pp"] = 100 * (current["Negative_prop"] - prior["Negative_prop"])
            history.at[idx, "delta_unc_pp"] = 100 * (current["Uncertainty_prop"] - prior["Uncertainty_prop"])
    for field in ("matched_history_index", "match_gap_days", "match_signed_gap_days"):
        history[field] = history[field].astype("Int64")
    return history


def company_snapshot(history, as_of):
    rows = []
    as_of = pd.Timestamp(as_of).normalize()
    for (cik, form), group in history.groupby(["cik", "form"], sort=False):
        group = group.sort_values(["_report", "_filing", "accession"])
        recent = group.tail(3)
        latest = recent.iloc[-1]
        matched = int(recent.matched_history_index.notna().sum())
        complete = len(recent) == 3 and matched == 3
        age = (as_of - latest._filing).days
        fresh = age <= FRESHNESS_DAYS[form]
        row = {
            "ticker": latest.ticker, "tickers": latest.tickers, "cik": cik,
            "company": latest.company, "funds": latest.funds, "form": form,
            "n_filings": len(group), "first_report_date": group.iloc[0].report_date,
            "latest_report_date": latest.report_date, "latest_filing_date": latest.filing_date,
            "latest_accession": latest.accession, "latest_doc_url": latest.doc_url,
            "latest_history_index": int(latest.history_index),
            "recent_history_indices": recent.history_index.astype(int).tolist(),
            "recent_matched_history_indices": recent.matched_history_index.tolist(),
            "latest_matched_history_index": latest.matched_history_index,
            "latest_match_gap_days": latest.match_gap_days,
            "latest_n_words": int(latest.n_words), "filing_age_days": age,
            "freshness_limit_days": FRESHNESS_DAYS[form], "fresh": fresh,
            "matched_latest_three": matched, "trend_eligible": complete,
            "ranking_eligible": complete and fresh,
            "latest_negative_pct": latest.Negative_pct,
            "latest_uncertainty_pct": latest.Uncertainty_pct,
            "latest_negative_tokens": int(latest.Negative_tokens),
            "latest_uncertainty_tokens": int(latest.Uncertainty_tokens),
            "latest_delta_neg_pp": latest.delta_neg_pp,
            "latest_delta_unc_pp": latest.delta_unc_pp,
            "recent_three_mean_delta_neg_pp": recent.delta_neg_pp.mean() if complete else None,
            "recent_three_mean_delta_unc_pp": recent.delta_unc_pp.mean() if complete else None,
            "recent_three_first_report_date": recent.iloc[0].report_date if complete else None,
        }
        for short in ("neg", "unc"):
            values = recent["delta_" + short + "_pp"]
            for direction, result in (("decreases", values.lt(0)), ("increases", values.gt(0)), ("unchanged", values.eq(0))):
                row[f"recent_three_{short}_{direction}"] = int(result.sum()) if complete else None
        rows.append(row)
    snapshots = pd.DataFrame(rows)
    if snapshots.empty:
        return snapshots
    for form in MIN_WORDS:
        same = snapshots.form.eq(form)
        ranks = [
            ("rank_latest_uncertainty", same & snapshots.fresh, "latest_uncertainty_pct", False),
            ("rank_negative_improvement", same & snapshots.ranking_eligible & snapshots.recent_three_mean_delta_neg_pp.lt(0), "recent_three_mean_delta_neg_pp", True),
            ("rank_uncertainty_decline", same & snapshots.ranking_eligible & snapshots.recent_three_mean_delta_unc_pp.lt(0), "recent_three_mean_delta_unc_pp", True),
            ("rank_uncertainty_rise", same & snapshots.ranking_eligible & snapshots.recent_three_mean_delta_unc_pp.gt(0), "recent_three_mean_delta_unc_pp", False),
        ]
        for output, mask, field, ascending in ranks:
            if output not in snapshots:
                snapshots[output] = np.nan
            snapshots.loc[mask, output] = snapshots.loc[mask, field].rank(method="min", ascending=ascending)
    return snapshots.sort_values(["ticker", "cik", "form"], kind="stable").reset_index(drop=True)


def _summary(rows):
    if not rows:
        return {"n_companies": 0}
    frame = pd.DataFrame(rows)
    current = frame[frame.ranking_eligible]
    summary = {
        "n_companies": len(frame), "n_fresh": int(frame.fresh.sum()),
        "n_stale": int((~frame.fresh).sum()),
        "n_latest_yoy_available": int(frame.latest_delta_unc_pp.notna().sum()),
        "n_trend_eligible": int(frame.trend_eligible.sum()),
        "n_current_trend_eligible": len(current),
        "n_incomplete_recent_three": int((~frame.trend_eligible).sum()),
        "n_latest_yoy_missing": int(frame.latest_delta_unc_pp.isna().sum()),
    }
    for short in ("neg", "unc"):
        values = current[f"recent_three_mean_delta_{short}_pp"]
        for direction, matched in (("decreases", values.lt(0)), ("increases", values.gt(0)), ("unchanged", values.eq(0))):
            summary[f"n_{short}_{direction}"] = int(matched.sum())
            summary[f"n_{short}_{direction}_three_of_three"] = int(current[f"recent_three_{short}_{direction}"].eq(3).sum())
        summary[f"mean_company_recent_three_{short}_change_pp"] = values.mean()
        summary[f"median_company_recent_three_{short}_change_pp"] = values.median()
    for title, rank in (("negative_improvement", "rank_negative_improvement"),
                        ("uncertainty_rise", "rank_uncertainty_rise"),
                        ("highest_uncertainty", "rank_latest_uncertainty"),
                        ("uncertainty_decline", "rank_uncertainty_decline")):
        summary["top_ten_" + title] = frame[frame[rank].notna()].sort_values([rank, "ticker"]).head(10).to_dict("records")
    summary["coverage_gaps"] = frame[(~frame.fresh) | (~frame.trend_eligible)][[
        "ticker", "company", "form", "latest_filing_date", "filing_age_days", "fresh", "n_filings", "matched_latest_three", "trend_eligible"
    ]].to_dict("records")
    return summary


def build_monitor(scores, universe, as_of):
    history, excluded, precision = prepare_history(scores, universe, as_of)
    history = match_anniversaries(history)
    snapshot = company_snapshot(history, as_of)
    historical = history.drop(columns=[c for c in history if c.startswith("_")]).to_dict("records")
    quarterly = snapshot[snapshot.form.eq("10-Q")].to_dict("records") if len(snapshot) else []
    annual = snapshot[snapshot.form.eq("10-K")].to_dict("records") if len(snapshot) else []
    seen = set(history.cik)
    gaps = universe[~universe.cik.astype(str).str.zfill(10).isin(seen)]
    metadata = {
        "as_of_date": str(as_of), "input_filings": len(scores), "retained_filings": len(history),
        "retained_companies": history.cik.nunique(), "excluded_filings": len(excluded),
        "exclusion_counts": excluded.exclusion_reason.value_counts().to_dict(),
        "n_10q": int(history.form.eq("10-Q").sum()), "n_10k": int(history.form.eq("10-K").sum()),
        "min_words": MIN_WORDS, "anniversary_tolerance_days": MATCH_TOLERANCE_DAYS,
        "freshness_days": FRESHNESS_DAYS, "negative_dictionary_words": 2345, "uncertainty_dictionary_words": 297,
        "token_count_recovery_max_error": precision,
        "rank_measure": "Active-category word occurrences divided by total document words",
        "change_unit": "Percentage points", "latest_order": "Report date, then filing date",
        "recent_three_order": "Oldest to newest report date",
        "match_rule": "Closest same-form report date to the previous calendar-year anniversary, within 45 days, with an earlier publication date or acceptance timestamp; ties choose the earlier report date",
        "trend_rule": "All three latest same-form filings must have anniversary matches; current rankings also require a fresh latest filing",
        "rank_ties": "Equal values receive the minimum shared rank; tied names are displayed alphabetically",
        "history_scope": "Canonical original filings meeting document-length and date criteria; excluded source records are listed separately",
        "weighted_score_note": "Existing corpus-weighted source scores are retained for traceability and are not used for company rankings",
        "holdings_scope": "Current holdings company selection; historical ETF allocations are measured separately from filing language",
        "universe_companies": len(universe), "universe_companies_without_eligible_filings": len(gaps),
        "first_filing_date": history.filing_date.min() if len(history) else None,
        "last_filing_date": history.filing_date.max() if len(history) else None,
    }
    return _clean({"metadata": metadata, "history": historical, "quarterly": quarterly, "annual": annual,
                   "excluded_history": excluded.to_dict("records"),
                   "universe_coverage_gaps": gaps.to_dict("records"),
                   "summary": {"quarterly": _summary(quarterly), "annual": _summary(annual)}})


def save_monitor(data, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "data.json").write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    for key in ("history", "quarterly", "annual", "excluded_history", "universe_coverage_gaps"):
        frame = pd.DataFrame(data[key])
        for field in ("recent_history_indices", "recent_matched_history_indices"):
            if field in frame:
                frame[field] = frame[field].map(json.dumps)
        frame.to_csv(output_dir / (key + ".csv"), index=False)
