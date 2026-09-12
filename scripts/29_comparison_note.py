"""A short companion note on one question: ARK holdings against QQQ holdings.

Same data and specifications as the report; every number is read from the
CSV that produced it. Run after 21_group_comparison.py and 27_report_figures.py.

    python scripts/29_comparison_note.py
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

ARKD, QQQD, COMP, FIG = OUTPUT_DIR / "ark", OUTPUT_DIR / "ndx", OUTPUT_DIR / "comparison", OUTPUT_DIR / "report_figures"


def p_text(v):
    if not np.isfinite(v):
        return "not estimable"
    return "p < 0.001" if v < .001 else f"p = {v:.3f}"


def p_short(v):
    if v is None or not np.isfinite(v):
        return "n.e."
    return "< 0.001" if v < .001 else f"{v:.3f}"


def one(frame, **conditions):
    mask = pd.Series(True, index=frame.index)
    for column, value in conditions.items():
        mask &= frame[column].eq(value)
    hit = frame.loc[mask]
    if len(hit) != 1:
        raise ValueError(f"expected one row for {conditions}, found {len(hit)}")
    return hit.iloc[0]


def diff(frame, **conditions):
    two = one(frame[frame.inference.eq("firm_quarter_cluster")], **conditions)
    if two.status == "ok":
        return two, False
    return one(frame[frame.inference.eq("firm_cluster")], **conditions), True


def cell(value, p, fallback=False, digits=3):
    return f"{value:+.{digits}f} ({p_short(p)}{'*' if fallback else ''})"


def main() -> int:
    audit = {run: json.loads((folder / "audit.json").read_text()) for run, folder in [("ark", ARKD), ("ndx", QQQD)]}
    text = {run: pd.read_csv(folder / "text_sample.csv", dtype={"cik": str}) for run, folder in [("ark", ARKD), ("ndx", QQQD)]}
    t4 = {run: pd.read_csv(folder / "table4.csv") for run, folder in [("ark", ARKD), ("ndx", QQQD)]}
    sw = {run: pd.read_csv(folder / "disclosure" / "switch_regressions.csv") for run, folder in [("ark", ARKD), ("ndx", QQQD)]}
    tr = pd.read_csv(COMP / "corrected_trends.csv")
    dx = pd.read_csv(COMP / "differences_excluding_item_1a.csv")
    od = pd.read_csv(COMP / "outcome_differences.csv")
    universe = pd.read_csv(UNIVERSE_DIR / "universe.csv", dtype={"cik": str})
    universe["cik"] = universe.cik.str.zfill(10)
    universe["group"] = universe.funds.map(holdings_group)
    label = dict(zip(universe.cik, universe.group))
    filers = universe[universe.status.eq("domestic_filer")]
    n_both = int(filers.group.eq("BOTH").sum())
    n_ark_only, n_qqq_only = int(filers.group.eq("ARK").sum()), int(filers.group.eq("NDX").sum())
    all_text = pd.read_csv(OUTPUT_DIR / "all" / "text_sample.csv")
    sec = pd.read_csv(INTERIM_DIR / "risk_sections.csv", dtype={"cik": str})
    sec = sec[sec.accession.isin(all_text.accession)].copy()
    sec["group"] = sec.cik.str.zfill(10).map(label)
    groups = {"ark": ["ARK", "BOTH"], "ndx": ["NDX", "BOTH"]}
    name = {"ark": "ARK holdings", "ndx": "QQQ holdings"}

    # ---- levels
    k_mean = {run: (100 * text[run][text[run].form.eq("10-K")].Negative_prop.mean(),
                    100 * text[run][text[run].form.eq("10-K")].Uncertainty_prop.mean()) for run in text}
    risk_share = {run: 100 * sec[sec.form.eq("10-K") & sec.risk_found & sec.group.isin(groups[run])].risk_share.mean() for run in text}
    DX = lambda model, cat, scope: diff(dx, model=model, sample="10-K", category=cat, scope=scope)
    lv = {(cat, scope): DX("level_difference", cat, scope) for cat in ["Negative", "Uncertainty"] for scope in ["whole filing", "excluding Item 1A"]}
    lv_share = DX("level_difference", "Section length", "Item 1A share of words")
    td = {(cat, scope): DX("trend_difference", cat, scope) for cat in ["Negative", "Uncertainty"] for scope in ["whole filing", "excluding Item 1A"]}
    n_k = int(lv[("Negative", "whole filing")][0].n)

    # ---- trends, each portfolio on its own located annual reports
    T = lambda run, cat, scope: one(tr, run=run, sample="10-K", category=cat, scope=scope)
    W = lambda run, m: one(t4[run][t4[run].model.eq("within_firm_trend") & t4[run].inference.eq("firm_quarter_cluster")], sample="10-K", measure=m)

    # ---- market outcomes, each portfolio on its own located filings
    S = lambda run, form, m, spec: one(sw[run], sample=form, measure=m, model=spec)
    OD = lambda outcome, form, m, spec: diff(od, outcome=outcome, sample=form, measure_name=m, model=spec)
    outcomes = [
        ("Quarterly reports: four-session return on negative words", "10-Q", "Negative_prop", "filing_return", "return"),
        ("Quarterly reports: next-quarter volatility on uncertainty, prior volatility controlled", "10-Q", "Uncertainty_prop", "volatility_with_prevol", "volatility"),
        ("Annual reports: next-quarter volatility on uncertainty, prior volatility controlled", "10-K", "Uncertainty_prop", "volatility_with_prevol", "volatility"),
    ]

    # ---- disclosure practice
    q = {run: sec[sec.form.eq("10-Q") & sec.risk_found & sec.group.isin(groups[run])] for run in text}
    practice = {}
    for run, part in q.items():
        years = part.quarter.str[:4]
        first, last = years.min(), years.max()
        practice[run] = dict(
            restate=100 * part.risk_mode.eq("full").mean(), refer=100 * part.risk_mode.eq("reference_only").mean(),
            words_full=part[part.risk_mode.eq("full")].risk_words.median(),
            words_ref=part[part.risk_mode.eq("reference_only")].risk_words.median(),
            restate_first=100 * part[years.eq(first)].risk_mode.eq("full").mean(),
            restate_last=100 * part[years.eq(last)].risk_mode.eq("full").mean(), first=first, last=last, n=len(part))

    note = Report(
        "ARK Holdings against QQQ Holdings: What the Filing-Language Comparison Shows",
        "Companion note to the report on uncertainty and sentiment in the filings of ARK ETF holdings. Same "
        "data, measures and specifications; 10-K and 10-Q filings of January 2021 to September 2026.",
        running_head="ARK holdings against QQQ holdings")

    note.section("The question and the design")
    note.p(
        f"Do the companies ARK holds write their filings differently from the companies in QQQ, the Invesco "
        f"Nasdaq-100 ETF, and does any difference carry information? The same pipeline scores every original "
        f"10-K and 10-Q of the {audit['ark']['final_companies']} ARK holdings ({audit['ark']['expected_original_filings']:,} "
        f"filings) and the {audit['ndx']['final_companies']} QQQ holdings ({audit['ndx']['expected_original_filings']:,} "
        f"filings) that file with the SEC; {n_both} companies are in both portfolios. Each portfolio's own "
        f"results include those {n_both}. Each difference between the portfolios is one regression on the "
        f"{n_ark_only} companies held only by ARK and the {n_qqq_only} held only by QQQ, so that no filing sits "
        f"on both sides, with the coefficient on a QQQ indicator (levels), on its interaction with time "
        f"(trends) or with the tone measure (market outcomes). A significant result in one portfolio next to "
        f"an insignificant one in the other is never read as a difference. Every difference is estimated "
        f"twice on identical filings: on the whole filing, and on the filing excluding Item 1A, the "
        f"risk-factor section, because a word-share measure moves when a company prints more or fewer risk "
        f"factors even if it writes the same way.")

    note.section("Levels: ARK reads more negative and more uncertain, and the gap is disclosure length")
    note.p(
        f"On the whole filing, QQQ annual reports carry {abs(100 * lv[('Negative', 'whole filing')][0].coef):.2f} pp "
        f"fewer negative words and {abs(100 * lv[('Uncertainty', 'whole filing')][0].coef):.2f} pp fewer uncertainty "
        f"words than ARK annual reports, both well inside 5%. Item 1A takes {risk_share['ndx']:.0f}% of a QQQ "
        f"annual report's words against {risk_share['ark']:.0f}% of an ARK one. Remove that section from the "
        f"same filings and the gaps are {abs(100 * lv[('Negative', 'excluding Item 1A')][0].coef):.3f} pp "
        f"({p_text(lv[('Negative', 'excluding Item 1A')][0].p)}) and "
        f"{abs(100 * lv[('Uncertainty', 'excluding Item 1A')][0].coef):.3f} pp "
        f"({p_text(lv[('Uncertainty', 'excluding Item 1A')][0].p)}). Figure 1 shows the company-level "
        f"distributions: the boxes separate on the whole filing and sit on top of each other without Item 1A. "
        f"The difference between the two portfolios is how much risk disclosure their companies print, not how "
        f"they write the rest of the document.")
    rows = [
        {"Measure, annual reports": "Negative words (% of words)", "ARK holdings": f"{k_mean['ark'][0]:.2f}", "QQQ holdings": f"{k_mean['ndx'][0]:.2f}",
         "QQQ less ARK, whole filing (pp)": cell(100 * lv[('Negative', 'whole filing')][0].coef, lv[('Negative', 'whole filing')][0].p, lv[('Negative', 'whole filing')][1]),
         "QQQ less ARK, excluding Item 1A (pp)": cell(100 * lv[('Negative', 'excluding Item 1A')][0].coef, lv[('Negative', 'excluding Item 1A')][0].p, lv[('Negative', 'excluding Item 1A')][1])},
        {"Measure, annual reports": "Uncertainty words (% of words)", "ARK holdings": f"{k_mean['ark'][1]:.2f}", "QQQ holdings": f"{k_mean['ndx'][1]:.2f}",
         "QQQ less ARK, whole filing (pp)": cell(100 * lv[('Uncertainty', 'whole filing')][0].coef, lv[('Uncertainty', 'whole filing')][0].p, lv[('Uncertainty', 'whole filing')][1]),
         "QQQ less ARK, excluding Item 1A (pp)": cell(100 * lv[('Uncertainty', 'excluding Item 1A')][0].coef, lv[('Uncertainty', 'excluding Item 1A')][0].p, lv[('Uncertainty', 'excluding Item 1A')][1])},
        {"Measure, annual reports": "Item 1A share of the filing's words (%)", "ARK holdings": f"{risk_share['ark']:.1f}", "QQQ holdings": f"{risk_share['ndx']:.1f}",
         "QQQ less ARK, whole filing (pp)": cell(100 * lv_share[0].coef, lv_share[0].p, lv_share[1], 1), "QQQ less ARK, excluding Item 1A (pp)": ""},
    ]
    note.sub("Table 1. Levels in annual reports")
    note.note(f"ARK and QQQ columns: means over each portfolio's annual reports in the text sample. Difference "
              f"columns: one regression per cell on the {n_k} annual reports with a located Item 1A of the "
              f"companies held by only one portfolio, calendar-quarter and seasonal effects, two-way clustered "
              f"inference; p-values in brackets.")
    note.table(pd.DataFrame(rows))
    note.figure(FIG / "figB7_distributions.png", "Figure 1")
    note.note("Figure 1. Company-mean word shares in annual reports with a located Item 1A, companies held only "
              "by ARK against companies held only by QQQ, whole filing and excluding Item 1A. Boxes span the "
              "interquartile range, whiskers the 5th to 95th percentile, dots are companies.")

    note.section("Trends: both rise; one difference survives the correction")
    note.p(
        f"Negative and uncertainty language rises within company in both portfolios, on the whole filing and "
        f"outside Item 1A, all at {p_text(T('ark', 'Negative', 'whole filing').p)}. ARK's slopes are steeper. On "
        f"the whole filing the uncertainty difference is significant ({abs(100 * td[('Uncertainty', 'whole filing')][0].coef):.3f} pp "
        f"a year, {p_text(td[('Uncertainty', 'whole filing')][0].p)}) and the negative one is not "
        f"({p_text(td[('Negative', 'whole filing')][0].p)}); outside Item 1A it is the other way round: ARK's "
        f"negative tone rises {abs(100 * td[('Negative', 'excluding Item 1A')][0].coef):.3f} pp a year faster "
        f"({p_text(td[('Negative', 'excluding Item 1A')][0].p)}) and the uncertainty difference is "
        f"{abs(100 * td[('Uncertainty', 'excluding Item 1A')][0].coef):.3f} pp ({p_text(td[('Uncertainty', 'excluding Item 1A')][0].p)}). "
        f"That faster rise in negative words outside the risk section is the one difference between the "
        f"portfolios that does not go away when Item 1A is removed. Figure 2 shows the series.")
    rows = []
    for cat in ["Negative", "Uncertainty"]:
        rows.append({"Measure, annual reports": f"{cat} words, pp a year",
                     "ARK, whole filing": f"{100 * T('ark', cat, 'whole filing').coef:+.3f} ({p_short(T('ark', cat, 'whole filing').p)})",
                     "QQQ, whole filing": f"{100 * T('ndx', cat, 'whole filing').coef:+.3f} ({p_short(T('ndx', cat, 'whole filing').p)})",
                     "QQQ less ARK, whole filing": cell(100 * td[(cat, 'whole filing')][0].coef, td[(cat, 'whole filing')][0].p, td[(cat, 'whole filing')][1]),
                     "ARK, excl. Item 1A": f"{100 * T('ark', cat, 'excluding Item 1A').coef:+.3f} ({p_short(T('ark', cat, 'excluding Item 1A').p)})",
                     "QQQ, excl. Item 1A": f"{100 * T('ndx', cat, 'excluding Item 1A').coef:+.3f} ({p_short(T('ndx', cat, 'excluding Item 1A').p)})",
                     "QQQ less ARK, excl. Item 1A": cell(100 * td[(cat, 'excluding Item 1A')][0].coef, td[(cat, 'excluding Item 1A')][0].p, td[(cat, 'excluding Item 1A')][1])})
    fallback = any(v[1] for v in td.values())
    note.sub("Table 2. Within-company trends in annual reports, 2021 to 2026")
    note.note("Portfolio columns: within-company slopes with company and seasonal effects on each portfolio's "
              "annual reports with a located Item 1A. Difference columns: interaction of a QQQ indicator with "
              "elapsed years, one regression on the disjoint sample."
              + (" * Company-clustered inference where the two-way clustered covariance was not positive definite." if fallback else ""))
    note.table(pd.DataFrame(rows), keep_together=True)
    note.figure(FIG / "figB6_groups_series.png", "Figure 2")
    note.note("Figure 2. Both measures by quarter, ARK holdings and QQQ holdings (each including the shared "
              "companies), company-centred means with 95% bands; annual reports by filing year.")

    note.section("Market outcomes: the return association belongs to ARK, and to its risk section")
    ret_a, ret_q = S("ark", "10-Q", "Negative_prop_total", "filing_return"), S("ndx", "10-Q", "Negative_prop_total", "filing_return")
    ret_ab, ret_d, ret_db = S("ark", "10-Q", "Negative_prop_body", "filing_return"), OD("return", "10-Q", "Negative_prop_total", "filing_return"), OD("return", "10-Q", "Negative_prop_body", "filing_return")
    vq, vqb = OD("volatility", "10-Q", "Uncertainty_prop_total", "volatility_with_prevol"), OD("volatility", "10-Q", "Uncertainty_prop_body", "volatility_with_prevol")
    vk, vkb = OD("volatility", "10-K", "Uncertainty_prop_total", "volatility_with_prevol"), OD("volatility", "10-K", "Uncertainty_prop_body", "volatility_with_prevol")
    note.p(
        f"In ARK quarterly reports a higher negative word share goes with a lower four-session excess return "
        f"({100 * ret_a.effect_1sd:+.2f} pp per standard deviation, {p_text(ret_a.p)}); in QQQ quarterly reports it "
        f"does not ({100 * ret_q.effect_1sd:+.2f} pp, {p_text(ret_q.p)}), and the difference is significant "
        f"({100 * ret_d[0].effect_1sd:+.1f} pp, {p_text(ret_d[0].p)}). Excluding Item 1A the ARK association is "
        f"{100 * ret_ab.effect_1sd:+.2f} pp ({p_text(ret_ab.p)}) and the difference {100 * ret_db[0].effect_1sd:+.1f} pp "
        f"({p_text(ret_db[0].p)}). What the whole-filing measure picks up in ARK is which companies printed "
        f"their risk factors that quarter: a restated section adds thousands of negative words, and those "
        f"quarters carry lower returns than quarters in which the company refers to the annual report. That is "
        f"a disclosure effect, not a tone effect, and the design cannot separate it from whatever else marks "
        f"those quarters. Uncertainty and next-quarter volatility, with prior volatility controlled, do not "
        f"differ between the portfolios in quarterly reports ({p_text(vq[0].p)}, {p_text(vqb[0].p)}); in annual "
        f"reports the coefficients differ on the whole filing ({100 * vk[0].effect_1sd:+.1f} pp, {p_text(vk[0].p)}) "
        f"and not excluding Item 1A ({p_text(vkb[0].p)}), the same pattern.")
    rows = []
    for label_, form, measure, spec, outcome in outcomes:
        cells = {"Test": label_}
        for scope, suffix in [("whole filing", "total"), ("excluding Item 1A", "body")]:
            a, b_ = S("ark", form, f"{measure}_{suffix}", spec), S("ndx", form, f"{measure}_{suffix}", spec)
            d_, fb = OD(outcome, form, f"{measure}_{suffix}", spec)
            cells[f"ARK, {scope}"] = f"{100 * a.effect_1sd:+.2f} ({p_short(a.p)})"
            cells[f"QQQ, {scope}"] = f"{100 * b_.effect_1sd:+.2f} ({p_short(b_.p)})"
            cells[f"QQQ less ARK, {scope}"] = cell(100 * d_.effect_1sd, d_.p, fb, 2)
        rows.append(cells)
    note.sub("Table 3. Effect per standard deviation of the word share, percentage points")
    note.note("Portfolio columns: each portfolio's own regression on its filings with a located Item 1A and "
              "complete market data, company and calendar-quarter effects, size, dollar volume, prior excess "
              "return and prior volatility as controls. Difference columns: interaction of the measure with a "
              "QQQ indicator on the disjoint sample. Effects per standard deviation of the measure in the "
              "estimation sample, so the difference is not the arithmetic gap between the two portfolio columns.")
    note.table(pd.DataFrame(rows), keep_together=True)

    note.section("Disclosure practice: the two portfolios behave alike")
    rows = [
        {"Quarterly reports with a located Item 1A": "Reports", "ARK holdings": f"{practice['ark']['n']:,}", "QQQ holdings": f"{practice['ndx']['n']:,}"},
        {"Quarterly reports with a located Item 1A": "Restate the risk factors (%)", "ARK holdings": f"{practice['ark']['restate']:.0f}", "QQQ holdings": f"{practice['ndx']['restate']:.0f}"},
        {"Quarterly reports with a located Item 1A": "Refer the reader to the annual report (%)", "ARK holdings": f"{practice['ark']['refer']:.0f}", "QQQ holdings": f"{practice['ndx']['refer']:.0f}"},
        {"Quarterly reports with a located Item 1A": "Median Item 1A words when restated", "ARK holdings": f"{practice['ark']['words_full']:,.0f}", "QQQ holdings": f"{practice['ndx']['words_full']:,.0f}"},
        {"Quarterly reports with a located Item 1A": "Median Item 1A words when referred", "ARK holdings": f"{practice['ark']['words_ref']:.0f}", "QQQ holdings": f"{practice['ndx']['words_ref']:.0f}"},
        {"Quarterly reports with a located Item 1A": f"Restating share, {practice['ark']['first']} to {practice['ark']['last']} (%)",
         "ARK holdings": f"{practice['ark']['restate_first']:.0f} to {practice['ark']['restate_last']:.0f}", "QQQ holdings": f"{practice['ndx']['restate_first']:.0f} to {practice['ndx']['restate_last']:.0f}"},
    ]
    note.sub("Table 4. How quarterly reports handle Item 1A")
    note.table(pd.DataFrame(rows), widths=[260, 100, 100])
    note.p(
        f"About half of quarterly reports in either portfolio restate their risk factors and the rest mostly "
        f"refer the reader to the annual report; both shares drift towards referring over the period. ARK "
        f"companies write longer sections when they do restate ({practice['ark']['words_full']:,.0f} against "
        f"{practice['ndx']['words_full']:,.0f} median words), which is the same fact as the larger Item 1A share "
        f"of their annual reports.")

    note.section("What to take from it")
    note.bullets([
        "On the raw Loughran-McDonald word shares, ARK holdings look more negative and more uncertain than "
        "QQQ holdings. That gap is the size of their risk-factor sections and nothing else; outside Item 1A "
        "the two portfolios write alike.",
        "Both portfolios' annual reports are becoming more negative and more uncertain every year. The one "
        "difference that survives removing Item 1A is that ARK's negative language outside the risk section "
        "rises faster.",
        "The negative-tone return association exists in ARK and not in QQQ, and it is a disclosure event, "
        "which companies printed their risk factors that quarter, rather than a tone signal.",
        "For monitoring or comparing the two portfolios, use the measures excluding Item 1A. The whole-filing "
        "measures rank companies by how much risk disclosure they print.",
    ])
    note.link("Full results: Section 7 and Table 9 of the report; Appendix Tables C4 to C7 (QQQ's own exhibits), "
              "C12 and C13 (every difference test), Figures B6 and B7.",
              "https://github.com/robynge/FRE-GY-7871A-Assignment1")

    note.save(OUTPUT_DIR / "ARK_vs_QQQ_Note.pdf", OUTPUT_DIR / "ARK_vs_QQQ_NOTE.md")
    print("Wrote the comparison note")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
