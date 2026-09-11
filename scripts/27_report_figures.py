"""Eight figures for the report, all from computed outputs.

Colour and line conventions hold across every figure so the reader learns them
once: ARK holdings in blue, Nasdaq-100 constituents in red, the whole-filing
measure as a solid line and the measure excluding Item 1A as a dashed line, the
VIX in grey. Company rankings use one colour; the zero line carries the sign.

    python scripts/27_report_figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path.home() / ".claude/skills/scientific-figure-pro/scripts"))
from scientific_figure_pro import (  # noqa: E402
    PALETTE, FigureStyle, apply_publication_style, create_subplots, finalize_figure,
)
from src.config import INTERIM_DIR, OUTPUT_DIR, PRICE_DIR, UNIVERSE_DIR, holdings_group  # noqa: E402
from src.disclosure import build_panel  # noqa: E402

OUT = OUTPUT_DIR / "report_figures"
ARK, NDX, GREY = PALETTE["blue_main"], PALETTE["red_strong"], "#8C9195"
FILL_ARK, FILL_NDX = "#C9D7EA", "#EAC4C2"
UP, DOWN = PALETTE["red_strong"], "#3E8E41"
QUARTERS = pd.period_range("2021Q1", "2026Q3", freq="Q").astype(str).tolist()
# Calendar-year companies file their 10-K in the first calendar quarter, leaving
# 6 to 25 quarterly reports in each Q1 cell against 66 to 91 in other quarters.
# Quarterly series blank any cell below this floor; annual series use the
# smaller floor since a filing year holds 55 to 77 annual reports per group.
MIN_PER_CELL = 30
MIN_PER_YEAR = 5
WIDTH = 7.2


def quarter_labels(ax, step=4):
    ticks = list(range(0, len(QUARTERS), step))
    ax.set_xticks(ticks)
    ax.set_xticklabels([QUARTERS[i] for i in ticks], rotation=0)
    ax.set_xlim(-0.5, len(QUARTERS) - 0.5)


def centred_quarterly(frame: pd.DataFrame, measure: str) -> pd.Series:
    """Firm-centred mean by quarter, restored to the frame's grand mean, in pp."""
    data = frame.dropna(subset=[measure]).copy()
    data["adjusted"] = data[measure] - data.groupby("cik")[measure].transform("mean") + data[measure].mean()
    grouped = data.groupby("quarter").adjusted.agg(["mean", "size"])
    grouped.loc[grouped["size"] < MIN_PER_CELL, "mean"] = np.nan
    return 100 * grouped["mean"].reindex(QUARTERS)


def centred_annual(frame: pd.DataFrame, measure: str) -> pd.Series:
    """Firm-centred mean by filing year, in pp, indexed by the year's first quarter.

    Annual reports cluster in the first calendar quarter, so a quarterly mean
    of 10-K scores is one well-populated point and three sparse ones a year.
    The document is annual; it is plotted as annual.
    """
    data = frame.dropna(subset=[measure]).copy()
    data["adjusted"] = data[measure] - data.groupby("cik")[measure].transform("mean") + data[measure].mean()
    data["year"] = data.quarter.str[:4]
    grouped = data.groupby("year").adjusted.agg(["mean", "size"])
    grouped.loc[grouped["size"] < MIN_PER_YEAR, "mean"] = np.nan
    series = pd.Series(np.nan, index=QUARTERS)
    for year, value in grouped["mean"].items():
        series[f"{year}Q1"] = 100 * value
    return series


def load() -> dict:
    universe = pd.read_csv(UNIVERSE_DIR / "universe.csv", dtype={"cik": str})
    group = {str(r.cik).zfill(10): holdings_group(r.funds) for r in universe.itertuples()}
    text = pd.read_csv(OUTPUT_DIR / "all" / "text_sample.csv", dtype={"cik": str})
    sections = pd.read_csv(INTERIM_DIR / "risk_sections.csv", dtype={"cik": str})
    sections = sections[sections.accession.isin(text.accession)].copy()  # same filings as Tables 2 to 4
    sections["cik"] = sections.cik.str.zfill(10)
    sections["group"] = sections.cik.map(group)
    text["cik"] = text.cik.str.zfill(10)
    text["group"] = text.cik.map(group)
    returns = pd.read_csv(OUTPUT_DIR / "all" / "return_sample.csv", dtype={"cik": str})
    vix = pd.read_csv(PRICE_DIR / "prices.csv", index_col=0, parse_dates=True)["^VIX"]
    vix = vix.groupby(vix.index.to_period("Q").astype(str)).mean().reindex(QUARTERS)
    return dict(sections=sections, text=text, returns=returns, vix=vix)


def in_group(frame: pd.DataFrame, name: str) -> pd.DataFrame:
    """ARK and NDX both include the 22 shared companies, as the portfolios do."""
    return frame[frame.group.isin([name, "BOTH"])]


# ---------------------------------------------------------------- Figure 1
def figure_1(d: dict) -> None:
    fig, axes = create_subplots(2, 2, figsize=(WIDTH, 4.6), constrained_layout=True)
    panels = [("Negative_prop", "10-K"), ("Negative_prop", "10-Q"),
              ("Uncertainty_prop", "10-K"), ("Uncertainty_prop", "10-Q")]
    for ax, (measure, form) in zip(axes, panels):
        part = d["text"][d["text"].form.eq(form)]
        x = np.arange(len(QUARTERS))
        aggregate = centred_annual if form == "10-K" else centred_quarterly
        for name, colour in [("ARK", ARK), ("NDX", NDX)]:
            series = aggregate(in_group(part, name), measure)
            values = series.to_numpy()
            if form == "10-K":
                mask = ~np.isnan(values)
                ax.plot(x[mask], values[mask], color=colour, lw=1.6, marker="o", ms=2.8,
                        label="ARK holdings" if name == "ARK" else "Nasdaq-100")
            else:
                # Blank cells break the line; a bridge would draw data that is not there.
                ax.plot(x, values, color=colour, lw=1.6, marker="o", ms=2.8,
                        label="ARK holdings" if name == "ARK" else "Nasdaq-100")
        if form == "10-Q":
            twin = ax.twinx()
            twin.plot(x, d["vix"].to_numpy(), color=GREY, lw=1.1, ls="--", label="VIX")
            twin.set_ylim(10, 40)
            twin.tick_params(axis="y", labelsize=7, colors=GREY)
            twin.spines["top"].set_visible(False)
            twin.spines["right"].set_color(GREY)
            twin.set_ylabel("VIX", color=GREY, fontsize=8)
        label = "Negative words (%)" if measure.startswith("Negative") else "Uncertainty words (%)"
        ax.set_title("10-K, by filing year" if form == "10-K" else "10-Q, by quarter",
                     loc="left", fontsize=9)
        if form == "10-K":
            ax.set_ylabel(label)
        quarter_labels(ax, step=4)
        ax.tick_params(axis="x", labelsize=7)
        ax.grid(axis="y", alpha=.2)
    handles, labels = axes[0].get_legend_handles_labels()
    handles.append(plt_line(GREY, "--"))
    labels.append("VIX (right axis)")
    fig.legend(handles, labels, loc="upper center", ncol=3, frameon=False, fontsize=8,
               bbox_to_anchor=(0.5, 1.04))
    finalize_figure(fig, OUT / "fig1_series.png", formats=["png"], dpi=300)


def plt_line(colour, ls):
    from matplotlib.lines import Line2D
    return Line2D([0], [0], color=colour, lw=1.1, ls=ls)


# ---------------------------------------------------------------- Figure 2
def firm_level(d: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Latest 10-K level and within-firm slope of uncertainty excluding Item 1A."""
    k = d["sections"]
    k = k[k.form.eq("10-K") & k.risk_found & k.group.isin(["ARK", "BOTH"])].copy()
    k["filing_date"] = pd.to_datetime(k.filing_date)
    k["years"] = (k.filing_date - pd.Timestamp("2021-01-01")).dt.days / 365.25
    latest = (k.sort_values("filing_date").groupby("ticker").tail(1)
              .assign(level=lambda f: 100 * f.Uncertainty_prop_body)[["ticker", "level", "filing_date"]])
    slopes = []
    for ticker, part in k.groupby("ticker"):
        if len(part) < 3:
            continue
        slope = np.polyfit(part.years, 100 * part.Uncertainty_prop_body, 1)[0]
        slopes.append({"ticker": ticker, "slope": slope, "n": len(part)})
    return latest.reset_index(drop=True), pd.DataFrame(slopes)


def figure_2(d: dict) -> None:
    latest, slopes = firm_level(d)
    latest.to_csv(OUT / "fig2_levels.csv", index=False)
    slopes.to_csv(OUT / "fig2_slopes.csv", index=False)
    fig, axes = create_subplots(1, 2, figsize=(WIDTH, 5.4), constrained_layout=True)

    ranked = latest.sort_values("level")
    show = pd.concat([ranked.head(15), ranked.tail(15)])
    y = np.arange(len(show))
    axes[0].hlines(y, latest.level.median(), show.level, color="#D9D9D9", lw=1)
    axes[0].scatter(show.level, y, color=ARK, s=18, zorder=3, edgecolor="black", lw=.4)
    axes[0].axvline(latest.level.median(), color=GREY, lw=1, ls="--")
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(show.ticker, fontsize=7)
    axes[0].set_xlabel("Uncertainty words excluding Item 1A, latest 10-K (%)")
    axes[0].set_title("Level: 15 lowest and 15 highest", loc="left", fontsize=9)
    axes[0].text(latest.level.median(), len(show) - .2, " median", color=GREY, fontsize=7, va="bottom")
    axes[0].axhline(14.5, color=GREY, lw=.8, ls=":")

    ranked = slopes.sort_values("slope")
    show = pd.concat([ranked.head(10), ranked.tail(10)])
    y = np.arange(len(show))
    axes[1].hlines(y, 0, show.slope, color="#D9D9D9", lw=1)
    axes[1].scatter(show.slope, y, color=ARK, s=18, zorder=3, edgecolor="black", lw=.4)
    axes[1].axvline(0, color=GREY, lw=1)
    axes[1].set_yticks(y)
    axes[1].set_yticklabels(show.ticker, fontsize=7)
    axes[1].set_xlabel("Change per year, 2021 to 2026 (pp)")
    axes[1].set_title("Trend: 10 largest falls and 10 largest rises", loc="left", fontsize=9)
    axes[1].axhline(9.5, color=GREY, lw=.8, ls=":")
    for ax in axes:
        ax.grid(axis="x", alpha=.2)
        ax.tick_params(axis="x", labelsize=8)
    finalize_figure(fig, OUT / "fig2_firms.png", formats=["png"], dpi=300)


# ---------------------------------------------------------------- Figure 3
def figure_3(d: dict) -> None:
    k = d["sections"]
    k = k[k.form.eq("10-K") & k.risk_found & k.group.isin(["ARK", "NDX"])]
    means = k.groupby(["cik", "group"])[["Negative_prop_total", "Negative_prop_body",
                                          "Uncertainty_prop_total", "Uncertainty_prop_body"]].mean().reset_index()
    fig, axes = create_subplots(1, 2, figsize=(WIDTH, 3.2), constrained_layout=True)
    for ax, category in zip(axes, ["Negative", "Uncertainty"]):
        data, positions, colours = [], [], []
        for offset, scope in [(0, "total"), (3, "body")]:
            for shift, (name, colour) in enumerate([("ARK", ARK), ("NDX", NDX)]):
                data.append(100 * means.loc[means.group.eq(name), f"{category}_prop_{scope}"].to_numpy())
                positions.append(offset + shift)
                colours.append(colour)
        boxes = ax.boxplot(data, positions=positions, widths=.7, patch_artist=True,
                           showfliers=False, medianprops=dict(color="black", lw=1.2),
                           whiskerprops=dict(lw=.9), capprops=dict(lw=.9))
        for patch, colour in zip(boxes["boxes"], colours):
            patch.set_facecolor(colour)
            patch.set_alpha(.55)
            patch.set_edgecolor("black")
            patch.set_linewidth(.6)
        ax.set_xticks([0.5, 3.5])
        ax.set_xticklabels(["Whole filing", "Excluding Item 1A"])
        ax.set_ylabel(f"{category} words, firm mean (%)")
        ax.set_title(category, loc="left", fontsize=9)
        ax.grid(axis="y", alpha=.2)
    from matplotlib.patches import Patch
    fig.legend([Patch(facecolor=ARK, alpha=.55, edgecolor="black"),
                Patch(facecolor=NDX, alpha=.55, edgecolor="black")],
               [f"ARK only ({means.group.eq('ARK').sum()})",
                f"Nasdaq-100 only ({means.group.eq('NDX').sum()})"], loc="upper center", ncol=2,
               frameon=False, fontsize=8, bbox_to_anchor=(0.5, 1.06))
    finalize_figure(fig, OUT / "fig3_distributions.png", formats=["png"], dpi=300)


# ---------------------------------------------------------------- Figure 4
def figure_4(d: dict) -> None:
    rows = pd.read_csv(OUTPUT_DIR / "all" / "disclosure" / "switch_regressions.csv")
    rows = rows[rows.measure.isin(["Uncertainty_prop_total", "Uncertainty_prop_body"])
                & rows.model.str.startswith("volatility") & rows.status.eq("ok")].copy()
    scale = rows.effect_1sd / rows.coef
    rows["lo"], rows["hi"] = 100 * rows.ci_low * scale, 100 * rows.ci_high * scale
    rows["effect"] = 100 * rows.effect_1sd
    # 10-K rows are omitted: on ~580 annual reports the confidence intervals
    # span forty percentage points and compress every other row to a dot.
    order = [("10-Q", "Uncertainty_prop_total"), ("10-Q", "Uncertainty_prop_body"),
             ("All", "Uncertainty_prop_total"), ("All", "Uncertainty_prop_body")]
    labels = {("10-K", "Uncertainty_prop_total"): "10-K, whole filing",
              ("10-K", "Uncertainty_prop_body"): "10-K, excluding Item 1A",
              ("10-Q", "Uncertainty_prop_total"): "10-Q, whole filing",
              ("10-Q", "Uncertainty_prop_body"): "10-Q, excluding Item 1A",
              ("All", "Uncertainty_prop_total"): "All, whole filing",
              ("All", "Uncertainty_prop_body"): "All, excluding Item 1A"}
    fig, axes = create_subplots(1, 1, figsize=(WIDTH, 2.7), constrained_layout=True)
    ax = axes[0]
    for i, key in enumerate(order):
        for spec, dy, filled in [("volatility_without_prevol", -.18, False),
                                 ("volatility_with_prevol", .18, True)]:
            r = rows[(rows["sample"] == key[0]) & (rows.measure == key[1]) & (rows.model == spec)]
            if r.empty:
                continue
            r = r.iloc[0]
            body = "body" in key[1]
            ax.plot([r.lo, r.hi], [i + dy, i + dy], color=ARK, lw=1.4, ls="--" if body else "-")
            ax.scatter([r.effect], [i + dy], s=28, zorder=3, edgecolor=ARK, lw=1.2,
                       marker="s" if body else "o", facecolor=ARK if filled else "white")
    ax.axvline(0, color=GREY, lw=1)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([labels[k] for k in order], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Annualised volatility per 1 SD of uncertainty, pp (95% CI)")
    from matplotlib.lines import Line2D
    ax.legend([Line2D([0], [0], marker="o", color=ARK, mfc="white", lw=0, ms=6),
               Line2D([0], [0], marker="o", color=ARK, mfc=ARK, lw=0, ms=6),
               Line2D([0], [0], marker="o", color=ARK, lw=1.4, ms=6, mfc=ARK),
               Line2D([0], [0], marker="s", color=ARK, lw=1.4, ls="--", ms=6, mfc=ARK)],
              ["Without prior volatility", "With prior volatility",
               "Whole filing", "Excluding Item 1A"], loc="lower right", fontsize=7.5, ncol=2)
    ax.grid(axis="x", alpha=.2)
    finalize_figure(fig, OUT / "fig4_volatility.png", formats=["png"], dpi=300)


# ---------------------------------------------------------------- Figure 5
def figure_5(d: dict) -> None:
    merged = d["returns"].merge(
        d["sections"][["accession", "group", "Negative_prop_total", "Negative_prop_body", "risk_found"]],
        on="accession", how="inner")
    merged = merged[merged.form.eq("10-Q") & merged.risk_found]
    fig, axes = create_subplots(1, 2, figsize=(WIDTH, 3.0), constrained_layout=True)
    for ax, (name, title) in zip(axes, [("ARK", "ARK holdings"), ("NDX", "Nasdaq-100")]):
        part = in_group(merged, name).copy()
        for measure, colour, ls, label in [("Negative_prop_total", ARK if name == "ARK" else NDX, "-", "Whole filing"),
                                           ("Negative_prop_body", ARK if name == "ARK" else NDX, "--", "Excluding Item 1A")]:
            part["q"] = pd.qcut(part[measure].rank(method="first"), 5, labels=False) + 1
            med = part.groupby("q").event_excess.median() * 100
            ax.plot(med.index, med.to_numpy(), color=colour, ls=ls, lw=1.6, marker="o", ms=3.4,
                    mfc="white" if ls == "--" else colour, label=label)
        ax.axhline(0, color=GREY, lw=.8)
        ax.set_xticks([1, 2, 3, 4, 5])
        ax.set_xticklabels(["Low", "2", "3", "4", "High"])
        ax.set_xlabel("Quintile of negative word share")
        ax.set_title(f"{title} ({len(part):,} quarterly reports)", loc="left", fontsize=9)
        ax.grid(axis="y", alpha=.2)
    axes[0].set_ylabel("Median four-session excess return (%)")
    axes[0].legend(fontsize=8, loc="lower left")
    lo = min(ax.get_ylim()[0] for ax in axes)
    hi = max(ax.get_ylim()[1] for ax in axes)
    for ax in axes:
        ax.set_ylim(lo, hi)
    finalize_figure(fig, OUT / "fig5_quintiles.png", formats=["png"], dpi=300)


# ---------------------------------------------------------------- Figure 6
def figure_6(d: dict) -> None:
    """Annual shares: quarterly cells are too thin in every first calendar quarter."""
    q = d["sections"]
    q = q[q.form.eq("10-Q") & q.risk_found].copy()
    q["year"] = q.quarter.str[:4]
    modes = ["full", "partial_update", "reference_only", "omitted"]
    names = ["Risk factors restated", "No material change, updates given",
             "No material change, reader referred to 10-K", "Nothing disclosed"]
    colours = [ARK, PALETTE["blue_secondary"], PALETTE["red_2"], PALETTE["neutral"]]
    years = sorted(q.year.unique())
    fig, axes = create_subplots(1, 2, figsize=(WIDTH, 3.0), constrained_layout=True)
    for ax, (name, title) in zip(axes, [("ARK", "ARK holdings"), ("NDX", "Nasdaq-100")]):
        part = in_group(q, name)
        shares = pd.crosstab(part.year, part.risk_mode, normalize="index").reindex(years)
        shares = shares.reindex(columns=modes).fillna(0) * 100
        counts = part.groupby("year").size().reindex(years)
        bottom = np.zeros(len(years))
        for mode, colour, label in zip(modes, colours, names):
            ax.bar(range(len(years)), shares[mode].to_numpy(), bottom=bottom, color=colour,
                   width=.72, edgecolor="white", lw=.5, label=label)
            bottom += shares[mode].to_numpy()
        for i, (y, n) in enumerate(zip(years, counts)):
            ax.text(i, 101, f"n={n}", ha="center", va="bottom", fontsize=6.5, color=GREY)
        ax.set_ylim(0, 108)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.set_xticks(range(len(years)))
        ax.set_xticklabels(years)
        ax.set_title(title, loc="left", fontsize=9)
    axes[0].set_ylabel("Share of quarterly reports (%)")
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=2,
               frameon=False, fontsize=7.5, bbox_to_anchor=(0.5, 1.16))
    finalize_figure(fig, OUT / "fig6_modes.png", formats=["png"], dpi=300)


# ---------------------------------------------------------------- Figure 7
def figure_7(d: dict) -> None:
    q = d["sections"]
    q = q[q.form.eq("10-Q") & q.risk_found]
    fig, axes = create_subplots(1, 2, figsize=(WIDTH, 3.0), constrained_layout=True)
    x = np.arange(len(QUARTERS))
    for ax, category in zip(axes, ["Negative", "Uncertainty"]):
        for name, colour in [("ARK", ARK), ("NDX", NDX)]:
            part = in_group(q, name)
            for scope, ls, marker in [("total", "-", "o"), ("body", "--", "s")]:
                series = centred_quarterly(part, f"{category}_prop_{scope}")
                ax.plot(x, series.to_numpy(), color=colour, ls=ls, lw=1.5, marker=marker, ms=2.6,
                        mfc="white" if ls == "--" else colour,
                        label=f"{'ARK holdings' if name == 'ARK' else 'Nasdaq-100'}, "
                              f"{'whole filing' if scope == 'total' else 'excluding Item 1A'}")
        ax.set_title(f"{category} words, 10-Q", loc="left", fontsize=9)
        ax.set_ylabel(f"{category} words (%)")
        quarter_labels(ax, step=4)
        ax.tick_params(axis="x", labelsize=7)
        ax.grid(axis="y", alpha=.2)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=2,
               frameon=False, fontsize=7.5, bbox_to_anchor=(0.5, 1.18))
    finalize_figure(fig, OUT / "fig7_whole_vs_body.png", formats=["png"], dpi=300)


# ---------------------------------------------------------------- Figure 8
def figure_8(d: dict) -> pd.DataFrame:
    panel = build_panel(d["sections"])
    q = panel[panel.form.eq("10-Q")]
    biggest_drop = q[q.transition.eq("to_reference")].nsmallest(1, "risk_words_change").iloc[0]
    biggest_rise = q[q.transition.eq("to_full")].nlargest(1, "risk_words_change").iloc[0]
    selected = pd.DataFrame([biggest_drop, biggest_rise])[
        ["ticker", "filing_date", "prev_risk_words", "risk_words", "risk_words_change", "transition"]]
    selected.to_csv(OUT / "fig8_selected.csv", index=False)

    fig, axes = create_subplots(1, 2, figsize=(WIDTH, 3.2), constrained_layout=True)
    for ax, event, caption in zip(axes, [biggest_drop, biggest_rise],
                                  ["Largest single-quarter fall in Item 1A words",
                                   "Largest single-quarter rise in Item 1A words"]):
        firm = d["sections"][(d["sections"].ticker.eq(event.ticker)) & d["sections"].form.eq("10-Q")
                             & d["sections"].risk_found].copy()
        firm["filing_date"] = pd.to_datetime(firm.filing_date)
        firm = firm.sort_values("filing_date")
        x = np.arange(len(firm))
        ax.bar(x, firm.risk_words / 1000, color="#C9D3E3", width=.72, edgecolor="none")
        ax.set_ylabel("Item 1A words (thousands)")
        ax.set_title(f"{event.ticker}: {caption}", loc="left", fontsize=9)
        twin = ax.twinx()
        twin.plot(x, 100 * firm.Uncertainty_prop_total, color=ARK, lw=1.6, marker="o", ms=3,
                  label="Whole filing")
        twin.plot(x, 100 * firm.Uncertainty_prop_body, color=ARK, lw=1.6, ls="--", marker="s", ms=3,
                  mfc="white", label="Excluding Item 1A")
        twin.set_ylabel("Uncertainty words (%)")
        twin.set_ylim(0, max(3.5, (100 * firm.Uncertainty_prop_total).max() * 1.2))
        twin.spines["top"].set_visible(False)
        labels = [f"{t.year} Q{t.quarter}" for t in firm.filing_date]
        ticks = list(range(0, len(firm), max(1, len(firm) // 5)))
        ax.set_xticks(ticks)
        ax.set_xticklabels([labels[i] for i in ticks], fontsize=7)
        if ax is axes[0]:
            twin.legend(fontsize=8, loc="upper right")
    finalize_figure(fig, OUT / "fig8_cases.png", formats=["png"], dpi=300)
    return selected


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    apply_publication_style(FigureStyle(font_size=9, axes_linewidth=1.0))
    d = load()
    figure_1(d)
    figure_2(d)
    figure_3(d)
    figure_4(d)
    figure_5(d)
    figure_6(d)
    figure_7(d)
    selected = figure_8(d)
    print("Figure 8 cases:")
    print(selected.to_string(index=False))
    print(f"\nWrote eight figures to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
