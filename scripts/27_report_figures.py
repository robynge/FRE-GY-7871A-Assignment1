"""Figures for the report body (1 and 2) and the appendix (B1 to B7), all from computed outputs.

Every figure except the two comparison figures (B6 and B7) describes the ARK
holdings alone. Conventions hold throughout: ARK holdings in blue, QQQ holdings
in red, the whole-filing measure as a solid line with filled circles and the
measure excluding Item 1A as a dashed line with hollow squares, shaded bands are
95% confidence intervals, the VIX sits in its own strip in grey.

    python scripts/27_report_figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path.home() / ".claude/skills/scientific-figure-pro/scripts"))
from scientific_figure_pro import (  # noqa: E402
    PALETTE, FigureStyle, apply_publication_style, create_subplots, finalize_figure,
)
from src.config import INTERIM_DIR, OUTPUT_DIR, PRICE_DIR, UNIVERSE_DIR, holdings_group  # noqa: E402
from src.disclosure import build_panel  # noqa: E402

OUT = OUTPUT_DIR / "report_figures"
ARK, QQQ, GREY = PALETTE["blue_main"], PALETTE["red_strong"], "#8C9195"
QUARTERS = pd.period_range("2021Q1", "2026Q3", freq="Q").astype(str).tolist()
YEARS = [q for q in QUARTERS if q.endswith("Q1")]
WIDTH = 7.2
RNG = np.random.default_rng(7)
GROUP_LABEL = {"ARK": "ARK holdings", "NDX": "QQQ holdings"}
GROUP_COLOUR = {"ARK": ARK, "NDX": QQQ}


# ------------------------------------------------------------------ helpers
def load() -> dict:
    universe = pd.read_csv(UNIVERSE_DIR / "universe.csv", dtype={"cik": str})
    group = {str(r.cik).zfill(10): holdings_group(r.funds) for r in universe.itertuples()}
    text = pd.read_csv(OUTPUT_DIR / "all" / "text_sample.csv", dtype={"cik": str})
    text["cik"] = text.cik.str.zfill(10)
    text["group"] = text.cik.map(group)
    # the section split describes the same filings as the tables
    sections = pd.read_csv(INTERIM_DIR / "risk_sections.csv", dtype={"cik": str})
    sections = sections[sections.accession.isin(text.accession)].copy()
    sections["cik"] = sections.cik.str.zfill(10)
    sections["group"] = sections.cik.map(group)
    returns = pd.read_csv(OUTPUT_DIR / "ark" / "return_sample.csv", dtype={"cik": str})
    vix = pd.read_csv(PRICE_DIR / "prices.csv", index_col=0, parse_dates=True)["^VIX"]
    vix = vix.groupby(vix.index.to_period("Q").astype(str)).mean().reindex(QUARTERS)
    return dict(sections=sections, text=text, returns=returns, vix=vix)


def in_group(frame: pd.DataFrame, name: str) -> pd.DataFrame:
    """ARK and QQQ holdings both include the 22 shared companies, as the portfolios do."""
    return frame[frame.group.isin([name, "BOTH"])]


def tidy(ax) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def year_axis(ax) -> None:
    ax.set_xticks([QUARTERS.index(y) for y in YEARS])
    ax.set_xticklabels([y[:4] for y in YEARS])
    ax.set_xticks(range(len(QUARTERS)), minor=True)
    ax.set_xlim(-0.5, len(QUARTERS) - 0.5)


def cells(frame: pd.DataFrame, measure: str, by: str) -> pd.DataFrame:
    """Company-centred mean, standard error and count by quarter or filing year, in pp.

    Each company's score less its own mean, plus the group mean, so entry and
    exit of companies do not move the series. Annual reports are keyed to the
    first quarter of their filing year, where most are filed.
    """
    data = frame.dropna(subset=[measure]).copy()
    data["adjusted"] = 100 * (data[measure] - data.groupby("cik")[measure].transform("mean")
                              + data[measure].mean())
    data["key"] = data.quarter.str[:4] + "Q1" if by == "year" else data.quarter
    out = data.groupby("key").adjusted.agg(["mean", "std", "size"])
    out["se"] = out["std"] / np.sqrt(out["size"])
    return out.reindex(QUARTERS)


def band_line(ax, table: pd.DataFrame, colour: str, ls="-", marker="o", hollow=False,
              label=None, lw=1.6) -> None:
    x = np.arange(len(QUARTERS))
    ok = table["mean"].notna().to_numpy()
    m, se = table["mean"].to_numpy(), table["se"].fillna(0).to_numpy()
    ax.fill_between(x[ok], (m - 1.96 * se)[ok], (m + 1.96 * se)[ok], color=colour, alpha=.13, lw=0)
    ax.plot(x[ok], m[ok], color=colour, ls=ls, lw=lw, marker=marker, ms=3,
            mfc="white" if hollow else colour, label=label)


# ------------------------------------------------- Figure 1: ARK series and VIX
def figure_1(d: dict) -> None:
    ark = in_group(d["text"], "ARK")
    fig = plt.figure(figsize=(WIDTH, 4.1), constrained_layout=True)
    grid = fig.add_gridspec(3, 2, height_ratios=[3, 3, 1.1])
    for row, measure in enumerate(["Negative_prop", "Uncertainty_prop"]):
        for col, form in enumerate(["10-K", "10-Q"]):
            ax = fig.add_subplot(grid[row, col])
            tidy(ax)
            part = ark[ark.form.eq(form)]
            band_line(ax, cells(part, measure, "year" if form == "10-K" else "quarter"), ARK)
            ax.set_title(f"{form}, by {'filing year' if form == '10-K' else 'quarter'}",
                         loc="left", fontsize=9)
            if col == 0:
                ax.set_ylabel(f"{measure.split('_')[0]} words (%)")
            year_axis(ax)
            ax.grid(axis="y", alpha=.2)
    vix = fig.add_subplot(grid[2, :])
    tidy(vix)
    vix.plot(np.arange(len(QUARTERS)), d["vix"].to_numpy(), color=GREY, lw=1.3)
    vix.set_ylabel("VIX")
    vix.set_ylim(10, 35)
    vix.set_yticks([10, 20, 30])
    vix.set_title("VIX, quarterly mean of daily closes", loc="left", fontsize=9)
    year_axis(vix)
    vix.grid(axis="y", alpha=.2)
    fig.legend([Line2D([0], [0], color=ARK, lw=1.6, marker="o", ms=3), Patch(facecolor=ARK, alpha=.13)],
               ["ARK holdings, company-centred mean", "95% confidence band"],
               loc="upper center", ncol=2, frameon=False, fontsize=8, bbox_to_anchor=(0.5, 1.04))
    finalize_figure(fig, OUT / "fig1_ark_series.png", formats=["png"], dpi=300)


# ---------------------------------------------------- Figure 2: two ARK cases
def figure_2(d: dict) -> pd.DataFrame:
    sections = in_group(d["sections"], "ARK")
    panel = build_panel(sections)
    q = panel[panel.form.eq("10-Q")]
    biggest_drop = q[q.transition.eq("to_reference")].nsmallest(1, "risk_words_change").iloc[0]
    biggest_rise = q[q.transition.eq("to_full")].nlargest(1, "risk_words_change").iloc[0]
    selected = pd.DataFrame([biggest_drop, biggest_rise])[
        ["ticker", "filing_date", "prev_risk_words", "risk_words", "risk_words_change", "transition"]]
    selected.to_csv(OUT / "fig2_selected.csv", index=False)

    fig, axes = create_subplots(1, 2, figsize=(WIDTH, 2.7), constrained_layout=True)
    for ax, event, caption, note in zip(
            axes, [biggest_drop, biggest_rise],
            ["Largest single-quarter fall in Item 1A words", "Largest single-quarter rise in Item 1A words"],
            ["stops restating", "restates again"]):
        firm = sections[sections.ticker.eq(event.ticker) & sections.form.eq("10-Q") & sections.risk_found].copy()
        firm["filing_date"] = pd.to_datetime(firm.filing_date)
        firm = firm.sort_values("filing_date").reset_index(drop=True)
        x = np.arange(len(firm))
        ax.bar(x, firm.risk_words / 1000, color="#C9D3E3", width=.72, edgecolor="none")
        ax.set_ylabel("Item 1A words (thousands)")
        ax.set_title(f"{event.ticker}: {caption}", loc="left", fontsize=9)
        twin = ax.twinx()
        twin.plot(x, 100 * firm.Uncertainty_prop_total, color=ARK, lw=1.5, marker="o", ms=2.6, label="Whole filing")
        twin.plot(x, 100 * firm.Uncertainty_prop_body, color=ARK, lw=1.5, ls=(0, (3, 2)), marker="s", ms=2.6,
                  mfc="white", label="Excluding Item 1A")
        twin.set_ylabel("Uncertainty words (%)")
        top = max(3.5, (100 * firm.Uncertainty_prop_total).max() * 1.25)
        twin.set_ylim(0, top)
        twin.spines["top"].set_visible(False)
        i = int(firm.index[firm.filing_date.eq(pd.Timestamp(event.filing_date))][0])
        twin.annotate(note, xy=(i, 100 * firm.Uncertainty_prop_total.iloc[i]), xytext=(i, top * .93),
                      ha="center", fontsize=7, color=ARK,
                      arrowprops=dict(arrowstyle="-", color=ARK, lw=.8))
        years = firm.filing_date.dt.year
        ticks = [j for j in range(len(firm)) if j == 0 or years.iloc[j] != years.iloc[j - 1]]
        ticks = [j for k, j in enumerate(ticks) if k == len(ticks) - 1 or ticks[k + 1] - j >= 2]
        ax.set_xticks(ticks)
        ax.set_xticklabels([str(years.iloc[j]) for j in ticks], fontsize=7)
        if ax is axes[0]:
            twin.legend(fontsize=7.5, loc="center right")
    finalize_figure(fig, OUT / "fig2_cases.png", formats=["png"], dpi=300)
    return selected


# --------------------------- Figure B7: company-level distributions, disjoint groups
def figure_b7(d: dict) -> None:
    k = d["sections"]
    k = k[k.form.eq("10-K") & k.risk_found & k.group.isin(["ARK", "NDX"])]
    means = k.groupby(["cik", "group"])[["Negative_prop_total", "Negative_prop_body",
                                          "Uncertainty_prop_total", "Uncertainty_prop_body"]].mean().reset_index()
    fig, axes = create_subplots(1, 2, figsize=(WIDTH, 2.6), constrained_layout=True)
    for ax, category in zip(axes, ["Negative", "Uncertainty"]):
        data, positions, colours = [], [], []
        for offset, scope in [(0, "total"), (3, "body")]:
            for shift, name in enumerate(["ARK", "NDX"]):
                values = 100 * means.loc[means.group.eq(name), f"{category}_prop_{scope}"].to_numpy()
                data.append(values)
                positions.append(offset + shift)
                colours.append(GROUP_COLOUR[name])
                ax.scatter(offset + shift + RNG.uniform(-.22, .22, len(values)), values, s=5,
                           color=GROUP_COLOUR[name], alpha=.45, lw=0, zorder=2)
        boxes = ax.boxplot(data, positions=positions, widths=.7, patch_artist=True,
                           showfliers=False, medianprops=dict(color="black", lw=1.2),
                           whiskerprops=dict(lw=.9), capprops=dict(lw=.9), zorder=3)
        for patch, colour in zip(boxes["boxes"], colours):
            patch.set_facecolor(colour)
            patch.set_alpha(.35)
            patch.set_edgecolor("black")
            patch.set_linewidth(.6)
        ax.set_xticks([0.5, 3.5])
        ax.set_xticklabels(["Whole filing", "Excluding Item 1A"])
        ax.set_ylabel(f"{category} words, company mean (%)")
        ax.set_title(category, loc="left", fontsize=9)
        ax.grid(axis="y", alpha=.2)
    fig.legend([Patch(facecolor=ARK, alpha=.5, edgecolor="black"), Patch(facecolor=QQQ, alpha=.5, edgecolor="black")],
               [f"ARK only ({means.group.eq('ARK').sum()} companies)",
                f"QQQ only ({means.group.eq('NDX').sum()} companies)"], loc="upper center", ncol=2,
               frameon=False, fontsize=8, bbox_to_anchor=(0.5, 1.07))
    finalize_figure(fig, OUT / "figB7_distributions.png", formats=["png"], dpi=300)


# ------------------------------ Figure B1: ARK 10-Q, whole filing vs excluding
def figure_b1(d: dict) -> None:
    q = in_group(d["sections"], "ARK")
    q = q[q.form.eq("10-Q") & q.risk_found]
    fig, axes = create_subplots(1, 2, figsize=(WIDTH, 3.0), constrained_layout=True)
    for ax, category in zip(axes, ["Negative", "Uncertainty"]):
        for scope, ls, marker, hollow, label in [("total", "-", "o", False, "Whole filing"),
                                                ("body", "--", "s", True, "Excluding Item 1A")]:
            table = cells(q, f"{category}_prop_{scope}", "quarter")
            base = table.loc[[k for k in QUARTERS if k.startswith("2021")]].dropna(subset=["mean"])
            table = table.assign(mean=table["mean"] - np.average(base["mean"], weights=base["size"]))
            band_line(ax, table, ARK, ls=ls, marker=marker, hollow=hollow, label=label)
        ax.axhline(0, color=GREY, lw=.8)
        ax.set_title(f"{category} words, 10-Q", loc="left", fontsize=9)
        ax.set_ylabel("Change since 2021 (pp)")
        year_axis(ax)
        ax.grid(axis="y", alpha=.2)
    axes[0].legend(fontsize=8, loc="upper left")
    finalize_figure(fig, OUT / "figB1_ark_whole_vs_body.png", formats=["png"], dpi=300)


# -------------------------------------------- Figure B2: ARK company ranking
def firm_level(d: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Latest annual-report level and within-company slope, uncertainty excluding Item 1A."""
    k = in_group(d["sections"], "ARK")
    k = k[k.form.eq("10-K") & k.risk_found].copy()
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


def figure_b2(d: dict) -> None:
    latest, slopes = firm_level(d)
    latest.to_csv(OUT / "figB2_levels.csv", index=False)
    slopes.to_csv(OUT / "figB2_slopes.csv", index=False)
    fig, axes = create_subplots(1, 2, figsize=(WIDTH, 5.4), constrained_layout=True)

    ranked = latest.sort_values("level")
    show = pd.concat([ranked.head(15), ranked.tail(15)])
    y = np.arange(len(show))
    median = latest.level.median()
    axes[0].hlines(y, median, show.level, color="#D9D9D9", lw=1)
    axes[0].scatter(show.level, y, color=ARK, s=18, zorder=3, edgecolor="black", lw=.4)
    axes[0].axvline(median, color=GREY, lw=1, ls="--")
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(show.ticker, fontsize=7)
    axes[0].set_xlabel("Uncertainty words excluding Item 1A, latest annual report (%)")
    axes[0].set_title("Level: 15 lowest and 15 highest", loc="left", fontsize=9)
    axes[0].text(median, len(show) - .2, " median", color=GREY, fontsize=7, va="bottom")
    axes[0].axhline(14.5, color=GREY, lw=.8, ls=":")
    axes[0].text(axes[0].get_xlim()[0] + .01, 14.5,
                 f" {len(latest) - len(show)} companies between the two groups not shown",
                 fontsize=6.5, color=GREY, va="center", ha="left",
                 bbox=dict(facecolor="white", edgecolor="none", pad=1))

    ranked = slopes.sort_values("slope")
    show = pd.concat([ranked.head(10), ranked.tail(10)])
    y = np.arange(len(show))
    axes[1].hlines(y, 0, show.slope, color="#D9D9D9", lw=1)
    axes[1].scatter(show.slope, y, color=ARK, s=18, zorder=3, edgecolor="black", lw=.4)
    axes[1].axvline(0, color=GREY, lw=1)
    axes[1].set_yticks(y)
    axes[1].set_yticklabels([f"{t} ({n})" for t, n in zip(show.ticker, show.n)], fontsize=7)
    axes[1].set_xlabel("Change per year, 2021 to 2026 (pp)")
    axes[1].set_title("Trend: 10 largest falls and 10 largest rises", loc="left", fontsize=9)
    axes[1].axhline(9.5, color=GREY, lw=.8, ls=":")
    for ax in axes:
        ax.grid(axis="x", alpha=.2)
        ax.tick_params(axis="x", labelsize=8)
    finalize_figure(fig, OUT / "figB2_ark_firms.png", formats=["png"], dpi=300)


# ----------------------------------- Figure B3: ARK uncertainty and volatility
def figure_b3(d: dict) -> None:
    rows = pd.read_csv(OUTPUT_DIR / "ark" / "disclosure" / "switch_regressions.csv")
    rows = rows[rows.measure.isin(["Uncertainty_prop_total", "Uncertainty_prop_body"])
                & rows.model.str.startswith("volatility") & rows.status.eq("ok")].copy()
    scale = rows.effect_1sd / rows.coef
    rows["lo"], rows["hi"] = 100 * rows.ci_low * scale, 100 * rows.ci_high * scale
    rows["effect"] = 100 * rows.effect_1sd
    order = [("10-Q", "Uncertainty_prop_total"), ("10-Q", "Uncertainty_prop_body"),
             ("All", "Uncertainty_prop_total"), ("All", "Uncertainty_prop_body")]
    labels = {("10-Q", "Uncertainty_prop_total"): "10-Q, whole filing",
              ("10-Q", "Uncertainty_prop_body"): "10-Q, excluding Item 1A",
              ("All", "Uncertainty_prop_total"): "All, whole filing",
              ("All", "Uncertainty_prop_body"): "All, excluding Item 1A"}
    fig, axes = create_subplots(1, 1, figsize=(WIDTH, 3.0), constrained_layout=True)
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
    fig.legend([Line2D([0], [0], marker="o", color=ARK, mfc="white", lw=0, ms=6),
                Line2D([0], [0], marker="o", color=ARK, mfc=ARK, lw=0, ms=6),
                Line2D([0], [0], marker="o", color=ARK, lw=1.4, ms=6, mfc=ARK),
                Line2D([0], [0], marker="s", color=ARK, lw=1.4, ls="--", ms=6, mfc=ARK)],
               ["Without prior volatility", "With prior volatility", "Whole filing", "Excluding Item 1A"],
               loc="upper center", ncol=4, frameon=False, fontsize=7.5, bbox_to_anchor=(0.5, 1.05))
    ax.grid(axis="x", alpha=.2)
    finalize_figure(fig, OUT / "figB3_ark_volatility.png", formats=["png"], dpi=300)


# -------------------------------------- Figure B4: ARK return by tone quintile
def figure_b4(d: dict) -> None:
    merged = d["returns"].merge(
        d["sections"][["accession", "Negative_prop_total", "Negative_prop_body", "risk_found"]],
        on="accession", how="inner")
    part = merged[merged.form.eq("10-Q") & merged.risk_found].copy()
    fig, axes = create_subplots(1, 1, figsize=(WIDTH * .6, 3.0), constrained_layout=True)
    ax = axes[0]
    for measure, ls, marker, hollow, label, dx in [
            ("Negative_prop_total", "-", "o", False, "Whole filing", -.06),
            ("Negative_prop_body", "--", "s", True, "Excluding Item 1A", .06)]:
        part["q"] = pd.qcut(part[measure].rank(method="first"), 5, labels=False) + 1
        medians, lo, hi = [], [], []
        for k in range(1, 6):
            v = 100 * part.loc[part.q.eq(k), "event_excess"].to_numpy()
            boots = np.median(RNG.choice(v, size=(2000, len(v)), replace=True), axis=1)
            medians.append(np.median(v))
            lo.append(np.percentile(boots, 2.5))
            hi.append(np.percentile(boots, 97.5))
        medians, lo, hi = map(np.array, (medians, lo, hi))
        ax.errorbar(np.arange(1, 6) + dx, medians, yerr=[medians - lo, hi - medians], color=ARK,
                    ls=ls, lw=1.5, marker=marker, ms=3.8, mfc="white" if hollow else ARK,
                    capsize=2, elinewidth=.9, label=label)
    ax.axhline(0, color=GREY, lw=.8)
    ax.set_xticks([1, 2, 3, 4, 5])
    ax.set_xticklabels(["Low", "2", "3", "4", "High"])
    ax.set_xlabel("Quintile of negative word share")
    ax.set_ylabel("Median four-session excess return (%)")
    ax.set_title(f"ARK holdings, {len(part):,} quarterly reports", loc="left", fontsize=9)
    ax.legend(fontsize=8, loc="lower left")
    ax.grid(axis="y", alpha=.2)
    finalize_figure(fig, OUT / "figB4_ark_quintiles.png", formats=["png"], dpi=300)


# --------------------------------------- Figure B5: ARK disclosure modes by year
def figure_b5(d: dict) -> None:
    q = in_group(d["sections"], "ARK")
    q = q[q.form.eq("10-Q") & q.risk_found].copy()
    q["year"] = q.quarter.str[:4]
    modes = ["full", "partial_update", "reference_only", "omitted"]
    names = ["Risk factors restated", "No material change, updates given",
             "No material change, reader referred to the annual report", "Nothing disclosed"]
    colours = [ARK, PALETTE["blue_secondary"], PALETTE["red_2"], PALETTE["neutral"]]
    years = sorted(q.year.unique())
    shares = pd.crosstab(q.year, q.risk_mode, normalize="index").reindex(years)
    shares = shares.reindex(columns=modes).fillna(0) * 100
    counts = q.groupby("year").size().reindex(years)
    fig, axes = create_subplots(1, 1, figsize=(WIDTH * .62, 3.1), constrained_layout=True)
    ax = axes[0]
    bottom = np.zeros(len(years))
    for mode, colour, label in zip(modes, colours, names):
        values = shares[mode].to_numpy()
        ax.bar(range(len(years)), values, bottom=bottom, color=colour, width=.72,
               edgecolor="white", lw=.5, label=label)
        if mode in ("full", "reference_only"):
            for i, (v, b) in enumerate(zip(values, bottom)):
                ax.text(i, b + v / 2, f"{v:.0f}%", ha="center", va="center", fontsize=7,
                        color="white" if mode == "full" else "black")
        bottom += values
    for i, n in enumerate(counts):
        ax.text(i, 101, f"n={n}", ha="center", va="bottom", fontsize=6.5, color=GREY)
    ax.set_ylim(0, 108)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_xticks(range(len(years)))
    ax.set_xticklabels(years)
    ax.set_ylabel("Share of quarterly reports (%)")
    ax.set_title("ARK holdings", loc="left", fontsize=9)
    fig.legend(*ax.get_legend_handles_labels(), loc="upper center", ncol=1, frameon=False,
               fontsize=7.5, bbox_to_anchor=(0.5, 1.30))
    finalize_figure(fig, OUT / "figB5_ark_modes.png", formats=["png"], dpi=300)


# ------------------------------------ Figure B6: ARK and QQQ holdings, the series
def figure_b6(d: dict) -> None:
    fig, axes = create_subplots(2, 2, figsize=(WIDTH, 4.6), constrained_layout=True)
    panels = [("Negative_prop", "10-K"), ("Negative_prop", "10-Q"),
              ("Uncertainty_prop", "10-K"), ("Uncertainty_prop", "10-Q")]
    for ax, (measure, form) in zip(axes, panels):
        part = d["text"][d["text"].form.eq(form)]
        for name in ["ARK", "NDX"]:
            band_line(ax, cells(in_group(part, name), measure, "year" if form == "10-K" else "quarter"),
                      GROUP_COLOUR[name], label=GROUP_LABEL[name])
        ax.set_title(f"{form}, by {'filing year' if form == '10-K' else 'quarter'}", loc="left", fontsize=9)
        if form == "10-K":
            ax.set_ylabel(f"{measure.split('_')[0]} words (%)")
        year_axis(ax)
        ax.grid(axis="y", alpha=.2)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles + [Patch(facecolor=GREY, alpha=.25)], labels + ["95% confidence band"],
               loc="upper center", ncol=3, frameon=False, fontsize=8, bbox_to_anchor=(0.5, 1.04))
    finalize_figure(fig, OUT / "figB6_groups_series.png", formats=["png"], dpi=300)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob("*"):
        stale.unlink()
    apply_publication_style(FigureStyle(font_size=9, axes_linewidth=1.0))
    d = load()
    figure_1(d)
    selected = figure_2(d)
    figure_b1(d)
    figure_b2(d)
    figure_b3(d)
    figure_b4(d)
    figure_b5(d)
    figure_b6(d)
    figure_b7(d)
    print("Figure 2 cases:")
    print(selected.to_string(index=False))
    print(f"\nWrote the figures to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
