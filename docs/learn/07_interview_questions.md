# 07 · Interview questions

Answer out loud in 30–60 seconds: the idea, an example from this repo, the caveat.

## The project

**"Walk me through this project."**

> It's a casebook of causal inference on observational data, the follow-up to my A/B testing work. I took four
> classic questions where nobody could randomise (a minimum-wage increase, a change to organ-donor sign-up, a
> job-training programme and California's tobacco tax) and answered each with the method that fits: DiD,
> propensity-score methods, and synthetic control, which I implemented from scratch. Each result is replicated
> against the published paper or an experimental benchmark, and each comes with placebo tests, sensitivity
> analysis and simulations with known effects. The headline lessons: methods recover the experimental answer on
> the job-training data only when pre-programme earnings are measured; and with a single treated state, a
> "p < 0.001" DiD became p = 0.19 under permutation inference.

**"What's the most interesting thing you found?"** Dropping one variable (pre-programme earnings) turns every
method's +$1,000–1,900 into about −$3,500, with tight CIs. Confident and wrong. The estimator matters much less
than the confounders you measure.

## Concepts

**Correlation vs causation, with an example.** NSW participants earned $8,498 less than survey respondents, but
the programme raised earnings by $1,794. The gap was selection: the programme targeted people with weak work
histories.

**What is selection bias?** The difference between groups that would exist even without treatment:
E[Y(0)|D=1] − E[Y(0)|D=0].

**ATE vs ATT?** Effect averaged over everyone vs over the treated. Policy evaluation usually wants ATT ("did it
help those it reached?"); matching/IPW here estimate ATT.

**What's a confounder? A collider?** Confounder: causes treatment and outcome (control for it). Collider: caused
by both (controlling for it creates bias, e.g. analysing only people who got a job interview).

## Difference-in-differences

**Explain DiD in one sentence.** The treated group's change minus the control group's change, which removes
fixed differences between groups and common shocks over time.

**Key assumption, and how do you check it?** Parallel trends. Check pre-trends (event study), placebo groups and
placebo dates, a second control group. You can never fully test it.

**Why cluster standard errors?** Repeated observations of the same unit are correlated; ignoring it understates
uncertainty. Cluster at the level treatment is assigned.

**What if only one unit is treated?** Clustered SEs are unreliable; use permutation (randomisation) inference.
Organ donation: clustered p < 0.001, permutation p = 0.19.

**What's wrong with TWFE under staggered adoption?** It uses already-treated units as controls for later-treated
ones; with effects that change over time this can bias or flip the sign (Goodman-Bacon). Use Callaway–Sant'Anna,
Sun–Abraham, or stacked DiD.

**Card & Krueger in two sentences?** NJ raised its minimum wage, PA didn't; fast-food employment rose slightly in
NJ relative to PA (+2.75 FTE per store), contradicting the simple prediction of job losses. It's contested (other
data sources found small negative effects), and it made natural experiments mainstream.

## Propensity scores

**What is a propensity score and why use it?** P(treated | X). Balancing on it balances X (Rosenbaum–Rubin), so
you match on one number instead of many.

**How do you know your propensity model is good?** Covariate balance after matching/weighting (|SMD| < 0.1),
not AUC. A model that predicts treatment perfectly signals *no overlap*, which is bad.

**Matching vs IPW vs doubly robust?** Matching: intuitive, discards data, bootstrap not strictly valid. IPW: uses
all data, unstable with extreme weights. Doubly robust: consistent if either the outcome or the propensity model
is right; usually the default.

**What's overlap and what do you do without it?** Every treated unit needs comparable controls. Trim to common
support, and say the effect applies only to that population.

**Can matching fix unobserved confounding?** No. Only the covariates you have are balanced; that's why
sensitivity analysis exists.

## Synthetic control

**When would you use it?** One or few treated aggregate units (a state, a market), a long pre-period, many
untreated units.

**Why weights that are non-negative and sum to one?** Interpolation, not extrapolation; transparent weights you
can sanity-check.

**How do you get a p-value?** Placebo-in-space: apply the method to every untreated unit, rank the treated
unit's post/pre RMSPE ratio. Prop 99: 1st of 39, p = 0.026.

**What can go wrong?** Poor pre-fit, a treated unit outside the donors' range, spillovers to donors, other
shocks to the treated unit, non-convex optimisation (different solutions; I cross-checked with pysyncon).

## Product / business framing

**"We launched a feature in Brazil only. Did it work?"** Synthetic control (or CausalImpact) on Brazil vs other
markets' pre-period trends, with placebo markets; or DiD if there's a comparable set of markets.

**"Users who use feature X retain better. Should we push X?"** Selection: engaged users adopt X. Use pre-period
engagement as covariates (matching/IPW), run a sensitivity analysis, ideally run an encouragement experiment
(randomly promote X) and use it as an instrument.

**"Marketing ran a campaign in 3 cities. What was the lift?"** DiD with matched control cities, event-study plot,
permutation inference over cities (few treated units), check spillovers (people in control cities seeing ads).

**How would you convince a sceptical stakeholder?** Show the pre-period (trends / fit / balance) first, then the
effect, then the placebos, then what would have to be true for the result to be wrong.
