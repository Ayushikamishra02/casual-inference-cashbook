"""Command line: `casebook <command>`.

    casebook data              download/verify the datasets and print their sizes
    casebook report [--quick]  run all four cases + simulations; figures, tables, reports/metrics.json
    casebook case NAME         print one case's main results (minwage | organ | training | tobacco)
    casebook simulate          estimator checks on simulated data with known effects
"""
from __future__ import annotations

import argparse
import warnings

import pandas as pd


def _print_case(name: str) -> None:
    from . import cases

    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", 12)
    if name == "minwage":
        r = cases.minimum_wage()
        print(r["table"].round(2).to_string(), "\n")
        print(r["robustness"].round(3).to_string(index=False))
    elif name == "organ":
        r = cases.organ_donation()
        print(r["main"].as_dict())
        print(r["event_study"].round(4).to_string(index=False))
        print({k: v for k, v in r["permutation"].items() if k != "placebo_effects"})
    elif name == "training":
        r = cases.job_training(n_boot=100, n_perm=0)
        print("experimental benchmark:", {k: round(v, 1) for k, v in r["benchmark"].items()})
        print(r["estimates"].round(0).to_string())
        print("\nwithout pre-programme earnings:\n", r["no_earnings"].round(0).to_string())
    elif name == "tobacco":
        r = cases.tobacco()
        w = r["fit"].weights
        print(w[w > 0.001].round(3).to_string())
        print(f"\neffect 1989-2000: {r['effect_1989_2000']:.1f} packs/person/year; 2000: {r['effect_2000']:.1f}")
        print("permutation p-values:", {k: round(v, 3) for k, v in r["p_values"].items()})


def main(argv: list[str] | None = None) -> None:
    warnings.filterwarnings("ignore")
    p = argparse.ArgumentParser(prog="casebook", description="Causal inference casebook")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("data")
    r = sub.add_parser("report")
    r.add_argument("--quick", action="store_true")
    r.add_argument("--no-dowhy", action="store_true")
    c = sub.add_parser("case")
    c.add_argument("name", choices=["minwage", "organ", "training", "tobacco"])
    sub.add_parser("simulate")
    a = p.parse_args(argv)
    if a.cmd == "data":
        from .data import main as data_main

        data_main()
    elif a.cmd == "report":
        from .report import main as report_main

        report_main((["--quick"] if a.quick else []) + (["--no-dowhy"] if a.no_dowhy else []))
    elif a.cmd == "case":
        _print_case(a.name)
    elif a.cmd == "simulate":
        from .simulate import run_all

        for k, v in run_all().items():
            print(f"\n== {k}\n{v.round(3).to_string()}")


if __name__ == "__main__":
    main()
