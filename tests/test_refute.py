"""DoWhy agrees with our own regression, and its placebo refuter collapses the effect towards zero."""
import importlib.util

import pytest
import statsmodels.formula.api as smf

from causalbook import matching

pytestmark = [pytest.mark.slow,
              pytest.mark.skipif(importlib.util.find_spec("dowhy") is None, reason="dowhy not installed")]


def test_dowhy_matches_statsmodels_and_placebo_is_null(nsw_obs):
    from causalbook import refute

    r = refute.dowhy_analysis(nsw_obs, n_sims=10)
    ps = matching.propensity(nsw_obs)
    d = refute._prep(nsw_obs[matching.common_support(nsw_obs, ps)].reset_index(drop=True))
    d["treat"] = d.treat.astype(int)
    ols = smf.ols("re78 ~ treat + " + " + ".join(refute.DW_COLUMNS), data=d).fit().params["treat"]
    assert r["estimates"]["linear regression"] == pytest.approx(ols, rel=1e-6)
    assert abs(r["refuters"]["placebo treatment (shuffle who was treated)"]["new"]) < 700
    assert r["default_settings_estimate"] < 500       # documented pitfall: DoWhy's default PS clipping
