# 01 · Potential outcomes: why "did it work?" is hard

## The question

In 1976–77 the National Supported Work (NSW) programme gave disadvantaged men 9–18 months of paid work
experience. Did it raise their earnings?

The obvious comparison: earnings of participants vs everyone else. Using 15,992 men from the Current Population
Survey (CPS) as "everyone else":

| | 1978 earnings |
|---|---|
| NSW participants | $6,349 |
| CPS men | $14,847 |
| **difference** | **−$8,498** |

Taken at face value, the programme cost each participant $8,500 a year. But NSW was also run as a **randomised
experiment**: applicants were randomly admitted or turned away. Comparing admitted and turned-away applicants:
**+$1,794** (SE $671). The programme *raised* earnings. The naive comparison was wrong by more than $10,000, and
it got the sign wrong.

## Potential outcomes

Each person has two potential outcomes: Y(1), earnings if they join, and Y(0), earnings if they don't. The effect
for that person is Y(1) − Y(0). We only ever see one of them. That is the **fundamental problem of causal
inference**: causal inference is a missing-data problem.

What we *can* compute is the difference in averages between groups, which decomposes as:

```
E[Y | D=1] − E[Y | D=0]  =  E[Y(1) − Y(0) | D=1]   +   ( E[Y(0) | D=1] − E[Y(0) | D=0] )
   observed difference        effect on the treated            selection bias
     −$8,498          =          ≈ +$1,794            +            ≈ −$10,300
```

**Selection bias** is the difference between the groups *had nobody been treated*. NSW targeted men with little
work history; their earnings would have been far below the average CPS man's anyway. The comparison mixes the
programme's effect with who signed up.

Randomisation makes selection bias zero on average: a coin flip doesn't know your earnings potential. Every method
in this casebook is a strategy for making selection bias (approximately) zero **without** a coin flip, and each
one needs an assumption you have to defend.

## ATE vs ATT

- **ATE**: the average effect if *everyone* were treated.
- **ATT**: the average effect on those who *were* treated. Usually the policy question ("did the programme help
  the people in it?") and what matching/weighting estimate here.

## Three pictures of confounding (DAGs)

A directed acyclic graph (DAG) draws what causes what:

```
 Confounder: control for it            Mediator: don't control for it       Collider: never control for it
   past earnings                         D ──► hours worked ──► Y               D ──► got an interview ◄── Y
    │        │
    ▼        ▼
    D ──────► Y
```

- **Confounder**: causes both treatment and outcome (past earnings → joined NSW; past earnings → future earnings).
  Must be adjusted for.
- **Mediator**: on the path from treatment to outcome. Adjusting for it removes part of the effect you want.
- **Collider**: caused by both treatment and outcome. Adjusting for it *creates* bias.

"Control for everything" is wrong; "control for the confounders, and only those" is right, and needs domain
knowledge.

## The strategies, and the assumption each one needs

| Strategy | Idea | Key assumption | Case here |
|---|---|---|---|
| Randomised experiment | coin flip decides treatment | (by design) | NSW experiment = benchmark |
| **Difference-in-differences** | compare *changes* over time, treated vs control | parallel trends: without treatment, the two groups would have changed by the same amount | minimum wage, organ donation |
| **Matching / weighting** | compare treated with *similar* untreated units | no unmeasured confounders + overlap | job training |
| **Synthetic control** | build a weighted twin from untreated units | the twin that matched before keeps tracking after; no shocks only to the treated unit | California tobacco tax |
| Instrumental variables, regression discontinuity | use an "as-if random" nudge or cutoff | exclusion restriction / continuity | not covered (see lesson 06) |

None of these assumptions can be proven from data. What you *can* do is test their observable implications
(pre-trends, balance, placebos), and show how wrong they would have to be to change the conclusion. That is
lesson 05.

## Why this project has a benchmark

LaLonde (1986) asked exactly this: if we throw away the experiment's control group and use survey data instead,
do econometric methods recover the experimental answer? His answer was "mostly no", and it reshaped empirical
economics. Dehejia & Wahba (1999) showed propensity-score methods did much better on a subsample. Lesson 03
re-runs that horse race. Having the true answer is rare; it's what makes this dataset the standard test.

Next: [02 · Difference-in-differences](02_difference_in_differences.md)
