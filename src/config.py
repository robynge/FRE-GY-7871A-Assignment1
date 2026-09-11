"""Central configuration for the data pipeline.

This file defines the sample: which funds, which window, which forms. The
analysis parameters (event windows, filter thresholds) are specified in the
assignment brief and are yours to set.
"""

import os
from pathlib import Path

# ----------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
LEXICON_DIR = DATA / "lexicons"
FILING_DIR = DATA / "filings"
PRICE_DIR = DATA / "prices"
UNIVERSE_DIR = DATA / "universe"
INTERIM_DIR = DATA / "interim"
OUTPUT_DIR = ROOT / "outputs"

for _d in (LEXICON_DIR, FILING_DIR, PRICE_DIR, UNIVERSE_DIR, INTERIM_DIR, OUTPUT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------------
# SEC EDGAR
# ----------------------------------------------------------------------------
# The SEC requires a declared User-Agent with a real contact address, and rate
# limits to 10 requests/second. Set SEC_USER_AGENT in your environment:
#     Windows PowerShell:  $env:SEC_USER_AGENT = "Your Name your.netid@nyu.edu"
#     macOS / Linux:       export SEC_USER_AGENT="Your Name your.netid@nyu.edu"
SEC_USER_AGENT = os.environ.get("SEC_USER_AGENT") or os.environ.get("EDGAR_IDENTITY", "")
SEC_MAX_REQUESTS_PER_SEC = 6.0  # below the SEC's limit of 10, on purpose

# ----------------------------------------------------------------------------
# Sample definition  (Section 3 of the assignment)
# ----------------------------------------------------------------------------
ARK_FUNDS = ["ARKK", "ARKQ", "ARKW", "ARKF", "ARKG", "ARKX"]

# Benchmark index used as the comparison group. The Nasdaq-100 constituents are
# carried through the same holdings schema as the ARK funds so that one audited
# universe build covers both groups; membership is recoverable from the `funds`
# column afterwards. QQQ tracks this index, so QQQ is not a separate group.
INDEX_LABELS = ["NDX"]
HOLDING_FUND_LABELS = ARK_FUNDS + INDEX_LABELS


def holdings_group(funds: str) -> str:
    """Which side of the comparison a company sits on: ARK, NDX, or BOTH.

    `funds` is the pipe-joined fund column carried through the universe and
    candidate files. Companies held by an ARK fund and also in the index are
    labelled BOTH; they belong to each group when a group is selected, so that
    neither side is silently made unrepresentative by the overlap.
    """
    labels = set(str(funds).split("|"))
    in_ark = bool(labels & set(ARK_FUNDS))
    in_index = bool(labels & set(INDEX_LABELS))
    if in_ark and in_index:
        return "BOTH"
    return "ARK" if in_ark else "NDX"


def in_group(funds: str, group: str) -> bool:
    """True when a company belongs to the named group, overlap included."""
    label = holdings_group(funds)
    return label == group or label == "BOTH" and group in ("ARK", "NDX")

SAMPLE_START = "2021-01-01"          # filing date, inclusive
SAMPLE_END = "2026-09-09"            # filing date, inclusive; incomplete current quarter
COURSE_SAMPLE_END = "2025-12-31"     # original assignment window, retained as a comparison
AS_OF_DATE = "2026-09-09"            # retrieval cutoff for this reproducible run
MARKET_END = "2026-09-09"            # exclusive: completed daily closes through September 8
FORMS = ["10-K", "10-Q"]             # amendments (10-K/A, 10-Q/A) are excluded

# Series downloaded alongside the filers, for you to use as benchmarks.
BENCHMARK = "SPY"                    # stands in for the CRSP value-weighted index
ALT_BENCHMARK = "ARKK"               # thematic-peer benchmark
VIX_TICKER = "^VIX"                  # market-implied uncertainty

# ----------------------------------------------------------------------------
# Word-list downloads (verified working 2026-09-05; if a link rots, see README)
# ----------------------------------------------------------------------------
LM_MASTER_DICT_URL = (
    "https://drive.usercontent.google.com/download"
    "?id=1iq2RUf8qGFEAk1g8wQntP3habOnR3fXF&export=download&confirm=t"
)
LM_MASTER_DICT_PATH = LEXICON_DIR / "LoughranMcDonald_MasterDictionary.csv"

# Optional. The Harvard General Inquirer negative list is NOT required for this
# assignment; it is here only for the extra-credit comparison in the brief.
HARVARD_GI_URL = "https://inquirer.sites.fas.harvard.edu/inqtabs.txt"
HARVARD_GI_PATH = LEXICON_DIR / "inqtabs.txt"

# Economic Policy Uncertainty index (Baker, Bloom & Davis), free, monthly.
# An optional external series to plot against your own uncertainty measure.
EPU_MONTHLY_URL = "https://www.policyuncertainty.com/media/US_Policy_Uncertainty_Data.xlsx"

LM_CATEGORIES = [
    "Negative", "Positive", "Uncertainty",
    "Litigious", "Strong_Modal", "Weak_Modal",
]
