"""Two figures for the disclosure section.

Figure 2 follows four companies through a change of practice. The whole-filing
uncertainty share moves with the length of Item 1A; the share of everything
except Item 1A does not. That is the argument in one picture.

Figure 3 is the same point across the sample: the share of quarterly reports
that restate their risk factors, quarter by quarter, against the two measures.

    python scripts/23_disclosure_figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import INTERIM_DIR, OUTPUT_DIR  # noqa: E402

ACCENT = "#8264FF"
INK = "#0A0A23"
GREY = "#8C9195"
CASES = ["COIN", "TXG", "SOFI", "ABSI"]
PRINTS = ("full", "partial_update")

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                     "axes.spines.top": False, "axes.spines.right": False})


def quarterly_10q(sections: pd.DataFrame) -> pd.DataFrame:
    data = sections[sections.form.eq("10-Q") & sections.risk_found].copy()
    data["filing_date"] = pd.to_datetime(data.filing_date)
    return data.sort_values("filing_date")


def figure_two(data: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(7.15, 4.9), sharex=False)
    legend_source = None
    for ax, ticker in zip(axes.flat, CASES):
        firm = data[data.ticker.eq(ticker)]
        if firm.empty:
            ax.set_visible(False)
            continue
        x = range(len(firm))
        ax.bar(x, firm.risk_words, color="#E4DDFF", width=.72, label="Item 1A words")
        ax.set_ylabel("Item 1A words", fontsize=7.5)
        ax.tick_params(axis="y", labelsize=7)
        ax.set_title(ticker, loc="left", fontsize=9, color=INK)

        twin = ax.twinx()
        twin.plot(x, 100 * firm.Uncertainty_prop_total, color=INK, lw=1.6,
                  marker="o", ms=2.6, label="Whole filing")
        twin.plot(x, 100 * firm.Uncertainty_prop_body, color=ACCENT, lw=1.6,
                  marker="s", ms=2.6, label="Excluding Item 1A")
        twin.set_ylabel("Uncertainty words (%)", fontsize=7.5)
        twin.tick_params(axis="y", labelsize=7)
        twin.spines["top"].set_visible(False)
        twin.set_ylim(0, max(3.2, 100 * firm.Uncertainty_prop_total.max() * 1.25))

        labels = [f"{d.year} Q{d.quarter}" for d in firm.filing_date]
        ticks = list(range(0, len(firm), max(1, len(firm) // 5)))
        ax.set_xticks(ticks, [labels[i] for i in ticks], rotation=30, fontsize=7)
        if legend_source is None:
            legend_source = twin
    if legend_source is not None:
        fig.legend(*legend_source.get_legend_handles_labels(), loc="upper right",
                   frameon=False, fontsize=7.5, ncol=2)
    fig.text(.01, .005,
             "Bars: words in Item 1A. Lines: uncertainty word share of the whole filing "
             "and of the filing excluding Item 1A (right axis).\nQuarterly reports only; "
             "quarters where no Item 1A heading was located are absent.", fontsize=7,
             color=GREY)
    fig.tight_layout(rect=[0, .06, 1, .96])
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def figure_three(data: pd.DataFrame, path: Path) -> None:
    data = data.copy()
    data["prints"] = data.risk_mode.isin(PRINTS)
    quarters = data.groupby("quarter").agg(
        prints=("prints", "mean"),
        total=("Uncertainty_prop_total", "mean"),
        body=("Uncertainty_prop_body", "mean"),
        n=("accession", "size")).reset_index()
    quarters = quarters[quarters.n >= 10]

    fig, ax = plt.subplots(figsize=(7.15, 3.1))
    x = range(len(quarters))
    ax.bar(x, 100 * quarters.prints, color="#E4DDFF", width=.72)
    ax.set_ylabel("Reports restating risk factors (%)", fontsize=8, color=GREY)
    ax.set_ylim(0, 100)
    ax.tick_params(axis="y", labelsize=7, colors=GREY)

    twin = ax.twinx()
    twin.plot(x, 100 * quarters.total, color=INK, lw=1.8, marker="o", ms=3,
              label="Whole filing")
    twin.plot(x, 100 * quarters.body, color=ACCENT, lw=1.8, marker="s", ms=3,
              label="Excluding Item 1A")
    twin.set_ylabel("Uncertainty words (%)", fontsize=8)
    twin.tick_params(axis="y", labelsize=7)
    twin.spines["top"].set_visible(False)
    twin.legend(frameon=False, fontsize=8, loc="upper left", ncol=2)

    ticks = list(range(0, len(quarters), 2))
    ax.set_xticks(ticks, [quarters.quarter.iloc[i] for i in ticks], rotation=30, fontsize=7)
    fig.text(.01, .005,
             "Quarterly reports with a located Item 1A, quarters with at least ten "
             "filings. Bars: share of reports that restate their risk factors\nrather "
             "than pointing to the annual report. Lines: equal-weighted mean uncertainty "
             "word share (right axis).", fontsize=7, color=GREY)
    fig.tight_layout(rect=[0, .1, 1, 1])
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    sections = pd.read_csv(INTERIM_DIR / "risk_sections.csv")
    data = quarterly_10q(sections)
    out = OUTPUT_DIR / "all" / "disclosure"
    out.mkdir(parents=True, exist_ok=True)
    figure_two(data, out / "figure2_cases.png")
    figure_three(data, out / "figure3_practice.png")
    print(f"Wrote {out/'figure2_cases.png'} and {out/'figure3_practice.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
