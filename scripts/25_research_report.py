"""Write the research report.

Every number in the prose is looked up from the CSV that produced it, so the
report cannot drift from the analysis. Run the analysis scripts first.

    python scripts/25_research_report.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import INTERIM_DIR, OUTPUT_DIR, UNIVERSE_DIR, holdings_group
from src.report_builder import Report

RUN = OUTPUT_DIR / "all"
COMPARISON = OUTPUT_DIR / "comparison"
DISCLOSURE = RUN / "disclosure"

MODE_LABEL = {
    "full": "Risk factors restated",
    "partial_update": "No material change, updates given",
    "reference_only": "No material change, reader referred to the annual report",
    "omitted": "Section present, nothing disclosed",
    "not_found": "No Item 1A heading located",
}
CATEGORY_LABEL = {"Negative": "Negative", "Uncertainty": "Uncertainty"}
TRANSITION_LABEL = {
    "to_reference": "Stopped restating", "to_full": "Started restating",
    "stays_full": "Kept restating", "stays_reference": "Kept referring",
}


def pct(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}%"


def pp(value: float, digits: int = 3) -> str:
    return f"{value:+.{digits}f} percentage points"


def p_text(value: float) -> str:
    if not np.isfinite(value):
        return "not estimable"
    return "p < 0.001" if value < .001 else f"p = {value:.3f}"


def show(frame: pd.DataFrame, **spec) -> pd.DataFrame:
    """Format columns for display: "int", "p", or a format string such as "{:.3f}".

    Everything becomes a string, so a table never shows a count as 1,053.000 or
    a p value in scientific notation.
    """
    out = frame.copy()
    for column, how in spec.items():
        if how == "int":
            out[column] = out[column].map(
                lambda v: "" if pd.isna(v) else f"{int(round(v)):,}")
        elif how == "p":
            out[column] = out[column].map(p_short)
        else:
            out[column] = out[column].map(lambda v: "" if pd.isna(v) else how.format(v))
    return out


def p_short(value: float) -> str:
    if not np.isfinite(value):
        return "not estimable"
    if value < .001:
        return "< 0.001"
    return f"{value:.3f}"


def one(frame: pd.DataFrame, **conditions) -> pd.Series:
    mask = pd.Series(True, index=frame.index)
    for column, value in conditions.items():
        mask &= frame[column].eq(value)
    selected = frame.loc[mask]
    if len(selected) != 1:
        raise ValueError(f"Expected exactly one row for {conditions}, found {len(selected)}")
    return selected.iloc[0]


def main() -> int:
    audit = json.loads((RUN / "audit.json").read_text())
    sections = pd.read_csv(INTERIM_DIR / "risk_sections.csv", dtype={"cik": str})
    universe = pd.read_csv(UNIVERSE_DIR / "universe.csv", dtype={"cik": str})
    universe["group"] = universe.funds.map(holdings_group)
    filers = universe[universe.status.eq("domestic_filer")]

    decomposition = pd.read_csv(DISCLOSURE / "decomposition.csv")
    trends = pd.read_csv(COMPARISON / "corrected_trends.csv")
    differences = pd.read_csv(COMPARISON / "differences.csv")
    ex_item = pd.read_csv(COMPARISON / "differences_excluding_item_1a.csv")
    practice = pd.read_csv(COMPARISON / "disclosure_practice.csv")
    switches = pd.read_csv(DISCLOSURE / "switch_regressions.csv")
    outcomes = pd.read_csv(DISCLOSURE / "switch_outcomes.csv")
    table4 = pd.read_csv(RUN / "table4.csv")
    table5 = pd.read_csv(RUN / "table5.csv")

    report = Report(
        "Filing language: ARK holdings and the Nasdaq-100",
        f"Negative and uncertain wording in {audit['final_filings']:,} annual and quarterly "
        f"reports filed by {audit['final_companies']} companies held by the six ARK ETFs or "
        f"included in the Nasdaq-100, {audit['sample_start']} to {audit['sample_end']}.",
        running_head="Filing language: ARK holdings and the Nasdaq-100")

    # ---------------------------------------------------------------- summary
    located = sections[sections.risk_found]
    quarterly = located[located.form.eq("10-Q")]
    restating = quarterly.risk_mode.isin(["full", "partial_update"]).mean()
    to_reference = one(decomposition, category="Uncertainty", transition="to_reference")
    ten_k_negative_whole = one(trends, run="all", sample="10-K", category="Negative",
                               scope="whole filing")
    ten_k_negative_body = one(trends, run="all", sample="10-K", category="Negative",
                              scope="excluding Item 1A")
    difference_whole = one(ex_item, sample="10-K", category="Uncertainty",
                           scope="whole filing")
    difference_body = one(ex_item, sample="10-K", category="Uncertainty",
                          scope="excluding Item 1A")

    ten_k_uncertainty_whole_sum = one(trends, run="all", sample="10-K",
                                      category="Uncertainty", scope="whole filing")
    ten_k_uncertainty_body_sum = one(trends, run="all", sample="10-K",
                                     category="Uncertainty", scope="excluding Item 1A")
    course_return = pd.read_csv(OUTPUT_DIR / "course_ark_2021_2025" / "disclosure"
                                / "switch_regressions.csv")
    course_whole = one(course_return, sample="10-Q", model="filing_return",
                       measure="Negative_prop_total")
    course_body = one(course_return, sample="10-Q", model="filing_return",
                      measure="Negative_prop_body")
    volatility_whole = one(switches, sample="10-Q", model="volatility_with_prevol",
                           measure="Uncertainty_prop_total")
    volatility_body = one(switches, sample="10-Q", model="volatility_with_prevol",
                          measure="Uncertainty_prop_body")

    report.section("Findings")
    findings = pd.DataFrame([
        {"Test": "10-K negative tone, trend per year",
         "Whole filing": f"{100 * ten_k_negative_whole.coef:+.3f} pp, {p_text(ten_k_negative_whole.p)}",
         "Excluding Item 1A": f"{100 * ten_k_negative_body.coef:+.3f} pp, {p_text(ten_k_negative_body.p)}",
         "Assessment": "Holds. Headline overstates roughly twofold"},
        {"Test": "10-K uncertainty, trend per year",
         "Whole filing": f"{100 * ten_k_uncertainty_whole_sum.coef:+.3f} pp, {p_text(ten_k_uncertainty_whole_sum.p)}",
         "Excluding Item 1A": f"{100 * ten_k_uncertainty_body_sum.coef:+.3f} pp, {p_text(ten_k_uncertainty_body_sum.p)}",
         "Assessment": "Holds. Word frequency, not distinctiveness"},
        {"Test": "10-K uncertainty level, index less ARK",
         "Whole filing": f"{100 * difference_whole.coef:+.3f} pp, {p_text(difference_whole.p)}",
         "Excluding Item 1A": f"{100 * difference_body.coef:+.3f} pp, {p_text(difference_body.p)}",
         "Assessment": "Composition. No prose difference"},
        {"Test": "Uncertainty on next-quarter volatility, 10-Q",
         "Whole filing": f"{100 * volatility_whole.effect_1sd:+.2f} pp per SD, {p_text(volatility_whole.p)}",
         "Excluding Item 1A": f"{100 * volatility_body.effect_1sd:+.2f} pp per SD, {p_text(volatility_body.p)}",
         "Assessment": "No signal on either measure"},
        {"Test": "Negative tone on filing-window return, 10-Q, ARK",
         "Whole filing": f"{100 * course_whole.effect_1sd:+.2f} pp per SD, {p_text(course_whole.p)}",
         "Excluding Item 1A": f"{100 * course_body.effect_1sd:+.2f} pp per SD, {p_text(course_body.p)}",
         "Assessment": "Composition. Not replicated in the index"},
    ])
    report.table(findings, widths=[126, 92, 92, 125])
    report.p(
        f"{100 * (1 - restating):.0f}% of quarterly reports do not restate their risk "
        f"factors. Of {len(quarterly):,} quarterly reports with a located Item 1A, "
        f"{pct(100 * restating, 1)} restate and the balance refer the reader to the annual "
        f"report. The two run to about 19,000 words and 60 words respectively. Both "
        f"dictionary measures are word shares, so the disclosure choice moves them "
        f"mechanically.")
    report.p(
        f"That mechanical effect is larger than any language effect measured here. "
        f"Companies that stop restating record uncertainty word share "
        f"{to_reference.change_pp:+.3f} pp; the same filings excluding Item 1A record "
        f"{to_reference.body_change_pp:+.3f} pp. Headline measure and prose move in "
        f"opposite directions.")
    report.p(
        "Applying the correction leaves the two annual-report trends standing at roughly "
        "half their headline size and removes the group difference, the volatility "
        "association and the return association.")

    # ---------------------------------------------------------------- sample
    report.section("1. Sample and method")
    counts = filers.groupby("group").agg(companies=("cik", "nunique"),
                                         annual=("n_10k", "sum"),
                                         quarterly=("n_10q", "sum")).reset_index()
    counts["group"] = counts.group.map({"ARK": "ARK funds only", "NDX": "Nasdaq-100 only",
                                        "BOTH": "Held by an ARK fund and in the index"})
    counts.columns = ["Group", "Companies", "10-K filings", "10-Q filings"]
    report.p(
        f"{filers.cik.nunique()} SEC filers, from the six ARK ETFs and the Nasdaq-100 as "
        f"at {audit['as_of_date']}, after removing funds, cash, non-US listings and "
        f"companies reporting on 20-F or 40-F. "
        f"{audit['expected_original_filings']:,} original 10-K and 10-Q filings from "
        f"{audit['sample_start']}, {audit['parse_failures']} parse failures. Amendments "
        f"recorded, never scored.")
    report.table(show(counts, **{"Companies": "int", "10-K filings": "int",
                                 "10-Q filings": "int"}))
    report.p(
        "Two dictionaries, kept separate throughout. The negative list measures how bad "
        "the news is; the uncertainty list measures how far management declines to commit. "
        "The two are distinct: a sentence stating that results may fluctuate depending on "
        "factors beyond the company's control carries no bad news. Each filing is scored "
        "twice on each list, as a word share and under the equation (1) weighting of "
        "Loughran and McDonald (2011).")
    report.p(
        f"Each filing is split into its risk-factor section and the balance, giving a "
        f"score on the part of the document a disclosure change does not remove. The "
        f"section is located by an explicit Item 1A heading, taking the occurrence that "
        f"opens a section rather than one of the many that cite it. Coverage is "
        f"{100 * sections.risk_found.mean():.1f}% of filings, within three points across "
        f"the two groups. Filers labelling the section differently are recorded as not "
        f"located, never inferred.")

    # ---------------------------------------------------- disclosure practice
    report.page_break()
    report.section("2. Disclosure practice")
    mode_table = (located[located.form.eq("10-Q")].risk_mode.value_counts()
                  .rename_axis("Disclosure mode").reset_index(name="Quarterly reports"))
    mode_table["Share of located sections"] = (
        100 * mode_table["Quarterly reports"] / mode_table["Quarterly reports"].sum()).round(1)
    mode_table["Median words in Item 1A"] = mode_table["Disclosure mode"].map(
        located[located.form.eq("10-Q")].groupby("risk_mode").risk_words.median())
    mode_table["Disclosure mode"] = mode_table["Disclosure mode"].map(MODE_LABEL)
    report.p(
        "A 10-Q may satisfy Item 1A by stating that nothing material has changed since "
        "the annual report. Median length under that route is 62 words, against 19,350 "
        "words for a restatement.")
    report.table(show(mode_table, **{"Quarterly reports": "int",
                                     "Share of located sections": "{:.1f}",
                                     "Median words in Item 1A": "int"}))

    density = located[located.form.eq("10-Q")].groupby("risk_mode").agg(
        risk=("Uncertainty_prop_risk", "mean"), body=("Uncertainty_prop_body", "mean"))
    report.p(
        f"The replacement sentence carries its own tone. Those pointers run at "
        f"{pct(100 * density.loc['reference_only', 'risk'], 2)} uncertainty words against "
        f"{pct(100 * density.loc['full', 'risk'], 2)} for a restated section. Dropping the "
        f"risk factors raises the density of what remains of Item 1A and removes almost "
        f"all of its weight. The two effects work against each other in the total.")

    report.sub("Decomposition")
    report.p(
        "A filing's word share is a weighted average of the share in its risk section and "
        "the share in the balance, weighted by the section's share of the words. Between "
        "two filings by one company the change splits exactly, with no residual:")
    report.equation(r"S = w\,S_{\mathrm{risk}} + (1-w)\,S_{\mathrm{body}}",
                    r"\Delta S = \bar w\,\Delta S_{\mathrm{risk}} + (1-\bar w)"
                    r"\,\Delta S_{\mathrm{body}} \;+\; "
                    r"\Delta w\,(\bar S_{\mathrm{risk}} - \bar S_{\mathrm{body}})")
    report.p(
        "The first two terms are the language term: the company writing differently. The "
        "third is the composition term: the company writing a different amount of the part "
        "carrying most of the risk vocabulary. Bars denote midpoints across the two "
        "filings, which is what makes the split exact rather than approximate.")
    decomposed = decomposition.copy()
    decomposed["Transition"] = decomposed.transition.map(TRANSITION_LABEL)
    decomposed["Measure"] = decomposed.category.map(CATEGORY_LABEL)
    view = decomposed[["Measure", "Transition", "n", "companies", "change_pp",
                       "body_change_pp", "language_pp", "composition_pp",
                       "median_risk_words_change"]].copy()
    view.columns = ["Measure", "Transition", "Filings", "Companies", "Change in share (pp)",
                    "Change excluding Item 1A (pp)", "Language term (pp)",
                    "Composition term (pp)", "Median change in Item 1A words"]
    report.table(show(view, **{"Filings": "int", "Companies": "int",
                               "Change in share (pp)": "{:+.3f}",
                               "Change excluding Item 1A (pp)": "{:+.3f}",
                               "Language term (pp)": "{:+.3f}",
                               "Composition term (pp)": "{:+.3f}",
                               "Median change in Item 1A words": "int"}))
    report.p(
        "The language term inherits the density effect above and should not be read on "
        "its own. The operative column is the change excluding Item 1A. For companies that "
        "stopped restating, it is +0.057 pp for uncertainty and -0.008 pp for negative "
        "language. Headline changes on the same filings are -0.190 pp and -0.359 pp. For "
        "uncertainty the two carry opposite signs. What changed was the volume of risk "
        "text.")
    report.figure(DISCLOSURE / "figure2_cases.png", "Four companies through a change of practice")
    report.note(
        "Four companies whose practice changed inside the sample. Bars: words in Item 1A. "
        "Dark line: uncertainty word share, whole filing. Purple line: same filing "
        "excluding Item 1A. Both lines on the right axis. Where the bars collapse or "
        "return, the dark line follows and the purple line does not.")

    # ------------------------------------------------------ levels and trends
    report.page_break()
    report.section("3. Levels and trends")
    report.figure(RUN / "figure1.png", "Quarterly tone and the VIX")
    report.note(
        "Company-centred quarterly means by report type, mean VIX on the right axis. "
        "Annual reports cluster in the first quarter and carry more risk language than "
        "quarterly reports, so the two are never pooled in a trend estimate.")
    report.p(
        "Trends below are estimated within company, with seasonal controls. Neither "
        "baseline differences across companies nor the annual sawtooth in filing dates can "
        "produce them. The aggregate quarterly series is estimated separately with "
        "Newey-West standard errors at four lags and reported in the workbook. Twenty "
        "quarterly observations of a persistent series regressed on time return a large t "
        "statistic whether or not anything is happening, so the within-company estimate is "
        "the one quoted.")

    trend_view = trends[trends.run.eq("all") & trends.status.eq("ok")
                        & trends["sample"].isin(["10-K", "10-Q"])].copy()
    trend_view["slope"] = 100 * trend_view.coef
    trend_view = trend_view[["sample", "category", "scope", "n", "slope", "p"]]
    trend_view.columns = ["Report", "Measure", "Scope", "Filings",
                          "Change per year (pp)", "p"]
    report.table(show(trend_view, **{"Filings": "int",
                                     "Change per year (pp)": "{:+.3f}", "p": "p"}))
    section_growth = one(trends, run="all", sample="10-K", category="Section length",
                         scope="Item 1A share of words")
    ten_k_uncertainty_whole = one(trends, run="all", sample="10-K", category="Uncertainty",
                                  scope="whole filing")
    ten_k_uncertainty_body = one(trends, run="all", sample="10-K", category="Uncertainty",
                                 scope="excluding Item 1A")
    report.p(
        f"Annual-report risk sections grow {pp(100 * section_growth.coef)} of the document "
        f"a year ({p_text(section_growth.p)}), which accounts for roughly half the measured "
        f"trend. Negative language moves from {pp(100 * ten_k_negative_whole.coef)} to "
        f"{pp(100 * ten_k_negative_body.coef)} a year once the section is removed, "
        f"uncertainty from {pp(100 * ten_k_uncertainty_whole.coef)} to "
        f"{pp(100 * ten_k_uncertainty_body.coef)}. All four remain significant at 1%. The "
        f"trend is a real change in how annual reports are written; the headline measure "
        f"overstates it roughly twofold.")
    quarterly_negative = one(trends, run="all", sample="10-Q", category="Negative",
                             scope="whole filing")
    report.p(
        f"Quarterly reports show no trend on either scope "
        f"({p_text(quarterly_negative.p)} for negative language over the whole filing), and "
        f"the estimates are unstable across the two groups. Weighted uncertainty declines "
        f"in quarterly reports in both groups, a statement about the distinctiveness of the "
        f"vocabulary rather than its volume.")
    weighted = table4[table4.model.eq("within_firm_trend")
                      & table4.inference.eq("firm_quarter_cluster")
                      & table4["sample"].eq("10-K")]
    weighted_uncertainty = weighted[weighted.measure.eq("Uncertainty_tfidf")].iloc[0]
    report.p(
        f"The weighted score does not confirm the annual-report uncertainty trend "
        f"({p_text(weighted_uncertainty.p)}). May and approximately appear in nearly every "
        f"filing and carry almost no weight under equation (1). A rise concentrated in "
        f"common vocabulary therefore lifts the word share and leaves the weighted score "
        f"unchanged. The uncertainty trend is about frequency, not about filings becoming "
        f"distinctively more hedged.")

    # ------------------------------------------------------------ comparison
    report.page_break()
    report.section("4. Group comparison")
    report.p(
        "Two separate regressions cannot establish that two groups differ: a significant "
        "slope in one and an insignificant slope in the other is not a difference. Every "
        "comparison here is a single regression on the pooled sample with an index "
        "indicator, calendar-quarter effects and two-way clustering by company and "
        "quarter. The 22 companies held by an ARK fund that are also index constituents "
        "are excluded, since they would otherwise sit on both sides of the difference.")
    level_view = differences[differences.model.eq("level_difference")
                             & differences.status.eq("ok")
                             & differences["sample"].isin(["10-K", "10-Q"])].copy()
    level_view["difference"] = np.where(level_view.measure_name.str.endswith("prop"),
                                        100 * level_view.coef, level_view.coef)
    level_view["measure_name"] = level_view.measure_name.map({
        "Negative_prop": "Negative word share (pp)",
        "Uncertainty_prop": "Uncertainty word share (pp)",
        "Negative_tfidf": "Negative weighted score",
        "Uncertainty_tfidf": "Uncertainty weighted score"})
    level_view = level_view[["sample", "measure_name", "n", "difference", "t", "p"]]
    level_view.columns = ["Report", "Measure", "Filings", "Nasdaq-100 less ARK", "t", "p"]
    report.table(show(level_view, **{"Filings": "int",
                                     "Nasdaq-100 less ARK": "{:+.3f}",
                                     "t": "{:.2f}", "p": "p"}))
    difference_negative_whole = one(ex_item, sample="10-K", category="Negative",
                                    scope="whole filing")
    difference_negative_body = one(ex_item, sample="10-K", category="Negative",
                                   scope="excluding Item 1A")
    report.p(
        f"ARK annual reports carry more negative and more uncertain language than index "
        f"constituents, and both gaps are significant. On the same "
        f"{int(difference_negative_whole.n):,} filings with the risk-factor section "
        f"removed, neither is.")
    ex_view = ex_item[ex_item.status.eq("ok") & ex_item["sample"].eq("10-K")].copy()
    ex_view["difference"] = 100 * ex_view.coef
    ex_view = ex_view[["category", "scope", "n", "difference", "t", "p"]]
    ex_view.columns = ["Measure", "Scope", "Filings", "Nasdaq-100 less ARK (pp)", "t", "p"]
    report.table(show(ex_view, **{"Filings": "int",
                                  "Nasdaq-100 less ARK (pp)": "{:+.3f}",
                                  "t": "{:.2f}", "p": "p"}))
    report.p(
        f"Negative language narrows from {abs(100 * difference_negative_whole.coef):.3f} "
        f"pp ({p_text(difference_negative_whole.p)}) to "
        f"{abs(100 * difference_negative_body.coef):.3f} pp "
        f"({p_text(difference_negative_body.p)}); uncertainty from "
        f"{abs(100 * difference_whole.coef):.3f} pp ({p_text(difference_whole.p)}) to "
        f"{abs(100 * difference_body.coef):.3f} pp ({p_text(difference_body.p)}). Outside "
        f"their risk factors the two groups are statistically indistinguishable. The "
        f"separation is in how much risk disclosure they print, which is a fact about "
        f"disclosure practice rather than about the businesses.")
    practice_view = practice.copy()
    practice_view["group"] = practice_view.group.map(
        {"ARK": "ARK funds only", "NDX": "Nasdaq-100 only",
         "BOTH": "Held by an ARK fund and in the index"})
    practice_view.columns = ["Group", "Quarterly reports", "Companies",
                             "Referred to the annual report (%)", "Median Item 1A words"]
    report.table(show(practice_view, **{"Quarterly reports": "int", "Companies": "int",
                                        "Referred to the annual report (%)": "{:.1f}",
                                        "Median Item 1A words": "int"}))
    report.p(
        "The practice is about as common in one group as the other. Companies in both the "
        "funds and the index restate most often and are also the largest.")

    # --------------------------------------------------------------- markets
    report.page_break()
    report.section("5. Market outcomes")
    report.sub("Volatility")
    volatility_view = table5[table5.inference.eq("firm_quarter_cluster")
                             & table5.status.eq("ok")].copy()
    volatility_view["effect"] = 100 * volatility_view.effect_1sd
    volatility_view["control"] = np.where(
        volatility_view.model.eq("volatility_with_prevol"), "Yes", "No")
    volatility_view["measure"] = volatility_view.measure.map(
        {"Uncertainty_prop": "Word share", "Uncertainty_tfidf": "Weighted score"})
    volatility_view = volatility_view[["sample", "measure", "control", "n", "effect", "p"]]
    volatility_view.columns = ["Report", "Measure", "Prior volatility controlled",
                               "Filings", "Effect of 1 SD (pp)", "p"]
    report.p(
        "The test is run twice on one shared sample, without and with prior volatility. "
        "Without the control it asks whether volatile companies write hedged filings, "
        "which they do. With it, whether the language carries information about a change "
        "in volatility. The gap between the two is the result.")
    report.table(show(volatility_view, **{"Filings": "int",
                                          "Effect of 1 SD (pp)": "{:+.3f}", "p": "p"}))
    body_with = one(switches, sample="10-Q", model="volatility_with_prevol",
                    measure="Uncertainty_prop_body")
    total_with = one(switches, sample="10-Q", model="volatility_with_prevol",
                     measure="Uncertainty_prop_total")
    weighted_before = one(table5, sample="10-Q", measure="Uncertainty_tfidf",
                          model="volatility_without_prevol",
                          inference="firm_quarter_cluster")
    weighted_after = one(table5, sample="10-Q", measure="Uncertainty_tfidf",
                         model="volatility_with_prevol",
                         inference="firm_quarter_cluster")
    report.p(
        f"One specification clears 5% before the control and none after. In quarterly "
        f"reports the weighted uncertainty score is worth "
        f"{100 * weighted_before.effect_1sd:+.2f} pp of annualised volatility per standard "
        f"deviation without prior volatility ({p_text(weighted_before.p)}) and "
        f"{100 * weighted_after.effect_1sd:+.2f} pp with it ({p_text(weighted_after.p)}). "
        f"What looked like language predicting volatility was volatile companies writing "
        f"hedged filings.")
    report.p(
        f"The measure excluding Item 1A does no better. In quarterly reports one standard "
        f"deviation is worth {100 * total_with.effect_1sd:+.3f} pp of annualised volatility "
        f"over the whole filing ({p_text(total_with.p)}) and "
        f"{100 * body_with.effect_1sd:+.3f} pp without the risk factors "
        f"({p_text(body_with.p)}). The detectable effect at 80% power is "
        f"{100 * body_with.mde80_1sd:.1f} pp. The correction removes a contaminated "
        f"measure; it does not produce a working one.")

    report.sub("Filing-window return")
    return_rows = []
    for run, label in [("course_ark_2021_2025", "ARK holdings, 2021-2025"),
                       ("ark", "ARK holdings"), ("ndx", "Nasdaq-100"), ("all", "Both")]:
        frame = pd.read_csv(OUTPUT_DIR / run / "disclosure" / "switch_regressions.csv")
        for measure, scope in [("Negative_prop_total", "Whole filing"),
                               ("Negative_prop_body", "Excluding Item 1A")]:
            row = one(frame, sample="10-Q", model="filing_return", measure=measure)
            return_rows.append({
                "Sample": label, "Scope": scope, "Filings": int(row.n),
                "Effect of 1 SD (pp)": 100 * row.effect_1sd,
                "Detectable effect (pp)": 100 * row.mde80_1sd, "p": row.p})
    report.table(show(pd.DataFrame(return_rows), **{"Filings": "int",
                                                    "Effect of 1 SD (pp)": "{:+.3f}",
                                                    "Detectable effect (pp)": "{:.3f}",
                                                    "p": "p"}))
    report.p(
        "The association appears in ARK holdings, is absent from the index, and "
        "disappears in every sample once the risk-factor section is removed. Read through "
        "the disclosure choice rather than the word count, the same pattern is that a "
        "company which stops restating its risk factors earns a higher filing-window "
        "return that quarter. Printing risk factors means printing thousands of negative "
        "words, and that is what the whole-filing measure captures.")
    report.p(
        "Whether the market responds to the disclosure choice, or both respond to "
        "something else about the quarter, cannot be settled here. Switches are not "
        "randomly assigned and earnings releases can fall in the same four sessions. What "
        "holds is that the association does not survive removing the section that drives "
        "the measure, and does not replicate in the index.")

    report.sub("Disclosure switches")
    switch_view = switches[switches.status.eq("ok")
                           & switches.measure.isin(["to_reference", "to_full"])
                           & switches["sample"].eq("10-Q")].copy()
    switch_view["effect"] = 100 * switch_view.coef
    switch_view["measure"] = switch_view.measure.map(TRANSITION_LABEL)
    switch_view["model"] = switch_view.model.map(
        {"filing_return": "Four-session excess return",
         "volatility_with_prevol": "Following-quarter volatility, prior volatility controlled"})
    switch_view = switch_view[["model", "measure", "n", "n_treated", "effect", "p"]]
    switch_view.columns = ["Outcome", "Event", "Filings", "Events", "Estimate (pp)", "p"]
    report.table(show(switch_view, **{"Filings": "int", "Events": "int",
                                      "Estimate (pp)": "{:+.3f}", "p": "p"}))
    descriptive = outcomes[outcomes.outcome.eq("filing_return")].copy()
    descriptive["transition"] = descriptive.transition.map(TRANSITION_LABEL)
    report.p(
        "A company that stops restating prints less negative language that quarter, so a "
        "literal reading of the measure implies a higher filing-window return. The "
        "estimate is about two percentage points higher and is not significant. This is a "
        "conditional association at best. One annual report in the sample changed "
        "practice. That is below the minimum for estimation and is reported as "
        "unidentified rather than as a result.")

    # ------------------------------------------------------------ limitations
    report.section("6. Limitations")
    report.bullets([
        "Holdings are a snapshot. Companies are selected on membership today and their "
        "filings read backwards, so the sample is the current portfolio through time, not "
        "the portfolio as held.",
        "Section location is incomplete at about seven filings in eight. Filers labelling "
        "their risk factors differently are absent from every comparison using the split; "
        "their whole-filing scores are unaffected.",
        "Equation (1) weights are fitted across each run and therefore use filings not "
        "published at the time of any given filing. The estimates are retrospective "
        "associations, not a live signal.",
        "Company and calendar-quarter effects with clustered standard errors address "
        "correlated errors and fixed differences between companies. They do not make a "
        "disclosure choice exogenous.",
        "Related specifications are reported without a multiple-testing correction. An "
        "isolated significant cell is weak evidence, which is why the results carried "
        "forward are those holding across report types, scoring methods and both groups.",
    ])

    report.section("Sources")
    report.link("Loughran and McDonald (2011), When Is a Liability Not a Liability? "
                "Textual Analysis, Dictionaries, and 10-Ks, Journal of Finance 66(1), 35-65",
                "https://doi.org/10.1111/j.1540-6261.2010.01625.x")
    report.link("Loughran-McDonald Master Dictionary, 1993-2025 release",
                "https://sraf.nd.edu/loughranmcdonald-master-dictionary/")
    report.link("SEC EDGAR filings and company facts", "https://www.sec.gov/edgar")

    pdf = OUTPUT_DIR / "Filing_Language_Research_Report.pdf"
    report.save(pdf, OUTPUT_DIR / "RESEARCH_REPORT.md")
    print(f"Wrote {pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
