"""The four case studies, each answering one "did it work?" question with its main estimate and the checks that
try to break it. Every function returns plain dicts/DataFrames used by the report, the tests and the lessons.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import data, did, matching, synth


# ================================================================================ 1. minimum wage (2x2 DiD)
def _gap_at_mean(t4: pd.DataFrame) -> did.Estimate:
    """Card & Krueger's dose-response model (Table 4 iii): change in FTE on the size of the wage increase a
    store needed ("wage gap"). Coefficient 15.65 per unit of gap; converted here to FTE at the average NJ gap
    so it sits on the same scale as the other estimates."""
    e = did.first_difference(t4, "fte_before", "fte_after", "wage_gap")
    g = float(t4.loc[t4.nj == 1, "wage_gap"].mean())
    return did.Estimate(e.effect * g, e.se * g, e.n, f"wage-gap model at the average NJ gap (Table 4 iii: {e.effect:.2f})")


def minimum_wage() -> dict:
    """Did New Jersey's April 1992 minimum-wage rise ($4.25 -> $5.05) cost fast-food jobs?
    Control group: eastern Pennsylvania, just across the border, where the minimum stayed $4.25."""
    w = data.card_krueger()
    long = data.card_krueger_long()
    table = did.did_table(w, "nj", "fte_before", "fte_after", ("PA", "NJ"))
    reg = did.did_regression(long, "fte", "nj", "post", "store_id", label="regression DiD (all stores)")

    # Card & Krueger Table 4 sample: employment in both waves + wage data (or permanently closed)
    t4 = w[w.fte_before.notna() & w.fte_after.notna() & w.wage_before.notna()
           & (w.wage_after.notna() | w.perm_closed.astype(bool))]
    checks = [
        did.first_difference(t4, "fte_before", "fte_after", "nj", label="change in FTE on NJ dummy (Table 4 i)"),
        did.first_difference(t4, "fte_before", "fte_after", "nj", "C(chain) + co_owned",
                             label="... + chain and ownership controls (Table 4 ii)"),
        _gap_at_mean(t4),
        did.first_difference(t4, "fte_before", "fte_after", "nj", "C(chain) + co_owned", cov_type="HC1",
                             label="NJ dummy + controls, robust SEs"),
    ]
    # Did the treatment actually happen? ("first stage"): starting wages
    wage = did.did_regression(long, "wage", "nj", "post", "store_id", label="starting wage ($)")
    # Did prices respond? (an effect the theory predicts)
    price = did.did_regression(long, "price", "nj", "post", "store_id", label="price of a meal ($)")
    # Within-NJ comparison: stores already paying >= $5.00 were barely affected -> a control group inside NJ
    nj = w[w.nj == 1].copy()
    nj["low_wage"] = (nj.wage_before <= 4.25 + 1e-9).astype(int)
    nj = nj[(nj.low_wage == 1) | (nj.wage_before >= 5.00)]
    within = did.did_table(nj, "low_wage", "fte_before", "fte_after", ("NJ high-wage", "NJ low-wage"))
    # Placebo: two PA regions, neither treated -> should show nothing
    pa = w[w.nj == 0].assign(pa1=lambda d: (d.region == "PA (near Philadelphia)").astype(int))
    placebo = did.did_table(pa, "pa1", "fte_before", "fte_after", ("PA Allentown-Easton", "PA near Philadelphia"))
    # Temporarily closed stores counted as zero employment
    w0 = w.copy()
    w0.loc[w0.temp_closed.astype(bool), "fte_after"] = 0.0
    t0 = did.did_table(w0, "nj", "fte_before", "fte_after", ("PA", "NJ"))

    def row(t, label):
        r = t.iloc[2]
        return did.Estimate(float(r.change), float(r.change_se), 0, label)

    robustness = [reg, *checks, row(within, "within NJ: low-wage vs high-wage stores"),
                  row(t0, "temporarily closed stores counted as 0 FTE"),
                  row(placebo, "PLACEBO: PA region vs PA region (no treatment)")]
    return {"data": w, "table": table, "regression": reg, "robustness": pd.DataFrame([e.as_dict() for e in robustness]),
            "wage_first_stage": wage, "price": price, "within_nj": within, "placebo_pa": placebo,
            "baseline_fte_nj": float(table.loc["NJ", "before"])}


# ================================================================================ 2. organ donation (event study)
def organ_donation() -> dict:
    """Did California's 'active choice' organ-donor question at the DMV (July 2011) raise registrations?"""
    d = data.organ_donations()
    main = did.twfe(d, "rate", "state", "t", "treated", label="TWFE DiD, SEs clustered by state")
    es = did.event_study(d, "rate", "state", "t", "california", 4)
    perm = did.permutation_test(d, "rate", "state", "t", "California", 4)
    pit = did.placebo_in_time(d, "rate", "state", "t", "california", 4, 3)
    pre = d[(d.california == 1) & (d.post == 0)].rate.mean()
    return {"data": d, "main": main, "event_study": es, "permutation": perm, "placebo_in_time": pit,
            "baseline_rate_ca": float(pre), "relative_effect": main.effect / pre}


# ================================================================================ 3. job training (matching)
def job_training(n_boot: int = 200, n_perm: int = 200) -> dict:
    """Did the NSW job-training programme raise 1978 earnings? Pretend the experiment's control group is lost
    and use 15,992 CPS survey respondents instead; then check every method against the experimental answer."""
    exp = data.nsw_experiment()
    obs = data.nsw_observational()
    bench = matching.experimental_benchmark(exp)
    ps = matching.propensity(obs)
    keep = matching.common_support(obs, ps)
    trimmed, ps_t = obs[keep].reset_index(drop=True), ps[keep]
    t = trimmed.treat.to_numpy() == 1
    est = matching.estimate_all(obs)
    boots = matching.bootstrap(obs, n_boot=n_boot) if n_boot else None
    table = pd.DataFrame({"estimate": pd.Series(est)})
    if boots is not None:
        table["ci_low"] = boots.quantile(0.025)
        table["ci_high"] = boots.quantile(0.975)
    table["error_vs_experiment"] = table.estimate - bench["difference"]
    no_earn = pd.Series(matching.estimate_all(obs, ps_formula=matching.DW_FORMULA_NO_EARNINGS,
                                              covs=matching.OUTCOME_COVS_NO_EARNINGS))
    nn = matching.nn_match(trimmed, ps_t, k=5, caliper=0.1)
    weights = {"before (raw CPS)": np.where(t, 1.0, 1.0), "after IPW": matching.ipw_weights(ps_t, t),
               "after 5-NN matching": nn["weights"]}
    balance_trimmed = matching.balance_table(trimmed, weights)
    balance_raw = matching.balance_table(obs, {"raw": np.ones(len(obs))})["raw"]
    balance = pd.concat([balance_raw.rename("before (all CPS)"), balance_trimmed.drop(columns="before (raw CPS)")],
                        axis=1)
    out = {"benchmark": bench, "estimates": table, "no_earnings": no_earn, "balance": balance,
           "raw_naive": matching.naive(obs),
           "ps": pd.DataFrame({"ps": ps, "treat": obs.treat, "kept": keep}),
           "n_obs": len(obs), "n_kept": int(keep.sum()), "n_controls_used_5nn": nn["n_controls_used"],
           "sensitivity": matching.robustness_value(trimmed)}
    if n_perm:
        out["placebo"] = matching.placebo_permutation(obs, n_perm=n_perm)
    return out


# ================================================================================ 4. Prop 99 (synthetic control)
def tobacco(run_placebos: bool = True) -> dict:
    """Did California's 1988 Proposition 99 (tobacco tax + anti-smoking programme) cut cigarette sales?"""
    d = data.prop99()
    res = synth.fit(d, "California", 1989)
    out = {"data": d, "fit": res, "effect_1989_2000": res.effect(), "effect_2000": float(res.path.gap.iloc[-1]),
           "pre_rmspe": res.rmspe(False), "did_vs_average": synth.did_vs_average(d, "California", 1989)}
    ca_1988 = float(res.path.loc[res.path.year == 1988, "treated"].iloc[0])
    synth_2000 = float(res.path.synthetic.iloc[-1])
    out["relative_effect_2000"] = out["effect_2000"] / synth_2000
    out["ca_1988"] = ca_1988
    # in-time placebo: pretend the law passed in 1980 (fit on 1970-79, look at 1980-88, before the real law)
    early = [("lnincome", range(1972, 1980)), ("retprice", range(1972, 1980)), ("age15to24", range(1972, 1980)),
             ("cigsale", [1970]), ("cigsale", [1975]), ("cigsale", [1979])]
    out["placebo_in_time"] = synth.fit(d, "California", 1980, end_time=1988, specs=early)
    if run_placebos:
        p = synth.placebo_in_space(d, "California", 1989)
        out["placebos"] = p
        out["p_values"] = {"all 38 placebos": synth.permutation_p(p),
                           "placebos with pre-MSPE < 20x CA": synth.permutation_p(p, 20),
                           "< 5x": synth.permutation_p(p, 5), "< 2x": synth.permutation_p(p, 2)}
        out["leave_one_out"] = synth.leave_one_out(d, res)
    return out
