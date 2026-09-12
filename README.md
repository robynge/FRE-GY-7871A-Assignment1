# Uncertainty and sentiment in the filings of ARK ETF holdings

FRE-GY 7871 A · Assignment 1, extended to September 2026 and to a comparison with QQQ holdings

The study scores every original 10-K and 10-Q filed between 1 January 2021 and 9 September 2026 by the 93 SEC filers held by the six ARK ETFs on 9 September 2026 (1,805 filings) on the Loughran–McDonald negative and uncertainty word lists, as a share of words and with the tf.idf weighting of equation (1) in Loughran and McDonald (2011). It runs the assignment's tests on the ARK holdings: within-company and aggregate trends, post-filing volatility with and without a prior-volatility control, and the four-session return around the filing. Two extensions follow. Each result is repeated on the filing excluding Item 1A, the risk-factor section, because many quarterly reports replace their risk factors with a reference to the annual report and a word-share measure cannot tell that choice apart from a change in tone. And one section compares the ARK holdings with the holdings of Invesco QQQ, the Nasdaq-100 constituents, each difference tested in one regression on the companies held by only one portfolio. No result pools the two portfolios.

- **Report (six pages):** [PDF](outputs/ARK_Filing_Language_Report.pdf) · [Markdown](outputs/REPORT.md). Tables 1–6 and Figure 1 as the assignment specifies, then the risk-factor section and the QQQ comparison.
- **Appendix:** [PDF](outputs/ARK_Filing_Language_Appendix.pdf) · [Markdown](outputs/APPENDIX.md). Methods, supplementary figures B1–B7, supplementary tables C1–C13.
- **Data workbook:** [ARK_Filing_Language.xlsx](outputs/ARK_Filing_Language.xlsx). One row per filing with every score, section split and market outcome, one sheet per exhibit, and a Notes sheet defining each sample.
- **Figures:** [outputs/report_figures/](outputs/report_figures/), with the CSVs behind the company ranking and the case studies.
- **Executed notebook:** [analysis.ipynb](analysis.ipynb), the assignment's Tables 1–6 and Figure 1 for the ARK holdings, executed before the QQQ holdings were added to the universe.
- **AI assistance disclosure:** [AI_USE.md](AI_USE.md).

The analysis uses the official Loughran–McDonald Master Dictionary, 1993–2025 release, updated March 2026. Only positive category flags are included: **2,345 active negative words and 297 uncertainty words**. Negative year flags identify removed words and are excluded. Including the ten removed entries reproduces the assignment's count of 2,355; the analysis instead uses only current active entries. Dictionary proportions and equation (1) weights are computed separately for negative and uncertainty words, and equation (1) weights are refitted inside each estimation sample.

## Reproduce

Python 3.11 is supported. Create an isolated environment and install the recorded dependency versions:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-versions.txt
```

SEC requests use the existing genuine contact string in `SEC_USER_AGENT` or `EDGAR_IDENTITY`. Never commit that identity or credentials. Then run the scripts in this order:

```bash
python scripts/00_get_holdings.py            # ARK holdings snapshot, 9 September 2026
python scripts/00_get_lexicons.py            # Loughran-McDonald master dictionary
python scripts/00_combine_holdings.py        # ARK snapshot + QQQ constituent list -> combined_holdings_raw.csv
python scripts/01_build_universe.py --holdings data/universe/combined_holdings_raw.csv
python scripts/02_download_filings.py
python scripts/03_get_market_data.py
python -m pytest -q
python scripts/18_risk_sections.py           # Item 1A location and disclosure mode, one row per filing
python scripts/19_group_analysis.py          # Tables 1-6 for each run under outputs/<run>/
for run in all ark ndx; do python scripts/20_disclosure_outcomes.py --run $run; done
python scripts/21_group_comparison.py        # ARK against QQQ, one regression per difference
python scripts/24_corrected_trends.py        # trends on the whole filing and excluding Item 1A
python scripts/27_report_figures.py          # Figures 1-2 and B1-B7
python scripts/22_workbook.py                # data workbook
python scripts/28_report.py                  # the report and the appendix, PDF and Markdown
```

Script 19 writes six runs: `ark` (the report's sample: ARK holdings, including the 22 companies also held by QQQ), `ndx` (QQQ holdings, including the same 22), `ark_only` and `ndx_only` (the overlap removed), `course_ark_2021_2025` (ARK holdings over the assignment's own window) and `all` (every company; used only as the input to the difference tests in script 21 and never reported as a result). Each run holds its text, volatility and return samples and `table1.csv` to `table6.csv`. Script 20 writes the disclosure-mode shares, the decomposition of word-share changes, the switch events and the switch regressions to `outputs/<run>/disclosure/`. Script 21 writes the difference tests to `outputs/comparison/`, and script 24 the corrected trends. Script 28 reads every number it prints from those CSVs, so the report cannot drift from the analysis.

SEC metadata are refreshed when older than the configured retrieval date; unchanged original documents are reused. The committed notebook was executed on the ARK-only universe; `python scripts/05_notebook.py` re-executes it on whatever universe `01_build_universe.py` last built.

## Earlier scripts

Scripts 04 and 05 build the assignment notebook. Scripts 08 to 17 are an ARK-only company-monitoring extension (declining negative language, rising uncertainty, highest current uncertainty, largest declines) whose questions Section 6 of the report, Figure B2 and Table C8 of the appendix and the workbook's ARK firm ranking sheet now answer on the measure excluding Item 1A; their spreadsheet and document outputs are not part of the deliverable. Neither is part of the run order above.

## Samples and timing

Every successfully parsed original filing receives four scores before analysis filters. Descriptive statistics and trends use the text sample, after the minimum-word filter and one filing per company per quarter. Return regressions use their own complete four-session outcome sample. The paired volatility regressions use an identical sample with complete post-filing volatility and controls, with and without the pre-filing volatility regressor. Every statistic on the risk-factor section is computed on the text sample, so the section exhibits and the tone exhibits describe the same filings.

Item 1A is located by its heading and closed at the next titled item heading; filings whose heading cannot be located under those rules are reported as not located and excluded from the section split rather than guessed at. Quarterly reports with a located heading are classified as restating their risk factors, claiming no material change with updates, referring the reader to the annual report, or disclosing nothing. The rules are in Appendix A and in `src/risk_section.py`.

Latest filings remain in the text sample when their future market windows are not yet observable. Missing future returns are never filled or extrapolated. Market data include complete daily closes through 8 September 2026. The 2026 third quarter is incomplete. Tables report separate sample attrition and the figures show confidence bands that widen where cells are sparse.

Day 0 uses the later of the SEC filing date and the acceptance date, shifts after the actual NYSE session close (including early closes), and aligns to the next trading session. Returns use adjusted closes; size and dollar volume use nominal prices and volumes reconstructed from corporate actions. Outstanding shares must match the scored filing's accession and cover-page date.

Aggregate trend inference includes Newey–West with four lags. Within-company trends include company and seasonal effects; outcome models include company and calendar-quarter effects, with two-way company and calendar-quarter clustering. Differences between the portfolios are read from a QQQ indicator, or its interaction with time or with the measure, in one regression on the disjoint sample. Indicators identified by fewer than ten filings are reported as not estimable. No winsorisation or significance-based model selection is applied.

## Sources and scope

The six dated 9 September 2026 ARK holdings files come from [the user-supplied ARK archive](https://github.com/robynge/ark-routine/tree/main/data/holdings/2026/2026-09-09); the dates inside all six source files agree. The QQQ holdings are the 102 Nasdaq-100 constituents of the same date as listed on slickcharts.com, saved as `data/universe/ndx_holdings_raw.csv` because no script downloads them; the list agrees with the Nasdaq-100 constituent list published by Nasdaq. After removing funds, cash and non-US local listings, merging share classes by CIK and recording companies that file 20-F or 40-F, 93 ARK holdings and 94 QQQ holdings remain, 22 companies in both.

Method: Loughran and McDonald (2011), [Journal of Finance 66(1), 35–65](https://doi.org/10.1111/j.1540-6261.2010.01625.x). Dictionary version and removal-flag semantics: [Notre Dame official source](https://sraf.nd.edu/loughranmcdonald-master-dictionary/). Filings and company facts: SEC EDGAR. Prices, volume and VIX: Yahoo Finance via yfinance.

Downloaded data, filing-level scores, logs and caches are excluded from Git. The report, the appendix, the workbook, the figures, code, tests and the executed notebook are provided. These are retrospective conditional associations; holdings selection, unbalanced reporting quarters, template language and overlap with earnings news limit interpretation. Full-corpus weights use later documents and are not a real-time forecasting procedure.
