"""The report (six pages, ARK holdings) and its appendix (a separate document).

Every number in the prose is read from the CSV that produced it. Run the
analysis scripts, then 27_report_figures.py, then this.

    python scripts/28_report.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import INTERIM_DIR, OUTPUT_DIR, PRICE_DIR, UNIVERSE_DIR, holdings_group
from src.report_builder import Report

ARKD, QQQD = OUTPUT_DIR / "ark", OUTPUT_DIR / "ndx"
COMP = OUTPUT_DIR / "comparison"
FIG = OUTPUT_DIR / "report_figures"

# Loughran and McDonald (2011): Table II means for the full 10-K, 1994 to 2008,
# and the 2011 list sizes.
LM = dict(negative=1.39, uncertainty=1.20, list_negative=2_337, list_uncertainty=285)
BRIEF = dict(list_negative=2_355, ark_companies=124)

MEASURE = {"Negative_prop": "Negative, word share", "Uncertainty_prop": "Uncertainty, word share",
           "Negative_tfidf": "Negative, tf.idf", "Uncertainty_tfidf": "Uncertainty, tf.idf"}
MODE = {"full": "Risk factors restated", "partial_update": "No material change, updates given",
        "reference_only": "No material change, reader referred to the annual report",
        "omitted": "Nothing disclosed", "not_found": "No Item 1A heading located"}
TRANSITION = {"to_reference": "Stopped restating", "to_full": "Started restating",
              "stays_full": "Kept restating", "stays_reference": "Kept referring"}
FILTER = {"Combine share classes by company CIK": "Merge share classes by company (CIK)",
          "foreign_reporting_forms": "Files 20-F or 40-F, not 10-K or 10-Q",
          "no_report_evidence": "No 10-K, 10-Q, 20-F or 40-F on record",
          "first_10x_after_sample": "First 10-K or 10-Q filed after the sample window",
          "10x_outside_sample": "10-K or 10-Q filed only outside the sample window",
          "incomplete_cached_history": "Filing history incomplete",
          "All 10-K/Q and amendments": "All 10-K and 10-Q filings and amendments",
          "Minimum words: 2,000 K / 1,000 Q": "At least 2,000 words (10-K) or 1,000 (10-Q)",
          "Earliest company filing each quarter": "One filing per company per quarter, the earliest",
          "Eligible text filings": "Filings in the text sample",
          "Usable day 0 and prior price at least $3": "Event day priced and day -1 price at least $3",
          "Outcome window elapsed by market cutoff": "Outcome window complete by the market-data cutoff",
          "60 observed returns before and after": "60 daily returns observed before and after",
          "60 observed returns before filing": "60 daily returns observed before the filing",
          "Complete pre/post volatility windows": "Complete volatility windows before and after",
          "Accession-matched outstanding shares": "Share count on the filing's cover page",
          "Complete liquidity and model controls": "Dollar volume and other controls available"}


# ------------------------------------------------------------------ helpers
def p_text(v):
    if not np.isfinite(v):
        return "not estimable"
    return "p < 0.001" if v < .001 else f"p = {v:.3f}"


def p_short(v):
    if v is None or not np.isfinite(v):
        return "n.e."
    return "< 0.001" if v < .001 else f"{v:.3f}"


def show(frame, **spec):
    out = frame.copy()
    for column, how in spec.items():
        if how == "int":
            out[column] = out[column].map(lambda v: "" if pd.isna(v) else f"{int(round(v)):,}")
        elif how == "p":
            out[column] = out[column].map(p_short)
        else:
            out[column] = out[column].map(lambda v: "" if pd.isna(v) else how.format(v))
    return out


def one(frame, **conditions):
    mask = pd.Series(True, index=frame.index)
    for column, value in conditions.items():
        mask &= frame[column].eq(value)
    hit = frame.loc[mask]
    if len(hit) != 1:
        raise ValueError(f"expected one row for {conditions}, found {len(hit)}")
    return hit.iloc[0]


def diff(frame, **conditions):
    """A difference-test row: two-way clustered inference, or company clusters when
    that covariance was not positive definite. Returns (row, fallback_used)."""
    two = one(frame[frame.inference.eq("firm_quarter_cluster")], **conditions)
    if two.status == "ok":
        return two, False
    return one(frame[frame.inference.eq("firm_cluster")], **conditions), True


def p_mark(row, fallback):
    return p_short(row.p) + ("*" if fallback else "")


def signed(v, digits=2):
    return f"{0:.{digits}f}" if abs(v) < 0.5 * 10 ** -digits else f"{v:+.{digits}f}"


def pp(v, digits=3):
    return f"{100 * v:+.{digits}f} pp"


def read(path, **kw):
    return pd.read_csv(path, **kw)


def centred_annual(frame, measure):
    f = frame.copy()
    f["adj"] = f[measure] - f.groupby("cik")[measure].transform("mean") + f[measure].mean()
    f["year"] = f.quarter.str[:4]
    return 100 * f.groupby("year").adj.mean()


# --------------------------------------------------------------------- data
def load():
    d = {}
    d["audit"] = json.loads((ARKD / "audit.json").read_text())
    d["audit_q"] = json.loads((QQQD / "audit.json").read_text())
    d["t1u"], d["t1"] = read(ARKD / "table1_universe.csv"), read(ARKD / "table1.csv")
    d["t1u_q"], d["t1_q"] = read(QQQD / "table1_universe.csv"), read(QQQD / "table1.csv")
    for run, folder in [("ark", ARKD), ("ndx", QQQD)]:
        d[f"text_{run}"] = read(folder / "text_sample.csv", dtype={"cik": str})
        d[f"t3_{run}"] = read(folder / "table3.csv")
        d[f"t4_{run}"] = read(folder / "table4.csv")
        d[f"t5_{run}"] = read(folder / "table5.csv")
        d[f"t6_{run}"] = read(folder / "table6.csv")
        d[f"sw_{run}"] = read(folder / "disclosure" / "switch_regressions.csv")
        d[f"dec_{run}"] = read(folder / "disclosure" / "decomposition.csv")
    d["events"] = read(ARKD / "disclosure" / "switch_events.csv")
    d["tr"] = read(COMP / "corrected_trends.csv")
    d["diff"] = read(COMP / "differences.csv")
    d["diff_ex"] = read(COMP / "differences_excluding_item_1a.csv")
    d["odiff"] = read(COMP / "outcome_differences.csv")
    universe = read(UNIVERSE_DIR / "universe.csv", dtype={"cik": str})
    universe["cik"] = universe.cik.str.zfill(10)
    universe["group"] = universe.funds.map(holdings_group)
    d["universe"] = universe
    label = dict(zip(universe.cik, universe.group))
    text = read(OUTPUT_DIR / "all" / "text_sample.csv", dtype={"cik": str})
    text["cik"] = text.cik.str.zfill(10)
    text["group"] = text.cik.map(label)
    d["text"] = text
    sections = read(INTERIM_DIR / "risk_sections.csv", dtype={"cik": str})
    sections = sections[sections.accession.isin(text.accession)].copy()
    sections["cik"] = sections.cik.str.zfill(10)
    sections["group"] = sections.cik.map(label)
    d["sections"] = sections
    d["levels"] = read(FIG / "figB2_levels.csv")
    d["slopes"] = read(FIG / "figB2_slopes.csv")
    d["cases"] = read(FIG / "fig2_selected.csv")
    vix = read(PRICE_DIR / "prices.csv", index_col=0, parse_dates=True)["^VIX"]
    d["vix_q"] = vix.groupby(vix.index.to_period("Q").astype(str)).mean().loc["2021Q1":"2026Q3"]
    return d


def in_group(frame, name):
    return frame[frame.group.isin([name, "BOTH"])]


def summary_table(text):
    rows = []
    for form in ["10-K", "10-Q"]:
        part = text[text.form.eq(form)]
        for m, label in MEASURE.items():
            s = part[m] * (100 if m.endswith("prop") else 1)
            rows.append({"Form": form, "Measure": label, "N": len(s), "Mean": s.mean(), "SD": s.std(),
                         "P25": s.quantile(.25), "Median": s.median(), "P75": s.quantile(.75)})
    return show(pd.DataFrame(rows), N="int", Mean="{:.3f}", SD="{:.3f}", P25="{:.3f}",
                Median="{:.3f}", P75="{:.3f}")


def words_table(t3):
    neg = t3[t3.category.eq("Negative")].head(30).reset_index(drop=True)
    unc = t3[t3.category.eq("Uncertainty")].head(30).reset_index(drop=True)
    first, second = slice(0, 15), slice(15, 30)
    table = pd.DataFrame({
        "Rank": neg["rank"][first].to_numpy(), "Negative word": neg.word[first].to_numpy(),
        "Share (%)": neg.share_pct[first].to_numpy(), "Uncertainty word": unc.word[first].to_numpy(),
        "Share (%) ": unc.share_pct[first].to_numpy(),
        "Rank ": neg["rank"][second].to_numpy(), "Negative word ": neg.word[second].to_numpy(),
        "Share (%)  ": neg.share_pct[second].to_numpy(), "Uncertainty word ": unc.word[second].to_numpy(),
        "Share (%)   ": unc.share_pct[second].to_numpy()})
    return show(table, **{"Rank": "int", "Rank ": "int", "Share (%)": "{:.2f}", "Share (%) ": "{:.2f}",
                          "Share (%)  ": "{:.2f}", "Share (%)   ": "{:.2f}"})


def trend_table(t4):
    within = t4[t4.model.eq("within_firm_trend") & t4.inference.eq("firm_quarter_cluster")]
    agg = t4[t4.model.eq("aggregate_trend") & t4.inference.eq("HAC4")]
    merged = agg.merge(within, on=["sample", "measure"], suffixes=("_a", "_w"))
    merged = merged[merged["sample"].isin(["10-K", "10-Q"])]
    merged["Measure"] = merged.measure.map(MEASURE)
    scale = np.where(merged.measure.str.endswith("prop"), 100, 1)
    out = pd.DataFrame({"Report": merged["sample"], "Measure": merged.Measure,
                        "Aggregate slope": scale * merged.coef_a, "Newey-West t": merged.t_a,
                        "Within-company slope": scale * merged.coef_w, "t": merged.t_w,
                        "p": merged.p_w, "Filings": merged.n_w})
    return show(out, **{"Aggregate slope": "{:+.3f}", "Newey-West t": "{:.2f}",
                        "Within-company slope": "{:+.3f}", "t": "{:.2f}", "p": "p", "Filings": "int"})


def volatility_table(t5):
    t = t5[t5.inference.eq("firm_quarter_cluster")].copy()
    t["Prior volatility"] = np.where(t.model.eq("volatility_with_prevol"), "Yes", "No")
    out = pd.DataFrame({"Report": t["sample"], "Measure": t.measure.map(MEASURE),
                        "Prior volatility": t["Prior volatility"], "Filings": t.n,
                        "Effect per SD (pp)": 100 * t.effect_1sd, "Detectable (pp)": 100 * t.mde80_1sd,
                        "p": t.p})
    return show(out, Filings="int", **{"Effect per SD (pp)": "{:+.2f}", "Detectable (pp)": "{:.2f}", "p": "p"})


def return_table(t6):
    t = t6[t6.inference.eq("firm_quarter_cluster")]
    out = pd.DataFrame({"Report": t["sample"], "Measure": t.measure.map(MEASURE), "Filings": t.n,
                        "Effect per SD (pp)": 100 * t.effect_1sd, "Detectable (pp)": 100 * t.mde80_1sd,
                        "p": t.p})
    return show(out, Filings="int", **{"Effect per SD (pp)": "{:+.2f}", "Detectable (pp)": "{:.2f}", "p": "p"})


def filters_table(t1u, t1):
    a = t1u.rename(columns={"filter": "Filter", "removed": "Removed", "remaining": "Remaining", "unit": "Unit"})
    a["Filter"] = a.Filter.map(FILTER).fillna(a.Filter)
    b = t1.rename(columns={"sample": "Sample", "filter": "Filter", "removed": "Removed",
                           "remaining": "Remaining", "companies": "Companies"})
    b["Filter"] = b.Filter.map(FILTER).fillna(b.Filter)
    b["Sample"] = b.Sample.where(b.Sample.ne(b.Sample.shift()), "")
    return (show(a, Removed="int", Remaining="int"),
            show(b[["Sample", "Filter", "Removed", "Remaining", "Companies"]], Removed="int",
                 Remaining="int", Companies="int"))


# ------------------------------------------------------------------- report
def main() -> int:
    d = load()
    a = d["audit"]
    sec = d["sections"]
    ark_sec = in_group(sec, "ARK")
    q_loc = ark_sec[ark_sec.form.eq("10-Q") & ark_sec.risk_found]
    k_loc = ark_sec[ark_sec.form.eq("10-K") & ark_sec.risk_found]
    filers = d["universe"][d["universe"].status.eq("domestic_filer")]
    n_ark = int(filers.group.isin(["ARK", "BOTH"]).sum())
    n_qqq = int(filers.group.isin(["NDX", "BOTH"]).sum())
    n_both = int(filers.group.eq("BOTH").sum())

    # ---- disclosure practice, ARK holdings
    mode_n = q_loc.risk_mode.value_counts()
    n_q = len(q_loc)
    share = {m: 100 * mode_n.get(m, 0) / n_q for m in ["full", "partial_update", "reference_only", "omitted"]}
    restated = q_loc[q_loc.risk_mode.eq("full")]
    words_full = restated.risk_words.median()
    dens = {k: 100 * restated[c].mean() for k, c in [("u_in", "Uncertainty_prop_risk"), ("u_out", "Uncertainty_prop_body"),
                                                     ("n_in", "Negative_prop_risk"), ("n_out", "Negative_prop_body")]}
    words_ref = q_loc[q_loc.risk_mode.eq("reference_only")].risk_words.median()
    risk_share_k = 100 * k_loc.risk_share.mean()
    coverage = 100 * ark_sec.risk_found.mean()
    correlation = [c for c in a["correlations"] if c["form"] == "All"][0]["prop"]

    # ---- ARK trends
    t4 = d["t4_ark"]
    within = t4[t4.model.eq("within_firm_trend") & t4.inference.eq("firm_quarter_cluster")]
    W = lambda form, m: one(within, sample=form, measure=m)
    a_kn, a_ku = W("10-K", "Negative_prop"), W("10-K", "Uncertainty_prop")
    a_kn_t, a_ku_t = W("10-K", "Negative_tfidf"), W("10-K", "Uncertainty_tfidf")
    a_qu, a_qu_t = W("10-Q", "Uncertainty_prop"), W("10-Q", "Uncertainty_tfidf")
    agg = t4[t4.model.eq("aggregate_trend")]
    nw_kn = one(agg, sample="10-K", measure="Negative_prop", inference="HAC4")
    ols_kn = one(agg, sample="10-K", measure="Negative_prop", inference="OLS")
    nw_qu = one(agg, sample="10-Q", measure="Uncertainty_prop", inference="HAC4")
    n_agg_k, n_agg_q = int(nw_kn.n), int(nw_qu.n)
    tr = d["tr"]
    T = lambda run, form, cat, scope: one(tr, run=run, sample=form, category=cat, scope=scope)
    c_kn_w, c_kn_b = T("ark", "10-K", "Negative", "whole filing"), T("ark", "10-K", "Negative", "excluding Item 1A")
    c_ku_w, c_ku_b = T("ark", "10-K", "Uncertainty", "whole filing"), T("ark", "10-K", "Uncertainty", "excluding Item 1A")
    c_ks = T("ark", "10-K", "Section length", "Item 1A share of words")
    c_qn_w, c_qn_b = T("ark", "10-Q", "Negative", "whole filing"), T("ark", "10-Q", "Negative", "excluding Item 1A")
    c_qu_w, c_qu_b = T("ark", "10-Q", "Uncertainty", "whole filing"), T("ark", "10-Q", "Uncertainty", "excluding Item 1A")
    c_qs = T("ark", "10-Q", "Section length", "Item 1A share of words")
    shown = lambda r: round(100 * r.coef, 3)
    cut_n, cut_u = 1 - shown(c_kn_b) / shown(c_kn_w), 1 - shown(c_ku_b) / shown(c_ku_w)

    # ---- series endpoints, as Figure 1 computes them
    k10 = in_group(d["text"][d["text"].form.eq("10-K")], "ARK")
    ends = {m: centred_annual(k10, m) for m in ["Negative_prop", "Uncertainty_prop"]}
    arkq = in_group(d["text"][d["text"].form.eq("10-Q")], "ARK").copy()
    arkq["adj"] = arkq.Negative_prop - arkq.groupby("cik").Negative_prop.transform("mean") + arkq.Negative_prop.mean()
    q1_cells = arkq.groupby("quarter").size()
    q1_cells = q1_cells[q1_cells.index.str.endswith("Q1")]
    vix_peak = d["vix_q"].idxmax()
    names = d["text_ark"].drop_duplicates("ticker").set_index("ticker").company.str.title()

    # ---- ARK market outcomes
    t5 = d["t5_ark"][d["t5_ark"].inference.eq("firm_quarter_cluster")]
    V = lambda form, m, spec: one(t5, sample=form, measure=m, model=spec)
    v_qt_no, v_qt_with = V("10-Q", "Uncertainty_tfidf", "volatility_without_prevol"), V("10-Q", "Uncertainty_tfidf", "volatility_with_prevol")
    v_qp_no, v_qp_with = V("10-Q", "Uncertainty_prop", "volatility_without_prevol"), V("10-Q", "Uncertainty_prop", "volatility_with_prevol")
    v_k_mde = 100 * t5[t5["sample"].eq("10-K")].mde80_1sd.min(), 100 * t5[t5["sample"].eq("10-K")].mde80_1sd.max()
    n_sig_after = int((t5[t5.model.eq("volatility_with_prevol")].p < .05).sum())
    sw = d["sw_ark"]
    S = lambda form, m, spec: one(sw, sample=form, measure=m, model=spec)
    lv_w, lv_b = S("10-Q", "Uncertainty_prop_total", "volatility_with_prevol"), S("10-Q", "Uncertainty_prop_body", "volatility_with_prevol")
    t6 = d["t6_ark"][d["t6_ark"].inference.eq("firm_quarter_cluster")]
    r_q, r_all = one(t6, sample="10-Q", measure="Negative_prop"), one(t6, sample="All", measure="Negative_prop")
    lr_w, lr_b = S("10-Q", "Negative_prop_total", "filing_return"), S("10-Q", "Negative_prop_body", "filing_return")

    # ---- decomposition and cases
    dec = d["dec_ark"]
    to_ref_u = one(dec, category="Uncertainty", transition="to_reference")
    to_ref_n = one(dec, category="Negative", transition="to_reference")
    cases, ev = d["cases"], d["events"]
    drop, rise = cases.iloc[0], cases.iloc[1]
    drop_ev = ev[ev.ticker.eq(drop.ticker) & ev.filing_date.eq(drop.filing_date)].iloc[0]
    prior_ref = ev[ev.ticker.eq(rise.ticker) & ev.transition.eq("to_reference")
                   & (pd.to_datetime(ev.filing_date) < pd.Timestamp(rise.filing_date))]
    rise_years = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}[int(round(
        (pd.Timestamp(rise.filing_date) - pd.to_datetime(prior_ref.filing_date).max()).days / 365.25))]
    levels, slopes = d["levels"], d["slopes"]
    top_level, low_level = levels.sort_values("level", ascending=False).head(3), levels.sort_values("level").head(3)
    top_rise = slopes.sort_values("slope", ascending=False).head(3)

    # ---- comparison with QQQ holdings (identical located filings; QQQ less ARK)
    dx, od = d["diff_ex"], d["odiff"]
    DX = lambda model, form, cat, scope: diff(dx, model=model, sample=form, category=cat, scope=scope)
    OD = lambda outcome, form, m, spec: diff(od, outcome=outcome, sample=form, measure_name=m, model=spec)
    lvl_kn_w, lvl_kn_b = DX("level_difference", "10-K", "Negative", "whole filing"), DX("level_difference", "10-K", "Negative", "excluding Item 1A")
    lvl_ku_w, lvl_ku_b = DX("level_difference", "10-K", "Uncertainty", "whole filing"), DX("level_difference", "10-K", "Uncertainty", "excluding Item 1A")
    trd_kn_w, trd_kn_b = DX("trend_difference", "10-K", "Negative", "whole filing"), DX("trend_difference", "10-K", "Negative", "excluding Item 1A")
    trd_ku_w, trd_ku_b = DX("trend_difference", "10-K", "Uncertainty", "whole filing"), DX("trend_difference", "10-K", "Uncertainty", "excluding Item 1A")
    lvl_ks = DX("level_difference", "10-K", "Section length", "Item 1A share of words")
    ret_w, ret_b = OD("return", "10-Q", "Negative_prop_total", "filing_return"), OD("return", "10-Q", "Negative_prop_body", "filing_return")
    vol_w, vol_b = OD("volatility", "10-Q", "Uncertainty_prop_total", "volatility_with_prevol"), OD("volatility", "10-Q", "Uncertainty_prop_body", "volatility_with_prevol")
    kvol_w, kvol_b = OD("volatility", "10-K", "Uncertainty_prop_total", "volatility_with_prevol"), OD("volatility", "10-K", "Uncertainty_prop_body", "volatility_with_prevol")
    qqq_sec = in_group(sec, "NDX")
    qq_loc = qqq_sec[qqq_sec.form.eq("10-Q") & qqq_sec.risk_found]
    share_q = {m: 100 * qq_loc.risk_mode.eq(m).mean() for m in ["full", "reference_only"]}
    risk_share_k_q = 100 * qqq_sec[qqq_sec.form.eq("10-K") & qqq_sec.risk_found].risk_share.mean()
    t4q = d["t4_ndx"]
    wq = t4q[t4q.model.eq("within_firm_trend") & t4q.inference.eq("firm_quarter_cluster")]
    q_kn, q_ku = one(wq, sample="10-K", measure="Negative_prop"), one(wq, sample="10-K", measure="Uncertainty_prop")
    t5q = d["t5_ndx"][d["t5_ndx"].inference.eq("firm_quarter_cluster")]
    t6q = d["t6_ndx"][d["t6_ndx"].inference.eq("firm_quarter_cluster")]
    q_min_p = min(t5q[t5q.model.eq("volatility_with_prevol")].p.min(), t6q.p.min())
    lm_k = {run: (100 * d[f"text_{run}"][d[f"text_{run}"].form.eq("10-K")].Negative_prop.mean(),
                  100 * d[f"text_{run}"][d[f"text_{run}"].form.eq("10-K")].Uncertainty_prop.mean())
            for run in ["ark", "ndx"]}
    a_q = d["audit_q"]

    # =================================================================== BODY
    body = Report(
        "Uncertainty and Sentiment in the Filings of ARK ETF Holdings, 2021 to 2026",
        f"FRE-GY 7871 A, Assignment 1. {a['expected_original_filings']:,} 10-K and 10-Q filings by "
        f"{a['final_companies']} companies held by the six ARK ETFs on 9 September 2026, scored on the "
        f"Loughran-McDonald negative and uncertainty word lists. Methods, supplementary tables and "
        f"further figures are in the separate appendix.",
        running_head="Uncertainty and sentiment in ARK holdings' filings")

    body.section("Summary")
    body.p(
        f"Negative and uncertain language in the annual reports of ARK holdings rises every year: within "
        f"company, negative words gain {pp(a_kn.coef)} a year and uncertainty words {pp(a_ku.coef)} "
        f"(both {p_text(a_kn.p)}, Table 4). Quarterly reports show no trend in negative words and a small "
        f"fall in the uncertainty tf.idf score. In quarterly reports that score predicts the following "
        f"quarter's volatility before the prior-volatility control and weakly after it "
        f"({100 * v_qt_no.effect_1sd:+.1f} pp per standard deviation without the control, "
        f"{100 * v_qt_with.effect_1sd:+.1f} pp with it, {p_text(v_qt_with.p)}, Table 5). Negative tone "
        f"does not predict the four-session return; in quarterly "
        f"reports the test cannot detect an effect below {100 * r_q.mde80_1sd:.1f} pp per standard "
        f"deviation (Table 6). Of the quarterly reports whose risk-factor section, Item 1A, can be located, "
        f"only {share['full']:.0f}% restate it; {share['reference_only']:.0f}% refer the reader to the "
        f"annual report, and that choice moves a word-share measure by itself. "
        f"Excluding Item 1A cuts the annual-report trends by {100 * min(cut_n, cut_u):.0f}% to "
        f"{100 * max(cut_n, cut_u):.0f}% and removes the one return association in the data (Section 6). "
        f"QQQ holdings carry fewer negative and uncertainty words in their annual reports; the gap is the "
        f"length of their risk sections, and outside Item 1A the two portfolios write alike except that "
        f"ARK's negative tone rises faster (Section 7).")

    # ---------------------------------------------------------------- 1
    body.section("1. Sample")
    body.p(
        f"The six ARK portfolios held {int(d['t1u'].iloc[0].remaining)} identifiers on 9 September 2026; "
        f"the assignment brief counts {BRIEF['ark_companies']} companies from an earlier snapshot. "
        f"Removing funds, cash and non-US listings, merging share classes and dropping companies that "
        f"file 20-F or 40-F leaves {a['final_companies']} SEC filers, {n_both} of them also held by QQQ, the Invesco Nasdaq-100 ETF. "
        f"They filed {a['expected_original_filings']:,} original 10-K and 10-Q documents from January "
        f"2021 to 9 September 2026, with {a['parse_failures']} parse failures; the {a['amendments']} "
        f"amendments are never scored. Table 1 lists every filter. The volatility and return samples "
        f"are filtered separately because a recent filing is scored before its outcome window has elapsed. "
        f"The assignment's window ends in 2025; the executed notebook and the data workbook hold the same "
        f"exhibits for that window.")
    panel_a, panel_b = filters_table(d["t1u"], d["t1"])
    body.sub("Table 1. Sample filters and the filings each removed")
    body.note("Panel A. From holding identifiers to SEC filers. Absence of 10-K or 10-Q filings is read "
              "from EDGAR, never inferred from domicile.")
    body.table(panel_a)
    body.note("Panel B. From filings to the three analysis samples.")
    body.table(panel_b, keep_together=False)

    # ---------------------------------------------------------------- 2
    body.section("2. Measures")
    body.p(
        f"The lists are the active entries of the March 2026 Loughran-McDonald Master Dictionary: "
        f"{a['lexicon_counts']['Negative']:,} negative and {a['lexicon_counts']['Uncertainty']} uncertainty "
        f"words ({a['lexicon_overlap']} on both). The brief's count of {BRIEF['list_negative']:,} includes "
        f"ten negative words since retired. Each filing is scored on each list twice: as a share of its "
        f"words, and with the tf.idf weighting of equation (1) in Loughran and McDonald (2011), fitted on "
        f"the ARK corpus, under which a word present in every filing carries no weight. Word shares are "
        f"in percent and differences in percentage points (pp). ARK annual reports average "
        f"{lm_k['ark'][0]:.2f}% negative and {lm_k['ark'][1]:.2f}% uncertainty words (Table 2), against "
        f"{LM['negative']:.2f}% and {LM['uncertainty']:.2f}% for the 1994 to 2008 10-Ks of Loughran and "
        f"McDonald; the two shares correlate at {correlation:.2f} across filings. Table 3 shows why the "
        f"scorings differ for uncertainty: MAY is "
        f"{d['t3_ark'][d['t3_ark'].category.eq('Uncertainty')].share_pct.iloc[0]:.0f}% of uncertainty "
        f"counts and appears in {a['uncertainty_word_document_pct']['MAY']:.0f}% of filings, so it counts "
        f"fully in the word share and not at all in tf.idf.")
    body.sub("Table 2. Summary statistics by report type")
    body.note("Word shares in percent; tf.idf in score units. Annual and quarterly reports are kept apart "
              "because a 10-K is longer and heavier in risk language.")
    body.table(summary_table(d["text_ark"]))
    body.sub("Table 3. Thirty most frequent words on each list")
    body.note("Share: the word's count divided by all occurrences of its own list in the ARK text sample.")
    body.table(words_table(d["t3_ark"]), keep_together=False)

    # ---------------------------------------------------------------- 3
    body.section("3. Trends")
    body.figure(FIG / "fig1_ark_series.png", "Figure 1")
    body.note(
        f"Figure 1. Both measures by quarter, ARK holdings, with the VIX. Lines are company-centred means "
        f"(each company's score less its own mean, plus the group mean) with 95% bands; annual reports are "
        f"aggregated by filing year because they cluster in the first calendar quarter. First-quarter "
        f"10-Q cells hold {int(q1_cells.min())} to {int(q1_cells.max())} reports, hence their wider bands.")
    body.p(
        f"Annual-report tone rises every year: negative words from {ends['Negative_prop']['2021']:.2f}% "
        f"in 2021 filings to {ends['Negative_prop']['2026']:.2f}% in 2026, uncertainty words from "
        f"{ends['Uncertainty_prop']['2021']:.2f}% to {ends['Uncertainty_prop']['2026']:.2f}%. Quarterly "
        f"reports show no trend in negative words; their uncertainty share falls on the aggregate test "
        f"(Newey-West t = {nw_qu.t:.2f}) but not within company ({p_text(a_qu.p)}), the pattern the "
        f"assignment warns of, and their uncertainty tf.idf score falls on both tests. The VIX, in the "
        f"bottom strip, peaks in {vix_peak}; the report offers no test of its relation to filing tone. "
        f"Table 4 tests the trends two ways: a regression of the quarterly mean on time with Newey-West "
        f"(four lags) standard errors, and a within-company regression with company and seasonal effects.")
    body.sub("Table 4. Trend tests, aggregate and within company")
    body.note(f"Slopes per year: percentage points for word shares, score units for tf.idf. Aggregate: "
              f"regression of the quarterly mean on time, {n_agg_k} quarters with annual reports and "
              f"{n_agg_q} with quarterly reports, Newey-West standard errors. Within company: filing-level, "
              f"company and seasonal effects, two-way clustered inference.")
    body.table(trend_table(d["t4_ark"]))
    body.p(
        f"Believed: the within-company annual-report trends. Both word shares rise at {p_text(a_kn.p)} "
        f"(t = {a_kn.t:.1f} and {a_ku.t:.1f}), the aggregate Newey-West test agrees (t = {nw_kn.t:.1f} "
        f"for negative words against {ols_kn.t:.1f} with ordinary errors), and the tf.idf score confirms "
        f"the negative trend ({a_kn_t.coef:+.2f} score units a year, {p_text(a_kn_t.p)}). Not believed as "
        f"a change in how distinctively companies hedge: the uncertainty tf.idf slope is flat "
        f"({p_text(a_ku_t.p)}), so the rise in uncertainty comes through words such as MAY. Section 6 "
        f"shows that Item 1A lengthening accounts for {100 * cut_n:.0f}% of the negative rise and "
        f"{100 * cut_u:.0f}% of the uncertainty rise. Quarterly reports show no trend on any scoring "
        f"except a fall in the uncertainty tf.idf score ({a_qu_t.coef:+.2f} a year, {p_text(a_qu_t.p)}).")

    # ---------------------------------------------------------------- 4
    body.section("4. Uncertainty and post-filing volatility")
    body.sub("Table 5. Volatility over the following quarter on uncertainty, with and without prior volatility")
    body.note("Effect: change in annualised volatility, in percentage points, per one standard deviation of "
              "the measure. Detectable: the effect this design finds with 80% power at 5%. Controls: log "
              "size, log dollar volume, prior excess return; company and calendar-quarter effects.")
    body.table(volatility_table(d["t5_ark"]), keep_together=False)
    body.p(
        f"The gap between the two estimates is the result. In quarterly reports the tf.idf score adds "
        f"{100 * v_qt_no.effect_1sd:+.2f} pp of annualised volatility per standard deviation without the "
        f"control ({p_text(v_qt_no.p)}) and {100 * v_qt_with.effect_1sd:+.2f} pp with it "
        f"({p_text(v_qt_with.p)}); the word share moves from {100 * v_qp_no.effect_1sd:+.2f} pp "
        f"({p_text(v_qp_no.p)}) to {100 * v_qp_with.effect_1sd:+.2f} pp ({p_text(v_qp_with.p)}). The "
        f"control removes about a quarter of each estimate. Annual reports show nothing, with detectable effects of "
        f"{v_k_mde[0]:.0f} to {v_k_mde[1]:.0f} pp. Believed weakly: {n_sig_after} of the twelve estimates "
        f"is significant after the control, at {p_text(v_qt_with.p)}, against detectable effects of "
        f"{100 * v_qt_with.mde80_1sd:.1f} pp; on the quarterly reports whose Item 1A is located, the "
        f"word-share estimate with the control is {100 * lv_w.effect_1sd:+.1f} pp ({p_text(lv_w.p)}) and, "
        f"excluding the section, {100 * lv_b.effect_1sd:+.1f} pp ({p_text(lv_b.p)}).")

    # ---------------------------------------------------------------- 5
    body.section("5. Sentiment and the filing-period return")
    body.sub("Table 6. Four-session excess return on negative tone, with controls")
    body.note("Excess return over the S&P 500 ETF from the filing event day to day 3, in percentage points "
              "per standard deviation of the measure. Same controls as Table 5 plus prior volatility.")
    body.table(return_table(d["t6_ark"]))
    body.p(
        f"No estimate reaches 5%: the closest is {100 * r_q.effect_1sd:+.2f} pp per standard deviation "
        f"of the negative word share in quarterly reports ({p_text(r_q.p)}). Not believed as evidence of "
        f"no effect: the test is underpowered, with a detectable effect of {100 * r_q.mde80_1sd:.1f} pp per "
        f"standard deviation in quarterly reports and {100 * r_all.mde80_1sd:.1f} pp across all filings. "
        f"Not believed as evidence of an effect either. Section 6 shows that on the quarterly reports whose "
        f"Item 1A is located the whole-filing estimate is {100 * lr_w.effect_1sd:+.2f} pp "
        f"({p_text(lr_w.p)}) and that this is a disclosure effect rather than a tone effect.")

    # ---------------------------------------------------------------- 6
    body.section("6. The risk-factor section")
    body.p(
        f"Of {n_q:,} ARK quarterly reports with a located Item 1A heading ({coverage:.0f}% of "
        f"filings), {share['full']:.0f}% restate, {share['partial_update']:.0f}% claim no material change "
        f"but add updates, {share['reference_only']:.0f}% refer the reader to the annual report and "
        f"{share['omitted']:.0f}% disclose nothing. A restated section runs to a median of "
        f"{words_full:,.0f} words, a reference to {words_ref:.0f}; in annual reports Item 1A is "
        f"{risk_share_k:.0f}% of all words. Item 1A is the most hedged and most negative part of a filing: "
        f"in restated sections {dens['u_in']:.1f}% of words are uncertainty words and {dens['n_in']:.1f}% "
        f"negative words, against {dens['u_out']:.1f}% and {dens['n_out']:.1f}% in the rest of the same "
        f"filings. A word share divides list words by all words, so replacing a {words_full / 1000:.0f},000-word "
        f"section with a {words_ref:.0f}-word reference removes far more list words than words, and the "
        f"whole-filing share falls although nothing else in the filing has changed. Across "
        f"{int(to_ref_u.n)} such quarters by {int(to_ref_u.companies)} companies the uncertainty share falls "
        f"{abs(to_ref_u.change_pp):.2f} pp and the negative share {abs(to_ref_n.change_pp):.2f} pp, while the "
        f"share of the rest of the filing moves {signed(to_ref_u.body_change_pp)} and "
        f"{signed(to_ref_n.body_change_pp)} pp. Figure 2 shows the two largest cases; Table 7 ranks the "
        f"holdings on the measure excluding Item 1A; Table 8 repeats each result on the same filings without "
        f"Item 1A.")
    body.figure(FIG / "fig2_cases.png", "Figure 2")
    body.note(
        f"Figure 2. Item 1A words (bars) and uncertainty word share of the whole filing (solid) and "
        f"excluding Item 1A (dashed, hollow squares), quarterly reports. Left: {drop.ticker} "
        f"({names[drop.ticker]}), "
        f"{pd.Timestamp(drop.filing_date):%B %Y}, {drop.prev_risk_words:,.0f} to {drop.risk_words:,.0f} "
        f"words; the whole-filing share falls {abs(100 * drop_ev.Uncertainty_change):.2f} pp, the share "
        f"excluding Item 1A {abs(100 * drop_ev.Uncertainty_body_change):.2f} pp. Right: {rise.ticker} "
        f"({names[rise.ticker]}), "
        f"{pd.Timestamp(rise.filing_date):%B %Y}, restating after {rise_years} years, "
        f"{rise.prev_risk_words:,.0f} to {rise.risk_words:,.0f} words.")
    high, low = levels.sort_values("level", ascending=False).head(5), levels.sort_values("level").head(5)
    up, down = slopes.sort_values("slope", ascending=False).head(5), slopes.sort_values("slope").head(5)
    ranking = pd.DataFrame({
        "Rank": [str(i) for i in range(1, 6)],
        "Most uncertain (%)": [f"{t}  {v:.2f}" for t, v in zip(high.ticker, high.level)],
        "Least uncertain (%)": [f"{t}  {v:.2f}" for t, v in zip(low.ticker, low.level)],
        "Largest rise (pp a year)": [f"{t}  {v:+.3f}" for t, v in zip(up.ticker, up.slope)],
        "Largest fall (pp a year)": [f"{t}  {v:+.3f}" for t, v in zip(down.ticker, down.slope)]})
    body.sub("Table 7. ARK holdings ranked on uncertainty words excluding Item 1A")
    body.note(f"Level: latest annual report with a located Item 1A, {len(levels)} companies. Trend: "
              f"within-company slope over 2021 to 2026 for the {len(slopes)} companies with at least three "
              f"such reports; slopes rest on three to six observations and rank companies. Tickers; full "
              f"lists in Appendix Figure B2 and Table C8.")
    body.table(ranking)
    rows = [
        ("Annual reports: negative words, trend (pp a year)", c_kn_w, c_kn_b),
        ("Annual reports: uncertainty words, trend (pp a year)", c_ku_w, c_ku_b),
        ("Quarterly reports: negative words, trend (pp a year)", c_qn_w, c_qn_b),
        ("Quarterly reports: uncertainty words, trend (pp a year)", c_qu_w, c_qu_b),
    ]
    table7 = [{"Result": label, "Filings": w.n, "Whole filing": 100 * w.coef, "p": w.p,
               "Excluding Item 1A": np.nan if b is None else 100 * b.coef, "p ": np.nan if b is None else b.p}
              for label, w, b in rows]
    table7 += [
        {"Result": "Quarterly reports: volatility on uncertainty, with prior volatility (pp per SD)",
         "Filings": lv_w.n, "Whole filing": 100 * lv_w.effect_1sd, "p": lv_w.p,
         "Excluding Item 1A": 100 * lv_b.effect_1sd, "p ": lv_b.p},
        {"Result": "Quarterly reports: four-session return on negative words (pp per SD)",
         "Filings": lr_w.n, "Whole filing": 100 * lr_w.effect_1sd, "p": lr_w.p,
         "Excluding Item 1A": 100 * lr_b.effect_1sd, "p ": lr_b.p}]
    table7 = show(pd.DataFrame(table7), Filings="int", **{"Whole filing": "{:+.3f}", "p": "p",
                                                          "Excluding Item 1A": "{:+.3f}", "p ": "p"})
    body.sub("Table 8. The same results on the whole filing and excluding Item 1A, identical filings")
    body.note("Within-company trends and outcome regressions as in Tables 4 to 6, on the filings whose "
              "Item 1A heading was located. Word-share measures only.")
    body.table(table7, widths=[250, 45, 62, 45, 72, 45])
    body.p(
        f"Believed: the whole-filing measures record how much risk disclosure a company prints as much as "
        f"how it writes. Item 1A's share of the annual report grows {pp(c_ks.coef, 2)} a year, and "
        f"removing the section cuts the annual-report trends to {pp(c_kn_b.coef)} and {pp(c_ku_b.coef)}, "
        f"still at {p_text(c_kn_b.p)}. In quarterly reports the section shrinks "
        f"({pp(c_qs.coef, 2)} a year, {p_text(c_qs.p)}) as more companies stop restating, and the negative "
        f"share of the rest of the filing rises {pp(c_qn_b.coef)} a year ({p_text(c_qn_b.p)}) while the "
        f"whole-filing measure is flat. The return association on the whole filing "
        f"({100 * lr_w.effect_1sd:+.2f} pp, {p_text(lr_w.p)}) disappears excluding the section "
        f"({100 * lr_b.effect_1sd:+.2f} pp, {p_text(lr_b.p)}): a company that prints its risk factors "
        f"prints thousands of negative words and earns a lower return that quarter than one that refers "
        f"to the annual report; the design cannot separate that from whatever else marks those quarters. "
        f"Uncertainty is highest at {', '.join(top_level.ticker)} and lowest at {', '.join(low_level.ticker)}; "
        f"it rises fastest at {', '.join(top_rise.ticker)} and falls fastest at {', '.join(down.ticker[:3])} "
        f"(Table 7).")

    # ---------------------------------------------------------------- 7
    body.section("7. Comparison with QQQ holdings")
    body.p(
        f"The same pipeline was run on the {a_q['final_companies']} SEC filers among the QQQ (Nasdaq-100) "
        f"constituents of 9 September 2026, {a_q['expected_original_filings']:,} filings, {n_both} of the "
        f"companies being in both portfolios (Appendix Tables C4 to C7). QQQ annual reports average "
        f"{lm_k['ndx'][0]:.2f}% negative and {lm_k['ndx'][1]:.2f}% uncertainty words against ARK's "
        f"{lm_k['ark'][0]:.2f}% and {lm_k['ark'][1]:.2f}% (Table 2), and they trend upward within company "
        f"at {pp(q_kn.coef)} and {pp(q_ku.coef)} a year (both {p_text(q_kn.p)}), as ARK's do. No QQQ "
        f"volatility or return estimate reaches 5% (smallest {p_text(q_min_p)}). Of quarterly reports with "
        f"a located Item 1A, {share_q['full']:.0f}% restate risk factors and {share_q['reference_only']:.0f}% "
        f"refer to the annual report. Table 9 tests each difference in one regression on the companies "
        f"held by only one portfolio, whole filing and excluding Item 1A on identical filings; "
        f"Appendix Figure B7 shows the company-level distributions behind the level rows.")
    rows = [
        ("Annual reports: negative words, level (pp)", lvl_kn_w, lvl_kn_b),
        ("Annual reports: uncertainty words, level (pp)", lvl_ku_w, lvl_ku_b),
        ("Annual reports: negative words, trend (pp a year)", trd_kn_w, trd_kn_b),
        ("Annual reports: uncertainty words, trend (pp a year)", trd_ku_w, trd_ku_b),
    ]
    table8 = [{"Result": label, "Filings": w[0].n, "Whole filing": 100 * w[0].coef, "p": p_mark(*w),
               "Excluding Item 1A": "" if b is None else f"{100 * b[0].coef:+.3f}",
               "p ": "" if b is None else p_mark(*b)} for label, w, b in rows]
    table8 += [
        {"Result": "Quarterly reports: four-session return on negative words (pp per SD)",
         "Filings": ret_w[0].n, "Whole filing": 100 * ret_w[0].effect_1sd, "p": p_mark(*ret_w),
         "Excluding Item 1A": f"{100 * ret_b[0].effect_1sd:+.3f}", "p ": p_mark(*ret_b)},
        {"Result": "Quarterly reports: volatility on uncertainty, with prior volatility (pp per SD)",
         "Filings": vol_w[0].n, "Whole filing": 100 * vol_w[0].effect_1sd, "p": p_mark(*vol_w),
         "Excluding Item 1A": f"{100 * vol_b[0].effect_1sd:+.3f}", "p ": p_mark(*vol_b)},
        {"Result": "Annual reports: volatility on uncertainty, with prior volatility (pp per SD)",
         "Filings": kvol_w[0].n, "Whole filing": 100 * kvol_w[0].effect_1sd, "p": p_mark(*kvol_w),
         "Excluding Item 1A": f"{100 * kvol_b[0].effect_1sd:+.3f}", "p ": p_mark(*kvol_b)}]
    table8 = show(pd.DataFrame(table8), Filings="int", **{"Whole filing": "{:+.3f}"})
    fallback = any(r[1] for r in [lvl_kn_w, lvl_kn_b, lvl_ku_w, lvl_ku_b, lvl_ks, trd_kn_w, trd_kn_b,
                                  trd_ku_w, trd_ku_b, ret_w, ret_b, vol_w, vol_b, kvol_w, kvol_b])
    body.sub("Table 9. QQQ holdings less ARK holdings")
    body.note("Coefficient on a QQQ indicator (levels), on its interaction with time (trends) or with the "
              "measure (outcomes) in one regression on the companies held by only one portfolio. Level "
              "differences with calendar-quarter effects; outcome differences with the controls of Tables "
              "5 and 6 and company effects. Filings whose Item 1A heading was located."
              + (" * Company-clustered inference; the two-way clustered covariance was not positive definite."
                 if fallback else ""))
    body.table(table8, widths=[250, 45, 62, 45, 72, 45])
    body.p(
        f"Believed: on the raw scores ARK holdings read more negative and more uncertain than QQQ "
        f"holdings, and the whole of that gap is how much risk-factor text they print. QQQ annual reports "
        f"carry {abs(100 * lvl_kn_w[0].coef):.2f} pp fewer negative and {abs(100 * lvl_ku_w[0].coef):.2f} pp "
        f"fewer uncertainty words on the whole filing ({p_text(lvl_kn_w[0].p)}, {p_text(lvl_ku_w[0].p)}); "
        f"Item 1A takes {risk_share_k_q:.0f}% of their words against {risk_share_k:.0f}% of ARK's "
        f"(difference {abs(100 * lvl_ks[0].coef):.1f} pp, {p_text(lvl_ks[0].p)}); excluding the section the "
        f"gaps are {abs(100 * lvl_kn_b[0].coef):.3f} pp ({p_text(lvl_kn_b[0].p)}) and "
        f"{abs(100 * lvl_ku_b[0].coef):.3f} pp ({p_text(lvl_ku_b[0].p)}), and the two distributions in "
        f"Figure B7 overlap. The negative-tone return association of Section 6 belongs to ARK alone: QQQ "
        f"shows none, the difference is significant on the whole filing ({100 * ret_w[0].effect_1sd:+.1f} pp "
        f"per standard deviation, {p_text(ret_w[0].p)}) and gone excluding Item 1A "
        f"({100 * ret_b[0].effect_1sd:+.1f} pp, {p_text(ret_b[0].p)}), a disclosure effect rather than a "
        f"tone effect. The volatility coefficients do not differ in quarterly reports ({p_text(vol_w[0].p)}, "
        f"{p_text(vol_b[0].p)}); in annual reports they differ on the whole filing "
        f"({100 * kvol_w[0].effect_1sd:+.1f} pp per standard deviation, {p_text(kvol_w[0].p)}) and not "
        f"excluding Item 1A ({p_text(kvol_b[0].p)}). One difference survives the correction: ARK's negative "
        f"tone outside Item 1A rises faster, by {abs(100 * trd_kn_b[0].coef):.3f} pp a year "
        f"({p_text(trd_kn_b[0].p)}); its uncertainty trend is steeper only on the whole filing "
        f"({abs(100 * trd_ku_w[0].coef):.3f} pp a year, {p_text(trd_ku_w[0].p)}). Compared on the measure "
        f"excluding Item 1A, the two portfolios differ in that one trend and in nothing else.")

    body.link("Loughran, T., and B. McDonald, 2011, When is a liability not a liability? Textual analysis, "
              "dictionaries, and 10-Ks, Journal of Finance 66, 35-65. Code, executed notebook, tests and the "
              "data workbook: github.com/robynge/FRE-GY-7871A-Assignment1",
              "https://github.com/robynge/FRE-GY-7871A-Assignment1")

    # =============================================================== APPENDIX
    app = Report(
        "Appendix: Uncertainty and Sentiment in the Filings of ARK ETF Holdings",
        "Methods, supplementary figures and supplementary tables for the report of the same title. "
        "Section A gives every specification; Sections B and C hold the exhibits the report cites.",
        running_head="Appendix")

    app.section("A. Methods")
    app.sub("Word lists and parsing")
    app.p(
        f"Word lists are the entries with a positive year in the Negative and Uncertainty columns of the "
        f"Loughran-McDonald Master Dictionary, 1993 to 2025 release, updated March 2026: "
        f"{a['lexicon_counts']['Negative']:,} and {a['lexicon_counts']['Uncertainty']} words. Filing text "
        f"is the primary document with hidden inline-XBRL content removed and tables dropped where more "
        f"than 15% of non-space characters are digits. Tokens are alphabetic strings of at least two "
        f"characters, uppercased. Exhibits and material incorporated by reference are not recovered.")
    app.sub("Scores")
    app.equation(r"P_{cj}=\frac{\sum_{i \in c} tf_{ij}}{W_j}")
    app.equation(r"T_{cj}=\sum_{i \in c,\, tf_{ij}>0}"
                 r"\frac{1+\ln(tf_{ij})}{1+\ln(a_j)}\,\ln\!\left(\frac{N}{df_i}\right)")
    app.p(
        "P is the word share of list c in filing j and W the filing's word count. T is equation (1) of "
        "Loughran and McDonald (2011): tf is the count of word i in filing j, a the filing's average word "
        "frequency (words divided by distinct words), N the number of filings in the estimation corpus and "
        "df the number containing word i. Logarithms are natural. Document frequencies are fitted within "
        "each sample (ARK holdings, QQQ holdings), so tf.idf scores are comparable across filings within a "
        "sample and not across samples.")
    app.sub("Locating Item 1A")
    app.p("The section opens at an occurrence of the heading Item 1A followed by Risk Factors that satisfies "
          "four conditions, and the last such occurrence in the filing is taken:")
    app.bullets([
        "It is not preceded within 60 characters by a reference cue such as in, see, under or Part I.",
        "It is not followed within 90 characters by another item number, which marks a table of contents "
        "or a cross-reference index.",
        "It is followed by text opening with a capital letter, since a citation continues with a lowercase "
        "word or a punctuation mark.",
        "It carries the item label; filers who head the section Risk Factors alone are recorded as not "
        "located.",
    ])
    app.p("The section closes at the next item heading whose title is also present, such as Item 1B "
          "Unresolved Staff Comments or Item 2 Unregistered Sales. A bare SIGNATURES line is not treated as "
          "a closing marker. Disclosure mode is read from the section's first 800 characters and its "
          "length: sections over 400 words are full restatements unless they claim no material change, in "
          "which case they are partial updates; shorter sections that claim no material change or point to "
          "the annual report are reference-only; shorter sections that do neither are recorded as nothing "
          "disclosed. Every statistic on the section is computed on the text sample, so the section "
          "exhibits and the tone exhibits describe the same filings.")
    app.sub("Decomposition")
    app.equation(r"S = w\,S_{\mathrm{risk}} + (1-w)\,S_{\mathrm{body}}")
    app.equation(r"\Delta S = \bar w\,\Delta S_{\mathrm{risk}} + (1-\bar w)\,\Delta S_{\mathrm{body}}"
                 r" \;+\; \Delta w\,(\bar S_{\mathrm{risk}} - \bar S_{\mathrm{body}})")
    app.p("w is Item 1A's share of the filing's words and bars denote the mean over the two filings being "
          "compared. The first two terms are the language term and the third the composition term; the "
          "identity is exact. Comparisons are within company and within form. The language term inherits "
          "the high uncertainty density of a one-sentence pointer, so the change in the filing excluding "
          "Item 1A is the statistic to read (Table C11).")
    app.sub("Event windows and controls")
    app.p(
        "Day 0 is the first NYSE session on or after the later of the filing date and the EDGAR acceptance "
        "date, with acceptance at or after the close moved to the next session. The filing-period return is "
        "the adjusted close on day 3 over the adjusted close on day -1, less the same ratio for SPY. Prior "
        "volatility is the sample standard deviation of 55 daily returns over days -60 to -6, annualised; "
        "post-filing volatility uses 60 returns over days 4 to 63. Size is the nominal close on day -1 times "
        "the cover-page share count of the filing being scored, from the XBRL fact "
        "EntityCommonStockSharesOutstanding. Dollar volume is the mean of nominal close times volume over "
        "days -60 to -6. Prior excess return is the SPY-adjusted buy-and-hold return over the same window. "
        "Filings with a day -1 price below three dollars are excluded. The outcome regressions carry company "
        "and calendar-quarter effects, log size, log dollar volume, prior excess return and, where stated, "
        "prior volatility.")
    app.sub("Regressions and inference")
    app.p(
        "The aggregate trend model regresses the quarterly mean on elapsed years and three seasonal "
        "indicators, with ordinary and Newey-West (four lags) standard errors. The within-company model adds "
        "company effects to filing-level observations. Saturated calendar-quarter effects are not used in "
        "trend models because they absorb the trend. Standard errors in all filing-level regressions are "
        "clustered two ways by company and calendar quarter, with inference degrees of freedom one fewer than "
        "the smaller cluster count; where that covariance is not positive definite the report marks the cell "
        "and uses company clusters alone. Effects per standard deviation use the standard deviation of the "
        "measure in the estimation sample. The detectable effect is the coefficient that a two-sided 5% "
        "test would find with 80% power at the estimated standard error. An indicator regressor identified "
        "by fewer than ten filings is reported as not estimable.")
    app.sub("The comparison with QQQ holdings")
    app.p(
        f"QQQ tracks the Nasdaq-100; its holdings are the {int(d['t1u_q'].iloc[0].remaining)} constituents "
        f"of 9 September 2026, which the same filters reduce to {a_q['final_companies']} SEC filers. Each "
        f"result in Section 7 of the report is a single regression on the companies held by only one "
        f"portfolio, {n_both} companies held by both being excluded so that no filing sits on both sides: "
        f"the coefficient on a QQQ indicator for a level difference (calendar-quarter effects, seasonal "
        f"indicators), on its interaction with elapsed years for a trend difference, and on its "
        f"interaction with the measure for a difference in an outcome coefficient (company and "
        f"calendar-quarter effects, the outcome regressions' controls). A significant estimate in one "
        f"portfolio beside an insignificant one in the other is never read as a difference. QQQ's own "
        f"exhibits, computed on all its holdings including the shared companies, are Tables C4 to C7.")

    app.page_break()
    app.section("B. Supplementary figures")
    app.figure(FIG / "figB1_ark_whole_vs_body.png", "Figure B1")
    app.note("Figure B1. ARK quarterly reports, whole filing (solid) and excluding Item 1A (dashed), "
             "company-centred means as change since 2021 with 95% bands. The whole-filing line is flat while "
             "the line excluding Item 1A rises for negative words (Table 8).")
    app.figure(FIG / "figB2_ark_firms.png", "Figure B2")
    app.note(f"Figure B2. ARK holdings ranked on uncertainty words excluding Item 1A. Left: latest annual "
             f"report with a located Item 1A, 15 lowest and 15 highest of {len(levels)} companies; dashed "
             f"line, the median. Right: within-company slope over 2021 to 2026, the 10 largest falls and 10 "
             f"largest rises among the {len(slopes)} companies with at least three such reports (number of "
             f"reports in brackets); slopes rest on three to six observations and rank companies. Table C8 "
             f"lists every company.")
    app.figure(FIG / "figB3_ark_volatility.png", "Figure B3")
    app.note("Figure B3. Effect of one standard deviation of uncertainty word share on annualised volatility "
             "with 95% intervals, ARK quarterly reports and all reports with a located Item 1A, without "
             "(hollow) and with (filled) prior volatility, whole filing (circles) and excluding Item 1A "
             "(squares). Annual reports alone are omitted; their intervals span tens of percentage points.")
    app.figure(FIG / "figB4_ark_quintiles.png", "Figure B4")
    app.note("Figure B4. Median four-session excess return by quintile of negative word share, ARK "
             "quarterly reports with a located Item 1A and complete market data, whole filing and excluding "
             "Item 1A, with bootstrap 95% intervals. The design follows Figure 1 of Loughran and McDonald "
             "(2011).")
    app.figure(FIG / "figB5_ark_modes.png", "Figure B5")
    app.note("Figure B5. Disclosure mode of Item 1A in ARK quarterly reports with a located heading, by "
             "filing year; 2026 covers filings through September.")
    app.figure(FIG / "figB6_groups_series.png", "Figure B6")
    app.note("Figure B6. Both measures by quarter, ARK holdings and QQQ holdings (each including the shared "
             "companies), company-centred means with 95% bands; annual reports by filing year.")
    app.figure(FIG / "figB7_distributions.png", "Figure B7")
    app.note("Figure B7. Company-mean word shares in annual reports with a located Item 1A, ARK-only "
             "against QQQ-only companies, whole filing and excluding Item 1A. Boxes span the interquartile "
             "range, whiskers the 5th to 95th percentile, dots are companies. The level rows of Table 9 "
             "test these differences.")

    app.page_break()
    app.section("C. Supplementary tables")
    rows = []
    for name, label in [("ARK", "ARK holdings"), ("NDX", "QQQ holdings")]:
        part = in_group(sec, name)
        part = part[part.form.eq("10-Q")].copy()
        part["year"] = part.quarter.str[:4]
        for year, block in part.groupby("year"):
            counts = block.risk_mode.value_counts(normalize=True) * 100
            rows.append({"Portfolio": label, "Year": year, "Reports": len(block),
                         **{MODE[m]: counts.get(m, 0.0) for m in MODE}})
    app.sub("Table C1. Disclosure mode by year, quarterly reports (%)")
    app.note("Shares of all quarterly reports in the text sample, including those with no located heading.")
    app.table(show(pd.DataFrame(rows), Reports="int", **{MODE[m]: "{:.1f}" for m in MODE}), keep_together=False)

    part = sw[sw.measure.isin(["to_reference", "to_full", "prints_risk_factors"])]
    c2 = pd.DataFrame({"Report": part["sample"],
                       "Outcome": part.model.map({"filing_return": "Four-session excess return",
                                                  "volatility_with_prevol": "Post-filing volatility, prior controlled"}),
                       "Regressor": part.measure.map({"to_reference": "Stopped restating", "to_full": "Started restating",
                                                      "prints_risk_factors": "Restates this quarter"}),
                       "Filings": part.n, "Treated": part.n_treated, "Estimate (pp)": 100 * part.coef,
                       "SE": 100 * part.se, "p": part.p,
                       "Status": part.status.map(lambda s: "" if s == "ok" else "not estimable")})
    app.sub("Table C2. ARK holdings: disclosure switches and market outcomes")
    app.note("Same controls and clustering as Tables 5 and 6. Treated: filings with the indicator on. An "
             "indicator identified by fewer than ten filings is not estimated.")
    app.table(show(c2, Filings="int", Treated="int", **{"Estimate (pp)": "{:+.2f}", "SE": "{:.2f}", "p": "p"}),
              keep_together=False)

    agg2 = agg[agg["sample"].isin(["10-K", "10-Q"])]
    c3 = pd.DataFrame({"Report": agg2["sample"], "Measure": agg2.measure.map(MEASURE),
                       "Standard errors": agg2.inference.map({"OLS": "Ordinary", "HAC4": "Newey-West, 4 lags"}),
                       "Slope per year": np.where(agg2.measure.str.endswith("prop"), 100 * agg2.coef, agg2.coef),
                       "t": agg2.t, "p": agg2.p})
    app.sub("Table C3. ARK holdings: aggregate trend, ordinary against Newey-West standard errors")
    app.table(show(c3, **{"Slope per year": "{:+.3f}", "t": "{:.2f}", "p": "p"}), keep_together=False)

    app.sub("Table C4. QQQ holdings: summary statistics by report type")
    app.note("tf.idf fitted on the QQQ corpus.")
    app.table(summary_table(d["text_ndx"]))
    app.sub("Table C5. QQQ holdings: trend tests, aggregate and within company")
    app.table(trend_table(d["t4_ndx"]))
    app.sub("Table C6. QQQ holdings: post-filing volatility on uncertainty")
    app.table(volatility_table(d["t5_ndx"]), keep_together=False)
    app.sub("Table C7. QQQ holdings: four-session excess return on negative tone")
    app.table(return_table(d["t6_ndx"]))

    firms = levels.merge(slopes, on="ticker", how="outer").sort_values("level", ascending=False)
    firms = firms.rename(columns={"ticker": "Ticker", "level": "Latest annual report (%)",
                                  "filing_date": "Filed", "slope": "Slope per year (pp)", "n": "Annual reports"})
    app.sub("Table C8. ARK holdings: uncertainty words excluding Item 1A, every company")
    app.note("Filed: the latest annual report with a located Item 1A. Slopes over all such reports, where at "
             "least three exist.")
    app.table(show(firms[["Ticker", "Filed", "Latest annual report (%)", "Slope per year (pp)", "Annual reports"]],
                   **{"Latest annual report (%)": "{:.2f}", "Slope per year (pp)": "{:+.3f}", "Annual reports": "int"}),
              keep_together=False)

    evq = ev[ev.form.eq("10-Q")]
    n_events = len(evq)
    evq = evq.reindex(evq.risk_words_change.abs().sort_values(ascending=False).index).head(20)
    evq = evq.sort_values("risk_words_change").copy()
    c9 = pd.DataFrame({"Ticker": evq.ticker, "Filed": evq.filing_date, "Transition": evq.transition.map(TRANSITION),
                       "Item 1A words before": evq.prev_risk_words, "Item 1A words after": evq.risk_words,
                       "Uncertainty change (pp)": 100 * evq.Uncertainty_change,
                       "Change excl. Item 1A (pp)": 100 * evq.Uncertainty_body_change})
    app.sub(f"Table C9. ARK holdings: the 20 largest disclosure switches in quarterly reports, of {n_events}")
    app.note("Ranked by the change in Item 1A words. The full list is in the data workbook.")
    app.table(show(c9, **{"Item 1A words before": "int", "Item 1A words after": "int",
                          "Uncertainty change (pp)": "{:+.3f}", "Change excl. Item 1A (pp)": "{:+.3f}"}),
              keep_together=False)

    cov = (100 * sec.groupby(["group", "form"]).risk_found.mean()).unstack().reset_index()
    cov["group"] = cov.group.map({"ARK": "ARK only", "NDX": "QQQ only", "BOTH": "Both"})
    cov.columns = ["Group", "10-K (%)", "10-Q (%)"]
    app.sub("Table C10. Share of filings with a located Item 1A heading")
    app.table(show(cov, **{"10-K (%)": "{:.1f}", "10-Q (%)": "{:.1f}"}))

    rows = []
    for run, label in [("ark", "ARK holdings"), ("ndx", "QQQ holdings")]:
        dd = d[f"dec_{run}"].copy()
        dd.insert(0, "Portfolio", label)
        rows.append(dd)
    c11 = pd.concat(rows, ignore_index=True)
    c11 = pd.DataFrame({"Portfolio": c11.Portfolio, "Measure": c11.category,
                        "Transition": c11.transition.map(TRANSITION), "Filings": c11.n,
                        "Companies": c11.companies, "Change (pp)": c11.change_pp,
                        "Change excl. Item 1A (pp)": c11.body_change_pp, "Language term (pp)": c11.language_pp,
                        "Composition term (pp)": c11.composition_pp,
                        "Median change in Item 1A words": c11.median_risk_words_change})
    app.sub("Table C11. Filing-to-filing change in word share by disclosure transition")
    app.note("Quarterly reports, each compared with the same company's previous quarterly report. The "
             "language and composition terms sum to the change.")
    app.table(show(c11, Filings="int", Companies="int",
                   **{"Change (pp)": "{:+.3f}", "Change excl. Item 1A (pp)": "{:+.3f}",
                      "Language term (pp)": "{:+.3f}", "Composition term (pp)": "{:+.3f}",
                      "Median change in Item 1A words": "int"}), keep_together=False)

    dxx = dx[dx.inference.eq("firm_quarter_cluster")]
    c12 = pd.DataFrame({"Report": dxx["sample"], "Measure": dxx.category, "Scope": dxx.scope,
                        "Quantity": dxx.model.map({"level_difference": "Level (pp)", "trend_difference": "Trend (pp a year)"}),
                        "QQQ less ARK": 100 * dxx.coef, "p": dxx.p, "Filings": dxx.n,
                        "Status": dxx.status.map(lambda s: "" if s == "ok" else "covariance not positive definite")})
    app.sub("Table C12. QQQ less ARK: levels and trends, whole filing and excluding Item 1A")
    app.note("One regression per row on the disjoint sample, filings with a located Item 1A. Two-way clustered "
             "inference; Table 9 falls back to company clusters where the status column is marked.")
    app.table(show(c12, **{"QQQ less ARK": "{:+.4f}", "p": "p", "Filings": "int"}), keep_together=False)

    odx = od[od.inference.eq("firm_quarter_cluster")]
    share_name = {**MEASURE, "Uncertainty_prop_total": "Uncertainty, word share",
                  "Uncertainty_prop_body": "Uncertainty, word share",
                  "Negative_prop_total": "Negative, word share", "Negative_prop_body": "Negative, word share"}
    c13 = pd.DataFrame({"Outcome": odx.outcome.map({"volatility": "Post-filing volatility",
                                                    "return": "Four-session excess return"}),
                        "Report": odx["sample"], "Scope": odx.scope, "Measure": odx.measure_name.map(share_name),
                        "Prior volatility": odx.model.map({"volatility_without_prevol": "No",
                                                           "volatility_with_prevol": "Yes", "filing_return": ""}),
                        "QQQ less ARK (pp per SD)": 100 * odx.effect_1sd, "p": odx.p, "Filings": odx.n})
    app.sub("Table C13. QQQ less ARK: difference in the volatility and return coefficients")
    app.note("Interaction of the measure with a QQQ indicator, one regression per row on the disjoint sample; "
             "all filings for the rows so marked, otherwise filings with a located Item 1A.")
    app.table(show(c13, **{"QQQ less ARK (pp per SD)": "{:+.2f}", "p": "p", "Filings": "int"}), keep_together=False)
    app.link("Loughran-McDonald Master Dictionary, 1993 to 2025 release, updated March 2026.",
             "https://sraf.nd.edu/loughranmcdonald-master-dictionary/")
    app.link("U.S. Securities and Exchange Commission, EDGAR filings and company facts.", "https://www.sec.gov/edgar")

    body.save(OUTPUT_DIR / "ARK_Filing_Language_Report.pdf", OUTPUT_DIR / "REPORT.md")
    app.save(OUTPUT_DIR / "ARK_Filing_Language_Appendix.pdf", OUTPUT_DIR / "APPENDIX.md")
    print("Wrote the report and the appendix")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
