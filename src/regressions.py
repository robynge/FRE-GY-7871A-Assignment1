"""Trend and filing-outcome regressions with explicit clustered inference.

Tone columns are fractions in their original units; no winsorisation is applied.
Trend tests use seasonal effects, never saturated calendar-quarter effects.
Outcome regressions use firm and calendar-quarter effects. The before/after
volatility specifications share exactly the same complete-case sample.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.linalg import qr
from scipy.stats import norm, t as student_t
from statsmodels.stats.sandwich_covariance import cov_cluster, cov_cluster_2groups, cov_hac

TONES = ["Negative_prop", "Uncertainty_prop", "Negative_tfidf", "Uncertainty_tfidf"]
CONTROLS = ["log_size", "log_dollar_volume", "pre_excess"]


def _complete(df, numeric, categorical):
    needed = list(dict.fromkeys(numeric + categorical))
    data = df.loc[:, needed].copy()
    for col in numeric:
        data[col] = pd.to_numeric(data[col], errors="coerce")
    return data.replace([np.inf, -np.inf], np.nan).dropna().reset_index(drop=True)


def _design(data, numeric, effects=(), form=False):
    x = data[numeric].astype(float).copy()
    if form and data["form"].nunique() > 1:
        x["is_10K"] = data["form"].eq("10-K").astype(float)
    for effect in effects:
        dummies = pd.get_dummies(data[effect].astype(str), prefix=effect,
                                 drop_first=True, dtype=float)
        x = pd.concat([x, dummies], axis=1)
    # A form-specific sample has no estimable form dummy; seasonal indicators
    # can also be absent in a small supplied subsample.
    x = x.loc[:, x.nunique() > 1]
    return sm.add_constant(x, has_constant="add").astype(float)


def _estimate(data, outcome, numeric, effects, form, focal, model, inference):
    """Return focal coefficient and uncertainty; retain non-estimable models."""
    n = len(data)
    firms = int(data["cik"].nunique()) if "cik" in data else 0
    quarters = int(data["quarter"].nunique()) if "quarter" in data else 0
    row = dict(model=model, outcome=outcome, term=focal, inference=inference,
               n=n, firm_clusters=firms, quarter_clusters=quarters,
               coef=np.nan, se=np.nan, t=np.nan, p=np.nan, ci_low=np.nan,
               ci_high=np.nan, mde80=np.nan, df_inference=np.nan, r_squared=np.nan,
               controls=",".join(numeric), fixed_effects=",".join(effects),
               form_control=False, dropped_nuisance="", design_rank=0,
               status="insufficient_data")
    if n == 0:
        return row
    x = _design(data, numeric, effects, form)
    if n <= 1:
        return row
    if focal not in x:
        row["status"] = "focal_not_identified"
        return row
    row["form_control"] = "is_10K" in x
    nuisance = x.drop(columns=[focal])
    # Unit column norms avoid making identification depend on tone units.
    # Use one tolerance for both ranks: the focal coefficient is unique exactly
    # when its column adds one dimension to the nuisance column space.
    scaled = x.to_numpy() / np.linalg.norm(x.to_numpy(), axis=0)
    scaled_nuisance = nuisance.to_numpy() / np.linalg.norm(nuisance.to_numpy(), axis=0)
    tolerance = np.finfo(float).eps * max(scaled.shape) * np.linalg.norm(scaled)
    basis, triangular, pivots = qr(scaled_nuisance, mode="economic", pivoting=True)
    nuisance_rank = int(np.count_nonzero(np.abs(np.diag(triangular)) > tolerance))
    focal_scaled = scaled[:, list(x.columns).index(focal)]
    identified_part = focal_scaled - basis[:, :nuisance_rank] @ (basis[:, :nuisance_rank].T @ focal_scaled)
    full_rank = nuisance_rank + int(np.linalg.norm(identified_part) > tolerance)
    row["design_rank"] = int(full_rank)
    if full_rank != nuisance_rank + 1:
        row["status"] = "focal_not_identified"
        return row
    if n <= full_rank:
        return row
    # Pivot only nuisance columns, never the focal regressor. This retains the
    # specified model's entire nuisance space even when seasons are absorbed by
    # firm effects, and bases covariance corrections on the effective rank.
    selected = sorted(pivots[:nuisance_rank])
    kept = nuisance.columns[selected].tolist()
    row["dropped_nuisance"] = ",".join(c for c in nuisance if c not in kept)
    x = x[[focal] + kept]
    fit = sm.OLS(data[outcome].astype(float), x, hasconst=True).fit()
    if inference == "OLS":
        covariance = fit.cov_params().to_numpy()
        df_inference = int(fit.df_resid)
    elif inference == "HAC4":
        covariance = cov_hac(fit, nlags=4, use_correction=True)
        df_inference = int(fit.df_resid)
    elif inference == "firm_cluster":
        if firms < 2:
            return row
        covariance = cov_cluster(fit, pd.factorize(data["cik"])[0], use_correction=True)
        df_inference = firms - 1
    elif inference == "firm_quarter_cluster":
        if min(firms, quarters) < 2:
            return row
        covariance = cov_cluster_2groups(fit, pd.factorize(data["cik"])[0],
                                        pd.factorize(data["quarter"])[0],
                                        use_correction=True)[0]
        df_inference = min(firms, quarters) - 1
    else:
        raise ValueError(f"Unknown inference: {inference}")
    index = list(x.columns).index(focal)
    coefficient = float(fit.params[focal])
    variance = float(covariance[index, index])
    row.update(coef=coefficient, df_inference=df_inference,
               r_squared=float(fit.rsquared), controls=",".join(numeric),
               fixed_effects=",".join(effects))
    if not np.isfinite(variance) or variance <= 0:
        row["status"] = "nonpositive_covariance"
        return row
    se = float(np.sqrt(variance))
    statistic = coefficient / se
    critical = float(student_t.ppf(.975, df_inference))
    row.update(se=se, t=statistic, p=float(2 * student_t.sf(abs(statistic), df_inference)),
               ci_low=coefficient - critical * se, ci_high=coefficient + critical * se,
               mde80=(critical + norm.ppf(.8)) * se, status="ok")
    return row


def trend_tests(df: pd.DataFrame) -> pd.DataFrame:
    """Tidy annual trend slopes for each of four tone measures.

    Models: quarter-level equal-filing means + seasonal indicators (ordinary OLS and HAC lag 4);
    filing-level trend + seasonal/form/firm effects, with firm clustering and
    conservative two-way firm/quarter clustering (df = min(cluster counts)-1).
    `time_years` is elapsed quarters / 4, so coefficients are annual changes.
    """
    rows = []
    seasons = ["season2", "season3", "season4"]
    for tone in TONES:
        data = _complete(df, [tone, "time_years"] + seasons, ["cik", "quarter", "form"])
        aggregate = data.groupby("quarter", as_index=False).agg(
            {tone: "mean", "time_years": "first", **{s: "first" for s in seasons}}
        ).sort_values("time_years")
        for inference in ["OLS", "HAC4"]:
            row = _estimate(aggregate, tone, ["time_years"] + seasons, (), False,
                            "time_years", "aggregate_trend", inference)
            row["measure"] = tone
            rows.append(row)
        for inference in ["firm_cluster", "firm_quarter_cluster"]:
            row = _estimate(data, tone, ["time_years"] + seasons, ("cik",), True,
                            "time_years", "within_firm_trend", inference)
            row["measure"] = tone
            rows.append(row)
    return pd.DataFrame(rows)


def outcome_tests(df: pd.DataFrame, kind=None) -> pd.DataFrame:
    """Tone coefficients for volatility and sentiment-return regressions.

    For each uncertainty measure, both volatility models use complete cases including
    pre_vol, even when that control is omitted from the specification. Returns
    use negative tone, pre-volatility, all other controls, and firm/quarter FE.
    Each specification reports firm and two-way clustered inference separately.
    """
    rows = []
    for tone in (["Uncertainty_prop", "Uncertainty_tfidf"] if kind != "return" else []):
        data = _complete(df, [tone, "post_vol", "pre_vol"] + CONTROLS,
                         ["cik", "quarter", "form"])
        for include_pre in [False, True]:
            predictors = [tone] + CONTROLS + (["pre_vol"] if include_pre else [])
            name = "volatility_with_prevol" if include_pre else "volatility_without_prevol"
            for inference in ["firm_cluster", "firm_quarter_cluster"]:
                row = _estimate(data, "post_vol", predictors, ("cik", "quarter"),
                                True, tone, name, inference)
                row["measure"] = tone
                rows.append(row)
    for tone in (["Negative_prop", "Negative_tfidf"] if kind != "volatility" else []):
        data = _complete(df, [tone, "event_excess", "pre_vol"] + CONTROLS,
                         ["cik", "quarter", "form"])
        for inference in ["firm_cluster", "firm_quarter_cluster"]:
            row = _estimate(data, "event_excess", [tone] + CONTROLS + ["pre_vol"],
                            ("cik", "quarter"), True, tone, "filing_return", inference)
            row["measure"] = tone
            rows.append(row)
    return pd.DataFrame(rows)
