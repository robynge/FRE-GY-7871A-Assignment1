"""Collect every computed result into one workbook.

One row per filing on the Filings sheet, one sheet per exhibit, and a Notes
sheet that states what each sample is and what the numbers are not. Nothing is
recomputed here: every figure is read from the CSV that the analysis wrote, so
the workbook and the report cannot disagree.

    python scripts/22_workbook.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import xlsxwriter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import INTERIM_DIR, OUTPUT_DIR, UNIVERSE_DIR, holdings_group

INK = "#0A0A23"
ACCENT = "#8264FF"
TINT = "#F0ECFF"
MUTED = "#676777"

RUNS = ["course_ark_2021_2025", "ark", "ndx", "ark_only", "ndx_only"]

MEASURE_NAMES = {
    "Negative_prop": "Negative word share",
    "Uncertainty_prop": "Uncertainty word share",
    "Negative_tfidf": "Negative weighted score",
    "Uncertainty_tfidf": "Uncertainty weighted score",
    "Negative_prop_total": "Negative share, whole filing",
    "Negative_prop_body": "Negative share, excluding Item 1A",
    "Uncertainty_prop_total": "Uncertainty share, whole filing",
    "Uncertainty_prop_body": "Uncertainty share, excluding Item 1A",
}

INFERENCE_NAMES = {
    "firm_quarter_cluster": "Company and calendar-quarter clusters",
    "firm_cluster": "Company clusters",
    "HAC4": "Newey-West, 4 lags",
    "OLS": "Ordinary least squares",
}

FILTER_NAMES = {
    "foreign_reporting_forms": "Files 20-F or 40-F, not 10-K or 10-Q",
    "no_report_evidence": "No 10-K, 10-Q, 20-F or 40-F on record",
    "first_10x_after_sample": "First 10-K or 10-Q filed after the sample window",
    "10x_outside_sample": "10-K or 10-Q filed only outside the sample window",
    "incomplete_cached_history": "Filing history incomplete; exclusion unresolved",
}

MODE_NAMES = {
    "full": "Risk factors restated",
    "partial_update": "No material change, stated updates",
    "reference_only": "No material change, reader sent to the annual report",
    "omitted": "Section present, nothing disclosed",
    "not_found": "No Item 1A heading located",
}


def read(path: Path, **kwargs) -> pd.DataFrame:
    return pd.read_csv(path, **kwargs) if path.exists() else pd.DataFrame()


class Book:
    def __init__(self, path: Path):
        self.wb = xlsxwriter.Workbook(str(path), {"nan_inf_to_errors": True})
        self.f = {
            "title": self.wb.add_format({"font_size": 15, "bold": True, "font_color": INK}),
            "sub": self.wb.add_format({"font_color": MUTED, "text_wrap": True, "valign": "top"}),
            "head": self.wb.add_format({"bold": True, "font_color": INK, "bg_color": TINT,
                                        "text_wrap": True, "valign": "bottom", "bottom": 1,
                                        "border_color": ACCENT}),
            "text": self.wb.add_format({"font_color": INK}),
            "num": self.wb.add_format({"num_format": "0.000", "font_color": INK}),
            "int": self.wb.add_format({"num_format": "#,##0", "font_color": INK}),
            "pct": self.wb.add_format({"num_format": "0.00%", "font_color": INK}),
            "date": self.wb.add_format({"num_format": "yyyy-mm-dd", "font_color": INK}),
            "p": self.wb.add_format({"num_format": "0.000", "font_color": INK}),
        }

    def sheet(self, name, title, subtitle):
        ws = self.wb.add_worksheet(name[:31])
        ws.hide_gridlines(2)
        ws.write(0, 0, title, self.f["title"])
        ws.write(1, 0, subtitle, self.f["sub"])
        ws.set_row(1, 30)
        return ws

    def table(self, ws, frame: pd.DataFrame, row=3, widths=None, formats=None):
        if frame.empty:
            ws.write(row, 0, "No observations for this sample.", self.f["text"])
            return row + 2
        formats = formats or {}
        for column, name in enumerate(frame.columns):
            ws.write(row, column, str(name), self.f["head"])
        for offset, record in enumerate(frame.itertuples(index=False, name=None), 1):
            for column, value in enumerate(record):
                name = frame.columns[column]
                style = self.f[formats.get(name, self._auto(frame[name]))]
                if pd.isna(value):
                    ws.write_blank(row + offset, column, None, style)
                elif isinstance(value, pd.Timestamp):
                    ws.write_datetime(row + offset, column, value.to_pydatetime(),
                                      self.f["date"])
                elif isinstance(value, (int, float)):
                    ws.write_number(row + offset, column, float(value), style)
                else:
                    ws.write_string(row + offset, column, str(value), style)
        ws.set_row(row, 42)
        ws.freeze_panes(row + 1, 1)
        ws.autofilter(row, 0, row + len(frame), len(frame.columns) - 1)
        for column, name in enumerate(frame.columns):
            width = (widths or {}).get(name)
            if width is None:
                width = min(42, max(11, int(frame[name].astype(str).str.len().max() or 11) + 2,
                                    len(str(name)) + 2))
            ws.set_column(column, column, width)
        return row + len(frame) + 3

    def close(self):
        self.wb.close()

    @staticmethod
    def _auto(series: pd.Series) -> str:
        if pd.api.types.is_integer_dtype(series):
            return "int"
        if pd.api.types.is_float_dtype(series):
            return "num"
        return "text"


def notes_rows(audits: dict) -> pd.DataFrame:
    rows = [
        ("Filings sheet", "One row per parsed original 10-K or 10-Q, 2021 onward. "
                          "Amendments are recorded in the manifest and never scored."),
        ("Groups", "ARK: held by one of the six ARK ETFs. NDX: held by Invesco QQQ, the "
                   "Nasdaq-100 constituents. BOTH: held by an ARK fund and by QQQ. The report "
                   "describes the ARK holdings; QQQ holdings appear only in the comparison. "
                   "Comparisons that must not share companies use the ARK-only and "
                   "NDX-only samples."),
        ("Word shares", "Category word occurrences divided by all retained words in the "
                        "filing. Repeated words count each time. A share is a property of "
                        "the writing, not a probability of loss."),
        ("Weighted scores", "Loughran-McDonald equation (1). Document frequencies are "
                            "fitted inside each run, so a weighted score is comparable "
                            "across filings within a run and not across runs."),
        ("Item 1A split", "Each filing is split into its risk-factor section and the rest. "
                          "Shares excluding Item 1A are the measure that a change of "
                          "disclosure practice does not move mechanically."),
        ("Disclosure modes", "; ".join(f"{k}: {v}" for k, v in MODE_NAMES.items())),
        ("Section coverage", "The section is located by an explicit Item 1A heading. "
                             "Filers who label the section differently are recorded as "
                             "not located and are excluded from the split, never guessed."),
        ("Regression results", "Estimated associations with company and calendar-quarter "
                               "effects and clustered standard errors. Not causal effects, "
                               "and not an implementable trading rule."),
        ("Switches", "A company choosing to stop or resume restating its risk factors is "
                     "not a random event. Outcomes around switches are conditional "
                     "associations."),
    ]
    for name, audit in audits.items():
        rows.append((f"Run: {name}",
                     f"{audit.get('sample_start')} to {audit.get('sample_end')}, "
                     f"{audit.get('final_filings')} filings, "
                     f"{audit.get('final_companies')} companies; market data through "
                     f"{audit.get('market_last_date')}."))
    return pd.DataFrame(rows, columns=["Item", "Definition"])


def filings_sheet(sections: pd.DataFrame) -> pd.DataFrame:
    scores = read(OUTPUT_DIR / "all" / "text_sample.csv", dtype={"cik": str})
    volatility = read(OUTPUT_DIR / "all" / "volatility_sample.csv", dtype={"cik": str})
    returns = read(OUTPUT_DIR / "all" / "return_sample.csv", dtype={"cik": str})
    market = volatility[["accession", "pre_vol", "post_vol"]].merge(
        returns[["accession", "event_excess"]], on="accession", how="outer")
    keep = ["accession", "ticker", "company", "cik", "form", "filing_date", "quarter",
            "n_words", "Negative_prop", "Uncertainty_prop", "Negative_tfidf",
            "Uncertainty_tfidf", "doc_url"]
    out = scores[[c for c in keep if c in scores.columns]].merge(
        sections[["accession", "group", "risk_found", "risk_mode", "risk_words",
                  "risk_share", "Negative_prop_body", "Uncertainty_prop_body"]],
        on="accession", how="left").merge(market, on="accession", how="left")
    out = out.rename(columns={
        "ticker": "Ticker", "company": "Company", "cik": "CIK", "form": "Form",
        "filing_date": "Filed", "quarter": "Filing quarter", "n_words": "Words",
        "group": "Group", "risk_found": "Item 1A located", "risk_mode": "Disclosure mode",
        "risk_words": "Item 1A words", "risk_share": "Item 1A share of words",
        "Negative_prop": "Negative share", "Uncertainty_prop": "Uncertainty share",
        "Negative_tfidf": "Negative weighted", "Uncertainty_tfidf": "Uncertainty weighted",
        "Negative_prop_body": "Negative share ex Item 1A",
        "Uncertainty_prop_body": "Uncertainty share ex Item 1A",
        "pre_vol": "Prior annualised volatility", "post_vol": "Following annualised volatility",
        "event_excess": "Four-session excess return", "doc_url": "SEC document",
        "accession": "Accession"})
    out["Disclosure mode"] = out["Disclosure mode"].map(MODE_NAMES).fillna(out["Disclosure mode"])
    out["Filed"] = pd.to_datetime(out["Filed"])
    return out.sort_values(["Ticker", "Filed"]).reset_index(drop=True)


def tidy_estimates(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    out = frame.copy()
    if "measure" in out:
        out["measure"] = out.measure.map(MEASURE_NAMES).fillna(out.measure)
    if "inference" in out:
        out["inference"] = out.inference.map(INFERENCE_NAMES).fillna(out.inference)
    columns = [c for c in ["run", "sample", "group", "scope", "category", "model",
                           "measure", "term", "inference", "n", "n_treated",
                           "firm_clusters", "quarter_clusters", "coef", "se", "t", "p",
                           "ci_low", "ci_high", "effect_1sd", "mde80_1sd", "r_squared",
                           "status"] if c in out.columns]
    return out[columns]


def main() -> int:
    audits = {}
    for name in RUNS:
        path = OUTPUT_DIR / name / "audit.json"
        if path.exists():
            audits[name] = json.loads(path.read_text())
    sections = read(INTERIM_DIR / "risk_sections.csv")
    text_sample = read(OUTPUT_DIR / "all" / "text_sample.csv")
    sections = sections[sections.accession.isin(text_sample.accession)].copy()  # same filings as Tables 2 to 4
    disclosure = OUTPUT_DIR / "all" / "disclosure"
    comparison = OUTPUT_DIR / "comparison"

    target = OUTPUT_DIR / "ARK_Filing_Language.xlsx"
    book = Book(target)

    ws = book.sheet("Notes", "Filing language in ARK holdings, with a comparison to QQQ holdings",
                    "What each sheet contains, how each measure is defined, and what it "
                    "does not establish. Read before quoting any number.")
    book.table(ws, notes_rows(audits), widths={"Item": 26, "Definition": 118})

    universe = read(UNIVERSE_DIR / "universe.csv", dtype={"cik": str})
    if not universe.empty:
        universe["group"] = universe.funds.map(holdings_group)
        ws = book.sheet("Universe", "Companies and why any were excluded",
                        "Company and security exclusions come before any filing-level "
                        "filter. Absence of 10-K or 10-Q filings is recorded as observed "
                        "reporting behaviour, never inferred nationality.")
        book.table(ws, universe[["ticker", "sec_name", "cik", "group", "funds", "n_10k",
                                 "n_10q", "status", "exclusion_reason"]])

    ws = book.sheet("Sample filters", "Filings removed at each step, by run",
                    "Text, volatility and return samples are filtered separately. Both "
                    "volatility specifications use one shared complete-case sample.")
    row = 3
    for name in RUNS:
        table1 = read(OUTPUT_DIR / name / "table1.csv")
        if table1.empty:
            continue
        ws.write(row, 0, f"Run: {name}", book.f["title"])
        row = book.table(ws, table1, row + 1)
        panel = read(OUTPUT_DIR / name / "table1_universe.csv")
        if not panel.empty:
            panel["filter"] = panel["filter"].map(FILTER_NAMES).fillna(panel["filter"])
            row = book.table(ws, panel, row)

    ws = book.sheet("Filings", "One row per scored filing",
                    "Word shares are fractions. Market columns are blank where the "
                    "outcome window had not elapsed or controls were unavailable.")
    book.table(ws, filings_sheet(sections),
               formats={"Negative share": "pct", "Uncertainty share": "pct",
                        "Item 1A share of words": "pct",
                        "Negative share ex Item 1A": "pct",
                        "Uncertainty share ex Item 1A": "pct",
                        "Four-session excess return": "pct",
                        "Prior annualised volatility": "pct",
                        "Following annualised volatility": "pct",
                        "Words": "int", "Item 1A words": "int"},
               widths={"Company": 34, "SEC document": 46, "Disclosure mode": 44})

    for sheet, filename, title, subtitle in [
        ("Summary stats", "table2.csv", "Language levels by report type",
         "Annual and quarterly reports are kept separate because their contents differ."),
        ("Dictionary words", "table3.csv", "Most frequent words in each list",
         "Each share divides a word's count by all occurrences in its own category."),
    ]:
        ws = book.sheet(sheet, title, subtitle)
        row = 3
        for name in RUNS:
            frame = read(OUTPUT_DIR / name / filename)
            if frame.empty:
                continue
            ws.write(row, 0, f"Run: {name}", book.f["title"])
            row = book.table(ws, frame, row + 1)

    for sheet, filename, title, subtitle in [
        ("Trends", "table4.csv", "Estimated change in language per year",
         "Aggregate slopes use Newey-West. Within-company slopes control company level "
         "and reporting season and are the ones to read first."),
        ("Volatility", "table5.csv", "Uncertainty and the following quarter's volatility",
         "Each measure is estimated with and without prior volatility on one shared "
         "sample. The gap between the two is the result."),
        ("Returns", "table6.csv", "Negative language and the filing-period return",
         "Four trading sessions from the filing event day, less the benchmark over the "
         "same sessions."),
    ]:
        ws = book.sheet(sheet, title, subtitle)
        row = 3
        for name in RUNS:
            frame = read(OUTPUT_DIR / name / filename)
            if frame.empty:
                continue
            ws.write(row, 0, f"Run: {name}", book.f["title"])
            row = book.table(ws, tidy_estimates(frame), row + 1)

    ws = book.sheet("Trend correction", "The same trend with Item 1A removed",
                    "Both columns use the identical filings, so the two slopes are "
                    "comparable. A section that grows as a share of the document raises "
                    "the whole-filing slope on its own.")
    corrected = read(comparison / "corrected_trends.csv")
    book.table(ws, tidy_estimates(corrected[corrected.run.ne("all")]))

    ws = book.sheet("ARK vs QQQ", "ARK holdings against QQQ holdings",
                    "A difference between the two is read from a QQQ indicator, or its "
                    "interaction with time or with the measure, in one regression on the "
                    "companies held by only one of them. Never from two separate p-values.")
    row = book.table(ws, read(comparison / "levels.csv"), 3)
    ws.write(row, 0, "Difference in level and in trend", book.f["title"])
    row = book.table(ws, tidy_estimates(read(comparison / "differences.csv")), row + 1)
    ws.write(row, 0, "The same difference with Item 1A removed", book.f["title"])
    row = book.table(ws, tidy_estimates(read(comparison / "differences_excluding_item_1a.csv")),
                     row + 1)
    ws.write(row, 0, "Difference in the volatility and return coefficients", book.f["title"])
    row = book.table(ws, tidy_estimates(read(comparison / "outcome_differences.csv")), row + 1)
    ws.write(row, 0, "Quarterly risk-factor practice", book.f["title"])
    book.table(ws, read(comparison / "disclosure_practice.csv"), row + 1)

    ws = book.sheet("Disclosure modes", "How often risk factors are actually restated",
                    "Quarterly reports only, as a share of filings in each year.")
    modes = read(disclosure / "mode_shares.csv")
    book.table(ws, modes)

    ws = book.sheet("Decomposition", "Language against composition",
                    "Each filing-to-filing change splits exactly into the two terms. "
                    "Read the change excluding Item 1A first: the language term inherits "
                    "the high word density of a one-sentence pointer.")
    row = 3
    for name, label in [("ark", "ARK holdings"), ("ndx", "QQQ holdings")]:
        ws.write(row, 0, label, book.f["title"])
        row = book.table(ws, read(OUTPUT_DIR / name / "disclosure" / "decomposition.csv"), row + 1)

    events = read(disclosure / "switch_events.csv")
    if not events.empty:
        columns = [c for c in ["ticker", "group", "form", "filing_date", "quarter",
                               "prev_mode", "risk_mode", "transition", "prev_risk_words",
                               "risk_words", "risk_words_change",
                               "Uncertainty_change", "Uncertainty_body_change",
                               "Negative_change", "Negative_body_change"]
                   if c in events.columns]
        ws = book.sheet("Switch events", "Every change of disclosure practice",
                        "One row per filing where a company started or stopped restating "
                        "its risk factors, against the same form in the previous period.")
        book.table(ws, events[columns])

    levels = read(OUTPUT_DIR / "report_figures" / "figB2_levels.csv")
    slopes = read(OUTPUT_DIR / "report_figures" / "figB2_slopes.csv")
    if not levels.empty:
        firms = levels.merge(slopes, on="ticker", how="outer").sort_values("level", ascending=False)
        firms = firms.rename(columns={"ticker": "Ticker", "filing_date": "Latest 10-K filed",
                                      "level": "Uncertainty share ex Item 1A, latest 10-K (%)",
                                      "slope": "Within-company slope, pp per year",
                                      "n": "Annual reports with located Item 1A"})
        ws = book.sheet("ARK firm ranking", "ARK holdings ranked on uncertainty excluding Item 1A",
                        "Annual reports only. Slopes are fitted on three to six observations and "
                        "rank companies; they are not precise estimates.")
        book.table(ws, firms, formats={"Annual reports with located Item 1A": "int"})

    ws = book.sheet("Switch outcomes", "Market outcomes around a switch",
                    "Descriptive first, then the same regressions as the main tables with "
                    "the switch indicator as the focal variable.")
    row = 3
    for name, label in [("ark", "ARK holdings"), ("ndx", "QQQ holdings")]:
        folder = OUTPUT_DIR / name / "disclosure"
        ws.write(row, 0, f"{label}: outcomes by transition", book.f["title"])
        row = book.table(ws, read(folder / "switch_outcomes.csv"), row + 1)
        ws.write(row, 0, f"{label}: regressions", book.f["title"])
        row = book.table(ws, tidy_estimates(read(folder / "switch_regressions.csv")), row + 1)

    book.close()
    print(f"Wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
