# 06 · Choosing a method and presenting the answer

## First question: can you run an experiment?

If yes, do (see the ab-testing-toolkit project). Everything here is for when you can't: the change already
happened, randomising is unethical/illegal/too expensive, or it's a policy that applies to a whole market.

## Decision guide

```
Is treatment assigned to a few big units (states, cities, countries, stores) at one point in time?
├── Yes, ONE or very few treated units, long pre-period ......................... synthetic control
│                                                                                 (+ placebo-in-space p-value)
├── Yes, several treated and control units, before AND after data ............... difference-in-differences
│      └── treatment starts at different times for different units ............. staggered DiD estimators
│                                                                                 (Callaway-Sant'Anna etc.), not plain TWFE
└── No: individuals chose / were selected into treatment
       ├── you observe the variables that drove selection (especially past outcomes)
       │                                                                       ... matching / IPW / doubly robust
       ├── a rule or cutoff decided treatment (score ≥ 600 gets the offer) ...... regression discontinuity
       └── something "as good as random" nudged treatment but affects the outcome
           only through it (distance to a branch, a lottery for an invitation) .. instrumental variables
```

| | DiD | Matching / weighting | Synthetic control |
|---|---|---|---|
| Data needed | treated + control, before + after | rich covariates on individuals | long panel, many untreated units |
| Key assumption | parallel trends | no unmeasured confounders + overlap | the pre-period twin keeps tracking |
| Handles unobserved *fixed* differences | ✓ (they cancel) | ✗ | ✓ (largely) |
| Handles unobserved *time-varying* differences | ✗ | ✗ | partly (if pre-fit is good) |
| Main diagnostic | pre-trends / event study | overlap + balance | pre-period RMSPE |
| Inference | clustered SEs (many clusters) or permutation | bootstrap / robust SEs | placebo-in-space |
| Case here | minimum wage, organ donation | job training | California tobacco |

Methods can be combined: DiD on a matched sample, synthetic DiD (Arkhangelsky et al. 2021), doubly robust DiD
(Sant'Anna & Zhao 2020).

## Presenting it: the one-page answer

Managers and clients don't want a regression table. They want: what happened, how sure we are, what it depends on,
what to do. Template:

> **Question.** Did Proposition 99 reduce cigarette consumption in California?
>
> **Answer.** Yes. By 2000, Californians bought about **26 fewer packs per person per year (−38%)** than our
> best estimate of what would have happened without it; −19 packs a year on average over 1989–2000.
>
> **How we know.** We compared California with a "synthetic California" built from 5 states that matched its
> smoking trend for the 19 years before the law. After 1989, the real and synthetic states diverge sharply.
>
> **How sure.** California's drop is larger, relative to its pre-law fit, than for any of 38 comparison states
> (p = 0.03). Dropping any single comparison state gives −17.5 to −21 packs.
>
> **What it depends on.** No other California-only event in 1989–2000 that cut smoking. Federal changes affect
> all states and cancel out.
>
> **Caveat.** This measures the package (tax + campaign); it can't separate the two.

Do the same for each case: [EXECUTIVE_SUMMARY.md](../EXECUTIVE_SUMMARY.md) has all four.

## Words to use and avoid

| Avoid | Say |
|---|---|
| "proves" | "is strong evidence that", "is consistent with" |
| "significant" (alone) | the size, the CI, and what it means in units people care about |
| "no effect" (when CI is wide) | "we can rule out effects larger than X" |
| "controlling for everything" | "controlling for A, B, C; an unmeasured factor as strong as D could change this" |

Next: [07 · Interview questions](07_interview_questions.md)
