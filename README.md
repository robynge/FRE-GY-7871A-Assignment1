# Filing tone and risk-factor disclosure: ARK holdings and the Nasdaq-100

FRE-GY 7871 A · Assignment 1, extended

The study scores every original 10-K and 10-Q filed between 1 January 2021 and 9 September 2026 by the companies held by the six ARK ETFs on 9 September 2026 and by the constituents of the Nasdaq-100 on the same date: 165 SEC filers, 3,413 filings. Each filing is scored on the Loughran–McDonald negative and uncertainty word lists, as a share of words and with the tf.idf weighting of equation (1) in Loughran and McDonald (2011). The assignment's tests are run on the pooled sample and on each group: within-company trends, post-filing volatility with and without a prior-volatility control, and the four-session return around the filing. Each test is then repeated on the filing excluding Item 1A, the risk-factor section, because many quarterly reports replace their risk factors with a reference to the annual report and a word-share measure cannot tell that choice apart from a change in tone.

- **Report:** [PDF](outputs/Filing_Tone_and_Risk_Factor_Disclosure.pdf) · [Markdown](outputs/REPORT.md). One document: executive summary, data, four results, mechanism, conclusion, methods appendix, supplementary tables.
- **Data workbook:** [ARK_vs_Nasdaq100_Filing_Language.xlsx](outputs/ARK_vs_Nasdaq100_Filing_Language.xlsx). One row per filing with every score, section split and market outcome, one sheet per exhibit, and a Notes sheet defining each sample.
- **Figures:** [outputs/report_figures/](outputs/report_figures/), with the CSVs behind the company rankings and case studies.
- **Executed notebook:** [analysis.ipynb](analysis.ipynb), the assignment's Tables 1–6 and Figure 1 for the ARK holdings alone, executed before the index was added (93 filers).
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
python scripts/00_combine_holdings.py        # ARK snapshot + Nasdaq-100 list -> combined_holdings_raw.csv
python scripts/01_build_universe.py --holdings data/universe/combined_holdings_raw.csv
python scripts/02_download_filings.py
python scripts/03_get_market_data.py
python -m pytest -q
python scripts/18_risk_sections.py           # Item 1A location and disclosure mode, one row per filing
python scripts/19_group_analysis.py          # Tables 1-6 for each run under outputs/<run>/
for run in all ark ndx; do python scripts/20_disclosure_outcomes.py --run $run; done
python scripts/21_group_comparison.py        # ARK against the Nasdaq-100 on one pooled sample
python scripts/24_corrected_trends.py        # trends on the whole filing and excluding Item 1A
python scripts/27_report_figures.py          # Figures 1-8
python scripts/22_workbook.py                # data workbook
python scripts/28_report.py                  # the report, PDF and Markdown
```

Script 19 writes six runs: `all` (both groups pooled), `ark` and `ndx` (each including the 22 companies held by ARK and in the index), `ark_only` and `ndx_only` (the overlap removed), and `course_ark_2021_2025` (ARK holdings over the assignment's own window). Each run holds its text, volatility and return samples and `table1.csv` to `table6.csv`. Script 20 writes the disclosure-mode shares, the decomposition of word-share changes, the switch events and the switch regressions to `outputs/<run>/disclosure/`. Script 21 writes the group-difference tests to `outputs/comparison/`, and script 24 the corrected trends. Script 28 reads every number it prints from those CSVs, so the report cannot drift from the analysis.

SEC metadata are refreshed when older than the configured retrieval date; unchanged original documents are reused. The committed notebook was executed on the ARK-only universe; `python scripts/05_notebook.py` re-executes it on whatever universe `01_build_universe.py` last built.

## Earlier scripts

Scripts 04 and 05 build the assignment notebook. Scripts 08 to 17 are an ARK-only company-monitoring extension (declining negative language, rising uncertainty, highest current uncertainty, largest declines) whose questions Section 3.3, Table B5 and the workbook's ARK firm ranking sheet now answer on the measure excluding Item 1A; their spreadsheet and document outputs are not part of the deliverable. Neither is part of the run order above.

## Samples and timing

Every successfully parsed original filing receives four scores before analysis filters. Descriptive statistics and trends use the text sample, 3,380 filings after the minimum-word filter and one filing per company per quarter. Return regressions use their own complete four-session outcome sample. The paired volatility regressions use an identical sample with complete post-filing volatility and controls, with and without the pre-filing volatility regressor. Every statistic on the risk-factor section is computed on the text sample, so the section exhibits and the tone exhibits describe the same filings.

Item 1A is located by its heading and closed at the next titled item heading; filings whose heading cannot be located under those rules are reported as not located and excluded from the section split rather than guessed at. Quarterly reports with a located heading are classified as restating their risk factors, claiming no material change with updates, referring the reader to the annual report, or disclosing nothing. The rules are in Appendix A of the report and in `src/risk_section.py`.

Latest filings remain in the text sample when their future market windows are not yet observable. Missing future returns are never filled or extrapolated. Market data include complete daily closes through 8 September 2026. The 2026 third quarter is incomplete. Tables report separate sample attrition and the figures blank sparse quarterly cells.

Day 0 uses the later of the SEC filing date and the acceptance date, shifts after the actual NYSE session close (including early closes), and aligns to the next trading session. Returns use adjusted closes; size and dollar volume use nominal prices and volumes reconstructed from corporate actions. Outstanding shares must match the scored filing's accession and cover-page date.

Aggregate trend inference includes Newey–West with four lags. Within-company trends include company and seasonal effects; outcome models include company and calendar-quarter effects, with two-way company and calendar-quarter clustering. Group differences are read from an index indicator on the pooled disjoint sample. Indicators identified by fewer than ten filings are reported as not estimable. No winsorisation or significance-based model selection is applied.

## Sources and scope

The six dated 9 September 2026 ARK holdings files come from [the user-supplied ARK archive](https://github.com/robynge/ark-routine/tree/main/data/holdings/2026/2026-09-09); the dates inside all six source files agree. The Nasdaq-100 constituents are the 102 listed on slickcharts.com for the same date, saved as `data/universe/ndx_holdings_raw.csv` because no script downloads them. After removing funds, cash and non-US local listings, merging share classes by CIK and recording companies that file 20-F or 40-F, 165 domestic 10-K/10-Q filers remain: 71 held by ARK only, 22 held by ARK and in the index, 72 in the index only.

Method: Loughran and McDonald (2011), [Journal of Finance 66(1), 35–65](https://doi.org/10.1111/j.1540-6261.2010.01625.x). Dictionary version and removal-flag semantics: [Notre Dame official source](https://sraf.nd.edu/loughranmcdonald-master-dictionary/). Filings and company facts: SEC EDGAR. Prices, volume and VIX: Yahoo Finance via yfinance.

Downloaded data, filing-level scores, logs and caches are excluded from Git. The report, the workbook, the figures, code, tests and the executed notebook are provided. These are retrospective conditional associations; holdings selection, unbalanced reporting quarters, template language and overlap with earnings news limit interpretation. Full-corpus weights use later documents and are not a real-time forecasting procedure.
