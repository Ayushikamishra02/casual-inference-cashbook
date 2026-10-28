"""Synthetic control (Abadie, Diamond & Hainmueller 2010), written from scratch.

When one unit (a state, a market, a country) is treated, build a "synthetic" twin: a weighted average of
untreated units whose weights are non-negative and sum to 1, chosen so the twin matches the treated unit before
treatment. After treatment, the gap between the unit and its twin is the estimated effect.

Two nested problems:
  inner  W(V) = argmin_W (X1 - X0 W)' V (X1 - X0 W)   s.t. W >= 0, sum(W) = 1     (match the predictors)
  outer  V    = argmin_V  mean over pre-years of (Z1 - Z0 W(V))^2                   (predictors that matter more
                                                                                     for the outcome get more weight)
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import minimize, nnls

# ADH (2010) predictor specification for Proposition 99: (variable, years to average over)
PROP99_PREDICTORS = [
    ("lnincome", range(1980, 1989)), ("retprice", range(1980, 1989)), ("age15to24", range(1980, 1989)),
    ("beer", range(1984, 1989)), ("cigsale", [1975]), ("cigsale", [1980]), ("cigsale", [1988]),
]


def simplex_weights(X1: np.ndarray, X0: np.ndarray, v: np.ndarray) -> np.ndarray:
    """min_W ||sqrt(V)(X1 - X0 W)||^2 with W >= 0 and sum(W) = 1, via non-negative least squares with the
    sum-to-one constraint added as a heavily weighted extra equation (exact in the limit, fast in practice)."""
    s = np.sqrt(v)[:, None]
    A, b = s * X0, s[:, 0] * X1
    lam = 1e3 * max(1.0, np.abs(A).max())
    A2 = np.vstack([A, lam * np.ones(X0.shape[1])])
    b2 = np.append(b, lam)
    w, _ = nnls(A2, b2, maxiter=50 * A2.shape[1])
    return w / w.sum()


@dataclass
class SynthResult:
    treated: str
    weights: pd.Series                 # donor weights (sum to 1)
    v: pd.Series                       # predictor importance (sum to 1)
    path: pd.DataFrame                 # year, treated, synthetic, gap
    predictors: pd.DataFrame           # treated vs synthetic vs donor average on each predictor
    treat_time: int
    meta: dict = field(default_factory=dict)

    def rmspe(self, post: bool) -> float:
        p = self.path[self.path.year >= self.treat_time] if post else self.path[self.path.year < self.treat_time]
        return float(np.sqrt((p.gap ** 2).mean()))

    @property
    def ratio(self) -> float:
        """post-treatment RMSPE / pre-treatment RMSPE: large = a big gap that wasn't there before."""
        return self.rmspe(True) / self.rmspe(False)

    def effect(self, years=None) -> float:
        p = self.path[self.path.year >= self.treat_time]
        if years is not None:
            p = p[p.year.isin(list(years))]
        return float(p.gap.mean())


def _predictor_matrix(df, unit, time, specs, units):
    rows, names = [], []
    for var, years in specs:
        years = list(years)
        s = df[df[time].isin(years)].groupby(unit)[var].mean()
        rows.append(s.reindex(units).to_numpy())
        names.append(f"{var} ({years[0]}-{years[-1]})" if len(years) > 1 else f"{var} ({years[0]})")
    return np.array(rows, dtype=float), names


def fit(df: pd.DataFrame, treated: str, treat_time: int, outcome: str = "cigsale", unit: str = "state",
        time: str = "year", specs=PROP99_PREDICTORS, donors: list[str] | None = None, fit_start: int | None = None,
        end_time: int | None = None, n_starts: int = 4, seed: int = 0) -> SynthResult:
    """Fit a synthetic control for `treated`. `donors` defaults to every other unit.
    `end_time` truncates the panel (used for in-time placebos)."""
    if end_time is not None:
        df = df[df[time] <= end_time]
    donors = [u for u in (donors or df[unit].unique()) if u != treated]
    units = [treated] + donors
    X, names = _predictor_matrix(df, unit, time, specs, units)
    if np.isnan(X).any():
        raise ValueError("missing predictor values for some units")
    X = X / X.std(axis=1, keepdims=True)             # put predictors on a common scale (as Synth does)
    X1, X0 = X[:, 0], X[:, 1:]
    Y = df.pivot(index=time, columns=unit, values=outcome)[units]
    pre = Y.index < treat_time
    if fit_start is not None:
        pre = pre & (Y.index >= fit_start)
    Z1, Z0 = Y.loc[pre].iloc[:, 0].to_numpy(), Y.loc[pre].iloc[:, 1:].to_numpy()

    def loss(theta):
        v = np.exp(theta - theta.max())
        v /= v.sum()
        w = simplex_weights(X1, X0, v)
        return float(np.mean((Z1 - Z0 @ w) ** 2))

    rng = np.random.default_rng(seed)
    k = len(X1)
    starts = [np.zeros(k)] + [rng.normal(0, 1.5, k) for _ in range(n_starts - 1)]
    best = min((minimize(loss, s, method="Nelder-Mead", options={"maxiter": 3000, "xatol": 1e-4, "fatol": 1e-6})
                for s in starts), key=lambda r: r.fun)
    v = np.exp(best.x - best.x.max())
    v /= v.sum()
    w = simplex_weights(X1, X0, v)

    synth = Y.iloc[:, 1:].to_numpy() @ w
    path = pd.DataFrame({"year": Y.index.to_numpy(), "treated": Y.iloc[:, 0].to_numpy(), "synthetic": synth})
    path["gap"] = path.treated - path.synthetic
    Xraw, _ = _predictor_matrix(df, unit, time, specs, units)
    pred = pd.DataFrame({"treated": Xraw[:, 0], "synthetic": Xraw[:, 1:] @ w, "donor average": Xraw[:, 1:].mean(1)},
                        index=names)
    return SynthResult(treated, pd.Series(w, index=donors).sort_values(ascending=False), pd.Series(v, index=names),
                       path, pred, treat_time, {"pre_mspe": best.fun})


def placebo_in_space(df: pd.DataFrame, treated: str, treat_time: int, **kw) -> pd.DataFrame:
    """Refit the synthetic control pretending each donor was treated (the real treated unit is removed from
    the donor pool). The treated unit's rank on the post/pre RMSPE ratio gives a permutation p-value."""
    units = [u for u in df[kw.get("unit", "state")].unique() if u != treated]
    rows = []
    real = fit(df, treated, treat_time, **kw)
    for u in [treated] + units:
        r = real if u == treated else fit(df, u, treat_time, donors=units, **kw)
        rows.append({"unit": u, "pre_rmspe": r.rmspe(False), "post_rmspe": r.rmspe(True), "ratio": r.ratio,
                     "effect": r.effect(), "is_treated": u == treated, "path": r.path[["year", "gap"]]})
    out = pd.DataFrame(rows).sort_values("ratio", ascending=False).reset_index(drop=True)
    out["rank"] = np.arange(1, len(out) + 1)
    return out


def permutation_p(placebos: pd.DataFrame, max_pre_ratio: float | None = None) -> float:
    """Share of units whose post/pre RMSPE ratio is at least the treated unit's. Optionally drop placebos whose
    pre-period fit was much worse than the treated unit's (they can't be compared fairly)."""
    p = placebos
    if max_pre_ratio is not None:
        tr = p.loc[p.is_treated, "pre_rmspe"].iloc[0]
        p = p[(p.pre_rmspe ** 2 <= max_pre_ratio * tr ** 2) | p.is_treated]
    r = p.loc[p.is_treated, "ratio"].iloc[0]
    return float((p.ratio >= r).mean())


def leave_one_out(df: pd.DataFrame, res: SynthResult, min_weight: float = 0.01, **kw) -> pd.DataFrame:
    """Drop each donor with a meaningful weight in turn and refit: is the result driven by a single donor?"""
    donors = list(res.weights.index)
    out = []
    for d in res.weights[res.weights > min_weight].index:
        r = fit(df, res.treated, res.treat_time, donors=[x for x in donors if x != d], **kw)
        out.append({"dropped": d, "weight_of_dropped": float(res.weights[d]), "effect": r.effect(),
                    "pre_rmspe": r.rmspe(False), "path": r.path[["year", "gap"]]})
    return pd.DataFrame(out)


def did_vs_average(df: pd.DataFrame, treated: str, treat_time: int, outcome="cigsale", unit="state",
                   time="year") -> pd.DataFrame:
    """The naive alternative: compare with the plain average of all other units (DiD), for contrast."""
    Y = df.pivot(index=time, columns=unit, values=outcome)
    avg = Y.drop(columns=treated).mean(axis=1)
    out = pd.DataFrame({"year": Y.index, "treated": Y[treated].to_numpy(), "average of others": avg.to_numpy()})
    pre = out.year < treat_time
    shift = (out.treated - out["average of others"])[pre].mean()
    out["did_counterfactual"] = out["average of others"] + shift
    out["did_gap"] = out.treated - out.did_counterfactual
    return out


def pysyncon_crosscheck(df: pd.DataFrame) -> dict | None:
    """Fit the same ADH specification with the independent `pysyncon` package (if installed) and compare.
    Synthetic control's outer optimisation is non-convex, so different optimisers can land on different
    (but similar) solutions; compare pre-period fit and effect, not just weights."""
    try:
        from pysyncon import Dataprep, Synth
    except ImportError:
        return None
    donors = [s for s in df.state.unique() if s != "California"]
    dp = Dataprep(foo=df, predictors=["lnincome", "retprice", "age15to24"], predictors_op="mean",
                  time_predictors_prior=range(1980, 1989),
                  special_predictors=[("beer", range(1984, 1989), "mean"), ("cigsale", [1975], "mean"),
                                      ("cigsale", [1980], "mean"), ("cigsale", [1988], "mean")],
                  dependent="cigsale", unit_variable="state", time_variable="year",
                  treatment_identifier="California", controls_identifier=donors,
                  time_optimize_ssr=range(1970, 1989))
    Z0, Z1 = dp.make_outcome_mats(time_period=range(1970, 2001))
    out = {}
    for name, (meth, init) in {"Nelder-Mead from equal weights": ("Nelder-Mead", "equal"),
                               "Nelder-Mead from regression start": ("Nelder-Mead", "ols")}.items():
        s = Synth()
        s.fit(dataprep=dp, optim_method=meth, optim_initial=init)
        w = s.weights()
        gap = Z1 - Z0 @ w
        out[name] = {"weights": w[w > 0.001].round(3).to_dict(),
                     "pre_rmspe": float(np.sqrt((gap.loc[:1988] ** 2).mean())),
                     "effect_1989_2000": float(gap.loc[1989:].mean())}
    return out
