"""Run the six exhibits separately for each side of the ARK / Nasdaq-100 comparison.

Six runs are produced:

    all                    every company, both groups pooled
    course_ark_2021_2025   ARK holdings, the assignment's own window
    ark                    ARK holdings, filings through the retrieval date
    ndx                    Nasdaq-100 constituents, same extended window
    ark_only / ndx_only    the two groups with the 22 shared companies removed

The shared companies sit in both the ark and ndx runs because both portfolios
hold them. The disjoint runs exist so that any difference between the groups can
be checked on samples that have no company in common.

Word weights for equation (1) are refitted inside each run, so a weighted score
is comparable across filings within a run and not across runs.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.analysis import run_analysis
from src.config import COURSE_SAMPLE_END, OUTPUT_DIR, SAMPLE_END

RUNS = [
    ("all", None, SAMPLE_END),
    ("course_ark_2021_2025", "ARK", COURSE_SAMPLE_END),
    ("ark", "ARK", SAMPLE_END),
    ("ndx", "NDX", SAMPLE_END),
    ("ark_only", "ARK_ONLY", SAMPLE_END),
    ("ndx_only", "NDX_ONLY", SAMPLE_END),
]


def main() -> int:
    for name, group, end in RUNS:
        started = time.time()
        print(f"\n{'=' * 70}\n{name}: group={group} through {end}\n{'=' * 70}", flush=True)
        data = run_analysis(sample_end=end, output_dir=OUTPUT_DIR / name, group=group)
        print(f"{name}: {len(data)} filings, {data.cik.nunique()} companies, "
              f"{time.time() - started:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
