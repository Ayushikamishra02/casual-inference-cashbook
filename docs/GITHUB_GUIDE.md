# Putting this project on GitHub

## 1. Run it on your laptop

```powershell
# Windows PowerShell (macOS/Linux: python3 -m venv .venv && source .venv/bin/activate)
cd causal-inference-casebook
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
casebook data            # downloads 2 small files (~70 KB) and checks them; 2 datasets come with `causaldata`
pytest                   # 20 tests, about 1-2 minutes
casebook case tobacco    # try each case: minwage | organ | training | tobacco
casebook report          # optional: regenerates every figure and reports/metrics.json (~5 min)
```

If `casebook` isn't found, the venv isn't active (your prompt should start with `(.venv)`).
`pytest -m "not slow"` skips the placebo-loop and DoWhy tests for a quicker run.

## 2. Create the repository

1. github.com → **New repository** → `causal-inference-casebook` → Public → no README/.gitignore/license → Create.
2. In the project folder:

```bash
git init
git add .
git status                 # check: data/raw contains only .gitkeep; no .venv
git commit -m "Causal inference casebook: DiD, propensity scores, synthetic control with placebo tests"
git branch -M main
git remote add origin https://github.com/Ayushikamishra02/causal-inference-casebook.git
git push -u origin main
```

The CI badge in the README already points at `Ayushikamishra02/causal-inference-casebook`; change it if you use
another name.

## 3. CI

`.github/workflows/ci.yml` installs the package, downloads the data, runs all tests (including the replications
of Card & Krueger and ADH) and lint on every push.

## 4. Repo page

- **About**: *"Did it work without an experiment? DiD, propensity scores and synthetic control (from scratch) on
  4 classic policy cases, replicated and stress-tested with placebos, sensitivity analysis and DoWhy"*
- **Topics**: `causal-inference` `difference-in-differences` `synthetic-control` `propensity-score`
  `econometrics` `dowhy` `statsmodels` `policy-evaluation` `data-science`
- Pin it next to `ab-testing-toolkit`: together they cover experiments and observational causal inference.

## 5. On your CV / LinkedIn

> **Causal Inference Casebook** (Python, statsmodels, scikit-learn, DoWhy)
> - Estimated policy effects without experiments using difference-in-differences, propensity-score matching/IPW/
>   doubly robust estimation, and a from-scratch synthetic control; replicated Card & Krueger (1994) and Abadie
>   et al. (2010) results exactly.
> - Recovered a randomised-trial benchmark ($1,794) from survey data (IPW $1,860), and showed that omitting one
>   confounder flips every estimate to −$3,500.
> - Stress-tested results with placebo-in-space/time, permutation inference (revealing a p < 0.001 DiD was
>   p = 0.19), Cinelli–Hazlett sensitivity analysis, DoWhy refuters and Monte Carlo simulations.
