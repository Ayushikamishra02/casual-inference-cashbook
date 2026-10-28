"""Load the four case-study datasets as tidy pandas DataFrames.

| Case | Data | Source |
|---|---|---|
| Minimum wage (DiD) | Card & Krueger (1994): 410 fast-food restaurants in NJ and eastern PA, Feb + Nov 1992 | public.dat from David Card's site, via a GitHub mirror (sha256-checked) |
| Organ donation (event study) | The Effect (Huntington-Klein): organ-donor registration rate, 27 states x 6 quarters | `causaldata` package |
| Job training (matching) | LaLonde (1986) / Dehejia-Wahba NSW experiment + CPS comparison group | `causaldata` package (The Mixtape) |
| Tobacco tax (synthetic control) | Abadie, Diamond & Hainmueller (2010): cigarette sales, 39 states, 1970-2000 | GitHub mirror (sha256-checked) |
"""
from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"

DOWNLOADS = {   # local name: (url, sha256)
    "card_krueger.rda": ("https://raw.githubusercontent.com/iangow/lmwr/master/data/cardkrueger.rda",
                         "9efe776a84281463111cddc13577795a49c2b1327b3f40cbab63ee62fe3017c4"),
    "prop99_smoking.csv": ("https://raw.githubusercontent.com/OscarEngelbrektson/SyntheticControlMethods/master/"
                           "examples/datasets/smoking_data.csv",
                           "d1b537fc9b69bee16ddee19b92869fd1632afa17f3b0744ae72ba2506da7b582"),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(name: str) -> Path:
    """Download a raw file once, verify its checksum, return the local path."""
    url, sha = DOWNLOADS[name]
    path = RAW / name
    if not path.exists() or _sha256(path) != sha:
        RAW.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, path)
        if _sha256(path) != sha:
            path.unlink(missing_ok=True)
            raise RuntimeError(f"checksum mismatch for {name} ({url})")
    return path


# --------------------------------------------------------------------------------------------- 1. minimum wage
CHAINS = {1: "Burger King", 2: "KFC", 3: "Roy Rogers", 4: "Wendy's"}
TEMP_CLOSED = {2, 4, 5}      # status2: closed for renovation / highway construction / mall fire
PERM_CLOSED = 3


def card_krueger() -> pd.DataFrame:
    """One row per restaurant (wide). FTE = full-time + managers + 0.5 x part-time, as in the paper."""
    import pyreadr

    d = pyreadr.read_r(str(fetch("card_krueger.rda")))["cardkrueger"]
    out = pd.DataFrame({
        "store_id": d["sheet"].astype(int),
        "chain": d["chain"].map(CHAINS),
        "co_owned": d["co_owned"].astype(bool),
        "state": np.where(d["state"] == 1, "NJ", "PA"),
        "nj": d["state"].astype(int),
        "region": np.select([d.southj == 1, d.centralj == 1, d.northj == 1, d.pa1 == 1, d.pa2 == 1],
                            ["south NJ", "central NJ", "north NJ", "PA (near Philadelphia)",
                             "PA (Allentown-Easton)"], "unknown"),
        "shore": d.shore.astype(bool),     # Jersey shore (overlaps the three NJ regions)
        "fte_before": d.empft + d.nmgrs + 0.5 * d.emppt,
        "fte_after": d.empft2 + d.nmgrs2 + 0.5 * d.emppt2,
        "wage_before": d.wage_st,
        "wage_after": d.wage_st2,
        "price_before": d.psoda + d.pfry + d.pentree,     # price of a standard meal: soda + fries + entree
        "price_after": d.psoda2 + d.pfry2 + d.pentree2,
        "hours_before": d.hrsopen,
        "hours_after": d.hrsopen2,
        "status_after": d.status2.astype("Int64"),
    })
    out["temp_closed"] = out.status_after.isin(TEMP_CLOSED)
    out["perm_closed"] = out.status_after.eq(PERM_CLOSED)
    # Card & Krueger's "gap" measure: how far a store's starting wage had to rise to reach the new $5.05 minimum
    out["wage_gap"] = np.where(out.nj == 1, np.maximum(0, 5.05 - out.wage_before) / out.wage_before, 0.0)
    return out


def card_krueger_long() -> pd.DataFrame:
    """Two rows per restaurant (before/after) for regression DiD."""
    w = card_krueger()
    keep = ["store_id", "chain", "co_owned", "state", "nj", "region", "wage_gap"]
    rows = []
    for t, suffix in [(0, "before"), (1, "after")]:
        p = w[keep].copy()
        p["post"] = t
        p["fte"] = w[f"fte_{suffix}"]
        p["wage"] = w[f"wage_{suffix}"]
        p["price"] = w[f"price_{suffix}"]
        rows.append(p)
    return pd.concat(rows, ignore_index=True)


# --------------------------------------------------------------------------------------------- 2. organ donation
def organ_donations() -> pd.DataFrame:
    """California made organ-donor sign-up 'active choice' at the DMV in July 2011 (Q3 2011)."""
    from causaldata import organ_donations as od

    d = od.load_pandas().data.rename(columns={"State": "state", "Quarter": "quarter", "Rate": "rate",
                                               "Quarter_Num": "t"})
    d["state"] = d["state"].astype(str)
    d["quarter"] = d["quarter"].astype(str)
    d["california"] = (d.state == "California").astype(int)
    d["post"] = (d.t >= 4).astype(int)            # Q3 2011 is quarter 4 of 6
    d["treated"] = d.california * d.post
    return d


# --------------------------------------------------------------------------------------------- 3. job training
COVARIATES = ["age", "educ", "black", "hisp", "marr", "nodegree", "re74", "re75"]


def _nsw_clean(d: pd.DataFrame, sample: str) -> pd.DataFrame:
    d = d.drop(columns="data_id").astype(float)
    d["treat"] = d["treat"].astype(int)
    d["u74"] = (d.re74 == 0).astype(int)        # unemployed (no earnings) in 1974 / 1975
    d["u75"] = (d.re75 == 0).astype(int)
    d["sample"] = sample
    return d


def nsw_experiment() -> pd.DataFrame:
    """The randomised NSW job-training experiment (Dehejia-Wahba subsample): 185 treated, 260 controls."""
    from causaldata import nsw_mixtape

    return _nsw_clean(nsw_mixtape.load_pandas().data, "experiment")


def nsw_observational() -> pd.DataFrame:
    """NSW *treated* men + 15,992 CPS men as a non-experimental comparison group (LaLonde's setup).
    The experimental controls are dropped: we pretend the experiment never happened."""
    from causaldata import cps_mixtape

    t = nsw_experiment()
    t = t[t.treat == 1].assign(sample="NSW treated")
    c = _nsw_clean(cps_mixtape.load_pandas().data, "CPS")
    return pd.concat([t, c], ignore_index=True)


# --------------------------------------------------------------------------------------------- 4. Prop 99
def prop99() -> pd.DataFrame:
    """Per-capita cigarette sales (packs) in 39 US states, 1970-2000. California passed Proposition 99
    (25-cent tax per pack + anti-smoking campaign) in Nov 1988, effective 1989. The other 38 states had no large
    tobacco-control programme in the period (ADH 2010 dropped states that did)."""
    d = pd.read_csv(fetch("prop99_smoking.csv"))
    d["year"] = d["year"].astype(int)
    d["california"] = (d.state == "California").astype(int)
    return d


def load_all() -> dict[str, pd.DataFrame]:
    return {"card_krueger": card_krueger(), "organ_donations": organ_donations(),
            "nsw_experiment": nsw_experiment(), "nsw_observational": nsw_observational(), "prop99": prop99()}


def main() -> None:
    for k, v in load_all().items():
        print(f"  {k:<20} {v.shape[0]:>7,} rows x {v.shape[1]} columns")


if __name__ == "__main__":
    main()
