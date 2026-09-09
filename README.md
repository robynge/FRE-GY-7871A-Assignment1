# Uncertainty and sentiment in SEC filings

FRE-GY 7871 A · Assignment 1 and current-period extension

The main analysis covers filing dates January 1, 2021–September 9, 2026. The original assignment explicitly requests 2021–2025; that period is also recomputed with the same active dictionaries and supplied as a separate comparison.

- [Executed notebook](analysis.ipynb)
- [Current-period report](REPORT.md) · [PDF](outputs/report.pdf)
- [2021–2025 course-period report](COURSE_REPORT.md) · [PDF](outputs/course_2021_2025/report.pdf)
- [AI assistance disclosure](AI_USE.md)

The analysis uses the official Loughran–McDonald Master Dictionary, 1993–2025 release, updated March 2026. Only positive category flags are included: **2,345 active negative words and 297 uncertainty words**. Negative year flags identify removed words and are excluded. Including the ten removed entries reproduces the assignment's count of 2,355; the analysis instead uses only current active entries. Dictionary proportions and equation (1) weights are computed separately for sentiment and uncertainty.

## Reproduce

Python 3.11 is supported. Create an isolated environment and install the recorded dependency versions:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-versions.txt
```

SEC requests use the existing genuine contact string in `SEC_USER_AGENT` or `EDGAR_IDENTITY`. Never commit that identity or credentials. Then run:

```bash
python scripts/00_get_holdings.py
python scripts/00_get_lexicons.py
python scripts/01_build_universe.py
python scripts/02_download_filings.py
python scripts/03_get_market_data.py
python scripts/06_survivorship.py
python -m pytest -q
python scripts/05_notebook.py
python scripts/07_report.py
python scripts/07_report.py --output-dir outputs/course_2021_2025 --report-path COURSE_REPORT.md
```

The notebook computes both date windows and saves its aggregate outputs. To compute the exhibits without notebook execution, use `python scripts/04_analyze.py`. SEC metadata are refreshed when older than the configured retrieval date; unchanged original documents are reused. Historical holdings comparisons use the GitHub CLI (`gh`).

## Samples and timing

Every successfully parsed original filing receives four scores before analysis filters. Descriptive statistics and trends use the eligible text sample, after minimum-word and earliest-company-quarter filters. Return regressions use their own complete four-session outcome sample. The paired volatility regressions use an identical sample with complete post-filing volatility and controls, with and without the pre-filing volatility regressor. Each estimation sample refits document frequencies.

Latest filings remain in the text sample when their future market windows are not yet observable. Missing future returns are never filled or extrapolated. Market data include complete daily closes through September 8, 2026. The 2026 third quarter is incomplete. Tables report separate sample attrition and the figure identifies sparse annual-report quarters.

Day 0 uses the later of the SEC filing date and the acceptance date, shifts after the actual NYSE session close (including early closes), and aligns to the next trading session. Returns use adjusted closes; size and dollar volume use nominal prices and volumes reconstructed from corporate actions. Outstanding shares must match the scored filing's accession and cover-page date.

Aggregate trend inference includes Newey–West with four lags. Within-company trends include company and seasonal effects; outcome models include company and calendar-quarter effects. Company and two-way company/quarter clustered inference are retained. No winsorisation or significance-based model selection is applied.

## Sources and scope

The frozen course holdings snapshot is retrieved from [the instructor repository](https://github.com/anmolsingh0219/FRE-GY-7871A-Assignment1), commit `532c65cf91cdf62a8d37c9bbe6ff0961c152d756`, with a checksum check. The same holdings selection supports both filing windows. ARKF/ARKX holdings are dated January 2, 2026 and the other four funds September 4, 2026; company eligibility is evaluated within the selected filing period.

Method: Loughran and McDonald (2011), [Journal of Finance 66(1), 35–65](https://doi.org/10.1111/j.1540-6261.2010.01625.x). Dictionary version and removal-flag semantics: [Notre Dame official source](https://sraf.nd.edu/loughranmcdonald-master-dictionary/). Filings and company facts: SEC EDGAR. Prices, volume and VIX: Yahoo Finance via yfinance.

Downloaded data, filing-level scores, logs and caches are excluded from Git. Reports, figures, code, tests and aggregate notebook outputs are provided. These are retrospective conditional associations; holdings selection, unbalanced reporting quarters, template language and overlap with earnings news limit interpretation. Full-corpus weights use later documents and are not a real-time forecasting procedure.
