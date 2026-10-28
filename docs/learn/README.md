# Learning path

This is the sequel to the A/B testing toolkit. There, *you* randomised, so a difference between groups was the
effect. Here nobody randomised: a state changed a law, a city ran a campaign, people chose to join a programme.
The lessons show how to still get a credible answer to *"did it work?"* and how to say how sure you are.

| # | Lesson | Case | You will be able to... |
|---|---|---|---|
| 01 | [Potential outcomes and why "did it work?" is hard](01_potential_outcomes.md) | job training | explain selection bias with a real -$8,498 vs +$1,794 example; name the assumption behind every method |
| 02 | [Difference-in-differences](02_difference_in_differences.md) | minimum wage, organ donation | estimate DiD three ways, test parallel trends, do inference with one treated unit |
| 03 | [Propensity scores, matching and weighting](03_propensity_scores.md) | job training | check overlap and balance, compare matching / IPW / doubly robust, run a sensitivity analysis |
| 04 | [Synthetic control](04_synthetic_control.md) | California tobacco tax | build a synthetic twin, read placebo tests, explain why it beats a plain average |
| 05 | [Robustness and refutation](05_robustness_and_refutation.md) | all | design placebo tests, use DoWhy's refuters, validate estimators with simulation |
| 06 | [Choosing a method and presenting it](06_choosing_a_method.md) | all | pick the method that fits the data, and write the one-page answer a manager reads |
| 07 | [Interview questions](07_interview_questions.md) | all | answer the causal-inference questions asked in product, economics and consulting interviews |

Run the code next to each lesson: `casebook case minwage`, `casebook case organ`, `casebook case training`,
`casebook case tobacco`, `casebook simulate`.

## Notation used throughout

| Symbol | Meaning |
|---|---|
| D | treatment indicator (1 = treated: NJ store, NSW participant, California) |
| Y(1), Y(0) | potential outcomes: the outcome *with* and *without* treatment for the same unit |
| ATE | average treatment effect, E[Y(1) − Y(0)] over everyone |
| ATT | average treatment effect on the treated, E[Y(1) − Y(0) \| D = 1]: "did it work for those who got it?" |
| FTE | full-time-equivalent employees = full-time + managers + ½ part-time |
| SE, CI | standard error; 95% confidence interval ≈ estimate ± 1.96 SE |
