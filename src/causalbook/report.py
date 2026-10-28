"""Run every case study, save figures, tables and reports/metrics.json (the numbers quoted in the docs).

    python -m causalbook.report            # full run (~3 minutes)
    python -m causalbook.report --quick    # fewer bootstrap/permutation draws, for a fast check
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from . import cases, data, simulate, synth, viz
from .data import ROOT

REPORTS = ROOT / "reports"
FIG = REPORTS / "figures"


def _save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / name)
    viz.plt.close(fig)


def _num(df: pd.DataFrame, n: int = 4) -> pd.DataFrame:
    return df.round({c: n for c in df.select_dtypes("number").columns})


def build(quick: bool = False, with_dowhy: bool = True) -> dict:
    REPORTS.mkdir(exist_ok=True)
    M: dict = {}

    # 1 ---------------------------------------------------------------- minimum wage
    mw = cases.minimum_wage()
    _save(viz.min_wage_did(mw["table"], mw["data"]), "01_min_wage_did.png")
    _save(viz.forest(mw["robustness"], "Minimum wage: the estimate under different choices",
                     "effect of NJ's minimum wage rise on FTE employment per store"), "02_min_wage_robustness.png")
    _num(mw["table"]).to_csv(REPORTS / "min_wage_table.csv")
    _num(mw["robustness"]).to_csv(REPORTS / "min_wage_robustness.csv", index=False)
    M["minimum_wage"] = {"table": _num(mw["table"], 3).to_dict("index"), "regression": mw["regression"].as_dict(),
                         "robustness": _num(mw["robustness"]).to_dict("records"),
                         "wage_first_stage": mw["wage_first_stage"].as_dict(), "price": mw["price"].as_dict(),
                         "baseline_fte_nj": mw["baseline_fte_nj"]}

    # 2 ---------------------------------------------------------------- organ donation
    od = cases.organ_donation()
    _save(viz.organ(od["data"], od["event_study"], od["permutation"]), "03_organ_donation.png")
    _num(od["event_study"]).to_csv(REPORTS / "organ_event_study.csv", index=False)
    M["organ_donation"] = {"main": od["main"].as_dict(), "baseline_rate_ca": od["baseline_rate_ca"],
                           "relative_effect": od["relative_effect"],
                           "permutation": {k: v for k, v in od["permutation"].items() if k != "placebo_effects"},
                           "placebo_in_time": od["placebo_in_time"].as_dict(),
                           "event_study": _num(od["event_study"]).to_dict("records")}

    # 3 ---------------------------------------------------------------- job training
    jt = cases.job_training(n_boot=60 if quick else 300, n_perm=50 if quick else 300)
    _save(viz.overlap(jt["ps"]), "04_lalonde_overlap.png")
    _save(viz.lalonde_estimates(jt["estimates"], jt["benchmark"], jt["raw_naive"], jt["no_earnings"]),
          "05_lalonde_estimates.png")
    _save(viz.love_plot(jt["balance"]), "06_lalonde_balance.png")
    _num(jt["estimates"], 1).to_csv(REPORTS / "lalonde_estimates.csv")
    _num(jt["balance"], 3).to_csv(REPORTS / "lalonde_balance.csv")
    M["job_training"] = {"benchmark": jt["benchmark"], "raw_naive": jt["raw_naive"],
                         "estimates": _num(jt["estimates"], 1).to_dict("index"),
                         "no_earnings": jt["no_earnings"].round(1).to_dict(), "n_obs": jt["n_obs"],
                         "n_kept": jt["n_kept"], "n_controls_used_5nn": jt["n_controls_used_5nn"],
                         "sensitivity": jt["sensitivity"],
                         "placebo": {k: v for k, v in jt["placebo"].items() if k != "draws"},
                         "max_abs_smd_before": float(jt["balance"]["before (all CPS)"].abs().max()),
                         "max_abs_smd_ipw": float(jt["balance"]["after IPW"].abs().max()),
                         "max_abs_smd_5nn": float(jt["balance"]["after 5-NN matching"].abs().max())}
    if with_dowhy:
        from .refute import dowhy_analysis

        M["job_training"]["dowhy"] = dowhy_analysis(data.nsw_observational(), n_sims=20 if quick else 100)

    # 4 ---------------------------------------------------------------- Prop 99
    tb = cases.tobacco()
    _save(viz.prop99_main(tb["fit"], tb["did_vs_average"]), "07_prop99_synth.png")
    _save(viz.prop99_placebos(tb["placebos"]), "08_prop99_placebos.png")
    _save(viz.prop99_robustness(tb["fit"], tb["leave_one_out"], tb["placebo_in_time"]), "09_prop99_robustness.png")
    r = tb["fit"]
    _num(r.path, 3).to_csv(REPORTS / "prop99_path.csv", index=False)
    dv = tb["did_vs_average"]
    M["tobacco"] = {"weights": r.weights[r.weights > 0.001].round(3).to_dict(), "v": r.v.round(3).to_dict(),
                    "predictors": _num(r.predictors, 3).to_dict("index"),
                    "effect_1989_2000": tb["effect_1989_2000"], "effect_2000": tb["effect_2000"],
                    "relative_effect_2000": tb["relative_effect_2000"], "pre_rmspe": tb["pre_rmspe"],
                    "post_rmspe": r.rmspe(True), "ratio": r.ratio, "p_values": tb["p_values"],
                    "did_vs_average_effect": float(dv[dv.year >= 1989].did_gap.mean()),
                    "placebo_in_time_effect": tb["placebo_in_time"].effect(),
                    "leave_one_out": _num(tb["leave_one_out"].drop(columns="path"), 3).to_dict("records"),
                    "ca_1988": tb["ca_1988"],
                    "published_adh_weights": {"Utah": 0.334, "Nevada": 0.234, "Montana": 0.199, "Colorado": 0.164,
                                              "Connecticut": 0.069},
                    "pysyncon_crosscheck": synth.pysyncon_crosscheck(tb["data"])}

    # 5 ---------------------------------------------------------------- simulations
    sims = simulate.run_all(0.5 if quick else 1.0)
    _save(viz.simulations(sims), "10_simulations.png")
    M["simulations"] = {k: _num(v, 3).to_dict("index") for k, v in sims.items()}

    (REPORTS / "metrics.json").write_text(json.dumps(M, indent=2, default=lambda o: o.item()
                                                     if isinstance(o, np.generic) else str(o)))
    return M


def main(argv=None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--quick", action="store_true")
    p.add_argument("--no-dowhy", action="store_true")
    a = p.parse_args(argv)
    M = build(quick=a.quick, with_dowhy=not a.no_dowhy)
    print(json.dumps({"minimum_wage": M["minimum_wage"]["regression"], "organ": M["organ_donation"]["main"],
                      "job_training": M["job_training"]["estimates"], "tobacco": M["tobacco"]["effect_1989_2000"]},
                     indent=1, default=str)[:2500])
    print("-> reports/")


if __name__ == "__main__":
    main()
