"""Synthetic control: the weight solver is correct, it recovers known effects, and Prop 99 matches ADH (2010)."""
import numpy as np
import pytest
from scipy.optimize import minimize

from causalbook import simulate, synth


def test_simplex_solver_matches_slsqp():
    rng = np.random.default_rng(0)
    X0, X1, v = rng.normal(size=(6, 12)), rng.normal(size=6), rng.dirichlet(np.ones(6))
    w = synth.simplex_weights(X1, X0, v)
    assert w.min() >= 0 and w.sum() == pytest.approx(1)
    obj = lambda w: float(((X1 - X0 @ w) ** 2 * v).sum())
    ref = minimize(obj, np.ones(12) / 12, method="SLSQP", bounds=[(0, 1)] * 12,
                   constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}], options={"ftol": 1e-12})
    assert obj(w) <= ref.fun + 1e-6


def test_recovers_effect_in_factor_model():
    s = simulate.check_synth(n_sims=8, seed=4)
    assert s["synthetic control"].mean() == pytest.approx(-10, abs=1.5)


def test_prop99_matches_published(smoking):
    r = synth.fit(smoking, "California", 1989)
    top = set(r.weights.head(5).index)
    assert top == {"Utah", "Nevada", "Montana", "Colorado", "Connecticut"}   # ADH (2010) Table 2 donors
    assert r.rmspe(False) < 2.0
    assert -21 < r.effect() < -17                                           # ADH: ~-19 packs on average
    assert r.path.gap.iloc[-1] == pytest.approx(-26, abs=2)                 # ~-26 packs by 2000


@pytest.mark.slow
def test_prop99_placebo_rank(smoking):
    p = synth.placebo_in_space(smoking, "California", 1989)
    assert p.iloc[0].unit == "California"
    assert synth.permutation_p(p) == pytest.approx(1 / 39)
