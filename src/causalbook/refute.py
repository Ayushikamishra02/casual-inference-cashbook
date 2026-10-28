"""Cross-check the job-training estimates with Microsoft's DoWhy library and run its refutation tests.

DoWhy makes the four steps of a causal analysis explicit: model (which variables are common causes),
identify (which estimand answers the question), estimate, and refute (try to break the result).
"""
from __future__ import annotations

import logging
import warnings

import numpy as np
import pandas as pd

from . import matching

# DoWhy needs plain columns, so the Dehejia-Wahba polynomial terms are materialised.
DW_COLUMNS = ["age", "age2", "age3", "educ", "educ2", "marr", "nodegree", "black", "hisp", "re74", "re75", "u74",
              "u75", "educ_re74"]


def _prep(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["age2"], d["age3"] = d.age ** 2, d.age ** 3
    d["educ2"], d["educ_re74"] = d.educ ** 2, d.educ * d.re74
    d["treat"] = d["treat"].astype(bool)
    return d


def _ps_model():
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    # essentially unpenalised logistic regression, so it matches the statsmodels propensity model
    return make_pipeline(StandardScaler(), LogisticRegression(C=1e6, max_iter=10_000))


def dowhy_analysis(df: pd.DataFrame, n_sims: int = 50, seed: int = 0) -> dict:
    """Estimate the ATT with DoWhy (regression and propensity weighting) and run three refuters."""
    from dowhy import CausalModel

    logging.getLogger("dowhy").setLevel(logging.ERROR)
    warnings.filterwarnings("ignore")
    ps = matching.propensity(df)
    d = _prep(df[matching.common_support(df, ps)].reset_index(drop=True))
    model = CausalModel(data=d, treatment="treat", outcome="re78", common_causes=DW_COLUMNS)
    estimand = model.identify_effect(proceed_when_unidentifiable=True)
    weighting = {"weighting_scheme": "ips_normalized_weight", "propensity_score_model": _ps_model(),
                 "min_ps_score": 1e-6, "max_ps_score": 1 - 1e-6}
    est = {
        "linear regression": model.estimate_effect(estimand, method_name="backdoor.linear_regression",
                                                   target_units="att"),
        "propensity weighting": model.estimate_effect(estimand, method_name="backdoor.propensity_score_weighting",
                                                      target_units="att", method_params=weighting),
    }
    default = model.estimate_effect(estimand, method_name="backdoor.propensity_score_weighting", target_units="att",
                                    method_params={"weighting_scheme": "ips_normalized_weight"})
    # Refuters re-run the estimator. DoWhy's refuters rebuild the weighting estimator with its default settings
    # (dropping our method_params), so they are run on the regression estimate, which has no hidden settings.
    main = est["linear regression"]
    refuters = {}
    for name, kw in [("placebo treatment (shuffle who was treated)",
                      {"method_name": "placebo_treatment_refuter", "placebo_type": "permute"}),
                     ("add a random common cause", {"method_name": "random_common_cause"}),
                     ("re-estimate on random 80% subsets", {"method_name": "data_subset_refuter",
                                                             "subset_fraction": 0.8})]:
        r = model.refute_estimate(estimand, main, num_simulations=n_sims, random_seed=seed, **kw)
        res = r.refutation_result or {}
        refuters[name] = {"original": float(r.estimated_effect), "new": float(np.mean(r.new_effect)),
                          "p_value": float(res.get("p_value", np.nan)) if res else np.nan}
    return {"estimand": str(estimand).split("Estimand assumption 1")[0].strip()[:400],
            "refuted_estimate": "linear regression",
            "estimates": {k: float(v.value) for k, v in est.items()},
            "default_settings_estimate": float(default.value),
            "refuters": refuters, "n": len(d)}
