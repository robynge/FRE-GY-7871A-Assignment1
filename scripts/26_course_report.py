"""Write the assignment report: ARK holdings, 2021 to 2025, Tables 1 to 6 and Figure 1.

Same computed results as the research report, restricted to the sample and the
window the assignment specifies, and organised around its six required exhibits.

    python scripts/26_course_report.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import INTERIM_DIR, OUTPUT_DIR
from src.report_builder import Report

RUN_NAME = "course_ark_2021_2025"
RUN = OUTPUT_DIR / RUN_NAME
COMPARISON = OUTPUT_DIR / "comparison"

FILTER_LABEL = {
    "foreign_reporting_forms": "Files 20-F or 40-F, not 10-K or 10-Q",
    "no_report_evidence": "No 10-K, 10-Q, 20-F or 40-F on record",
    "first_10x_after_sample": "First 10-K or 10-Q filed after the sample window",
    "10x_outside_sample": "10-K or 10-Q filed only outside the sample window",
    "incomplete_cached_history": "Filing history incomplete; exclusion unresolved",
}

MEASURE_LABEL = {
    "Negative_prop": "Negative word share (pp)",
    "Uncertainty_prop": "Uncertainty word share (pp)",
    "Negative_tfidf": "Negative weighted score",
    "Uncertainty_tfidf": "Uncertainty weighted score",
}


def p_short(value: float) -> str:
    if not np.isfinite(value):
        return "not estimable"
    return "< 0.001" if value < .001 else f"{value:.3f}"


def p_text(value: float) -> str:
    if not np.isfinite(value):
        return "not estimable"
    return "p < 0.001" if value < .001 else f"p = {value:.3f}"


def show(frame: pd.DataFrame, **spec) -> pd.DataFrame:
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


def one(frame: pd.DataFrame, **conditions) -> pd.Series:
    mask = pd.Series(True, index=frame.index)
    for column, value in conditions.items():
        mask &= frame[column].eq(value)
    selected = frame.loc[mask]
    if len(selected) != 1:
        raise ValueError(f"Expected one row for {conditions}, found {len(selected)}")
    return selected.iloc[0]


def main() -> int:
    audit = json.loads((RUN / "audit.json").read_text())
    waterfall = pd.read_csv(RUN / "table1.csv")
    company_panel = pd.read_csv(RUN / "table1_universe.csv")
    table2 = pd.read_csv(RUN / "table2.csv")
    table3 = pd.read_csv(RUN / "table3.csv")
    table4 = pd.read_csv(RUN / "table4.csv")
    table5 = pd.read_csv(RUN / "table5.csv")
    table6 = pd.read_csv(RUN / "table6.csv")
    trends = pd.read_csv(COMPARISON / "corrected_trends.csv")
    trends = trends[trends.run.eq(RUN_NAME) & trends.status.eq("ok")]
    sections = pd.read_csv(INTERIM_DIR / "risk_sections.csv", dtype={"cik": str})

    report = Report(
        "Uncertainty and sentiment in the filings of ARK holdings",
        f"Loughran and McDonald (2011) negative and uncertainty word lists applied to "
        f"{audit['final_filings']:,} 10-K and 10-Q filings by {audit['final_companies']} "
        f"companies held by the six ARK ETFs, filed {audit['sample_start']} to "
        f"{audit['sample_end']}. FRE-GY 7871 A, Assignment 1.",
        running_head="Uncertainty and sentiment in the filings of ARK holdings")

    # ------------------------------------------------------------- conclusions
    report.section("Conclusions")
    within_10k_negative = one(table4, sample="10-K", measure="Negative_prop",
                              model="within_firm_trend", inference="firm_quarter_cluster")
    within_10k_uncertainty = one(table4, sample="10-K", measure="Uncertainty_prop",
                                 model="within_firm_trend", inference="firm_quarter_cluster")
    body_10k_negative = one(trends, sample="10-K", category="Negative",
                            scope="excluding Item 1A")
    volatility_before = one(table5, sample="All", measure="Uncertainty_prop",
                            model="volatility_without_prevol",
                            inference="firm_quarter_cluster")
    volatility_after = one(table5, sample="All", measure="Uncertainty_prop",
                           model="volatility_with_prevol",
                           inference="firm_quarter_cluster")
    return_10q = one(table6, sample="10-Q", measure="Negative_prop",
                     model="filing_return", inference="firm_quarter_cluster")
    disclosure_tests = pd.read_csv(RUN / "disclosure" / "switch_regressions.csv")
    return_body = one(disclosure_tests, sample="10-Q", model="filing_return",
                      measure="Negative_prop_body")
    return_whole = one(disclosure_tests, sample="10-Q", model="filing_return",
                       measure="Negative_prop_total")
    switch_return = one(disclosure_tests, sample="10-Q", model="filing_return",
                        measure="to_reference")
    negative_10q_body_c = one(trends, sample="10-Q", category="Negative",
                              scope="excluding Item 1A")
    negative_10q_whole_c = one(trends, sample="10-Q", category="Negative",
                               scope="whole filing")
    report.p(
        "Reliance is stated per test, with the evidence behind it.")
    verdicts = pd.DataFrame([
        {"Test": "10-K tone trend, within company",
         "Result": f"Negative {100 * within_10k_negative.coef:+.3f} pp/yr, "
                   f"{p_text(within_10k_negative.p)}; uncertainty "
                   f"{100 * within_10k_uncertainty.coef:+.3f} pp/yr, "
                   f"{p_text(within_10k_uncertainty.p)}",
         "Verdict": "Relied on",
         "Basis": "Holds within company, on both scoring methods for negative language, "
                  "and survives removing Item 1A"},
        {"Test": "10-Q tone trend, within company",
         "Result": f"Whole filing {100 * negative_10q_whole_c.coef:+.3f} pp/yr, "
                   f"{p_text(negative_10q_whole_c.p)}; excluding Item 1A "
                   f"{100 * negative_10q_body_c.coef:+.3f} pp/yr, "
                   f"{p_text(negative_10q_body_c.p)}",
         "Verdict": "Whole-filing null not relied on",
         "Basis": "The risk section is shrinking as a share of the 10-Q; the null measures "
                  "that, not the prose"},
        {"Test": "Uncertainty on post-filing volatility",
         "Result": f"{100 * volatility_before.effect_1sd:+.2f} pp/SD without control, "
                   f"{p_text(volatility_before.p)}; "
                   f"{100 * volatility_after.effect_1sd:+.2f} pp/SD with control, "
                   f"{p_text(volatility_after.p)}",
         "Verdict": "No effect",
         "Basis": "Insignificant before and after the control; the gap that would be the "
                  "result is small because nothing was there to begin with"},
        {"Test": "Negative tone on filing-window return",
         "Result": f"Whole filing {abs(100 * return_whole.effect_1sd):.2f} pp/SD, "
                   f"{p_text(return_whole.p)}; excluding Item 1A "
                   f"{abs(100 * return_body.effect_1sd):.2f} pp/SD, "
                   f"{p_text(return_body.p)}",
         "Verdict": "Significant, not relied on as sentiment",
         "Basis": "Vanishes on the same filings once Item 1A is removed; what is priced is "
                  "the disclosure choice"},
    ])
    report.table(verdicts, widths=[104, 130, 88, 193])

    # ------------------------------------------------------------------ Table 1
    report.section("Table 1. Sample construction")
    report.p(
        "Company and security exclusions precede filing-level filters. A holding "
        "identifier is not a company: share classes of one issuer share a CIK, and funds, "
        "cash and non-US local listings are not issuers. Absence of 10-K or 10-Q filings "
        "is recorded from observed EDGAR behaviour, never inferred.")
    panel = company_panel.rename(columns={"filter": "Filter", "removed": "Removed",
                                          "remaining": "Remaining", "unit": "Unit"})
    panel["Filter"] = panel.Filter.map(FILTER_LABEL).fillna(panel.Filter)
    report.table(show(panel, **{"Removed": "int", "Remaining": "int"}))
    report.p(
        "Text, volatility and return samples are filtered separately, since a filing can "
        "be scored before its outcome window has elapsed. Both volatility specifications "
        "use one shared complete-case sample, so adding the control cannot change the "
        "sample as well as the model.")
    for name in ["Text", "Volatility", "Return"]:
        part = waterfall[waterfall["sample"].eq(name)]
        if part.empty:
            continue
        report.sub(f"{name} sample")
        view = part.rename(columns={"filter": "Filter", "removed": "Removed",
                                    "remaining": "Remaining", "companies": "Companies"})
        report.table(show(view[["Filter", "Removed", "Remaining", "Companies"]],
                          **{"Removed": "int", "Remaining": "int", "Companies": "int"}))
    report.p(
        f"{audit['amendments']} amendments were recorded and never scored, and "
        f"{audit['parse_failures']} filings failed to parse.")

    # ------------------------------------------------------------------ Table 2
    report.page_break()
    report.section("Table 2. Summary statistics by report type")
    report.p(
        "Annual and quarterly reports are kept apart throughout. A 10-K is longer and "
        "carries more risk language than a 10-Q, so any pooled statistic measures the mix "
        "as much as the language.")
    view = table2.rename(columns={"form": "Report", "measure": "Measure", "n": "Filings",
                                  "mean": "Mean", "sd": "SD", "p25": "P25",
                                  "median": "Median", "p75": "P75"})
    report.table(show(view[["Report", "Measure", "Filings", "Mean", "SD", "P25",
                            "Median", "P75"]],
                      **{"Filings": "int", "Mean": "{:.3f}", "SD": "{:.3f}",
                         "P25": "{:.3f}", "Median": "{:.3f}", "P75": "{:.3f}"}))
    correlations = audit.get("correlations", [])
    if correlations:
        pooled = next(c for c in correlations if c["form"] == "All")
        report.p(
            f"The two measures correlate at {pooled['prop']:.3f} on word shares and "
            f"{pooled['tfidf']:.3f} on weighted scores. They are related measures, not "
            f"independent evidence, which matters where one is significant and the other "
            f"is not.")

    # ------------------------------------------------------------------ Table 3
    report.section("Table 3. Most frequent words on each list")
    report.p(
        "Each share divides a word's occurrences by all occurrences in its own category, "
        "not by all words in the filings. The top 30 do not sum to 100%.")
    negative = table3[table3.category.eq("Negative")].head(30).reset_index(drop=True)
    uncertainty = table3[table3.category.eq("Uncertainty")].head(30).reset_index(drop=True)
    combined = pd.DataFrame({
        "Rank": negative["rank"], "Negative word": negative.word,
        "Share of negative words (%)": negative.share_pct,
        "Uncertainty word": uncertainty.word,
        "Share of uncertainty words (%)": uncertainty.share_pct})
    report.table(show(combined, **{"Rank": "int",
                                   "Share of negative words (%)": "{:.3f}",
                                   "Share of uncertainty words (%)": "{:.3f}"}),
                 keep_together=False)
    document_share = audit.get("uncertainty_word_document_pct", {})
    if document_share:
        report.p(
            f"MAY appears in {document_share.get('MAY', float('nan')):.1f}% of filings, "
            f"APPROXIMATELY in {document_share.get('APPROXIMATELY', float('nan')):.1f}%. A "
            f"word present in every document carries an inverse document frequency of zero: "
            f"it contributes nothing to the weighted score while still counting in the word "
            f"share. This is why weighting matters more for uncertainty than for negative "
            f"language. The uncertainty list is dominated by ubiquitous words.")

    # ---------------------------------------------------------- Figure 1, Table 4
    report.page_break()
    report.section("Figure 1. Both measures by quarter, with the VIX")
    report.figure(RUN / "figure1.png", "Quarterly tone and the VIX")
    report.note(
        "Company-centred quarterly means, plotted separately by report type, mean VIX on "
        "the right axis. Centring removes fixed differences in baseline tone between "
        "companies but not the effect of companies entering and leaving the sample. Annual "
        "reports cluster in the first quarter, so a pooled quarterly average would carry "
        "an annual sawtooth that is pure calendar artefact. Left and right axes are on "
        "different scales.")

    report.section("Table 4. Trend tests")
    report.p(
        "Two models. The aggregate model regresses the quarterly mean on elapsed years "
        "with seasonal indicators, reported with ordinary and Newey-West standard errors "
        "at four lags. The within-company model uses filing-level observations with "
        "company effects, seasonal indicators and two-way clustering by company and "
        "calendar quarter. Twenty quarterly observations of a persistent series return a "
        "large t statistic whether or not anything is happening, so the within-company "
        "estimate leads.")
    aggregate = table4[table4.model.eq("aggregate_trend") & table4.inference.eq("HAC4")]
    within = table4[table4.model.eq("within_firm_trend")
                    & table4.inference.eq("firm_quarter_cluster")]
    merged = aggregate.merge(within, on=["sample", "measure"], suffixes=("_agg", "_within"))
    merged["Measure"] = merged.measure.map(MEASURE_LABEL)
    merged["agg_slope"] = np.where(merged.measure.str.endswith("prop"),
                                   100 * merged.coef_agg, merged.coef_agg)
    merged["within_slope"] = np.where(merged.measure.str.endswith("prop"),
                                      100 * merged.coef_within, merged.coef_within)
    view = merged[["sample", "Measure", "agg_slope", "t_agg", "within_slope",
                   "t_within", "p_within", "n_within"]]
    view.columns = ["Report", "Measure", "Aggregate slope per year",
                    "Newey-West t", "Within-company slope per year", "t", "p", "Filings"]
    report.table(show(view, **{"Aggregate slope per year": "{:+.3f}",
                               "Newey-West t": "{:.2f}",
                               "Within-company slope per year": "{:+.3f}",
                               "t": "{:.2f}", "p": "p", "Filings": "int"}),
                 keep_together=False)

    report.sub("Trend, excluding Item 1A")
    report.p(
        "A word share is a property of the words a filing prints. If the risk-factor "
        "section grows or shrinks as a share of the document, the share moves with no "
        "change in how the company writes. Each filing is split into Item 1A and the "
        "balance, and the same within-company trend estimated on both. The two columns use "
        "identical filings.")
    trend_view = trends[trends["sample"].isin(["10-K", "10-Q"])].copy()
    trend_view["slope"] = 100 * trend_view.coef
    trend_view = trend_view[["sample", "category", "scope", "n", "slope", "p"]]
    trend_view.columns = ["Report", "Measure", "Scope", "Filings", "Slope per year (pp)", "p"]
    report.table(show(trend_view, **{"Filings": "int", "Slope per year (pp)": "{:+.3f}",
                                     "p": "p"}), keep_together=False)
    section_10q = one(trends, sample="10-Q", category="Section length",
                      scope="Item 1A share of words")
    negative_10q_whole = one(trends, sample="10-Q", category="Negative",
                             scope="whole filing")
    negative_10q_body = one(trends, sample="10-Q", category="Negative",
                            scope="excluding Item 1A")
    quarterly = sections[sections.form.eq("10-Q") & sections.risk_found]
    referring = quarterly.risk_mode.isin(["reference_only", "omitted"]).mean()
    report.p(
        f"The effect is largest in quarterly reports. {100 * referring:.0f}% of the 10-Qs "
        f"here satisfy Item 1A by stating that nothing material has changed, printing about "
        f"60 words where a restatement runs to tens of thousands. Over this window the "
        f"section shrinks {100 * section_10q.coef:+.3f} pp of the document a year "
        f"({p_text(section_10q.p)}). The whole-filing negative trend is "
        f"{100 * negative_10q_whole.coef:+.3f} pp a year "
        f"({p_text(negative_10q_whole.p)}); excluding Item 1A it is "
        f"{100 * negative_10q_body.coef:+.3f} pp ({p_text(negative_10q_body.p)}). "
        f"Quarterly prose is becoming more negative and the shrinking risk section masks "
        f"it.")
    report.p(
        f"In annual reports the correction runs the other way and is smaller. The trend "
        f"falls from {100 * within_10k_negative.coef:+.3f} to "
        f"{100 * body_10k_negative.coef:+.3f} pp a year and stays significant at 0.1%. "
        f"Roughly a third of the measured rise is the section growing; the balance is a "
        f"real change in the writing.")

    # ------------------------------------------------------------------ Table 5
    report.page_break()
    report.section("Table 5. Uncertainty and post-filing volatility")
    report.p(
        "Annualised volatility over trading days +4 to +63 after the filing event day, on "
        "the uncertainty measure with company and calendar-quarter effects, log size, log "
        "dollar volume and prior excess return. Run twice, without and with prior "
        "volatility, on one shared complete-case sample. Without the control the "
        "coefficient records that volatile companies write hedged filings. With it, whether "
        "the language says anything about a change in volatility.")
    view = table5[table5.inference.eq("firm_quarter_cluster")].copy()
    view["Prior volatility"] = np.where(view.model.eq("volatility_with_prevol"), "Yes", "No")
    view["Measure"] = view.measure.map(MEASURE_LABEL)
    view["effect"] = 100 * view.effect_1sd
    view = view[["sample", "Measure", "Prior volatility", "n", "effect", "p", "status"]]
    view.columns = ["Report", "Measure", "Prior volatility", "Filings",
                    "Effect of 1 SD (pp)", "p", "Status"]
    report.table(show(view, **{"Filings": "int", "Effect of 1 SD (pp)": "{:+.3f}",
                               "p": "p"}), keep_together=False)
    report.p(
        f"The expected pattern is a large significant coefficient before the control and a "
        f"smaller one after. Here the uncontrolled coefficient is already insignificant "
        f"({p_text(volatility_before.p)}), so the gap is small. That is a property of this "
        f"sample. Forcing the expected pattern by changing the sample or selecting a "
        f"specification would be worse than reporting it.")

    # ------------------------------------------------------------------ Table 6
    report.section("Table 6. Negative language and the filing-period return")
    report.p(
        "Buy-and-hold return over the filing event day and the three sessions following, "
        "less the benchmark over the same sessions, on the negative measure with company "
        "and calendar-quarter effects, prior volatility and the same controls. The "
        "detectable effect is the size this design would find with 80% power at the 5% "
        "level. An estimate below it is not evidence of absence, but it is a reason to "
        "discount an estimate that clears significance.")
    view = table6[table6.inference.eq("firm_quarter_cluster")].copy()
    view["Measure"] = view.measure.map(MEASURE_LABEL)
    view["effect"] = 100 * view.effect_1sd
    view["mde"] = 100 * view.mde80_1sd
    view = view[["sample", "Measure", "n", "effect", "mde", "p"]]
    view.columns = ["Report", "Measure", "Filings", "Effect of 1 SD (pp)",
                    "Detectable effect (pp)", "p"]
    report.table(show(view, **{"Filings": "int", "Effect of 1 SD (pp)": "{:+.3f}",
                               "Detectable effect (pp)": "{:.3f}", "p": "p"}))
    report.p(
        f"Two of six cells clear 5%, both in quarterly reports. In both the estimate "
        f"({abs(100 * return_10q.effect_1sd):.2f} pp per SD on the word share) sits just "
        f"below the detectable effect ({100 * return_10q.mde80_1sd:.2f} pp). On this table "
        f"alone the reading is that the test is underpowered. The split below gives a "
        f"better one.")
    report.sub("Attribution")
    report.p(
        f"Both columns below describe one sample: the {int(return_whole.n):,} quarterly "
        f"reports whose Item 1A could be located. The effect falls from "
        f"{abs(100 * return_whole.effect_1sd):.2f} pp per SD ({p_text(return_whole.p)}) to "
        f"{abs(100 * return_body.effect_1sd):.2f} pp ({p_text(return_body.p)}), against "
        f"{100 * return_whole.mde80_1sd:.2f} pp detectable. Read "
        f"through the disclosure choice instead of the word count it produces: a company "
        f"that stops restating its risk factors earns {100 * switch_return.coef:+.1f} pp "
        f"over the four sessions ({p_text(switch_return.p)}, "
        f"{int(switch_return.n_treated)} such quarters).")
    report.p(
        "A company that prints its risk factors prints thousands of negative words and "
        "scores badly; a company that points at its annual report does not. Whether the "
        "market responds to the disclosure choice, or both respond to something else about "
        "the quarter, cannot be settled here. Switches are not randomly assigned, earnings "
        "releases can fall in the same four sessions, and no correction is made for the "
        "number of related specifications. What holds is that the measured relation does "
        "not survive removing the section that drives the measure.")

    # ------------------------------------------------------------------- method
    report.page_break()
    report.section("Method")
    report.p(
        "Word lists are from the Loughran-McDonald Master Dictionary, using only entries "
        f"active in the current release: {audit['lexicon_counts']['Negative']:,} negative "
        f"and {audit['lexicon_counts']['Uncertainty']} uncertainty words, with "
        f"{audit['lexicon_overlap']} words on both lists. The two are scored separately "
        "throughout and never combined.")
    report.p("The proportional score divides category occurrences by all retained words:")
    report.equation(r"P_{cj}=\frac{\sum_{i \in c} tf_{ij}}{W_j}")
    report.p("Equation (1) of the paper weights each occurrence by log term frequency, "
             "normalised by the filing's average term frequency, times log inverse "
             "document frequency:")
    report.equation(r"T_{cj}=\sum_{i \in c,\, tf_{ij}>0}"
                    r"\frac{1+\ln(tf_{ij})}{1+\ln(a_j)}\,\ln\!\left(\frac{N}{df_i}\right)")
    report.p(
        "W is the filing's word count, a its words divided by its distinct words, N the "
        "documents in the estimation corpus, df the document frequency of the word. "
        "Document frequencies are refitted per sample, so a weighted score is comparable "
        "across filings within a table, not across tables.")
    report.p(
        "Filing text is the primary document, hidden inline-XBRL content removed, tables "
        "dropped where more than 15% of non-space characters are digits. Tokens are "
        "alphabetic, minimum two characters, uppercased to match the dictionary. Day 0 is "
        "the first NYSE session on or after the later of the filing date and the Eastern "
        "acceptance time, so a filing accepted after the close is attributed to the next "
        "session. Company size uses the share count on the cover page of the filing being "
        "scored, not a later one.")
    report.p(
        f"Item 1A is located by an explicit heading, taking the occurrence that opens a "
        f"section rather than one of the many that cite it, and ending at the next item "
        f"heading. Coverage is {100 * sections.risk_found.mean():.1f}% of filings. Filers "
        f"labelling the section differently are recorded as not located and dropped from "
        f"the split, never inferred; their whole-filing scores are unaffected.")

    report.section("Sources")
    report.link("Loughran and McDonald (2011), When Is a Liability Not a Liability? "
                "Textual Analysis, Dictionaries, and 10-Ks, Journal of Finance 66(1), 35-65",
                "https://doi.org/10.1111/j.1540-6261.2010.01625.x")
    report.link("Loughran-McDonald Master Dictionary, 1993-2025 release",
                "https://sraf.nd.edu/loughranmcdonald-master-dictionary/")
    report.link("SEC EDGAR filings and company facts", "https://www.sec.gov/edgar")
    report.link("Code and executed notebook",
                "https://github.com/robynge/FRE-GY-7871A-Assignment1")

    pdf = RUN / "Assignment1_Uncertainty_and_Sentiment.pdf"
    report.save(pdf, OUTPUT_DIR / "COURSE_REPORT.md")
    print(f"Wrote {pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
