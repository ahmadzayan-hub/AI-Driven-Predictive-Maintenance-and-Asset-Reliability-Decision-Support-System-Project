# Which way is better is declared, not inferred

- Status: accepted
- Date: 2026-10-20
- Adds an optional `better` field to a metric glossary entry
  (`server/metrics.py`) and changes the options the prescriptive stage offers
  (`server/analytics.py`). Extends ADR 0011, the glossary.

## Problem

The capstone dataset was run here through the governed pipeline with a column
mapping: measure `Downtime_Hours`, broken down by `Asset_Class`. Validation
passed, 47 claims all traced to calculations, and the recommendation was:

> We recommend: Protect the leading Asset_Class: "Railway Signalling". It is
> worth about 2,170 in Downtime_Hours — more than any other option we compared.

Railway Signalling is where the most hours are being lost. The product's
headline advice was to protect it.

The prescriptive stage took the largest group and called it the thing to
protect, and the smallest and called it the thing to grow. That is sound for
revenue and backwards for downtime, cost, failures, overdue work orders and
every other measure a maintenance product exists to reduce — which is to say,
backwards for most of this product's subject matter. The validator did not
object because there is nothing arithmetically wrong with it: every figure
reconciles and every claim cites a calculation. The defect is in what the
sentence means, and no check in this repository reads meaning.

Direction was already understood elsewhere — `maintenance/performance.py`,
`modelling.py` and `executive_export.py` all carry higher/lower-is-better for
KPI targets and colours — and the narrative stages knew nothing about it. Nor
was the assumption written down anywhere: `docs/KNOWN_LIMITATIONS.md` described
the stage as ranking "where the leverage is" without saying it assumed more was
always better.

## Decision

A glossary entry may declare `better` as `"higher"` or `"lower"`. Anything else
is refused with a sentence naming the metric, and leaving it out stays a normal
state. The prescriptive stage then has three behaviours:

| Declared | Largest group | Smallest group | Segment moving against the grain |
| --- | --- | --- | --- |
| `higher` | Protect the leading … | Grow the smallest … | Reverse the decline in … |
| `lower` | Reduce the largest source of … | *not offered* | Curb the increase in … |
| nothing | Act on the largest source of … | Act on the smallest source of … | Act on the largest movement against the overall direction … |

Three things follow from that table and are the point of it:

- **Undeclared, the stage states size and withholds the verb.** The number is
  unchanged — the ranking is still 10% of each option's base value — and a
  limitation claim says so in both languages: no entry declares whether a
  higher or lower measure is better, so these options are ranked by the size of
  the change they would make, not by the benefit of making it.
- **Where less is better, growing the smallest source is not offered at all.**
  "Grow the smallest site by downtime hours" is advice to cause more downtime;
  dropping the option is more honest than rewording it.
- **The segment to look at flips.** With less better, the segment moving
  against the desired direction is the one that rose, not the one that fell.

The glossary is the right home because this is the same kind of statement as
certification and ownership: somebody decides it and is accountable for it. It
sits next to the definition, where a reader checking what the number means also
learns which way is good news.

**Rejected: inferring direction from the column name.** A list of words like
downtime, cost, failure and backlog would have required no declaration from
anyone, and would be wrong on `Preventive_Maintenance_Ratio`,
`First_Time_Fix_Rate`, `Availability_Pct` and `Reliability_Index` — all of which
are better higher and none of which look it to a word list. This project
already refuses to guess which column is the measure (ADR 0011); guessing which
direction is good news is the same mistake with a worse failure mode, because
the guess appears in a recommendation rather than in a reported decision.

**Rejected: reading it from the KPI target layer.** `maintenance/performance.py`
holds a direction per target, but targets are configured against a run that
already exists, and the prescriptive stage runs inside that run. The data is not
there yet when the sentence is written.

## What this is worth, measured

Watched failing first, then passing:

- `tests/test_metrics.py`, three new tests: `better: "Lower"` is accepted and
  normalised to `lower`; an absent field stays `None`; `better: "up"` is refused
  with a sentence naming the metric and both allowed words. **32 tests, all
  passing.**
- `tests/test_analytics.py`, a new `MeasureDirectionTestCase` of five tests: an
  undeclared direction offers `largest_source`, no option title contains
  "Protect" or "Grow", and the limitation claim is present; `lower` reduces the
  largest source and offers nothing that grows the smallest; `lower` curbs the
  biggest increase rather than reversing the biggest decline; `higher` keeps the
  old behaviour and arithmetic (750 and 300 totals, 75.00 and 30.00 gains); and
  the declared direction reaches the stage from the glossary. **78 tests, all
  passing** on the merged tree, two of them the parallel session's.
- One existing test changed rather than added: the ranking test ran without a
  glossary, so its keys are now `largest_source` and `smallest_source`. The
  figures it checks are untouched, which is the evidence that this change moves
  words and not arithmetic.

The full-suite result for this session is in
[README testing](../../README.md#testing).

Re-run live against the same dataset with no glossary, the recommendation now
reads "Act on the largest source of Asset_Age_Years" and carries the limitation
claim. The "Protect the leading …" sentence is gone from an undeclared measure.

## Consequences

- A deployment with no glossary — which is every deployment, since none ships —
  gets size-ranked options and an explicit statement that they are size-ranked.
  That is a visible loss of confidence in the output, and it is the honest one:
  the product never knew the direction, and now it says so instead of implying
  the opposite.
- Declaring `better` is how an owner gets the stronger wording back, and it
  costs one line beside a definition they already have to write.
- Only the prescriptive stage reads the field. The descriptive, diagnostic and
  predictive headlines still describe movement without judging it ("down 44%
  over the period"), which was already direction-neutral, and the dashboard's
  performance colours keep their own per-target directions (dated decision
  `2026-10-20-semantic-performance-colors.md`). Those two places now have
  overlapping knowledge of the same fact, declared in different files; unifying
  them is not attempted here.
- The three options are still scored by the same 10% assumption, so the ranking
  is still about size. Direction decides what the product is willing to call an
  improvement, not how options are ordered.
- `docs/UI_GENERATION_PROMPT.md` and `docs/UI_PROMPT_CODEGEN.md` quoted the old
  sentence as example output and now quote the new one, with the declared-higher
  variant named beside it.
