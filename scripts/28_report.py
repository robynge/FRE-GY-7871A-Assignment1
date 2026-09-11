"""The report. One document, body plus two appendices.

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

ALL = OUTPUT_DIR / "all"
COMP = OUTPUT_DIR / "comparison"
DISC = ALL / "disclosure"
FIG = OUTPUT_DIR / "report_figures"

# Loughran and McDonald (2011): Table II means for the full 10-K, 1994 to 2008;
# Table VI t-statistics for uncertainty on post-event volatility (proportional
# and tf.idf weights) and that regression's sample; the 2011 list sizes.
LM = dict(negative=1.39, uncertainty=1.20, vol_t_prop=8.34, vol_t_tfidf=8.95,
          vol_n=49_179, list_negative=2_337, list_uncertainty=285)
BRIEF = dict(list_negative=2_355, ark_companies=124)

MEASURE = {"Negative_prop": "Negative, word share", "Uncertainty_prop": "Uncertainty, word share",
           "Negative_tfidf": "Negative, tf.idf", "Uncertainty_tfidf": "Uncertainty, tf.idf"}
GROUP = {"ARK": "ARK holdings", "NDX": "Nasdaq-100", "BOTH": "Both", "ALL": "Pooled"}
GROUP_EXACT = {"ARK": "ARK only", "NDX": "Nasdaq-100 only", "BOTH": "Both"}
MODE = {"full": "Risk factors restated", "partial_update": "No material change, updates given",
        "reference_only": "No material change, reader referred to the annual report",
        "omitted": "Nothing disclosed", "not_found": "No Item 1A heading located"}
TRANSITION = {"to_reference": "Stopped restating", "to_full": "Started restating",
              "stays_full": "Kept restating", "stays_reference": "Kept referring"}
FILTER = {"Combine share classes by company CIK": "Merge share classes and companies on both lists",
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
    if not np.isfinite(v):
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


def pp(v, digits=3):
    return f"{100 * v:+.{digits}f} pp"


def ci_pp(row):
    """Confidence bounds in percentage points per standard deviation."""
    scale = row.effect_1sd / row.coef
    return 100 * row.ci_low * scale, 100 * row.ci_high * scale


def read(path, **kw):
    return pd.read_csv(path, **kw)


# --------------------------------------------------------------------- data
def load():
    d = {}
    d["audit"] = json.loads((ALL / "audit.json").read_text())
    universe = read(UNIVERSE_DIR / "universe.csv", dtype={"cik": str})
    universe["cik"] = universe.cik.str.zfill(10)
    universe["group"] = universe.funds.map(holdings_group)
    d["universe"] = universe
    label = dict(zip(universe.cik, universe.group))
    text = read(ALL / "text_sample.csv", dtype={"cik": str})
    text["cik"] = text.cik.str.zfill(10)
    text["group"] = text.cik.map(label)
    d["text"] = text
    # the section split describes the same filings as Tables 2 to 4
    sections = read(INTERIM_DIR / "risk_sections.csv", dtype={"cik": str})
    sections = sections[sections.accession.isin(text.accession)].copy()
    sections["cik"] = sections.cik.str.zfill(10)
    sections["group"] = sections.cik.map(label)
    d["sections"] = sections
    d["table1"] = read(ALL / "table1.csv")
    d["companies"] = read(ALL / "table1_universe.csv")
    d["table3"] = read(ALL / "table3.csv")
    d["table4"] = read(ALL / "table4.csv")
    d["table5"] = read(ALL / "table5.csv")
    d["table6"] = read(ALL / "table6.csv")
    d["trends"] = read(COMP / "corrected_trends.csv")
    d["diff"] = read(COMP / "differences.csv")
    d["diff_ex"] = read(COMP / "differences_excluding_item_1a.csv")
    d["practice"] = read(COMP / "disclosure_practice.csv")
    d["decomp"] = read(DISC / "decomposition.csv")
    d["modes"] = read(DISC / "mode_shares.csv")
    d["events"] = read(DISC / "switch_events.csv")
    d["switch"] = {run: read(OUTPUT_DIR / run / "disclosure" / "switch_regressions.csv")
                   for run in ["all", "ark", "ndx"]}
    d["table6_by"] = {run: read(OUTPUT_DIR / run / "table6.csv") for run in ["all", "ark", "ndx"]}
    d["table4_by"] = {run: read(OUTPUT_DIR / run / "table4.csv") for run in ["ark_only", "ndx_only"]}
    d["levels"] = read(FIG / "fig2_levels.csv")
    d["slopes"] = read(FIG / "fig2_slopes.csv")
    d["cases"] = read(FIG / "fig8_selected.csv")
    vix = read(PRICE_DIR / "prices.csv", index_col=0, parse_dates=True)["^VIX"]
    d["vix_q"] = vix.groupby(vix.index.to_period("Q").astype(str)).mean().loc["2021Q1":"2026Q3"]
    return d


def in_group(frame, name):
    return frame[frame.group.isin([name, "BOTH"])]


def centred_annual(frame, measure):
    f = frame.copy()
    f["adj"] = f[measure] - f.groupby("cik")[measure].transform("mean") + f[measure].mean()
    f["year"] = f.quarter.str[:4]
    return 100 * f.groupby("year").adj.mean()


# ------------------------------------------------------------------- report
def main() -> int:
    d = load()
    a = d["audit"]
    sec, text = d["sections"], d["text"]
    located = sec[sec.risk_found]
    q_located = located[located.form.eq("10-Q")]
    k_located = located[located.form.eq("10-K")]
    filers = d["universe"][d["universe"].status.eq("domestic_filer")]
    n_ark, n_ndx, n_both = (int(filers.group.eq(g).sum()) for g in ["ARK", "NDX", "BOTH"])

    # ---- quarterly disclosure modes, one set of numbers used everywhere
    mode_n = q_located.risk_mode.value_counts()
    n_q = len(q_located)
    share = {m: 100 * mode_n.get(m, 0) / n_q for m in ["full", "partial_update", "reference_only", "omitted"]}
    not_restated = 100 - share["full"]
    words_full = q_located[q_located.risk_mode.eq("full")].risk_words.median()
    words_ref = q_located[q_located.risk_mode.eq("reference_only")].risk_words.median()
    density = q_located.groupby("risk_mode").Uncertainty_prop_risk.mean() * 100
    coverage = 100 * sec.risk_found.mean()
    coverage_g = {g: 100 * in_group(sec, g).risk_found.mean() for g in ["ARK", "NDX"]}
    risk_share_k = {g: 100 * in_group(k_located, g).risk_share.mean() for g in ["ARK", "NDX"]}
    correlation = [c for c in a["correlations"] if c["form"] == "All"][0]["prop"]

    # ---- trends
    tr = d["trends"]
    T = lambda run, sample, cat, scope: one(tr, run=run, sample=sample, category=cat, scope=scope)
    k_neg_w, k_neg_b = T("all", "10-K", "Negative", "whole filing"), T("all", "10-K", "Negative", "excluding Item 1A")
    k_unc_w, k_unc_b = T("all", "10-K", "Uncertainty", "whole filing"), T("all", "10-K", "Uncertainty", "excluding Item 1A")
    k_share = T("all", "10-K", "Section length", "Item 1A share of words")
    # ratios of the slopes as printed, so the prose agrees with Table 4 Panel B
    shown = lambda r: round(100 * r.coef, 3)
    ratio_neg, ratio_unc = shown(k_neg_b) / shown(k_neg_w), shown(k_unc_b) / shown(k_unc_w)
    ratio_lo, ratio_hi = sorted([ratio_neg, ratio_unc])
    ark_q_neg_w, ark_q_neg_b = T("ark", "10-Q", "Negative", "whole filing"), T("ark", "10-Q", "Negative", "excluding Item 1A")
    ark_q_share = T("ark", "10-Q", "Section length", "Item 1A share of words")
    ndx_q_neg_b = T("ndx", "10-Q", "Negative", "excluding Item 1A")
    ndx_k_neg_b = T("ndx", "10-K", "Negative", "excluding Item 1A")
    within4 = d["table4"][d["table4"].model.eq("within_firm_trend") & d["table4"].inference.eq("firm_quarter_cluster")]
    agg4 = d["table4"][d["table4"].model.eq("aggregate_trend")]
    a_neg, a_unc = one(within4, sample="10-K", measure="Negative_prop"), one(within4, sample="10-K", measure="Uncertainty_prop")
    a_neg_tfidf, a_unc_tfidf = one(within4, sample="10-K", measure="Negative_tfidf"), one(within4, sample="10-K", measure="Uncertainty_tfidf")
    q_unc_tfidf = one(within4, sample="10-Q", measure="Uncertainty_tfidf")
    ols_q = one(agg4, sample="10-Q", measure="Uncertainty_prop", inference="OLS")
    nw_q = one(agg4, sample="10-Q", measure="Uncertainty_prop", inference="HAC4")

    # ---- series endpoints and peaks, computed as Figure 1 computes them
    k10 = text[text.form.eq("10-K")]
    ends = {(g, m): centred_annual(in_group(k10, g), m) for g in ["ARK", "NDX"] for m in ["Negative_prop", "Uncertainty_prop"]}
    gap = lambda m, y: ends[("ARK", m)][y] - ends[("NDX", m)][y]
    arkq = in_group(text[text.form.eq("10-Q")], "ARK").copy()
    arkq["adj"] = arkq.Negative_prop - arkq.groupby("cik").Negative_prop.transform("mean") + arkq.Negative_prop.mean()
    cell = arkq.groupby("quarter").adj.agg(["mean", "size"])
    ark_peak = cell[cell["size"] >= 30]["mean"].idxmax()
    vix_peak = d["vix_q"].idxmax()

    # ---- group differences
    dx, dl = d["diff_ex"], d["diff"][d["diff"].model.eq("level_difference")]
    dt = d["diff"][d["diff"].model.eq("trend_difference")]
    D = lambda sample, cat, scope: one(dx, sample=sample, category=cat, scope=scope)
    k_dneg_w, k_dneg_b = D("10-K", "Negative", "whole filing"), D("10-K", "Negative", "excluding Item 1A")
    k_dunc_w, k_dunc_b = D("10-K", "Uncertainty", "whole filing"), D("10-K", "Uncertainty", "excluding Item 1A")
    k_tneg, k_tunc = one(dt, sample="10-K", measure_name="Negative_prop"), one(dt, sample="10-K", measure_name="Uncertainty_prop")
    k_dneg_a, k_dunc_a = one(dl, sample="10-K", measure_name="Negative_prop"), one(dl, sample="10-K", measure_name="Uncertainty_prop")
    q_dneg_w, q_dunc_w = one(dl, sample="10-Q", measure_name="Negative_prop"), one(dl, sample="10-Q", measure_name="Uncertainty_prop")
    q_dunc_t = one(dl, sample="10-Q", measure_name="Uncertainty_tfidf")
    firm_means = k_located[k_located.group.isin(["ARK", "NDX"])].groupby(["cik", "group"])[
        ["Uncertainty_prop_total", "Uncertainty_prop_body"]].mean().reset_index()
    med = lambda col, g: firm_means.loc[firm_means.group.eq(g), col].median()
    median_gap_w = 100 * (med("Uncertainty_prop_total", "ARK") - med("Uncertainty_prop_total", "NDX"))
    median_gap_b = 100 * (med("Uncertainty_prop_body", "ARK") - med("Uncertainty_prop_body", "NDX"))
    practice = {g: one(d["practice"], group=g).refers_pct for g in ["ARK", "NDX", "BOTH"]}

    # ---- market outcomes
    t5 = d["table5"][d["table5"].inference.eq("firm_quarter_cluster")]
    v_before = one(t5, sample="10-Q", measure="Uncertainty_tfidf", model="volatility_without_prevol")
    v_after = one(t5, sample="10-Q", measure="Uncertainty_tfidf", model="volatility_with_prevol")
    sw = d["switch"]
    V = lambda run, sample, measure, spec: one(sw[run], sample=sample, model=spec, measure=measure)
    v_whole = V("all", "10-Q", "Uncertainty_prop_total", "volatility_with_prevol")
    v_body = V("all", "10-Q", "Uncertainty_prop_body", "volatility_with_prevol")
    v_whole_hi, v_body_hi = ci_pp(v_whole)[1], ci_pp(v_body)[1]
    R = {run: {scope: one(sw[run], sample="10-Q", model="filing_return", measure=m)
               for scope, m in [("whole", "Negative_prop_total"), ("body", "Negative_prop_body")]}
         for run in ["ark", "ndx", "all"]}
    R_full = {run: one(d["table6_by"][run][d["table6_by"][run].inference.eq("firm_quarter_cluster")],
                       sample="10-Q", measure="Negative_prop", model="filing_return")
              for run in ["ark", "ndx", "all"]}
    sw_ark_ret = one(sw["ark"], sample="10-Q", model="filing_return", measure="to_reference")

    # ---- decomposition and cases
    dc = d["decomp"]
    to_ref_u, to_ref_n = one(dc, category="Uncertainty", transition="to_reference"), one(dc, category="Negative", transition="to_reference")
    to_full_u = one(dc, category="Uncertainty", transition="to_full")
    cases = d["cases"]
    drop, rise = cases.iloc[0], cases.iloc[1]
    ev = d["events"]
    drop_ev = ev[ev.ticker.eq(drop.ticker) & ev.filing_date.eq(drop.filing_date)].iloc[0]
    rise_ev = ev[ev.ticker.eq(rise.ticker) & ev.filing_date.eq(rise.filing_date)].iloc[0]
    prior_ref = ev[ev.ticker.eq(rise.ticker) & ev.transition.eq("to_reference")
                   & (pd.to_datetime(ev.filing_date) < pd.Timestamp(rise.filing_date))]
    rise_years = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}[int(round(
        (pd.Timestamp(rise.filing_date) - pd.to_datetime(prior_ref.filing_date).max()).days / 365.25))]

    lm_k = {g: (100 * in_group(k10, g).Negative_prop.mean(), 100 * in_group(k10, g).Uncertainty_prop.mean())
            for g in ["ARK", "NDX"]}
    slopes, levels = d["slopes"], d["levels"]
    top_level, low_level = levels.sort_values("level", ascending=False).head(3), levels.sort_values("level").head(3)
    top_rise, top_fall = slopes.sort_values("slope", ascending=False).head(3), slopes.sort_values("slope").head(3)

    report = Report(
        "Filing Tone and Risk-Factor Disclosure: ARK Holdings and the Nasdaq-100, 2021 to 2026",
        f"Negative and uncertain language in {a['expected_original_filings']:,} 10-K and 10-Q filings "
        f"by {a['final_companies']} companies, January 2021 to September 2026. FRE-GY 7871 A, "
        f"Assignment 1, extended.",
        running_head="Filing tone and risk-factor disclosure")

    # ============================================================ SUMMARY
    report.section("Executive Summary")
    report.p(
        f"This report scores {a['expected_original_filings']:,} annual and quarterly reports filed "
        f"between January 2021 and September 2026 by {a['final_companies']} companies that are held "
        f"by the six ARK ETFs or included in the Nasdaq-100. Each filing is scored on the Loughran and "
        f"McDonald (2011) negative and uncertainty word lists, both as a share of the filing's words "
        f"and with the term-frequency weighting of equation (1) in that paper, referred to below as "
        f"tf.idf. Differences and changes in word shares are reported in percentage points (pp). The "
        f"tests are those set by the assignment: trends within company, post-filing volatility with "
        f"and without a prior-volatility control, and the four-session return around the filing. "
        f"Each test is run on the whole filing and again on the filing excluding Item 1A, the "
        f"risk-factor section.")
    report.p(
        f"On the whole filing, annual-report tone rises in both groups: negative words gain "
        f"{pp(a_neg.coef)} a year within company and uncertainty words {pp(a_unc.coef)}, both at "
        f"{p_text(a_neg.p)}. ARK annual reports carry {abs(100 * k_dneg_a.coef):.2f} pp more "
        f"negative and {abs(100 * k_dunc_a.coef):.2f} pp more uncertain language than Nasdaq-100 "
        f"constituents. Uncertainty does not predict the following quarter's volatility once prior "
        f"volatility is controlled. Negative tone is associated with a lower four-session return in "
        f"ARK quarterly reports on the filings whose Item 1A could be located "
        f"({100 * R['ark']['whole'].effect_1sd:+.1f} pp per standard deviation, "
        f"{p_text(R['ark']['whole'].p)}); on all ARK quarterly reports the estimate is "
        f"{100 * R_full['ark'].effect_1sd:+.1f} pp ({p_text(R_full['ark'].p)}), and the index shows "
        f"no association.")
    report.p(
        f"Only {share['full']:.0f}% of the quarterly reports with a located Item 1A restate their "
        f"risk factors. "
        f"{share['reference_only']:.0f}% state that nothing material has changed and refer the reader "
        f"to the annual report, printing a median of {words_ref:.0f} words where a restatement runs to "
        f"{words_full:,.0f}. Because both measures are word shares, that choice moves them "
        f"mechanically. Excluding Item 1A cuts the annual-report trends by {100 * (1 - ratio_hi):.0f}% "
        f"to {100 * (1 - ratio_lo):.0f}%, and they remain significant. It closes the gap between ARK "
        f"and the index ({abs(100 * k_dunc_b.coef):.3f} pp for uncertainty, {p_text(k_dunc_b.p)}) and "
        f"removes the return association in ARK ({100 * R['ark']['body'].effect_1sd:+.1f} pp, "
        f"{p_text(R['ark']['body'].p)}). The volatility result does not change. On the whole filing, "
        f"the measures record how much risk disclosure a company prints as much as how it writes.")

    # ======================================================= 1 INTRODUCTION
    report.section("1. Introduction")
    report.p(
        "Loughran and McDonald (2011) showed that a negative word list built from the language of "
        "10-K filings predicts the market reaction to those filings, while the general-purpose "
        "Harvard psychology list does not: almost three-quarters of the Harvard list's negative "
        "counts in 10-Ks are words with no negative meaning in a financial statement. Their "
        "finance-specific lists have since become the standard tool for measuring tone in filings.")
    report.p(
        "This report applies two of those lists to the current holdings of the six ARK ETFs and to "
        "the constituents of the Nasdaq-100. The negative list measures how bad the news is. The "
        "uncertainty list measures how far management declines to commit: a sentence stating that "
        "results may fluctuate for reasons outside the company's control carries no bad news at "
        "all. The two are kept apart throughout and tested against different outcomes, negative "
        "tone against the return around the filing and uncertainty against subsequent volatility.")
    report.p(
        f"Four questions organise the results: whether filing tone is trending, whether ARK holdings "
        f"differ from the index, whether uncertainty predicts volatility, and whether negative tone "
        f"predicts the filing-period return. Each is answered twice, once on the whole filing as in "
        f"Loughran and McDonald and once on the filing excluding Item 1A. The second answer is "
        f"needed because {not_restated:.0f}% of quarterly reports with a located Item 1A do not "
        f"restate their risk factors "
        f"and a word-share measure cannot tell that choice apart from a change in tone. Loughran and "
        f"McDonald met the same problem with the MD&A section, which more than half of firms "
        f"incorporated by reference in 1994, and excluded those filings (pp. 40, 54). This report "
        f"decomposes the effect instead of excluding the filings. Sections 2 to 7 give the data, the "
        f"four results, the mechanism and the conclusions; Appendix A holds every specification and "
        f"Appendix B the supplementary tables.")

    # ================================================== 2 DATA AND MEASURES
    report.section("2. Data and Measures")
    report.sub("Sample")
    report.p(
        f"The universe is {int(d['companies'].iloc[0].remaining)} holding identifiers as at "
        f"9 September 2026: 121 from the six ARK ETF portfolios and 102 Nasdaq-100 constituents. The "
        f"assignment brief counts {BRIEF['ark_companies']} ARK companies from an earlier snapshot of "
        f"the same portfolios. The sample removes funds, cash and non-US local listings, merges share "
        f"classes by SEC company identifier (CIK), and records companies that report on Form 20-F or "
        f"40-F rather than 10-K and 10-Q from their EDGAR filing history. {a['final_companies']} SEC "
        f"filers remain: {n_ark} held by ARK only, {n_both} held by ARK and in the index, {n_ndx} in "
        f"the index only. Every original 10-K and 10-Q they filed from January 2021 was downloaded "
        f"and parsed, {a['expected_original_filings']:,} documents with {a['parse_failures']} parse "
        f"failures; the {a['amendments']} amendments are recorded and never scored. Table 1 shows "
        f"what each filter removed. Tables 1 to 6 keep the numbering the assignment specifies; "
        f"Tables 7 and 8 are additional.")
    companies = d["companies"].rename(columns={"filter": "Filter", "removed": "Removed",
                                               "remaining": "Remaining", "unit": "Unit"})
    companies["Filter"] = companies.Filter.map(FILTER).fillna(companies.Filter)
    report.sub("Table 1. Sample construction")
    report.note("Panel A. From holding identifiers to SEC filers. Absence of 10-K or 10-Q filings is "
                "recorded from observed EDGAR behaviour, never inferred from a company's domicile.")
    report.table(show(companies, Removed="int", Remaining="int"))
    report.note("Panel B. From filings to analysis samples. The text sample supports Tables 2 to 4. "
                "The volatility and return samples support Tables 5 and 6 and are filtered "
                "separately, because a filing can be scored before its outcome window has elapsed.")
    for name in ["Text", "Volatility", "Return"]:
        part = d["table1"][d["table1"]["sample"].eq(name)].rename(
            columns={"filter": "Filter", "removed": "Removed", "remaining": "Remaining",
                     "companies": "Companies"})
        part["Filter"] = part.Filter.map(FILTER).fillna(part.Filter)
        part.insert(0, "Sample", [name] + [""] * (len(part) - 1))
        report.table(show(part[["Sample", "Filter", "Removed", "Remaining", "Companies"]],
                          Removed="int", Remaining="int", Companies="int"), keep_together=False)

    report.sub("Measures")
    report.p(
        f"The word lists are the active entries in the March 2026 release of the Loughran-McDonald "
        f"Master Dictionary: {a['lexicon_counts']['Negative']:,} negative and "
        f"{a['lexicon_counts']['Uncertainty']} uncertainty words, {a['lexicon_overlap']} on both. "
        f"The 2011 paper used {LM['list_negative']:,} and {LM['list_uncertainty']}; the assignment "
        f"brief cites {BRIEF['list_negative']:,} negative words, a count that includes entries since "
        f"retired from the list. Each filing is scored twice on each list. The word share divides "
        f"list-word occurrences by all words retained from the filing. The tf.idf score weights each "
        f"occurrence by its log frequency, normalised by the filing's average word frequency, and by "
        f"the log inverse document frequency across the corpus, so a word that appears in every "
        f"filing receives no weight. Appendix A gives the formula and the parsing rules.")
    rows = []
    for g in ["ARK", "NDX"]:
        for form in ["10-K", "10-Q"]:
            part = in_group(text[text.form.eq(form)], g)
            for m, label in MEASURE.items():
                scale = 100 if m.endswith("prop") else 1
                s = part[m] * scale
                rows.append({"Group": GROUP[g], "Form": form, "Measure": label, "N": len(s),
                             "Mean": s.mean(), "SD": s.std(), "P25": s.quantile(.25),
                             "Median": s.median(), "P75": s.quantile(.75)})
    table2 = pd.DataFrame(rows)
    report.p(
        "Table 2 gives the level and spread of the four measures by group and report type, which "
        "the trend and difference tests take as their baseline, and the characteristics of the "
        "risk-factor section that the rest of the report turns on.")
    report.sub("Table 2. Summary statistics")
    report.note("Panel A. Tone measures by group and report type. Word shares in percent; tf.idf "
                "scores in score units, fitted on the pooled corpus. ARK holdings and Nasdaq-100 "
                "each include the 22 companies in both. Annual and quarterly reports are kept "
                "separate because a 10-K is longer and carries more risk language.")
    report.table(show(table2, N="int", Mean="{:.3f}", SD="{:.3f}", P25="{:.3f}",
                      Median="{:.3f}", P75="{:.3f}"), keep_together=False)
    panel_b2 = pd.DataFrame([
        {"Statistic": "Quarterly reports with a located Item 1A", "Value": f"{n_q:,}"},
        {"Statistic": "Share restating risk factors (%)", "Value": f"{share['full']:.1f}"},
        {"Statistic": "Share claiming no material change, with updates (%)", "Value": f"{share['partial_update']:.1f}"},
        {"Statistic": "Share referring the reader to the annual report (%)", "Value": f"{share['reference_only']:.1f}"},
        {"Statistic": "Share disclosing nothing (%)", "Value": f"{share['omitted']:.1f}"},
        {"Statistic": "Median Item 1A words, restated", "Value": f"{words_full:,.0f}"},
        {"Statistic": "Median Item 1A words, referred", "Value": f"{words_ref:,.0f}"},
        {"Statistic": "Uncertainty words inside Item 1A, restated (%)", "Value": f"{density['full']:.2f}"},
        {"Statistic": "Uncertainty words inside Item 1A, referred (%)", "Value": f"{density['reference_only']:.2f}"},
        {"Statistic": "Item 1A share of 10-K words, ARK holdings (%)", "Value": f"{risk_share_k['ARK']:.1f}"},
        {"Statistic": "Item 1A share of 10-K words, Nasdaq-100 (%)", "Value": f"{risk_share_k['NDX']:.1f}"},
        {"Statistic": "Correlation of negative and uncertainty word shares", "Value": f"{correlation:.2f}"},
        {"Statistic": "Filings with a located Item 1A heading (%)", "Value": f"{coverage:.1f}"},
    ])
    report.note("Panel B. The risk-factor section. Quarterly-report statistics use filings with a "
                "located Item 1A heading; the disclosure modes are defined in Appendix A.")
    report.table(panel_b2, widths=[330, 80])
    report.p(
        f"ARK annual reports average {lm_k['ARK'][0]:.2f}% negative and {lm_k['ARK'][1]:.2f}% "
        f"uncertain words, Nasdaq-100 annual reports {lm_k['NDX'][0]:.2f}% and "
        f"{lm_k['NDX'][1]:.2f}%. Loughran and McDonald report {LM['negative']:.2f}% and "
        f"{LM['uncertainty']:.2f}% for 50,115 10-Ks filed 1994 to 2008, with the negative share "
        f"rising from about 1.1% to 1.7% over their period. The levels here continue that rise. The "
        f"two measures correlate at {correlation:.2f} across filings, so they are related measures "
        f"rather than independent evidence.")

    t3 = d["table3"]
    neg = t3[t3.category.eq("Negative")].head(30).reset_index(drop=True)
    unc = t3[t3.category.eq("Uncertainty")].head(30).reset_index(drop=True)
    table3 = pd.DataFrame({"Rank": neg["rank"], "Negative word": neg.word,
                           "Share of negative count (%)": neg.share_pct,
                           "Uncertainty word": unc.word,
                           "Share of uncertainty count (%)": unc.share_pct})
    report.p(
        "Table 3 lists the thirty most frequent words on each list. It shows why the two scorings "
        "can disagree on uncertainty and agree on negative tone.")
    report.sub("Table 3. Thirty most frequent words on each list")
    report.note("Each share divides a word's count by all occurrences in its own list across the "
                "pooled text sample. The two lists are counted separately.")
    report.table(show(table3, Rank="int", **{"Share of negative count (%)": "{:.2f}",
                                              "Share of uncertainty count (%)": "{:.2f}"}),
                 keep_together=False)
    doc, top10 = a["uncertainty_word_document_pct"], a["top10_shares"]
    report.p(
        f"The ten most frequent uncertainty words account for {top10['Uncertainty']:.0f}% of "
        f"uncertainty counts, against {top10['Negative']:.0f}% for negative words. MAY alone is "
        f"{unc.share_pct.iloc[0]:.1f}% of uncertainty counts and appears in {doc['MAY']:.0f}% of "
        f"filings; APPROXIMATELY appears in {doc['APPROXIMATELY']:.0f}%. A word present in every "
        f"document has an inverse document frequency of zero, so MAY counts fully in the word share "
        f"and not at all in the tf.idf score. The uncertainty list is dominated by such words and "
        f"the negative list is not, which is why the two scorings diverge on the uncertainty trend "
        f"in Section 3.")

    report.sub("The risk-factor section")
    report.p(
        f"Each filing is also split at its Item 1A heading into the risk-factor section and the "
        f"balance of the document. The heading is located in {coverage:.1f}% of filings, "
        f"{coverage_g['ARK']:.0f}% for ARK holdings and {coverage_g['NDX']:.0f}% for the index, "
        f"both including the shared companies; filers who label the section differently are "
        f"recorded as not located and excluded from the split rather than guessed at. Among "
        f"quarterly reports with a located heading, {share['full']:.0f}% restate the risk factors, "
        f"{share['partial_update']:.0f}% claim no material change but add updates, "
        f"{share['reference_only']:.0f}% refer the reader to the annual report, and "
        f"{share['omitted']:.0f}% disclose nothing (Table 2, Panel B). Every test that follows is "
        f"reported on the whole filing and on the filing excluding Item 1A, on identical filings.")

    report.sub("Market data")
    report.p(
        "Day 0 is the first NYSE session on or after EDGAR accepts the filing. The filing-period "
        "return is the four-session buy-and-hold return from day 0, less the return on the S&P 500 "
        "ETF (SPY), following the window of Loughran and McDonald. Post-filing volatility covers "
        "trading days 4 to 63 and prior volatility days -60 to -6. Appendix A defines the windows, "
        "the size and liquidity controls and the price filter.")

    # ======================================================= 3 TREND
    report.section("3. Tone Trends, 2021 to 2026")
    report.sub("3.1 The series")
    report.p(
        "Figure 1 plots the two word shares by quarter for both groups and both report types, with "
        "the VIX for comparison as the assignment asks. It sets out what the trend tests in Table 4 "
        "then formalise.")
    report.figure(FIG / "fig1_series.png", "Figure 1")
    report.note(
        "Figure 1. Tone by group and report type. Lines are company-centred means: each company's "
        "score less its own mean, plus the group mean, so entry and exit of companies do not move the "
        "line. Annual reports are aggregated by filing year and plotted at the first quarter, where "
        "most are filed. Quarterly-report cells with fewer than 30 filings are blank, which removes "
        "every first calendar quarter: calendar-year companies file their 10-K then, leaving 6 to 25 "
        "quarterly reports. The VIX is the quarterly mean of daily closes.")
    report.p(
        f"Annual-report tone rises in both groups every year without a reversal. ARK negative words "
        f"rise from {ends[('ARK', 'Negative_prop')]['2021']:.2f}% in 2021 filings to "
        f"{ends[('ARK', 'Negative_prop')]['2026']:.2f}% in 2026, Nasdaq-100 from "
        f"{ends[('NDX', 'Negative_prop')]['2021']:.2f}% to {ends[('NDX', 'Negative_prop')]['2026']:.2f}%. "
        f"Uncertainty rises from {ends[('ARK', 'Uncertainty_prop')]['2021']:.2f}% to "
        f"{ends[('ARK', 'Uncertainty_prop')]['2026']:.2f}% and from "
        f"{ends[('NDX', 'Uncertainty_prop')]['2021']:.2f}% to {ends[('NDX', 'Uncertainty_prop')]['2026']:.2f}%. "
        f"The negative-word gap between the groups widens from {gap('Negative_prop', '2021'):.2f} pp "
        f"in 2021 to {gap('Negative_prop', '2026'):.2f} pp in 2026; the uncertainty gap moves from "
        f"{gap('Uncertainty_prop', '2021'):.2f} to {gap('Uncertainty_prop', '2026'):.2f} pp. Quarterly "
        f"reports show no drift on either measure. Their relation to the VIX is loose: the VIX peaks "
        f"in {vix_peak} and ARK negative words in {ark_peak}, and both run lower through 2024 and "
        f"2025. The report offers no formal test of that association.")

    report.sub("3.2 Trend tests")
    report.p(
        f"Table 4 estimates the trend two ways. The aggregate model regresses the quarterly mean on "
        f"elapsed years with seasonal indicators. The within-company model uses filing-level "
        f"observations with company effects and seasonal indicators. A series of 23 quarterly means "
        f"is short and serially correlated, so the aggregate model reports Newey-West t-statistics: "
        f"for quarterly-report uncertainty the ordinary t-statistic is {ols_q.t:.2f} and the "
        f"Newey-West {nw_q.t:.2f}. The within-company estimate is the one read for inference, "
        f"because company effects remove differences in baseline tone that a quarterly mean carries "
        f"whenever the mix of companies changes. Panel B repeats the within-company model on the "
        f"filing excluding Item 1A, on the same filings as the whole-filing column.")
    agg = agg4[agg4.inference.eq("HAC4")]
    panel_a = agg.merge(within4, on=["sample", "measure"], suffixes=("_a", "_w"))
    panel_a["Measure"] = panel_a.measure.map(MEASURE)
    is_prop = panel_a.measure.str.endswith("prop")
    panel_a["agg"] = np.where(is_prop, 100 * panel_a.coef_a, panel_a.coef_a)
    panel_a["wit"] = np.where(is_prop, 100 * panel_a.coef_w, panel_a.coef_w)
    panel_a = panel_a[["sample", "Measure", "agg", "t_a", "wit", "t_w", "p_w", "n_w"]]
    panel_a.columns = ["Report", "Measure", "Aggregate slope", "Newey-West t",
                       "Within-company slope", "t", "p", "Filings"]
    report.sub("Table 4. Trend tests")
    report.note("Panel A. Pooled sample, whole filing. Slopes are per year: percentage points for "
                "word shares, score units for tf.idf. Inference is described in Appendix A.")
    report.table(show(panel_a, **{"Aggregate slope": "{:+.3f}", "Newey-West t": "{:.2f}",
                                  "Within-company slope": "{:+.3f}", "t": "{:.2f}", "p": "p",
                                  "Filings": "int"}), keep_together=False)
    rows = []
    for run, g in [("all", "ALL"), ("ark", "ARK"), ("ndx", "NDX")]:
        for form in ["10-K", "10-Q"]:
            for cat in ["Negative", "Uncertainty"]:
                w, b = T(run, form, cat, "whole filing"), T(run, form, cat, "excluding Item 1A")
                rows.append({"Group": GROUP[g], "Form": form, "Measure": f"{cat}, word share",
                             "Whole filing": 100 * w.coef, "p": w.p,
                             "Excluding Item 1A": 100 * b.coef, "p ": b.p, "Filings": w.n})
            s = T(run, form, "Section length", "Item 1A share of words")
            rows.append({"Group": GROUP[g], "Form": form, "Measure": "Item 1A share of words",
                         "Whole filing": 100 * s.coef, "p": s.p, "Excluding Item 1A": np.nan,
                         "p ": np.nan, "Filings": s.n})
    panel_b = show(pd.DataFrame(rows), **{"Whole filing": "{:+.3f}", "p": "p",
                                          "Excluding Item 1A": "{:+.3f}", "p ": "p", "Filings": "int"})
    panel_b.loc[panel_b.Measure.eq("Item 1A share of words"), "p "] = ""
    report.note("Panel B. Within-company slopes, whole filing and excluding Item 1A, on identical "
                "filings (those with a located Item 1A), per year in percentage points. The last "
                "row of each block is the trend in Item 1A's share of the filing's words. ARK "
                "holdings and Nasdaq-100 each include the shared companies.")
    report.table(panel_b, keep_together=False)
    report.p(
        f"In annual reports both word shares rise within company at {p_text(a_neg.p)}: negative "
        f"words by {pp(a_neg.coef)} a year and uncertainty words by {pp(a_unc.coef)}. The "
        f"Newey-West aggregate t-statistics agree. The tf.idf score confirms the negative trend "
        f"({p_text(a_neg_tfidf.p)}) and not the uncertainty trend ({p_text(a_unc_tfidf.p)}). "
        f"Uncertainty is rising through words such as MAY that carry no tf.idf weight; the "
        f"frequency of hedging is rising and its distinctiveness is not.")
    report.p(
        f"Item 1A is growing at the same time. Its share of the annual report rises "
        f"{pp(k_share.coef)} a year ({p_text(k_share.p)}). On the same filings the whole-filing "
        f"slopes are {pp(k_neg_w.coef)} and {pp(k_unc_w.coef)}; excluding the section they are "
        f"{pp(k_neg_b.coef)} ({p_text(k_neg_b.p)}) and {pp(k_unc_b.coef)} ({p_text(k_unc_b.p)}). "
        f"The lengthening of Item 1A accounts for {100 * (1 - ratio_neg):.0f}% of the measured rise "
        f"in negative tone and {100 * (1 - ratio_unc):.0f}% of the rise in uncertainty; the balance is "
        f"a change in the rest of the document. Both groups show the pattern; "
        f"the smallest of the four group-level slopes is Nasdaq-100 negative tone at "
        f"{pp(ndx_k_neg_b.coef)} ({p_text(ndx_k_neg_b.p)}).")
    report.p(
        "Figure 2 shows the quarterly series on both measures. For ARK holdings the whole-filing "
        "line is flat while the line excluding Item 1A rises; for the index the two move together.")
    report.figure(FIG / "fig7_whole_vs_body.png", "Figure 2")
    report.note(
        "Figure 2. Quarterly reports, whole filing (solid) and excluding Item 1A (dashed), "
        "company-centred means. First calendar quarters are blank as in Figure 1.")
    report.p(
        f"In quarterly reports neither word share trends on the whole filing; ARK negative words "
        f"change {pp(ark_q_neg_w.coef)} a year ({p_text(ark_q_neg_w.p)}), and the uncertainty tf.idf "
        f"score declines in the pooled sample ({q_unc_tfidf.coef:+.3f} score units a year, "
        f"{p_text(q_unc_tfidf.p)}). Excluding Item 1A changes the reading for ARK. The section's "
        f"share of an ARK 10-Q falls {abs(100 * ark_q_share.coef):.2f} pp a year "
        f"({p_text(ark_q_share.p)}) as more companies stop restating, and the negative share of the "
        f"balance rises {pp(ark_q_neg_b.coef)} a year ({p_text(ark_q_neg_b.p)}). The solid ARK line "
        f"in Figure 2 is flat to declining and the dashed line rises. The prose of ARK quarterly "
        f"reports is becoming more negative and the shrinking risk section conceals it. The index "
        f"shows neither effect ({p_text(ndx_q_neg_b.p)} excluding Item 1A).")

    report.sub("3.3 Which holdings")
    report.p(
        "Figure 3 ranks the ARK holdings on the measure excluding Item 1A, first by current level "
        "and then by trend. The whole-filing measure is not used here because it would rank "
        "companies by whether they restate risk factors.")
    report.figure(FIG / "fig2_firms.png", "Figure 3")
    report.note(
        f"Figure 3. ARK holdings ranked on uncertainty words excluding Item 1A, annual reports. Left: "
        f"the latest annual report with a located Item 1A, 15 lowest and 15 highest of {len(levels)} "
        f"companies; the dashed line is "
        f"the median. Right: the within-company slope over 2021 to 2026 for the {len(slopes)} "
        f"companies with at least three annual reports, 10 largest falls and 10 largest rises. "
        f"Slopes rest on three to six observations and rank companies; they are not precise "
        f"estimates. Appendix Table B5 lists every company.")
    report.p(
        f"The median ARK holding runs {levels.level.median():.2f}% uncertainty words in its latest "
        f"annual report with a located Item 1A; the interquartile range is "
        f"{levels.level.quantile(.25):.2f} to {levels.level.quantile(.75):.2f}. "
        f"{', '.join(top_level.ticker)} sit highest at "
        f"{top_level.level.min():.2f} to {top_level.level.max():.2f}%; {', '.join(low_level.ticker)} "
        f"lowest at {low_level.level.min():.2f} to {low_level.level.max():.2f}%. The rise in "
        f"uncertainty is broad: {100 * (slopes.slope > 0).mean():.0f}% of the {len(slopes)} companies "
        f"have a positive slope, with a median of {slopes.slope.median():+.3f} pp a year. "
        f"{', '.join(top_rise.ticker)} rise fastest, at {top_rise.slope.min():+.2f} to "
        f"{top_rise.slope.max():+.2f} pp a year; {', '.join(top_fall.ticker)} fall fastest, at "
        f"{top_fall.slope.min():+.2f} to {top_fall.slope.max():+.2f}.")

    # ======================================================= 4 COMPARISON
    report.section("4. ARK Holdings versus the Nasdaq-100")
    report.p(
        f"Differences between the groups are estimated in one regression on the pooled sample with "
        f"an index indicator, calendar-quarter effects and two-way clustering. A significant slope "
        f"in one group beside an insignificant one in the other is not a difference. The {n_both} "
        f"companies held by ARK and in the index are dropped so that no filing sits on both sides. "
        f"Figure 4 shows the distributions being compared; Table 7 gives the tests.")
    report.figure(FIG / "fig3_distributions.png", "Figure 4")
    report.note(
        "Figure 4. Company-mean tone in annual reports with a located Item 1A, ARK-only against "
        "Nasdaq-100-only companies, on the whole filing and excluding Item 1A. Boxes span the "
        "interquartile range; whiskers the 5th to 95th percentile; the line is the median.")
    rows = []
    for form in ["10-K", "10-Q"]:
        for m, label in MEASURE.items():
            lv = one(dl, sample=form, measure_name=m)
            tv = dt[(dt["sample"] == form) & (dt.measure_name == m)]
            tv = tv.iloc[0] if len(tv) else None
            ok = tv is not None and tv.status == "ok"
            scale = 100 if m.endswith("prop") else 1
            rows.append({"Form": form, "Measure": label, "Level difference": scale * lv.coef, "p": lv.p,
                         "Trend difference per year": scale * tv.coef if ok else np.nan,
                         "p ": tv.p if ok else np.nan, "Filings": lv.n})
    report.sub("Table 7. Nasdaq-100 less ARK holdings")
    report.note("Panel A. Whole filing. Level difference is the coefficient on the index indicator; "
                "trend difference is the coefficient on its interaction with elapsed years. "
                "Percentage points for word shares, score units for tf.idf. A negative sign means "
                "the index is lower. n.e.: not estimable; the two-way clustered covariance of that "
                "interaction is not positive definite.")
    report.table(show(pd.DataFrame(rows), **{"Level difference": "{:+.3f}", "p": "p",
                                             "Trend difference per year": "{:+.4f}", "p ": "p",
                                             "Filings": "int"}))
    rows = []
    for form in ["10-K", "10-Q"]:
        for cat in ["Negative", "Uncertainty"]:
            w, b = D(form, cat, "whole filing"), D(form, cat, "excluding Item 1A")
            rows.append({"Form": form, "Measure": f"{cat}, word share", "Whole filing": 100 * w.coef,
                         "p": w.p, "Excluding Item 1A": 100 * b.coef, "p ": b.p, "Filings": w.n})
    report.note("Panel B. Level difference, whole filing and excluding Item 1A, on identical filings.")
    report.table(show(pd.DataFrame(rows), **{"Whole filing": "{:+.3f}", "p": "p",
                                             "Excluding Item 1A": "{:+.3f}", "p ": "p", "Filings": "int"}))
    report.p(
        f"On the whole filing, ARK annual reports carry more of both kinds of language and the gap "
        f"is widening. Nasdaq-100 annual reports have {abs(100 * k_dneg_a.coef):.3f} pp fewer "
        f"negative words ({p_text(k_dneg_a.p)}) and {abs(100 * k_dunc_a.coef):.3f} pp fewer "
        f"uncertainty words ({p_text(k_dunc_a.p)}) on the {int(k_dneg_a.n):,} filings of Panel A, "
        f"and their trends are {abs(100 * k_tneg.coef):.3f} and {abs(100 * k_tunc.coef):.4f} pp a "
        f"year flatter ({p_text(k_tneg.p)}, {p_text(k_tunc.p)}). Quarterly reports differ by less. "
        f"The word-share differences are not significant ({p_text(q_dneg_w.p)} for negative, "
        f"{p_text(q_dunc_w.p)} for uncertainty); the uncertainty tf.idf score is "
        f"{abs(q_dunc_t.coef):.2f} score units lower in the index ({p_text(q_dunc_t.p)}).")
    report.p(
        f"Excluding Item 1A closes the annual-report gaps. On the {int(k_dneg_w.n):,} filings with a "
        f"located Item 1A (Panel B) the whole-filing gaps are {abs(100 * k_dneg_w.coef):.3f} and "
        f"{abs(100 * k_dunc_w.coef):.3f} pp; excluding the section, negative language narrows to "
        f"{abs(100 * k_dneg_b.coef):.3f} pp ({p_text(k_dneg_b.p)}) and uncertainty to "
        f"{abs(100 * k_dunc_b.coef):.3f} pp ({p_text(k_dunc_b.p)}). Figure 4 shows the same: the "
        f"company medians for uncertainty differ by {median_gap_w:.2f} pp on the whole filing and by "
        f"{median_gap_b:.2f} pp excluding Item 1A. The difference between the groups is the length "
        f"of their risk sections, {risk_share_k['ARK']:.1f}% of an ARK annual report's words against "
        f"{risk_share_k['NDX']:.1f}% for a Nasdaq-100 constituent. Outside that section the two "
        f"groups write alike. Not printing risk factors in quarterly reports is about equally "
        f"common in both: {practice['ARK']:.0f}% of ARK-only and {practice['NDX']:.0f}% of "
        f"index-only quarterly reports either refer the reader to the annual report or disclose "
        f"nothing, against {practice['BOTH']:.0f}% for the companies in both groups, which are the "
        f"largest.")

    # ================================================= 5 MARKET OUTCOMES
    report.section("5. Tone and Subsequent Stock Behaviour")
    report.sub("5.1 Uncertainty and post-filing volatility")
    report.p(
        "Table 5 regresses annualised volatility over the quarter after the filing on the "
        "uncertainty measure, twice on one sample: without prior volatility and with it. The first "
        "specification cannot separate the language from the persistence of volatility itself, "
        "since a company whose stock is already volatile may also hedge more in its filings. The "
        "second asks whether the language carries information beyond prior volatility. The "
        "difference between the two estimates is the finding.")
    t5v = t5.copy()
    t5v["Prior volatility"] = np.where(t5v.model.eq("volatility_with_prevol"), "Yes", "No")
    t5v["Measure"] = t5v.measure.map(MEASURE)
    t5v["effect"], t5v["mde"] = 100 * t5v.effect_1sd, 100 * t5v.mde80_1sd
    t5v = t5v[["sample", "Measure", "Prior volatility", "n", "effect", "mde", "p"]]
    t5v.columns = ["Report", "Measure", "Prior volatility", "Filings", "Effect per SD (pp)",
                   "Detectable (pp)", "p"]
    report.sub("Table 5. Uncertainty and post-filing volatility")
    report.note("Panel A. Pooled sample, whole filing. Effect is the change in annualised volatility, "
                "in percentage points, per one standard deviation of the measure in that sample. "
                "Detectable is the effect this design finds with 80% power at the 5% level. "
                "Controls and clustering are in Appendix A.")
    report.table(show(t5v, Filings="int", **{"Effect per SD (pp)": "{:+.2f}", "Detectable (pp)": "{:.2f}",
                                              "p": "p"}), keep_together=False)
    rows = []
    for sample in ["All", "10-Q"]:
        for m, label in [("Uncertainty_prop_total", "Whole filing"), ("Uncertainty_prop_body", "Excluding Item 1A")]:
            for spec, ctrl in [("volatility_without_prevol", "No"), ("volatility_with_prevol", "Yes")]:
                r = V("all", sample, m, spec)
                lo, hi = ci_pp(r)
                rows.append({"Report": sample, "Scope": label, "Prior volatility": ctrl, "Filings": r.n,
                             "Effect per SD (pp)": 100 * r.effect_1sd, "95% interval": f"{lo:+.2f} to {hi:+.2f}",
                             "p": r.p})
    report.note("Panel B. Word share, whole filing and excluding Item 1A, on identical filings "
                "(those with a located Item 1A).")
    report.table(show(pd.DataFrame(rows), Filings="int", **{"Effect per SD (pp)": "{:+.2f}", "p": "p"}),
                 keep_together=False)
    k_rows = [V("all", "10-K", m, spec) for m in ["Uncertainty_prop_total", "Uncertainty_prop_body"]
              for spec in ["volatility_without_prevol", "volatility_with_prevol"]]
    n_k_located = int(k_rows[0].n)
    k_widths = [ci_pp(r)[1] - ci_pp(r)[0] for r in k_rows]
    report.p(
        "Figure 5 draws the Panel B estimates for quarterly reports and the pooled sample with their "
        "confidence intervals, so that the gap between the two specifications can be read directly.")
    report.figure(FIG / "fig4_volatility.png", "Figure 5")
    report.note(
        f"Figure 5. Effect of one standard deviation of uncertainty word share on annualised "
        f"volatility with 95% intervals, without (hollow) and with (filled) prior volatility, whole "
        f"filing (circles) and excluding Item 1A (squares). Annual-report rows are omitted; on the "
        f"{n_k_located} located annual reports the intervals are {min(k_widths):.0f} to "
        f"{max(k_widths):.0f} percentage points wide.")
    report.p(
        f"Only one estimate is significant at 5% before the control and none after it. The quarterly "
        f"tf.idf score adds {100 * v_before.effect_1sd:+.2f} pp of annualised volatility per standard "
        f"deviation without prior volatility ({p_text(v_before.p)}) and {100 * v_after.effect_1sd:+.2f} "
        f"pp with it ({p_text(v_after.p)}). Loughran and McDonald's Table VI reports a t-statistic of "
        f"{LM['vol_t_prop']:.1f} on the same relation with proportional weights, "
        f"{LM['vol_t_tfidf']:.1f} with tf.idf, across {LM['vol_n']:,} annual reports and with no "
        f"prior-volatility control. The estimates here have the same sign; the control removes them. "
        f"Excluding Item 1A does not restore them: {100 * v_body.effect_1sd:+.2f} pp with the control "
        f"({p_text(v_body.p)}). These are imprecise zeros rather than precise ones. In quarterly "
        f"reports the interval with the control reaches {v_whole_hi:.1f} pp for the whole-filing "
        f"measure and {v_body_hi:.1f} pp excluding Item 1A; effects of that size cannot be ruled out, "
        f"and nothing smaller can be.")

    report.sub("5.2 Negative tone and the filing-period return")
    n_fig6 = {g: int(R[g]["whole"].n) for g in ["ark", "ndx"]}
    report.p(
        "Figure 6 sorts quarterly reports into quintiles of negative word share and plots the median "
        "four-session excess return of each, on both measures, before any regression. Table 6 "
        "gives the regressions.")
    report.figure(FIG / "fig5_quintiles.png", "Figure 6")
    report.note(
        f"Figure 6. Median four-session excess return by quintile of negative word share, quarterly "
        f"reports with a located Item 1A and complete market data ({n_fig6['ark']:,} ARK, "
        f"{n_fig6['ndx']:,} Nasdaq-100, each including the shared companies), whole filing (solid) "
        f"and excluding Item 1A (dashed). The design follows Figure 1 of Loughran and McDonald (2011).")
    t6 = d["table6"][d["table6"].inference.eq("firm_quarter_cluster")].copy()
    t6["Measure"] = t6.measure.map(MEASURE)
    t6["effect"], t6["mde"] = 100 * t6.effect_1sd, 100 * t6.mde80_1sd
    t6 = t6[["sample", "Measure", "n", "effect", "mde", "p"]]
    t6.columns = ["Report", "Measure", "Filings", "Effect per SD (pp)", "Detectable (pp)", "p"]
    report.sub("Table 6. Negative tone and the filing-period return")
    report.note("Panel A. Pooled sample, whole filing, all filings with complete market data. Excess "
                "return over four sessions from the filing event day, in percentage points per "
                "standard deviation of the measure. Controls and clustering are in Appendix A.")
    report.table(show(t6, Filings="int", **{"Effect per SD (pp)": "{:+.2f}", "Detectable (pp)": "{:.2f}",
                                             "p": "p"}))
    rows = []
    for run, g in [("ark", "ARK"), ("ndx", "NDX"), ("all", "ALL")]:
        f, w, b = R_full[run], R[run]["whole"], R[run]["body"]
        rows.append({"Sample": GROUP[g], "All filings": f.n, "Effect (pp)": 100 * f.effect_1sd, "p": f.p,
                     "Located Item 1A": w.n, "Whole filing (pp)": 100 * w.effect_1sd, "p ": w.p,
                     "Excluding Item 1A (pp)": 100 * b.effect_1sd, "p  ": b.p})
    report.note("Panel B. Quarterly reports, word share, by sample. The first block uses every "
                "quarterly report with complete market data; the second block restricts to those "
                "with a located Item 1A so that the whole-filing and excluding columns describe one "
                "sample. ARK holdings and Nasdaq-100 each include the shared companies; Pooled counts "
                "every company once.")
    report.table(show(pd.DataFrame(rows), **{"All filings": "int", "Effect (pp)": "{:+.2f}", "p": "p",
                                             "Located Item 1A": "int", "Whole filing (pp)": "{:+.2f}",
                                             "p ": "p", "Excluding Item 1A (pp)": "{:+.2f}", "p  ": "p"}),
                 keep_together=False)
    report.p(
        f"In ARK quarterly reports one standard deviation of negative word share is associated with "
        f"{100 * R_full['ark'].effect_1sd:+.2f} pp of four-session excess return on all "
        f"{int(R_full['ark'].n):,} filings ({p_text(R_full['ark'].p)}) and with "
        f"{100 * R['ark']['whole'].effect_1sd:+.2f} pp on the {int(R['ark']['whole'].n):,} filings whose "
        f"Item 1A could be located ({p_text(R['ark']['whole'].p)}, against a detectable effect of "
        f"{100 * R['ark']['whole'].mde80_1sd:.2f} pp). Figure 6 shows the pattern on that subsample: "
        f"the highest quintile earns the lowest median return, though the relation is not monotonic. "
        f"In the index the estimates are {100 * R_full['ndx'].effect_1sd:+.2f} pp "
        f"({p_text(R_full['ndx'].p)}) and {100 * R['ndx']['whole'].effect_1sd:+.2f} pp "
        f"({p_text(R['ndx']['whole'].p)}), and the quintile plot is flat.")
    report.p(
        f"Excluding Item 1A removes the ARK association: on the same filings the effect is "
        f"{100 * R['ark']['body'].effect_1sd:+.2f} pp ({p_text(R['ark']['body'].p)}), and the dashed "
        f"line in Figure 6 no longer falls across quintiles. The disclosure choice itself points the "
        f"same way, short of significance at 5%: in the switch regression of Table B2 run on ARK "
        f"holdings, a company that stops restating its risk factors earns {100 * sw_ark_ret.coef:+.1f} "
        f"pp over the four sessions ({p_text(sw_ark_ret.p)}, {int(sw_ark_ret.n_treated)} such "
        f"quarters). A company that prints its risk factors prints thousands of negative words and "
        f"scores badly; one that refers to the annual report does not, and the whole-filing measure "
        f"captures that choice. Whether the market responds to the choice, or the choice and the "
        f"return both respond to something else about the quarter, this design cannot say: switches "
        f"are not randomly assigned and earnings releases fall in the same sessions.")

    # ====================================================== 6 MECHANISM
    report.section("6. Mechanism: Risk-Factor Disclosure in Quarterly Reports")
    def mode_share(group, year, mode):
        part = in_group(q_located, group)
        part = part[part.quarter.str[:4].eq(str(year))]
        return 100 * part.risk_mode.eq(mode).mean()
    report.p(
        "Figure 7 shows how the four disclosure modes divide the quarterly reports of each group in "
        "each year, and how that division has moved.")
    report.figure(FIG / "fig6_modes.png", "Figure 7")
    report.note(
        "Figure 7. Disclosure mode of Item 1A in quarterly reports with a located heading, share of "
        "filings by filing year, ARK holdings and Nasdaq-100 each including the shared companies. "
        "Modes are classified from the section's opening text and length by the rules in Appendix A. "
        "2026 covers filings through September.")
    report.p(
        f"A 10-Q satisfies Item 1A either by restating the risk factors or by stating that nothing "
        f"material has changed since the annual report. Of {n_q:,} quarterly reports with a located "
        f"heading, {mode_n['full']:,} ({share['full']:.0f}%) restate, {mode_n['reference_only']:,} "
        f"({share['reference_only']:.0f}%) refer the reader to the annual report, "
        f"{mode_n['partial_update']:,} ({share['partial_update']:.0f}%) claim no material change but "
        f"add updates, and {mode_n['omitted']:,} ({share['omitted']:.0f}%) disclose nothing. Among "
        f"ARK holdings the restating share drifts down from {mode_share('ARK', 2021, 'full'):.0f}% of "
        f"quarterly reports in 2021 to {mode_share('ARK', 2026, 'full'):.0f}% in 2026, while the share "
        f"referring to the annual report rises from {mode_share('ARK', 2021, 'reference_only'):.0f}% to "
        f"{mode_share('ARK', 2026, 'reference_only'):.0f}%; the index goes from "
        f"{mode_share('NDX', 2021, 'full'):.0f}% restating to {mode_share('NDX', 2026, 'full'):.0f}%. "
        f"Loughran and McDonald document the same behaviour for the MD&A section, incorporated by "
        f"reference by 55% of firms in 1994 and 9% in 2008, correlated with firm size, and describe "
        f"the sample as changing in a nonrandom way through time.")
    report.sub("Decomposition")
    report.p(
        "A filing's word share is a weighted average of the share inside Item 1A and the share in the "
        "balance, weighted by Item 1A's share of the words. Between two filings by one company the "
        "change therefore splits exactly into a language term, the two parts being written "
        "differently, and a composition term, the risk section changing size (Appendix A gives the "
        "identity). Table 8 reports both terms and the change in the balance alone.")
    dcv = dc.copy()
    dcv["Transition"] = dcv.transition.map(TRANSITION)
    dcv = dcv[["category", "Transition", "n", "companies", "change_pp", "body_change_pp",
               "language_pp", "composition_pp", "median_risk_words_change"]]
    dcv.columns = ["Measure", "Transition", "Filings", "Companies", "Change (pp)",
                   "Change excl. Item 1A (pp)", "Language term (pp)", "Composition term (pp)",
                   "Median change in Item 1A words"]
    report.sub("Table 8. Filing-to-filing change in word share, by disclosure transition")
    report.note("Quarterly reports, pooled sample, each compared with the same company's previous "
                "quarterly report. Transitions describe whether the company restated risk factors in "
                "the earlier and the later filing. The language and composition terms sum to the change.")
    report.table(show(dcv, Filings="int", Companies="int", **{"Change (pp)": "{:+.3f}",
                      "Change excl. Item 1A (pp)": "{:+.3f}", "Language term (pp)": "{:+.3f}",
                      "Composition term (pp)": "{:+.3f}", "Median change in Item 1A words": "int"}),
                 keep_together=False)
    report.p(
        f"When a company stops restating, its uncertainty word share falls {abs(to_ref_u.change_pp):.3f} "
        f"pp and its negative share {abs(to_ref_n.change_pp):.3f} pp, across {int(to_ref_u.n)} such "
        f"filings by {int(to_ref_u.companies)} companies. The balance of the filing moves the other "
        f"way for uncertainty ({to_ref_u.body_change_pp:+.3f} pp) and hardly at all for negative "
        f"language ({to_ref_n.body_change_pp:+.3f} pp). Companies that start restating show the "
        f"mirror image, {to_full_u.change_pp:+.3f} pp on the whole filing and "
        f"{to_full_u.body_change_pp:+.3f} pp on the balance. Companies that keep doing what they did "
        f"move by less than 0.01 pp on either measure.")
    report.p(
        f"The language term overstates how much the writing changed and should not be read alone. "
        f"The sentence that replaces the risk factors is itself about risk. Reference-only sections "
        f"run at {density['reference_only']:.2f}% uncertainty words against {density['full']:.2f}% "
        f"for a restated section, so the section's own share jumps when it collapses to one "
        f"sentence and the language term inherits the jump. The change in the balance of the filing "
        f"is the clean statistic, and it is small.")
    report.p(
        "Figure 8 shows the mechanism in the two companies with the largest single-quarter changes "
        "in Item 1A length, one in each direction.")
    report.figure(FIG / "fig8_cases.png", "Figure 8")
    report.note(
        f"Figure 8. Left: {drop.ticker}, {pd.Timestamp(drop.filing_date):%B %Y}, Item 1A from "
        f"{drop.prev_risk_words:,.0f} to {drop.risk_words:,.0f} words. Right: {rise.ticker}, "
        f"{pd.Timestamp(rise.filing_date):%B %Y}, from {rise.prev_risk_words:,.0f} to "
        f"{rise.risk_words:,.0f}. Bars are Item 1A words; lines are uncertainty word share of the whole "
        f"filing (solid) and excluding Item 1A (dashed).")
    report.p(
        f"When {drop.ticker} replaced a {drop.prev_risk_words / 1000:.0f}-thousand-word section with "
        f"{drop.risk_words:.0f} words, its whole-filing uncertainty share fell "
        f"{abs(100 * drop_ev.Uncertainty_change):.2f} pp and the share of the balance "
        f"{abs(100 * drop_ev.Uncertainty_body_change):.2f} pp. When {rise.ticker} restated after "
        f"{rise_years} years of referring, the whole-filing share rose "
        f"{100 * rise_ev.Uncertainty_change:.2f} pp for "
        f"one quarter and the balance {100 * rise_ev.Uncertainty_body_change:+.2f} pp. In both cases "
        f"the section's length accounts for most of the movement in the headline measure.")

    # ===================================================== 7 CONCLUSION
    report.section("7. Conclusion")
    report.p(
        f"Two of the four whole-filing results survive the correction, and the correction itself is "
        f"the main finding. Annual-report tone is rising. Within company, on the filing excluding "
        f"Item 1A, negative words gain {pp(k_neg_b.coef)} a year and uncertainty words "
        f"{pp(k_unc_b.coef)} in the pooled sample, both at {p_text(k_neg_b.p)}; the pattern holds in "
        f"each group, and the tf.idf score confirms it for negative tone. This is the report's "
        f"firmest result. It is {100 * ratio_lo:.0f}% to {100 * ratio_hi:.0f}% of the size the "
        f"whole-filing measure reports, because Item 1A is lengthening at the same time.")
    report.p(
        f"ARK holdings and Nasdaq-100 constituents write alike outside their risk sections. On the "
        f"annual reports with a located Item 1A, the {abs(100 * k_dunc_w.coef):.2f} pp uncertainty "
        f"gap on the whole filing is {abs(100 * k_dunc_b.coef):.3f} pp once the section is removed "
        f"({p_text(k_dunc_b.p)}). The difference between the two portfolios is a difference in how "
        f"much risk disclosure they print. That result is as firm as the trend: it holds on "
        f"identical filings and for both word lists.")
    report.p(
        f"Uncertainty does not predict the following quarter's volatility. The one estimate "
        f"significant before the prior-volatility control is not significant after it, and the "
        f"intervals in quarterly reports reach {v_whole_hi:.1f} pp of annualised volatility per "
        f"standard deviation on the whole filing and {v_body_hi:.1f} pp excluding Item 1A. This is an "
        f"imprecise zero rather than a demonstrated absence, and it does not change when the risk "
        f"section is excluded.")
    report.p(
        f"Negative tone is associated with the four-session return in ARK quarterly reports on the "
        f"whole filing, at {p_text(R['ark']['whole'].p)} on the filings with a located Item 1A and "
        f"{p_text(R_full['ark'].p)} on all of them, and not once Item 1A is removed "
        f"({p_text(R['ark']['body'].p)}) nor in the index on either measure. This report does not "
        f"read the whole-filing result as sentiment moving prices. On the whole filing the negative "
        f"word share of a quarterly report largely records whether the risk factors are printed, so "
        f"the result says that ARK holdings which print them earn lower returns that quarter than "
        f"holdings which refer to the annual report. The switch indicator points the same way at "
        f"{p_text(sw_ark_ret.p)}, and this design cannot separate either association from whatever "
        f"else distinguishes those quarters.")
    report.p(
        f"Two changes to practice follow for anyone monitoring a portfolio with these measures. Rank "
        f"and trend companies on the measure excluding Item 1A, or the ranking will sort them by "
        f"disclosure practice. And treat a change in that practice as an event in its own right: the "
        f"quarter in which a holding stops restating its risk factors moves its whole-filing "
        f"uncertainty share by {abs(to_ref_u.change_pp):.2f} pp on average (Table 8), against an "
        f"annual trend of {pp(a_unc.coef)}.")

    # ====================================================== APPENDIX A
    report.page_break()
    report.section("Appendix A. Methods")
    report.sub("Word lists and parsing")
    report.p(
        f"Word lists are the entries with a positive year in the Negative and Uncertainty columns of "
        f"the Loughran-McDonald Master Dictionary, 1993 to 2025 release, updated March 2026: "
        f"{a['lexicon_counts']['Negative']:,} and {a['lexicon_counts']['Uncertainty']} words. Filing "
        f"text is the primary document with hidden inline-XBRL content removed and tables dropped "
        f"where more than 15% of non-space characters are digits. Tokens are alphabetic strings of at "
        f"least two characters, uppercased. Exhibits and material incorporated by reference are not "
        f"recovered.")
    report.sub("Scores")
    report.equation(r"P_{cj}=\frac{\sum_{i \in c} tf_{ij}}{W_j}")
    report.equation(r"T_{cj}=\sum_{i \in c,\, tf_{ij}>0}"
                    r"\frac{1+\ln(tf_{ij})}{1+\ln(a_j)}\,\ln\!\left(\frac{N}{df_i}\right)")
    report.p(
        "P is the word share of list c in filing j and W the filing's word count. T is equation (1) "
        "of Loughran and McDonald (2011): tf is the count of word i in filing j, a the filing's "
        "average word frequency (words divided by distinct words), N the number of filings in the "
        "estimation corpus and df the number containing word i. Logarithms are natural; the paper "
        "does not state a base. Document frequencies are fitted on the pooled text sample, so tf.idf "
        "scores are comparable across filings within this report.")
    report.sub("Locating Item 1A")
    report.p(
        "The section opens at an occurrence of the heading Item 1A followed by Risk Factors that "
        "satisfies four conditions, and the last such occurrence in the filing is taken:")
    report.bullets([
        "It is not preceded within 60 characters by a reference cue such as in, see, under or Part I.",
        "It is not followed within 90 characters by another item number, which marks a table of "
        "contents or a cross-reference index.",
        "It is followed by text opening with a capital letter, since a citation continues with a "
        "lowercase word or a punctuation mark.",
        "It carries the item label; filers who head the section Risk Factors alone are recorded as "
        "not located.",
    ])
    report.p(
        "The section closes at the next item heading whose title is also present, such as Item 1B "
        "Unresolved Staff Comments or Item 2 Unregistered Sales. A bare SIGNATURES line is not "
        "treated as a closing marker.")
    report.p(
        "Disclosure mode is read from the section's first 800 characters and its length. Sections "
        "over 400 words are full restatements unless they claim no material change, in which case "
        "they are partial updates. Shorter sections that claim no material change or point to the "
        "annual report are reference-only; shorter sections that do neither are recorded as nothing "
        "disclosed.")
    report.sub("Decomposition")
    report.equation(r"S = w\,S_{\mathrm{risk}} + (1-w)\,S_{\mathrm{body}}")
    report.equation(r"\Delta S = \bar w\,\Delta S_{\mathrm{risk}} + (1-\bar w)\,\Delta S_{\mathrm{body}}"
                    r" \;+\; \Delta w\,(\bar S_{\mathrm{risk}} - \bar S_{\mathrm{body}})")
    report.p(
        "w is Item 1A's share of the filing's words and bars denote the mean over the two filings "
        "being compared. The first two terms are the language term and the third the composition "
        "term; the identity is exact. Comparisons are within company and within form.")
    report.sub("Event windows and controls")
    report.p(
        "Day 0 is the first NYSE session on or after the later of the filing date and the EDGAR "
        "acceptance date, with acceptance at or after the close moved to the next session. The "
        "filing-period return is the adjusted close on day 3 over the adjusted close on day -1, less "
        "the same ratio for SPY. Prior volatility is the sample standard deviation of 55 daily "
        "returns over days -60 to -6, annualised; post-filing volatility uses 60 returns over days 4 "
        "to 63. Size is the nominal close on day -1 times the cover-page share count of the filing "
        "being scored, from the XBRL fact EntityCommonStockSharesOutstanding. Dollar volume is the "
        "mean of nominal close times volume over days -60 to -6. Prior excess return is the "
        "SPY-adjusted buy-and-hold return over the same window. Filings with a day -1 price below "
        "three dollars are excluded. The outcome regressions carry company and calendar-quarter "
        "effects, log size, log dollar volume, prior excess return and, where stated, prior "
        "volatility.")
    report.sub("Regressions and inference")
    report.p(
        "The aggregate trend model regresses the quarterly mean on elapsed years and three seasonal "
        "indicators, with ordinary and Newey-West (four lags) standard errors. The within-company "
        "model adds company effects to filing-level observations. Saturated calendar-quarter effects "
        "are not used in trend models because they absorb the trend. Standard errors in all "
        "filing-level regressions are clustered two ways by company and calendar quarter, with "
        "inference degrees of freedom one fewer than the smaller cluster count. Group differences "
        "use the index indicator on the pooled disjoint sample with calendar-quarter effects. The "
        "detectable effect is the coefficient that a two-sided 5% test would find with 80% power at "
        "the estimated standard error. An indicator regressor identified by fewer than ten filings "
        "is reported as unidentified rather than estimated; one annual report in the sample changed "
        "disclosure mode.")

    # ====================================================== APPENDIX B
    report.page_break()
    report.section("Appendix B. Supplementary Tables")
    modes = d["modes"].copy()
    modes["group"] = modes.group.map(GROUP_EXACT)
    modes = modes.rename(columns={"group": "Group", "year": "Year", **MODE})
    modes["Year"] = modes.Year.astype(int).astype(str)
    modes = modes[["Group", "Year"] + [MODE[m] for m in ["full", "partial_update", "reference_only", "omitted", "not_found"]]]
    report.sub("Table B1. Disclosure mode by group and year, quarterly reports (%)")
    report.note("Groups here are disjoint: ARK only, Nasdaq-100 only, and the companies in both. "
                "Shares are of all quarterly reports, including those with no located heading.")
    report.table(show(modes, **{MODE[m]: "{:.1f}" for m in MODE}), keep_together=False)

    rows = []
    for run, g in [("all", "ALL"), ("ark", "ARK"), ("ndx", "NDX")]:
        part = sw[run][sw[run].status.eq("ok") & sw[run].measure.isin(["to_reference", "to_full", "prints_risk_factors"])]
        for _, r in part.iterrows():
            rows.append({"Sample": GROUP[g], "Report": r["sample"],
                         "Outcome": {"filing_return": "Four-session excess return",
                                     "volatility_with_prevol": "Post-filing volatility, prior controlled"}[r.model],
                         "Regressor": {"to_reference": "Stopped restating", "to_full": "Started restating",
                                       "prints_risk_factors": "Restates this quarter"}[r.measure],
                         "Filings": r.n, "Treated": r.n_treated, "Estimate (pp)": 100 * r.coef,
                         "SE": 100 * r.se, "p": r.p})
    report.sub("Table B2. Disclosure switches and market outcomes")
    report.note("Same controls and clustering as Tables 5 and 6. Treated is the number of filings "
                "with the indicator on. ARK holdings and Nasdaq-100 include the shared companies.")
    report.table(show(pd.DataFrame(rows), Filings="int", Treated="int",
                      **{"Estimate (pp)": "{:+.2f}", "SE": "{:.2f}", "p": "p"}), keep_together=False)

    agg2 = agg4.copy()
    agg2["Measure"] = agg2.measure.map(MEASURE)
    agg2["slope"] = np.where(agg2.measure.str.endswith("prop"), 100 * agg2.coef, agg2.coef)
    agg2["Inference"] = agg2.inference.map({"OLS": "Ordinary", "HAC4": "Newey-West, 4 lags"})
    agg2 = agg2[["sample", "Measure", "Inference", "slope", "t", "p"]]
    agg2.columns = ["Report", "Measure", "Standard errors", "Slope per year", "t", "p"]
    report.sub("Table B3. Aggregate trend, ordinary against Newey-West standard errors")
    report.table(show(agg2, **{"Slope per year": "{:+.3f}", "t": "{:.2f}", "p": "p"}), keep_together=False)

    rows = []
    for run, g in [("ark_only", "ARK only"), ("ndx_only", "Nasdaq-100 only")]:
        w = d["table4_by"][run]
        w = w[w.model.eq("within_firm_trend") & w.inference.eq("firm_quarter_cluster")]
        for _, r in w.iterrows():
            scale = 100 if r.measure.endswith("prop") else 1
            rows.append({"Sample": g, "Report": r["sample"], "Measure": MEASURE[r.measure],
                         "Within-company slope": scale * r.coef, "t": r.t, "p": r.p, "Filings": r.n})
    report.sub("Table B4. Within-company trends on the disjoint samples")
    report.note("The 22 companies held by ARK and in the index are excluded from both.")
    report.table(show(pd.DataFrame(rows), **{"Within-company slope": "{:+.3f}", "t": "{:.2f}", "p": "p",
                                             "Filings": "int"}), keep_together=False)

    firms = levels.merge(slopes, on="ticker", how="outer").sort_values("level", ascending=False)
    firms = firms.rename(columns={"ticker": "Ticker", "level": "Latest annual report (%)",
                                  "filing_date": "Filed", "slope": "Slope per year (pp)",
                                  "n": "Annual reports"})
    report.sub("Table B5. ARK holdings, uncertainty words excluding Item 1A")
    report.note("Filed is the date of the company's latest annual report with a located Item 1A. "
                "Slopes are within-company trends over all such reports, shown where at least "
                "three exist.")
    report.table(show(firms[["Ticker", "Filed", "Latest annual report (%)", "Slope per year (pp)",
                             "Annual reports"]],
                      **{"Latest annual report (%)": "{:.2f}", "Slope per year (pp)": "{:+.3f}",
                         "Annual reports": "int"}), keep_together=False)

    evq = ev[ev.form.eq("10-Q")]
    n_events = len(evq)
    evq = evq.reindex(evq.risk_words_change.abs().sort_values(ascending=False).index).head(20)
    evq = evq.sort_values("risk_words_change").copy()
    evq["Transition"] = evq.transition.map(TRANSITION)
    evq["group"] = evq.group.map(GROUP_EXACT)
    evq = evq[["ticker", "group", "filing_date", "Transition", "prev_risk_words", "risk_words",
               "Uncertainty_change", "Uncertainty_body_change"]]
    evq.columns = ["Ticker", "Group", "Filed", "Transition", "Item 1A words before", "Item 1A words after",
                   "Uncertainty change (pp)", "Change excl. Item 1A (pp)"]
    evq["Uncertainty change (pp)"] *= 100
    evq["Change excl. Item 1A (pp)"] *= 100
    report.sub(f"Table B6. The 20 largest disclosure switches in quarterly reports, of {n_events}")
    report.note("Ranked by the change in Item 1A words. The full list is in the data workbook that "
                "accompanies this report.")
    report.table(show(evq, **{"Item 1A words before": "int", "Item 1A words after": "int",
                              "Uncertainty change (pp)": "{:+.3f}", "Change excl. Item 1A (pp)": "{:+.3f}"}),
                 keep_together=False)

    cov = (100 * sec.groupby(["group", "form"]).risk_found.mean()).unstack().reset_index()
    cov["group"] = cov.group.map(GROUP_EXACT)
    cov.columns = ["Group", "10-K (%)", "10-Q (%)"]
    report.sub("Table B7. Share of filings with a located Item 1A heading, disjoint groups")
    report.table(show(cov, **{"10-K (%)": "{:.1f}", "10-Q (%)": "{:.1f}"}))

    report.section("References")
    report.link("Loughran, Tim, and Bill McDonald, 2011, When is a liability not a liability? Textual "
                "analysis, dictionaries, and 10-Ks, Journal of Finance 66, 35-65.",
                "https://doi.org/10.1111/j.1540-6261.2010.01625.x")
    report.link("Loughran-McDonald Master Dictionary, 1993 to 2025 release, updated March 2026.",
                "https://sraf.nd.edu/loughranmcdonald-master-dictionary/")
    report.link("U.S. Securities and Exchange Commission, EDGAR filings and company facts.",
                "https://www.sec.gov/edgar")
    report.link("Code, executed notebook and tests.", "https://github.com/robynge/FRE-GY-7871A-Assignment1")

    pdf = OUTPUT_DIR / "Filing_Tone_and_Risk_Factor_Disclosure.pdf"
    report.save(pdf, OUTPUT_DIR / "REPORT.md")
    print(f"Wrote {pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
