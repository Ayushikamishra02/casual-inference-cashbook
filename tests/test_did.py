"""DiD estimators: exact on noiseless data, and they reproduce the published Card & Krueger and organ-donation
numbers."""
import numpy as np
import pandas as pd
import pytest

from causalbook import cases, did, simulate


def test_twfe_exact_without_noise():
    rows = []
    for u in range(10):
        for t in range(1, 7):
            tr = int(u < 5)
            rows.append({"unit": u, "t": t, "y": 3 * u + 0.7 * t + 2.5 * tr * (t >= 4), "d": tr * (t >= 4),
                         "tu": tr})
    p = pd.DataFrame(rows)
    assert did.twfe(p, "y", "unit", "t", "d").effect == pytest.approx(2.5, abs=1e-9)
    es = did.event_study(p, "y", "unit", "t", "tu", 4)
    assert np.allclose(es[es.rel_time < 0].coef, 0, atol=1e-9)
    assert np.allclose(es[es.rel_time >= 0].coef, 2.5, atol=1e-9)


def test_did_simulation_unbiased_and_covers():
    s = simulate.check_did(n_sims=60, seed=11)
    ok = s[s.scenario == "parallel trends hold"]
    assert ok.did.mean() == pytest.approx(2.0, abs=0.1)
    assert ok.covered.mean() >= 0.85
    bad = s[s.scenario == "parallel trends violated"]
    assert bad.did.mean() > 2.8                       # the bias shows up when the assumption fails


def test_card_krueger_replication():
    r = cases.minimum_wage()
    assert r["regression"].effect == pytest.approx(2.75, abs=0.01)
    rob = r["robustness"].set_index("label")
    t4 = rob.loc["change in FTE on NJ dummy (Table 4 i)"]
    assert (round(t4.effect, 2), round(t4.se, 2)) == (2.33, 1.19)          # the paper's Table 4 column (i)
    gap = [k for k in rob.index if k.startswith("wage-gap model")][0]
    assert "15.65" in gap
    assert r["wage_first_stage"].effect > 0.4                                # wages really rose in NJ
    placebo = rob.loc["PLACEBO: PA region vs PA region (no treatment)"]
    assert placebo.ci_low < 0 < placebo.ci_high                              # nothing where nothing happened


def test_organ_donation():
    r = cases.organ_donation()
    assert r["main"].effect == pytest.approx(-0.0225, abs=0.0005)
    assert r["permutation"]["rank"] == 5 and r["permutation"]["n_units"] == 27
    assert abs(r["placebo_in_time"].effect) < 0.005
