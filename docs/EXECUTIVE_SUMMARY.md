# Executive summary: four "did it work?" questions

*For a non-technical reader. Each answer comes from data where no experiment was run, so each says how it was
checked and how confident to be.*

## 1. Did raising the minimum wage cost jobs? (New Jersey, 1992)

New Jersey raised its minimum wage from $4.25 to $5.05; neighbouring Pennsylvania didn't. Fast-food restaurants
in New Jersey **did not lose jobs relative to Pennsylvania**: they gained about 2.75 full-time-equivalent staff per
store (roughly 13%), while Pennsylvania stores shrank. Wages in New Jersey really did rise (by $0.48), and meal
prices rose a little (about 2%), suggesting costs were partly passed to customers.

**Confidence: moderate.** The result holds across seven ways of measuring it and passes a "fake treatment" check,
but it's one industry, one year, and one before/after comparison, and later studies using other data disagree
about the size.

## 2. Did changing the organ-donor question change sign-ups? (California, 2011)

California started requiring drivers to actively answer the donor question. Registration fell by about
2.25 percentage points (8%) relative to other states.

**Confidence: low.** Standard statistics call this highly significant, but with only one state changing its
policy, a fairer test (comparing California's change with every other state's change over the same months) finds
that 4 other states moved as much without any policy change. Treat it as a warning sign worth monitoring, not a
proven effect.

## 3. Did the job-training programme raise earnings? (NSW, 1976–77)

Participants earned **$8,498 less** than average workers in a national survey, which would suggest the programme
failed. But participants were chosen *because* they had weak work histories. After comparing them only with survey
respondents who had similar backgrounds and, crucially, similar earnings in the two years before, the programme is
estimated to have **raised earnings by about $1,600–1,900 a year**. A real randomised trial of the same programme
found **$1,794**, so the method worked here.

**Confidence: moderate, with a big condition.** If past earnings had not been recorded, every method would have
concluded the programme *cut* earnings by about $3,500. Lesson for any business analysis of an opt-in programme:
results are only as good as the background information you have on who opted in.

## 4. Did California's tobacco tax and anti-smoking campaign cut smoking? (Proposition 99, 1989)

We built a "synthetic California" from five states (Utah, Nevada, Montana, Colorado, Connecticut) whose combined
cigarette sales tracked California's almost exactly for 19 years before the law. After 1989 California fell far
below its twin: **19 fewer packs per person per year on average, and 26 fewer (−38%) by 2000.**

**Confidence: high.** No other state shows a gap this large relative to how well its twin fitted beforehand
(1 of 39), and leaving out any one of the five comparison states barely changes the answer.

## What this means for decisions

| If you need to know... | Use | Ask your analyst for |
|---|---|---|
| whether a change in some regions/stores worked | before/after vs comparison regions (DiD) | a chart of the pre-period trends, and a fake-date check |
| whether an opt-in programme works | matched comparison (propensity scores) | what pre-programme information was used, and how strong a missing factor would have to be to change the answer |
| whether a launch in one market worked | synthetic twin market | how closely the twin matched before launch, and the placebo-market ranking |

And when the decision is big and the change hasn't happened yet: **run an experiment instead.**
