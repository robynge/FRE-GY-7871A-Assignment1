"""Attribute a change in filing tone to what was written or to what was dropped.

A filing's word share is a weighted average of two parts:

    S = w * S_risk + (1 - w) * S_body

with w the risk section's share of the filing's words. Between two filings by
the same company the change splits exactly, with no residual, by taking
midpoints:

    dS = [w_bar * dS_risk + (1 - w_bar) * dS_body]   (language)
       + [dw * (S_risk_bar - S_body_bar)]            (composition)

The first term is the company writing differently. The second is the company
writing a different amount of the part that carries most of the risk words. A
10-Q that replaces its risk factors with a pointer to the annual report moves
the second term and leaves the first one alone, which is why a fall in the
headline score is not evidence that the business became safer.

Comparisons are within company and within form. A 10-K against a 10-Q would
measure the difference between the two documents, not a change in disclosure.

Read the language term with care. When a company replaces its risk factors with
a pointer, the section that remains is a single sentence about risk, and in this
corpus those sentences run at 6.3% uncertainty words against 3.3% for a restated
section. dS_risk therefore rises sharply for a reason that has nothing to do
with how the company writes. The honest summary statistic is the change in the
body alone, which is reported alongside the two terms and is what the reader
should be shown first.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

CATEGORIES = ["Negative", "Uncertainty"]

# Modes in which the risk factors are not printed in this filing.
REFERRING_MODES = ("reference_only", "omitted")
PRINTING_MODES = ("full", "partial_update")


def _transition(previous: str, current: str) -> str:
    if previous in PRINTING_MODES and current in REFERRING_MODES:
        return "to_reference"
    if previous in REFERRING_MODES and current in PRINTING_MODES:
        return "to_full"
    if previous in REFERRING_MODES and current in REFERRING_MODES:
        return "stays_reference"
    return "stays_full"


def build_panel(sections: pd.DataFrame) -> pd.DataFrame:
    """One row per filing that has a predecessor of the same form and company."""
    data = sections[sections.risk_found].copy()
    data["filing_date"] = pd.to_datetime(data.filing_date)
    data = data.sort_values(["cik", "form", "filing_date"])
    grouped = data.groupby(["cik", "form"], sort=False)

    lagged = {"risk_mode": "prev_mode", "risk_share": "prev_risk_share",
              "risk_words": "prev_risk_words", "n_words": "prev_n_words",
              "filing_date": "prev_filing_date", "quarter": "prev_quarter"}
    for source, target in lagged.items():
        data[target] = grouped[source].shift(1)
    for category in CATEGORIES:
        for part in ("total", "risk", "body"):
            data[f"prev_{category}_prop_{part}"] = grouped[f"{category}_prop_{part}"].shift(1)

    data = data[data.prev_mode.notna()].copy()
    data["transition"] = [_transition(p, c) for p, c in zip(data.prev_mode, data.risk_mode)]
    data["quarters_apart"] = (
        (data.filing_date.dt.to_period("Q").astype("int64")
         - pd.to_datetime(data.prev_filing_date).dt.to_period("Q").astype("int64")))
    data["risk_words_change"] = data.risk_words - data.prev_risk_words
    return data.reset_index(drop=True)


def decompose(panel: pd.DataFrame, category: str) -> pd.DataFrame:
    """Split each filing-to-filing tone change into language and composition."""
    out = panel.copy()
    weight, previous_weight = out.risk_share, out.prev_risk_share
    mean_weight = (weight + previous_weight) / 2
    weight_change = weight - previous_weight

    total, risk, body = (out[f"{category}_prop_{p}"] for p in ("total", "risk", "body"))
    prev_total, prev_risk, prev_body = (
        out[f"prev_{category}_prop_{p}"] for p in ("total", "risk", "body"))

    out[f"{category}_change"] = total - prev_total
    out[f"{category}_language"] = (mean_weight * (risk - prev_risk)
                                   + (1 - mean_weight) * (body - prev_body))
    out[f"{category}_composition"] = weight_change * ((risk + prev_risk) / 2
                                                      - (body + prev_body) / 2)
    out[f"{category}_residual"] = (out[f"{category}_change"]
                                   - out[f"{category}_language"]
                                   - out[f"{category}_composition"])
    # Free of the pointer-density problem described in the module docstring.
    out[f"{category}_body_change"] = body - prev_body
    return out


def decomposition_summary(panel: pd.DataFrame) -> pd.DataFrame:
    """Mean change and its two parts, in percentage points, by transition."""
    rows = []
    for category in CATEGORIES:
        data = decompose(panel, category)
        for transition, group in data.groupby("transition"):
            complete = group.dropna(subset=[f"{category}_change", f"{category}_language",
                                            f"{category}_composition"])
            if complete.empty:
                continue
            rows.append({
                "category": category, "transition": transition,
                "n": len(complete), "companies": complete.cik.nunique(),
                "change_pp": 100 * complete[f"{category}_change"].mean(),
                "body_change_pp": 100 * complete[f"{category}_body_change"].mean(),
                "language_pp": 100 * complete[f"{category}_language"].mean(),
                "composition_pp": 100 * complete[f"{category}_composition"].mean(),
                "max_abs_residual_pp": 100 * complete[f"{category}_residual"].abs().max(),
                "median_risk_words_change": complete.risk_words_change.median(),
            })
    return pd.DataFrame(rows)


def mode_counts(sections: pd.DataFrame, by: str = "group") -> pd.DataFrame:
    """Share of filings in each disclosure mode, quarterly reports only."""
    quarterly = sections[sections.form.eq("10-Q")]
    counts = pd.crosstab([quarterly[by], quarterly.filing_date.str[:4]], quarterly.risk_mode)
    counts.index.names = [by, "year"]
    return counts.div(counts.sum(axis=1), axis=0).mul(100).round(1)


def switch_events(panel: pd.DataFrame) -> pd.DataFrame:
    """Filings where the company changed whether it prints its risk factors."""
    events = panel[panel.transition.isin(["to_reference", "to_full"])].copy()
    for category in CATEGORIES:
        events = decompose(events, category)
    return events.sort_values(["filing_date", "ticker"]).reset_index(drop=True)


def outcome_by_transition(panel: pd.DataFrame, outcome: str) -> pd.DataFrame:
    """Market outcome around the filing, grouped by what the filer did.

    Descriptive only. Whether the switch itself carries information is a
    regression question, and mode switches are not randomly assigned.
    """
    if outcome not in panel:
        raise KeyError(f"{outcome} is not in the panel; merge the market sample first")
    data = panel.dropna(subset=[outcome])
    rows = []
    for transition, group in data.groupby("transition"):
        values = group[outcome]
        rows.append({
            "transition": transition, "n": len(values), "companies": group.cik.nunique(),
            "mean": values.mean(), "median": values.median(),
            "sd": values.std(), "t_vs_zero": values.mean() / (values.std() / np.sqrt(len(values)))
            if len(values) > 1 and values.std() > 0 else np.nan,
        })
    return pd.DataFrame(rows)
