# Uncertainty and sentiment in SEC filings

FRE-GY 7871 A · Assignment 1 · 2021–2025

Open [analysis.ipynb](analysis.ipynb) for saved results and reproducible analysis, [REPORT.md](REPORT.md) for the report text, or [the PDF](outputs/report.pdf). [AI_USE.md](AI_USE.md) discloses AI assistance.

The analysis uses Loughran–McDonald negative and uncertainty dictionaries, proportional and equation (1) weights, NYSE trading-day event windows, and company/quarter-aware inference. Negative sentiment and uncertainty remain separate throughout.

## Reproduce

Python 3.11 is supported. Create an isolated environment, activate it, then install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The exact versions used for the submitted run are recorded in `requirements-versions.txt` and can be installed with the same `-r` option.

SEC requires a contact identity. Set `SEC_USER_AGENT` to your existing genuine contact string, or use an already configured `EDGAR_IDENTITY`; the code accepts either. Never commit that identity or credentials.

```bash
python scripts/00_get_holdings.py
python scripts/00_get_lexicons.py
python scripts/01_build_universe.py
python scripts/02_download_filings.py --limit 3
python scripts/02_download_filings.py
python scripts/03_get_market_data.py
python scripts/06_survivorship.py
python -m pytest -q
python scripts/05_notebook.py
python scripts/07_report.py
```

The notebook recomputes the analysis and saves all outputs. To calculate exhibits without executing the notebook, run `python scripts/04_analyze.py`. Optional `03_prefetch_shares.py` preloads company facts while the main corpus downloads; rerun `03_get_market_data.py` once all original documents are available for cover-page fallbacks.

The historical holdings comparison uses the GitHub CLI (`gh`) and the public `robynge/ark-routine` repository. The primary classroom snapshot is retrieved from a pinned upstream commit and checked against its SHA-256 checksum. No data files are distributed here.

## Sample and methods

- The fixed classroom snapshot contains 130 raw holding tickers, with January 2 and September 4, 2026 dates. It is not silently replaced by current holdings.
- Preserve non-company securities, foreign local listings, unresolved identifiers, foreign reporting forms, and later filers in the universe audit. Combine company CIKs before downloading.
- Preserve amendments, parse failures and acquisition failures in an accession-level manifest. Stop visibly on repeated download failure.
- Keep visible inline-XBRL text; discard hidden scaffolding and numeric-heavy tables. Downloads and parsing are cached and checkpointed.
- Apply the assignment filters in order. Additional full-window, cover-share and liquidity exclusions are explicit. Every reported regression sample refits its own document frequencies.
- Convert acceptance timestamps to Eastern, apply the 16:00 cutoff, and use an exchange calendar. Missing returns are never forward filled.
- Separate nominal prices/volumes for size and liquidity from adjusted prices for total returns. Use only accession-matched cover-page outstanding shares, with strict tagged multi-class extraction when needed.
- Annual trend slopes use seasonal controls and company effects; aggregate inference includes OLS and Newey–West with four lags. Outcome models include company and calendar-quarter effects. Company-only and two-way clustered results are retained.
- The paired volatility models share observations. Return tests report approximate 80% minimum detectable effects; no significance threshold is used to select which models are retained.

All downloaded inputs, observation-level results, logs and runtime files stay under ignored local data/output directories. The submitted report and figure are permitted output artifacts.

## Provenance

Course starter: [anmolsingh0219/FRE-GY-7871A-Assignment1](https://github.com/anmolsingh0219/FRE-GY-7871A-Assignment1), commit `532c65cf91cdf62a8d37c9bbe6ff0961c152d756`.

Method: Loughran and McDonald (2011), [Journal of Finance 66(1), 35–65](https://doi.org/10.1111/j.1540-6261.2010.01625.x). Dictionary: [Notre Dame Software Repository for Accounting and Finance](https://sraf.nd.edu/loughranmcdonald-master-dictionary/). Filings and facts: SEC EDGAR. Prices, volume and VIX: Yahoo Finance via yfinance.

These are retrospective conditional associations. Current-holdings selection, firm identity changes, template reuse, earnings-event overlap and only 20 quarterly clusters limit interpretation. Full-sample word weights are not an out-of-sample trading signal.
