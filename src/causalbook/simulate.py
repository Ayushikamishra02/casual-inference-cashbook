"""Simulations with a KNOWN true effect: the only way to check that an estimator works, and to see exactly
when it breaks. Each scenario returns a tidy table of estimates across many simulated datasets.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import did, matching, synth


# --------------------------------------------------------------------------------------------- DiD
def did_panel(rng, n_units=60, n_periods=8, treat_share=0.5, effect=2.0, trend_gap=0.0, t0=5):
    """Unit and time effects, treatment from period t0 on. `trend_gap` > 0 makes treated units drift upward
    anyway: parallel trends is violated."""
    u = np.arange(n_units)
    treated = (u < n_units * treat_share).astype(int)
    a = rng.normal(0, 3, n_units) + 2 * treated           # treated units start at a different level: fine for DiD
    rows = []
    for t in range(1, n_periods + 1):
        y = a + 0.5 * t + trend_gap * treated * t + effect * treated * (t >= t0) + rng.normal(0, 1, n_units)
        rows.append(pd.DataFrame({"unit": u, "t": t, "treated_unit": treated, "y": y,
                                  "d": treated * (t >= t0)}))
    return pd.concat(rows, ignore_index=True)


def check_did(n_sims=200, seed=1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    out = []
    for scenario, gap in [("parallel trends hold", 0.0), ("parallel trends violated", 0.3)]:
        for _ in range(n_sims):
            p = did_panel(rng, trend_gap=gap)
            e = did.twfe(p, "y", "unit", "t", "d")
            naive_post = p[p.t >= 5].groupby("treated_unit").y.mean().diff().iloc[-1]
            lo, hi = e.ci
            out.append({"scenario": scenario, "did": e.effect, "covered": lo <= 2.0 <= hi,
                        "post-period comparison only": naive_post})
    return pd.DataFrame(out)


# --------------------------------------------------------------------------------------------- matching
def confounded(rng, n=3000, effect=1000.0):
    """Earnings-like outcome; people with low past earnings are more likely to be treated, and past earnings
    also predict future earnings: a confounder. True ATT = `effect`."""
    x1 = rng.gamma(2.0, 4000, n)                      # past earnings
    x2 = rng.normal(0, 1, n)                          # e.g. motivation proxy (observed)
    logit = 1.5 - 0.0004 * x1 + 0.8 * x2
    p = 1 / (1 + np.exp(-logit))
    t = rng.binomial(1, p)
    y0 = 2000 + 0.9 * x1 + 1500 * x2 + 0.00002 * x1 ** 2 + rng.normal(0, 3000, n)
    y = y0 + effect * t
    return pd.DataFrame({"treat": t, "x1": x1, "x2": x2, "re78": y})


def check_matching(n_sims=100, seed=2) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    f_ps, covs = "treat ~ x1 + x2", "x1 + x2"
    out = []
    for _ in range(n_sims):
        d = confounded(rng)
        ps = matching.propensity(d, f_ps)
        out.append({"naive difference": matching.naive(d),
                    "regression adjustment": matching.regression_att(d, covs=covs),
                    "PS matching (1-NN)": matching.nn_match(d, ps)["att"],
                    "IPW": matching.ipw_att(d, ps),
                    "doubly robust (AIPW)": matching.aipw_att(d, ps, covs=covs),
                    "IPW, confounder x2 omitted": matching.ipw_att(d, matching.propensity(d, "treat ~ x1"))})
    return pd.DataFrame(out)


# --------------------------------------------------------------------------------------------- synthetic control
def factor_panel(rng, n_donors=30, n_years=30, t0=21, effect=-10.0):
    """Interactive fixed effects: each unit loads differently on common shocks, so the plain average of
    controls does NOT track the treated unit (DiD fails), but a weighted combination can (synth works).
    The treated unit's loadings are a convex combination of 4 donors'."""
    years = np.arange(1, n_years + 1)
    f = np.cumsum(rng.normal(0, 1, (n_years, 2)), axis=0) * 3      # 2 trending common factors
    lam = rng.uniform(0, 2, (n_donors, 2))
    mu = rng.normal(100, 10, n_donors)
    wtrue = np.zeros(n_donors)
    wtrue[:4] = [0.4, 0.3, 0.2, 0.1]
    lam_t, mu_t = wtrue @ lam, wtrue @ mu
    Y = mu + f @ lam.T + rng.normal(0, 1, (n_years, n_donors))
    y1 = mu_t + f @ lam_t + rng.normal(0, 1, n_years) + effect * (years >= t0)
    rows = [pd.DataFrame({"state": f"donor{j:02d}", "year": years, "cigsale": Y[:, j]}) for j in range(n_donors)]
    rows.append(pd.DataFrame({"state": "treated", "year": years, "cigsale": y1}))
    return pd.concat(rows, ignore_index=True)


def check_synth(n_sims=40, seed=3, t0=21) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    specs = [("cigsale", [y]) for y in (5, 10, 15, 20)]
    out = []
    for _ in range(n_sims):
        p = factor_panel(rng, t0=t0)
        r = synth.fit(p, "treated", t0, specs=specs, n_starts=2)
        dv = synth.did_vs_average(p, "treated", t0)
        out.append({"synthetic control": r.effect(), "DiD vs average of donors": dv[dv.year >= t0].did_gap.mean(),
                    "pre_rmspe": r.rmspe(False)})
    return pd.DataFrame(out)


def summary(df: pd.DataFrame, truth: float, cols=None) -> pd.DataFrame:
    cols = cols or [c for c in df.columns if df[c].dtype.kind == "f"]
    return pd.DataFrame({"mean estimate": df[cols].mean(), "bias": df[cols].mean() - truth,
                         "sd across sims": df[cols].std(), "rmse": np.sqrt(((df[cols] - truth) ** 2).mean())})


def run_all(scale: float = 1.0) -> dict:
    d = check_did(int(200 * scale))
    m = check_matching(int(100 * scale))
    s = check_synth(int(40 * scale))
    did_sum = d.groupby("scenario").agg(mean_did=("did", "mean"), coverage=("covered", "mean"),
                                        post_only=("post-period comparison only", "mean"))
    return {"did": did_sum, "matching": summary(m, 1000.0),
            "synth": summary(s, -10.0, ["synthetic control", "DiD vs average of donors"])}
