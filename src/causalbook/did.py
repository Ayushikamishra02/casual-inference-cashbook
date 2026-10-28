"""Difference-in-differences (DiD): two-group/two-period tables, regression DiD, event studies and placebo /
permutation inference.

The idea: the treated group's change over time, minus the control group's change over the same time. The control
group's change stands in for what *would* have happened to the treated group without treatment (the "parallel
trends" assumption).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


@dataclass
class Estimate:
    effect: float
    se: float
    n: int
    label: str = ""

    @property
    def ci(self) -> tuple[float, float]:
        return self.effect - 1.96 * self.se, self.effect + 1.96 * self.se

    @property
    def p_value(self) -> float:
        from scipy import stats

        return float(2 * stats.norm.sf(abs(self.effect / self.se))) if self.se > 0 else float("nan")

    def as_dict(self) -> dict:
        lo, hi = self.ci
        return {"label": self.label, "effect": self.effect, "se": self.se, "ci_low": lo, "ci_high": hi,
                "p_value": self.p_value, "n": self.n}


def _mean_se(x: pd.Series) -> tuple[float, float, int]:
    x = x.dropna()
    return float(x.mean()), float(x.std(ddof=1) / np.sqrt(len(x))), len(x)


def did_table(wide: pd.DataFrame, group: str, before: str, after: str, labels=("control", "treated")) -> pd.DataFrame:
    """The classic 2x2 table: mean (SE) before and after, per group, and the difference of differences.
    Uses every available observation in each cell, like Card & Krueger's Table 3 row 3."""
    rows = {}
    for g, name in zip((0, 1), labels):
        d = wide[wide[group] == g]
        b, sb, nb = _mean_se(d[before])
        a, sa, na = _mean_se(d[after])
        # SE of the change uses stores observed in both waves (paired), as in the paper
        both = d[[before, after]].dropna()
        ch, sch, _ = _mean_se(both[after] - both[before])
        rows[name] = {"before": b, "before_se": sb, "after": a, "after_se": sa, "change": a - b, "change_se": sch,
                      "n_before": nb, "n_after": na}
    t = pd.DataFrame(rows).T
    diff = t.loc[labels[1]] - t.loc[labels[0]]
    diff[["before_se", "after_se", "change_se"]] = np.sqrt(t.loc[labels[1], ["before_se", "after_se", "change_se"]] ** 2
                                                           + t.loc[labels[0], ["before_se", "after_se", "change_se"]] ** 2)
    diff[["n_before", "n_after"]] = np.nan
    t.loc[f"{labels[1]} - {labels[0]}"] = diff
    return t


def did_regression(long: pd.DataFrame, y: str, treat: str, post: str, cluster: str, controls: str = "",
                   label: str = "") -> Estimate:
    """y = a + b*treat + c*post + DiD*(treat x post) [+ controls], SEs clustered by unit."""
    d = long.dropna(subset=[y])
    f = f"{y} ~ {treat} * {post}" + (f" + {controls}" if controls else "")
    m = smf.ols(f, data=d).fit(cov_type="cluster", cov_kwds={"groups": d[cluster]})
    k = f"{treat}:{post}"
    return Estimate(float(m.params[k]), float(m.bse[k]), int(m.nobs), label or f"{y}: regression DiD")


def first_difference(wide: pd.DataFrame, before: str, after: str, regressor: str, controls: str = "",
                     label: str = "", cov_type: str = "nonrobust") -> Estimate:
    """Regress the change (after - before) on the treatment indicator or intensity, one row per unit
    (Card & Krueger Table 4). Equivalent to unit fixed effects with two periods. `cov_type="nonrobust"`
    reproduces the paper's standard errors; use "HC1" for heteroskedasticity-robust ones."""
    d = wide.assign(_change=wide[after] - wide[before]).dropna(subset=["_change", regressor])
    m = smf.ols(f"_change ~ {regressor}" + (f" + {controls}" if controls else ""), data=d).fit(cov_type=cov_type)
    return Estimate(float(m.params[regressor]), float(m.bse[regressor]), int(m.nobs), label)


def twfe(panel: pd.DataFrame, y: str, unit: str, time: str, treated: str, label: str = "") -> Estimate:
    """Two-way fixed effects: y = unit FE + time FE + DiD * treated_now. SEs clustered by unit.
    Fine for one treatment date (as here); with staggered adoption dates TWFE can be badly biased."""
    m = smf.ols(f"{y} ~ {treated} + C({unit}) + C({time})", data=panel).fit(
        cov_type="cluster", cov_kwds={"groups": panel[unit]})
    return Estimate(float(m.params[treated]), float(m.bse[treated]), int(m.nobs), label)


def event_study(panel: pd.DataFrame, y: str, unit: str, time: str, treated_unit: str, first_treated_time: int,
                ref: int | None = None) -> pd.DataFrame:
    """One coefficient per period relative to treatment (leads and lags), relative to the last pre-period.
    Leads (before treatment) should be ~0 if trends were parallel; lags trace the effect over time."""
    ref = first_treated_time - 1 if ref is None else ref
    d = panel.copy()
    d["rel"] = d[time] - first_treated_time
    terms = []
    for t in sorted(d[time].unique()):
        if t == ref:
            continue
        name = f"ev_{t}"
        d[name] = ((d[time] == t) & (d[treated_unit] == 1)).astype(int)
        terms.append((t, name))
    f = f"{y} ~ {' + '.join(n for _, n in terms)} + C({unit}) + C({time})"
    m = smf.ols(f, data=d).fit(cov_type="cluster", cov_kwds={"groups": d[unit]})
    rows = [{"time": t, "rel_time": t - first_treated_time, "coef": m.params[n], "se": m.bse[n]} for t, n in terms]
    rows.append({"time": ref, "rel_time": ref - first_treated_time, "coef": 0.0, "se": 0.0})
    out = pd.DataFrame(rows).sort_values("time").reset_index(drop=True)
    out["ci_low"], out["ci_high"] = out.coef - 1.96 * out.se, out.coef + 1.96 * out.se
    return out


def permutation_test(panel: pd.DataFrame, y: str, unit: str, time: str, treated_unit_value: str,
                     first_treated_time: int) -> dict:
    """Randomisation inference for a single treated unit: re-run the DiD pretending each control unit was the
    treated one. The p-value is the share of units with an effect at least as large (in absolute value) as the
    real one. Honest when there is only one treated cluster, where clustered SEs are unreliable."""
    def est(u):
        d = panel.assign(_tr=((panel[unit] == u) & (panel[time] >= first_treated_time)).astype(int))
        g = d.assign(_g=(d[unit] == u).astype(int), _post=(d[time] >= first_treated_time).astype(int))
        m = g.groupby(["_g", "_post"])[y].mean()
        return (m[1, 1] - m[1, 0]) - (m[0, 1] - m[0, 0])

    effects = pd.Series({u: est(u) for u in panel[unit].unique()})
    real = effects[treated_unit_value]
    p = float((effects.abs() >= abs(real) - 1e-12).mean())
    return {"effect": float(real), "p_value": p, "n_units": len(effects), "rank": int((effects.abs() >= abs(real)
                                                                                         - 1e-12).sum()),
            "placebo_effects": effects.drop(treated_unit_value)}


def placebo_in_time(panel: pd.DataFrame, y: str, unit: str, time: str, treated_unit: str,
                    first_treated_time: int, fake_time: int) -> Estimate:
    """Pretend treatment started at `fake_time` (before the real date) using pre-period data only.
    A real-looking 'effect' here means the groups were already diverging: parallel trends is in doubt."""
    d = panel[panel[time] < first_treated_time].copy()
    d["_post"] = (d[time] >= fake_time).astype(int)
    d["_tr"] = d[treated_unit] * d["_post"]
    return twfe(d, y, unit, time, "_tr", label=f"placebo start at t={fake_time}")
