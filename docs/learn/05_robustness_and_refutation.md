# 05 · Robustness and refutation: trying to break your own result

An observational estimate is a claim *plus* assumptions you can't fully test. Credibility comes from attacking
the claim in every way you can think of and showing it survives (or reporting honestly where it doesn't). This
lesson collects the checks used across the casebook.

## 1. Placebo tests: look for an effect where there shouldn't be one

| Placebo type | Question | Example here | Result |
|---|---|---|---|
| **Placebo group** | does the method "find" an effect between two untreated groups? | PA region vs PA region | −2.71 FTE, CI includes 0 ✓ |
| **Placebo time** | is there an "effect" before the real treatment date? | organ donation 1 quarter early; Prop 99 in 1980 | −0.002 (p = 0.63) ✓; −2.8 packs vs −18.9 real (small, not zero) |
| **Placebo unit (in space)** | is the treated unit's effect unusual compared with untreated units? | 26 organ states; 38 tobacco states | rank 5/27 (p = 0.19) ✗ weak; rank 1/39 (p = 0.026) ✓ |
| **Placebo treatment** | does a random fake treatment produce an "effect"? | shuffle NSW participation 300× | mean $0, real effect beyond all ✓ |
| **Placebo outcome** | does treatment "affect" something it can't affect? | (e.g. pre-programme earnings as outcome) | (exercise) |

A placebo that *fails* is information, not an embarrassment: the organ-donation result is weaker than its
p < 0.001 suggests, and saying so is the right call.

## 2. Specification robustness: does the answer depend on choices?

Show the estimate across reasonable choices in one figure (the minimum-wage forest plot): with/without controls,
robust vs classical SEs, different samples (balanced panel, closed stores as zero), a different control group
(within NJ), treatment intensity instead of a dummy. If every bar points the same way, say so; if one choice flips
the sign, that choice needs a justification.

For LaLonde, the "specification curve" across 6 estimators runs from $984 to $1,860; the one choice that flips
the sign is dropping pre-programme earnings.

## 3. Sensitivity analysis: how wrong would the assumption have to be?

Placebos test *observable implications*. Sensitivity analysis quantifies the *unobservable* part:

- **Cinelli & Hazlett robustness value** (regression): the strength of a hidden confounder (as partial R² with
  both treatment and outcome) needed to erase the effect. LaLonde regression: **3.1%**, weaker than past
  earnings (4.4%): fragile.
- Others you should know by name: Rosenbaum bounds (matching: how much could hidden bias change the odds of
  treatment?), E-values (epidemiology, for risk ratios), Oster's δ (coefficient stability).

## 4. DoWhy: the four steps made explicit

Microsoft's DoWhy library structures an analysis as **model → identify → estimate → refute**:

```python
model = CausalModel(data=d, treatment="treat", outcome="re78", common_causes=DW_COLUMNS)  # 1. model (a DAG)
estimand = model.identify_effect()                         # 2. identify: backdoor adjustment on the common causes
est = model.estimate_effect(estimand, method_name="backdoor.linear_regression", target_units="att")  # 3.
model.refute_estimate(estimand, est, method_name="placebo_treatment_refuter", placebo_type="permute")  # 4.
```

Results on the NSW-vs-CPS data (`refute.py`, numbers in `reports/metrics.json`):

| | value |
|---|---|
| DoWhy linear regression (ATT) | $1,572, identical to statsmodels with the same covariates (tested) |
| DoWhy propensity weighting (our settings) | $1,747 |
| **DoWhy propensity weighting (library defaults)** | **−$38** |
| refuter: placebo treatment | effect → $62 ✓ (collapses to ~0) |
| refuter: add a random common cause | $1,572 → $1,572 ✓ (unchanged) |
| refuter: random 80% subsets | $1,604 ✓ (stable) |

The −$38 is a lesson in itself: DoWhy clips propensity scores to [0.05, 0.95] by default. With 16,000 CPS controls
whose true scores are ~0.001, clipping makes each of them count ~50× too much, and the effect disappears. **Always
read the defaults of the library you use**, and cross-check one estimate by hand. (DoWhy's refuters also rebuild
the weighting estimator with default settings, so we refute the regression estimate, which has no hidden
parameters.)

What refuters can and can't do: they catch fragile pipelines and coding errors. They can't detect an unmeasured
confounder, because they only perturb the data you have: nothing in them would flag that the analysis *without*
earnings history is wrong by over $5,000.

## 5. Simulation: test the estimator where you know the truth

The most underused check. Generate data from a model where you set the true effect, run the estimator many
times, look at bias and CI coverage (`simulate.py`, `casebook simulate`):

| Scenario | Truth | Result |
|---|---|---|
| DiD, parallel trends hold | 2.0 | mean 2.00, 95% CI covers truth 96% ✓ |
| DiD, treated units on a steeper trend | 2.0 | mean 3.18, coverage **0%** ✗ |
| Confounded selection, naive difference | 1,000 | bias **−6,155** ✗ |
| ... regression adjustment, misspecified | 1,000 | bias +893 ✗ |
| ... IPW / matching / AIPW, right PS model | 1,000 | bias −2 / +5 / −7 ✓ |
| ... IPW with one confounder omitted | 1,000 | bias +1,071 ✗ |
| Factor model, synthetic control vs DiD | −10 | RMSE 1.54 vs 3.25 |

![simulations](../../reports/figures/10_simulations.png)

Simulation tells you the estimator is *implemented* correctly and *when* it fails. It can't tell you which
scenario your real data is in; that's what the placebos and domain knowledge are for.

## 6. Process habits

- **Write the analysis plan before looking at outcomes** (which estimator, controls, sample): it stops you from
  trying specifications until one is significant.
- **Report the pre-period fit / balance first**, the effect second.
- **Replicate a known result** before trusting new code. This repo reproduces Card & Krueger's Table 3 and 4 and
  ADH's donor weights and p-value; the tests fail if those numbers move.

Next: [06 · Choosing a method and presenting it](06_choosing_a_method.md)
