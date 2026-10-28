"""Selection on observables: propensity scores, matching, weighting and doubly robust estimation of the
average treatment effect on the treated (ATT).

Assumption that everything here rests on ("unconfoundedness" / "no unmeasured confounders"): once you compare
people with the same observed characteristics X, who got treated is as good as random. Plus "overlap": for every
treated person there are comparable untreated people.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from sklearn.neighbors import NearestNeighbors

# Dehejia & Wahba (1999) propensity-score specification for NSW vs CPS
DW_FORMULA = ("treat ~ age + I(age**2) + I(age**3) + educ + I(educ**2) + marr + nodegree + black + hisp"
              " + re74 + re75 + u74 + u75 + I(educ*re74)")
OUTCOME_COVS = "age + I(age**2) + educ + I(educ**2) + marr + nodegree + black + hisp + re74 + re75 + u74 + u75"
BALANCE_COVS = ["age", "educ", "black", "hisp", "marr", "nodegree", "re74", "re75", "u74", "u75"]


def propensity(df: pd.DataFrame, formula: str = DW_FORMULA) -> np.ndarray:
    """P(treated | X) from a logistic regression."""
    m = smf.glm(formula, data=df, family=sm.families.Binomial()).fit()
    return np.clip(m.predict(df).to_numpy(), 1e-6, 1 - 1e-6)


def common_support(df: pd.DataFrame, ps: np.ndarray, treat: str = "treat") -> np.ndarray:
    """Keep controls whose score lies within the range of the treated units' scores (all treated are kept)."""
    t = df[treat].to_numpy() == 1
    lo, hi = ps[t].min(), ps[t].max()
    return t | ((ps >= lo) & (ps <= hi))


def smd(x_t: np.ndarray, x_c: np.ndarray, w_c: np.ndarray | None = None) -> float:
    """Standardised mean difference: (mean_t - mean_c) / pooled SD of the *unweighted* groups.
    |SMD| < 0.1 is the usual 'balanced' rule of thumb."""
    w_c = np.ones(len(x_c)) if w_c is None else w_c
    mc = np.average(x_c, weights=w_c)
    sd = np.sqrt((x_t.var(ddof=1) + x_c.var(ddof=1)) / 2)
    return float((x_t.mean() - mc) / sd) if sd > 0 else 0.0


def balance_table(df: pd.DataFrame, weights: dict[str, np.ndarray], covs=BALANCE_COVS, treat="treat") -> pd.DataFrame:
    """SMD of each covariate, unweighted and under each set of control weights."""
    t = df[treat].to_numpy() == 1
    out = {}
    for name, w in weights.items():
        out[name] = {c: smd(df.loc[t, c].to_numpy(), df.loc[~t, c].to_numpy(), w[~t]) for c in covs}
    return pd.DataFrame(out)


def nn_match(df: pd.DataFrame, ps: np.ndarray, y: str = "re78", treat: str = "treat", k: int = 1,
             caliper: float | None = None) -> dict:
    """k-nearest-neighbour matching on the propensity score (logit scale), with replacement.
    Returns the ATT and implied control weights (how often each control is used)."""
    lps = np.log(ps / (1 - ps))
    t = df[treat].to_numpy() == 1
    yv = df[y].to_numpy()
    nn = NearestNeighbors(n_neighbors=k).fit(lps[~t].reshape(-1, 1))
    dist, idx = nn.kneighbors(lps[t].reshape(-1, 1))
    keep = np.ones(t.sum(), bool) if caliper is None else (dist.max(axis=1) <= caliper * lps.std())
    ctrl_y = yv[~t][idx]
    att = float((yv[t][keep] - ctrl_y[keep].mean(axis=1)).mean())
    w = np.zeros(len(df))
    ctrl_pos = np.flatnonzero(~t)
    np.add.at(w, ctrl_pos[idx[keep].ravel()], 1.0 / k)
    w[t] = keep.astype(float)
    return {"att": att, "weights": w, "n_treated_matched": int(keep.sum()),
            "n_controls_used": int((w[~t] > 0).sum())}


def ipw_weights(ps: np.ndarray, t: np.ndarray) -> np.ndarray:
    """ATT weights: treated 1, controls p/(1-p) (controls that look like treated people count more)."""
    return np.where(t, 1.0, ps / (1 - ps))


def ipw_att(df: pd.DataFrame, ps: np.ndarray, y="re78", treat="treat") -> float:
    t = df[treat].to_numpy() == 1
    w = ipw_weights(ps, t)
    yv = df[y].to_numpy()
    return float(yv[t].mean() - np.average(yv[~t], weights=w[~t]))


def regression_att(df: pd.DataFrame, y="re78", treat="treat", covs: str = OUTCOME_COVS) -> float:
    """Outcome regression ('regression adjustment'): fit E[Y | X] on controls, predict the treated's
    untreated outcome, average the gap."""
    t = df[treat] == 1
    m = smf.ols(f"{y} ~ {covs}", data=df[~t]).fit()
    return float((df.loc[t, y] - m.predict(df[t])).mean())


def aipw_att(df: pd.DataFrame, ps: np.ndarray, y="re78", treat="treat", covs: str = OUTCOME_COVS) -> float:
    """Doubly robust ATT: regression adjustment plus an IPW correction of its residuals. Consistent if
    EITHER the propensity model OR the outcome model is right."""
    t = (df[treat] == 1).to_numpy()
    m0 = smf.ols(f"{y} ~ {covs}", data=df[~t]).fit().predict(df).to_numpy()
    yv = df[y].to_numpy()
    r = yv - m0
    odds = ps / (1 - ps)
    # treated residuals minus the odds-weighted (normalised) control residuals
    return float(r[t].mean() - np.average(r[~t], weights=odds[~t]))


def naive(df: pd.DataFrame, y="re78", treat="treat") -> float:
    t = df[treat] == 1
    return float(df.loc[t, y].mean() - df.loc[~t, y].mean())


def ols_with_controls(df: pd.DataFrame, y="re78", treat="treat", covs: str = OUTCOME_COVS) -> float:
    return float(smf.ols(f"{y} ~ {treat} + {covs}", data=df).fit().params[treat])


ESTIMATORS = ["naive difference (common support)", "OLS with controls", "regression adjustment", "PS matching (1-NN)",
              "PS matching (5-NN, caliper)", "IPW", "doubly robust (AIPW)"]


# The same specifications without pre-programme earnings (re74, re75, u74, u75): what if we hadn't measured them?
DW_FORMULA_NO_EARNINGS = ("treat ~ age + I(age**2) + I(age**3) + educ + I(educ**2) + marr + nodegree + black"
                          " + hisp")
OUTCOME_COVS_NO_EARNINGS = "age + I(age**2) + educ + I(educ**2) + marr + nodegree + black + hisp"


def estimate_all(df: pd.DataFrame, trim: bool = True, ps_formula: str = DW_FORMULA,
                 covs: str = OUTCOME_COVS) -> dict[str, float]:
    """Every estimator on one dataset (propensity model refit inside, so this can be bootstrapped)."""
    ps = propensity(df, ps_formula)
    if trim:
        keep = common_support(df, ps)
        df, ps = df[keep].reset_index(drop=True), ps[keep]
    return {
        "naive difference (common support)": naive(df),
        "OLS with controls": ols_with_controls(df, covs=covs),
        "regression adjustment": regression_att(df, covs=covs),
        "PS matching (1-NN)": nn_match(df, ps)["att"],
        "PS matching (5-NN, caliper)": nn_match(df, ps, k=5, caliper=0.1)["att"],
        "IPW": ipw_att(df, ps),
        "doubly robust (AIPW)": aipw_att(df, ps, covs=covs),
    }


def bootstrap(df: pd.DataFrame, n_boot: int = 200, seed: int = 0, treat: str = "treat") -> pd.DataFrame:
    """Stratified bootstrap (resample treated and controls separately), re-estimating the propensity score
    each time so its uncertainty is included. Note: the bootstrap is known to be not exactly valid for
    nearest-neighbour matching (Abadie & Imbens 2008); treat matching CIs as approximate."""
    rng = np.random.default_rng(seed)
    ti = np.flatnonzero(df[treat].to_numpy() == 1)
    ci = np.flatnonzero(df[treat].to_numpy() == 0)
    rows = []
    for _ in range(n_boot):
        idx = np.concatenate([rng.choice(ti, len(ti)), rng.choice(ci, len(ci))])
        rows.append(estimate_all(df.iloc[idx].reset_index(drop=True)))
    return pd.DataFrame(rows)


def experimental_benchmark(exp: pd.DataFrame, y="re78", treat="treat") -> dict:
    """The randomised experiment's answer: simple difference in means, and with covariate adjustment."""
    m0 = smf.ols(f"{y} ~ {treat}", data=exp).fit(cov_type="HC1")
    m1 = smf.ols(f"{y} ~ {treat} + {OUTCOME_COVS}", data=exp).fit(cov_type="HC1")
    return {"difference": float(m0.params[treat]), "difference_se": float(m0.bse[treat]),
            "adjusted": float(m1.params[treat]), "adjusted_se": float(m1.bse[treat]),
            "n_treated": int((exp[treat] == 1).sum()), "n_control": int((exp[treat] == 0).sum())}


def placebo_permutation(df: pd.DataFrame, n_perm: int = 200, seed: int = 0, treat: str = "treat") -> dict:
    """Shuffle who was 'treated' (keeping the number treated) and re-run the whole IPW pipeline, propensity model
    included. Shuffled labels have no effect by construction, so the placebo estimates should centre on 0 and
    the real estimate should stand out from them."""
    rng = np.random.default_rng(seed)
    obs = estimate_all(df)["IPW"]
    draws = []
    for _ in range(n_perm):
        d = df.assign(**{treat: rng.permutation(df[treat].to_numpy())})
        ps = propensity(d)
        draws.append(ipw_att(d, ps))
    draws = np.array(draws)
    return {"observed": obs, "placebo_mean": float(draws.mean()), "placebo_sd": float(draws.std()),
            "p_value": float((np.abs(draws) >= abs(obs)).mean()), "draws": draws}


def robustness_value(df: pd.DataFrame, y: str = "re78", treat: str = "treat", covs: str = OUTCOME_COVS,
                     alpha: float = 0.05) -> dict:
    """Cinelli & Hazlett (2020) sensitivity analysis for the regression estimate.
    RV = how strongly an unmeasured confounder would have to be associated with BOTH treatment and outcome
    (share of residual variance explained, partial R^2) to drive the estimate to zero (RV_q1) or to make it
    statistically insignificant (RV_qa). Compared with the strongest observed covariate as a benchmark."""
    from scipy import stats

    m = smf.ols(f"{y} ~ {treat} + {covs}", data=df).fit()
    dof = m.df_resid
    t = m.tvalues[treat]

    def rv(f):
        f = max(f, 0.0)
        return 0.5 * (np.sqrt(f ** 4 + 4 * f ** 2) - f ** 2)

    f_q1 = abs(t) / np.sqrt(dof)
    t_crit = stats.t.ppf(1 - alpha / 2, dof - 1)
    f_qa = f_q1 - t_crit / np.sqrt(dof - 1)
    partial_r2_treat = t ** 2 / (t ** 2 + dof)
    # benchmark: partial R2 of 1975 earnings with the outcome
    r2_re75 = m.tvalues["re75"] ** 2 / (m.tvalues["re75"] ** 2 + dof)
    return {"estimate": float(m.params[treat]), "t": float(t), "rv_q1": float(rv(f_q1)), "rv_qa": float(rv(f_qa)),
            "partial_r2_treatment": float(partial_r2_treat), "partial_r2_re75_outcome": float(r2_re75)}
