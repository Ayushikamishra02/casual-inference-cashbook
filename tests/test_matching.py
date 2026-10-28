"""Propensity-score methods: correct on simulated data with known confounding, and close to the experimental
benchmark on LaLonde's data."""
import numpy as np
import pytest

from causalbook import data, matching, simulate


def test_simulation_recovers_known_att():
    s = simulate.check_matching(n_sims=15, seed=5)
    for col in ["IPW", "doubly robust (AIPW)", "PS matching (1-NN)"]:
        assert s[col].mean() == pytest.approx(1000, abs=200), col
    assert s["naive difference"].mean() < 0                       # confounding flips the sign
    assert s["regression adjustment"].mean() > 1500               # misspecified outcome model is biased...
    assert abs(s["doubly robust (AIPW)"].mean() - 1000) < 200     # ...but AIPW is rescued by the right PS model


def test_experimental_benchmark():
    b = matching.experimental_benchmark(data.nsw_experiment())
    assert b["difference"] == pytest.approx(1794.34, abs=0.01)


def test_observational_estimates(nsw_obs):
    est = matching.estimate_all(nsw_obs)
    assert matching.naive(nsw_obs) == pytest.approx(-8497.5, abs=1)
    for k in ["IPW", "doubly robust (AIPW)", "regression adjustment"]:
        assert 800 < est[k] < 2500, k                              # right sign, right ballpark
    no = matching.estimate_all(nsw_obs, ps_formula=matching.DW_FORMULA_NO_EARNINGS,
                               covs=matching.OUTCOME_COVS_NO_EARNINGS)
    assert all(v < 0 for v in no.values())                         # without earnings history every method fails


def test_ipw_balances_covariates(nsw_obs):
    ps = matching.propensity(nsw_obs)
    keep = matching.common_support(nsw_obs, ps)
    d, p = nsw_obs[keep].reset_index(drop=True), ps[keep]
    t = d.treat.to_numpy() == 1
    bal = matching.balance_table(d, {"ipw": matching.ipw_weights(p, t)})
    assert bal["ipw"].abs().max() < 0.1


def test_nn_match_weights_count_controls(nsw_obs):
    ps = matching.propensity(nsw_obs)
    m = matching.nn_match(nsw_obs, ps, k=1)
    t = nsw_obs.treat.to_numpy() == 1
    assert m["weights"][~t].sum() == pytest.approx(t.sum())       # each treated person uses one control


def test_robustness_value_formula():
    r = matching.robustness_value(data.nsw_experiment(), covs="age + educ + re75")
    f = abs(r["t"]) / np.sqrt(445 - 5)
    assert r["rv_q1"] == pytest.approx(0.5 * (np.sqrt(f ** 4 + 4 * f ** 2) - f ** 2))
