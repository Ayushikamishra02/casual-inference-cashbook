"""Figures for the README and lessons."""
from __future__ import annotations

import matplotlib
import matplotlib.ticker

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

BLUE, ORANGE, GREEN, RED, PURPLE, GREY = "#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3", "#8C8C8C"
plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 140, "savefig.bbox": "tight", "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25, "font.size": 10, "axes.titlesize": 11,
    "axes.titleweight": "bold", "legend.frameon": False,
})


# ------------------------------------------------------------------------------------------- minimum wage
def min_wage_did(table: pd.DataFrame, w: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    ax = axes[0]
    x = [0, 1]
    nj, pa = table.loc["NJ"], table.loc["PA"]
    ax.plot(x, [pa.before, pa.after], "-o", color=ORANGE, lw=2, label="Pennsylvania (control)")
    ax.plot(x, [nj.before, nj.after], "-o", color=BLUE, lw=2, label="New Jersey (treated)")
    cf = nj.before + (pa.after - pa.before)
    ax.plot(x, [nj.before, cf], "--", color=BLUE, alpha=0.6, label="NJ if it had followed PA's trend")
    ax.annotate("", xy=(1.03, nj.after), xytext=(1.03, cf), arrowprops={"arrowstyle": "<->", "color": RED})
    ax.text(1.06, (nj.after + cf) / 2, f"DiD\n+{nj.after - cf:.2f}\nFTE", color=RED, va="center")
    ax.set_xticks(x, ["Feb 1992\n(before)", "Nov 1992\n(after NJ's increase)"])
    ax.set_xlim(-0.2, 1.35)
    ax.set(ylabel="full-time-equivalent employees per store",
           title="Employment did not fall in New Jersey relative to Pennsylvania")
    ax.legend(loc="upper right", fontsize=8)
    ax = axes[1]
    bins = np.arange(4.2, 5.65, 0.1)
    for st, c in [("NJ", BLUE), ("PA", ORANGE)]:
        for when, alpha in [("before", 0.35), ("after", 0.9)]:
            v = w.loc[w.state == st, f"wage_{when}"].dropna()
            h, _ = np.histogram(v, bins=bins)
            ax.step(bins[:-1] + 0.05, h / h.sum(), where="mid", color=c, alpha=alpha, lw=2,
                    label=f"{st} {when}")
    ax.axvline(5.05, color=RED, ls=":", lw=1)
    ax.text(5.03, ax.get_ylim()[1] * 0.92, "new NJ minimum $5.05 ", color=RED, fontsize=8, ha="right")
    ax.set(xlabel="starting wage ($/hour)", ylabel="share of stores",
           title="The treatment happened: NJ wages piled up at the new minimum")
    ax.legend(fontsize=8)
    fig.tight_layout()
    return fig


def forest(df: pd.DataFrame, title: str, xlabel: str, highlight: str = "PLACEBO", ref: float = 0.0):
    df = df.iloc[::-1].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(8.5, 0.42 * len(df) + 1.2))
    for i, r in df.iterrows():
        c = GREY if highlight in r.label else BLUE
        ax.errorbar(r.effect, i, xerr=[[r.effect - r.ci_low], [r.ci_high - r.effect]], fmt="o", color=c, capsize=3)
        ax.text(r.ci_high, i + 0.18, f" {r.effect:.2f}", fontsize=8, color=c)
    ax.axvline(ref, color="k", lw=1)
    ax.set_yticks(range(len(df)), df.label)
    ax.set(xlabel=xlabel, title=title)
    return fig


# ------------------------------------------------------------------------------------------- organ donation
def organ(d: pd.DataFrame, es: pd.DataFrame, perm: dict):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    q = d.groupby(["t", "quarter"]).size().reset_index()[["t", "quarter"]]
    ax = axes[0]
    ca = d[d.california == 1].set_index("t").rate
    oth = d[d.california == 0].groupby("t").rate.mean()
    ax.plot(ca.index, ca, "-o", color=BLUE, label="California")
    ax.plot(oth.index, oth, "-o", color=ORANGE, label="average of 26 other states")
    ax.axvline(3.5, color=RED, ls=":")
    ax.text(3.55, 0.36, "active choice\nstarts (Jul 2011)", color=RED, fontsize=8)
    ax.set_xticks(q.t, q.quarter, rotation=30)
    ax.set(ylabel="share of people registered as organ donors", title="Raw trends")
    ax.legend(fontsize=8)
    ax = axes[1]
    ax.errorbar(es.rel_time, es.coef, yerr=1.96 * es.se, fmt="o", color=PURPLE, capsize=3)
    ax.axhline(0, color="k", lw=1)
    ax.axvline(-0.5, color=RED, ls=":")
    ax.set(xlabel="quarters relative to policy (0 = Q3 2011; -1 is the reference)",
           ylabel="effect on registration rate", title="Event study: small pre-period wobble, drop after")
    ax = axes[2]
    pe = perm["placebo_effects"]
    ax.hist(pe, bins=15, color=GREY, alpha=0.7, label="26 placebo 'treated' states")
    ax.axvline(perm["effect"], color=BLUE, lw=2, label=f"California {perm['effect']:.3f}")
    ax.axvline(-perm["effect"], color=BLUE, lw=1, ls="--")
    ax.set(xlabel="DiD estimate if this state had been 'treated'", ylabel="states",
           title=f"Permutation test: p = {perm['p_value']:.2f}")
    ax.legend(fontsize=8)
    fig.tight_layout()
    return fig


# ------------------------------------------------------------------------------------------- job training
def overlap(ps: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(8, 3.8))
    bins = np.linspace(0, 1, 41)
    ax.hist(ps.loc[ps.treat == 0, "ps"], bins=bins, color=ORANGE, alpha=0.7, label="CPS comparison group")
    ax.hist(ps.loc[ps.treat == 1, "ps"], bins=bins, color=BLUE, alpha=0.8, label="NSW participants")
    ax.set_yscale("log")
    ax.set(xlabel="propensity score: estimated probability of being in the programme",
           ylabel="people (log scale)", title="Overlap: most CPS people look nothing like participants")
    ax.legend()
    return fig


def lalonde_estimates(est: pd.DataFrame, bench: dict, raw_naive: float, no_earn: pd.Series):
    order = list(est.index)
    fig, ax = plt.subplots(figsize=(9.5, 5))
    y = np.arange(len(order))[::-1]
    ax.axvspan(bench["difference"] - 1.96 * bench["difference_se"], bench["difference"] + 1.96 * bench["difference_se"],
               color=GREEN, alpha=0.12)
    ax.axvline(bench["difference"], color=GREEN, lw=2, label=f"experimental answer ${bench['difference']:,.0f}")
    for yy, k in zip(y, order):
        r = est.loc[k]
        ax.errorbar(r.estimate, yy, xerr=[[r.estimate - r.ci_low], [r.ci_high - r.estimate]] if "ci_low" in r else None,
                    fmt="o", color=BLUE, capsize=3)
        ax.plot(no_earn[k], yy - 0.25, "x", color=RED, ms=7)
    ax.plot([], [], "o", color=BLUE, label="with pre-programme earnings (95% bootstrap CI)")
    ax.plot([], [], "x", color=RED, label="WITHOUT pre-programme earnings")
    ax.axvline(0, color="k", lw=0.8)
    ax.set_yticks(y, order)
    ax.set(xlabel="estimated effect on 1978 earnings ($)",
           title=f"Recovering an experiment from survey data (raw gap before any adjustment: -${-raw_naive:,.0f})")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3, fontsize=8)
    return fig


def love_plot(bal: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    y = np.arange(len(bal))
    styles = [("before (all CPS)", "o", RED), ("after IPW", "s", BLUE), ("after 5-NN matching", "^", PURPLE)]
    for col, m, c in styles:
        ax.scatter(bal[col].abs(), y, marker=m, color=c, label=col, zorder=3)
    ax.axvline(0.1, color="k", ls=":", lw=1)
    ax.text(0.11, len(bal) - 0.6, "0.1 rule of thumb", fontsize=8)
    ax.set_yticks(y, bal.index)
    ax.set(xlabel="|standardised mean difference| (participants vs comparison)",
           title="Covariate balance: weighting/matching makes the groups comparable")
    ax.legend(fontsize=8, loc="upper left", bbox_to_anchor=(1.01, 1))
    return fig


# ------------------------------------------------------------------------------------------- Prop 99
def prop99_main(res, dv: pd.DataFrame):
    p = res.path
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.3))
    ax = axes[0]
    ax.plot(p.year, p.treated, color="k", lw=2, label="California")
    ax.plot(p.year, p.synthetic, "--", color=BLUE, lw=2, label="synthetic California")
    ax.plot(dv.year, dv["average of others"], ":", color=ORANGE, lw=2, label="average of 38 other states")
    ax.axvline(1988.5, color=RED, ls=":")
    ax.text(1989, 125, "Proposition 99", color=RED)
    ax.set(ylabel="cigarette packs sold per person per year", title="California vs its synthetic twin")
    ax.legend(fontsize=8)
    ax = axes[1]
    wts = res.weights[res.weights > 0.001]
    ax.bar(wts.index, wts.values, color=BLUE)
    for i, v in enumerate(wts.values):
        ax.text(i, v + 0.01, f"{v:.2f}", ha="center", fontsize=9)
    ax.set(ylabel="weight in synthetic California",
           title=f"Synthetic California = {len(wts)} states (the other {len(res.weights) - len(wts)} get 0)")
    fig.tight_layout()
    return fig


def prop99_placebos(placebos: pd.DataFrame, max_pre_ratio: float = 5.0):
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.3))
    ax = axes[0]
    tr_pre = placebos.loc[placebos.is_treated, "pre_rmspe"].iloc[0]
    for _, r in placebos.iterrows():
        if r.is_treated or r.pre_rmspe ** 2 > max_pre_ratio * tr_pre ** 2:
            continue
        ax.plot(r.path.year, r.path.gap, color=GREY, alpha=0.5, lw=1)
    ca = placebos.loc[placebos.is_treated, "path"].iloc[0]
    ax.plot(ca.year, ca.gap, color="k", lw=2.5, label="California")
    ax.plot([], [], color=GREY, label=f"placebo states (pre-fit < {max_pre_ratio:g}x CA's)")
    ax.axhline(0, color="k", lw=0.8)
    ax.axvline(1988.5, color=RED, ls=":")
    ax.set(ylabel="gap: actual - synthetic (packs per person)", title="In-space placebos: California is an outlier")
    ax.legend(fontsize=8, loc="lower left")
    ax = axes[1]
    p = placebos.sort_values("ratio")
    ax.barh(p.unit, p.ratio, color=[BLUE if t else GREY for t in p.is_treated])
    ax.set(xlabel="post / pre-period RMSPE", title="California ranks 1st of 39 (p = 1/39 = 0.026)")
    ax.tick_params(axis="y", labelsize=6.5)
    fig.tight_layout()
    return fig


def prop99_robustness(res, loo: pd.DataFrame, in_time):
    fig, axes = plt.subplots(1, 2, figsize=(13, 4))
    ax = axes[0]
    for _, r in loo.iterrows():
        ax.plot(r.path.year, r.path.gap, color=GREY, lw=1)
    ax.plot(res.path.year, res.path.gap, color="k", lw=2, label="all donors")
    ax.plot([], [], color=GREY, label="dropping one donor at a time")
    ax.axhline(0, color="k", lw=0.8)
    ax.axvline(1988.5, color=RED, ls=":")
    ax.set(ylabel="gap (packs per person)", title="Leave-one-out: no single donor drives the result")
    ax.legend(fontsize=8)
    ax = axes[1]
    p = in_time.path
    ax.plot(p.year, p.treated, color="k", lw=2, label="California")
    ax.plot(p.year, p.synthetic, "--", color=BLUE, lw=2, label="synthetic (fit on 1970-79)")
    ax.axvline(1979.5, color=GREY, ls=":")
    ax.text(1979.7, p.treated.max() * 0.98, "fake 1980 'law'", color=GREY, fontsize=8)
    gap = p[p.year >= 1980].gap.mean()
    ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    ax.set(title=f"In-time placebo: fake 1980 law, average gap {gap:.1f} (real law: about -19)",
           ylabel="packs per person")
    ax.legend(fontsize=8)
    fig.tight_layout()
    return fig


# ------------------------------------------------------------------------------------------- simulations
def simulations(sims: dict):
    fig, axes = plt.subplots(1, 3, figsize=(15, 3.8))
    ax = axes[0]
    d = sims["did"]
    ax.bar(d.index, d.mean_did, color=[GREEN, RED])
    ax.axhline(2.0, color="k", ls="--", lw=1)
    ax.text(0.5, 2.08, "true effect = 2", fontsize=8, ha="center")
    for i, (v, c) in enumerate(zip(d.mean_did, d.coverage)):
        ax.text(i, v / 2, f"mean {v:.2f}\n95% CI covers\nthe truth {c:.0%}", ha="center", fontsize=8,
                color="white", fontweight="bold")
    ax.set(title="DiD: unbiased only if trends are parallel", ylabel="average estimate")
    ax = axes[1]
    m = sims["matching"].sort_values("rmse")
    ax.barh(m.index, m.bias, color=[GREEN if abs(b) < 100 else RED for b in m.bias])
    for i, b in enumerate(m.bias):
        ax.text(b if b > 0 else 0, i, f"  {b:+,.0f}", va="center", fontsize=8)
    ax.axvline(0, color="k", lw=1)
    ax.set_xlim(m.bias.min() * 1.05, max(m.bias.max(), 0) + 1500)
    ax.set(xlabel="bias (true ATT = 1,000)", title="Selection on observables (known confounding)")
    ax = axes[2]
    s = sims["synth"]
    ax.bar(s.index, s.rmse, color=[GREEN, ORANGE])
    ax.set(ylabel="RMSE (true effect = -10)", title="Factor model: synth beats a plain average")
    fig.tight_layout()
    return fig
