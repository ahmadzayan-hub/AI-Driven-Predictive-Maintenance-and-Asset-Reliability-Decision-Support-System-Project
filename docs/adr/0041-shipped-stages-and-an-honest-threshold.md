# ADR 0041 — The shipped registry, and a threshold that does not read the holdout

**Status:** Accepted
**Date:** 2026-10-18

## Context

A project review on 18 October found two problems that are separate in the code
and the same problem in substance: the careful path was unreachable, and the
reachable path flattered itself.

1. **The maintenance stages were registered nowhere.** ADR 0039 added
   `MaintenanceGovernance` and ADR 0040 added `MaintenanceRisk`. Both load, both
   are tested, and both were absent from `config.json`, whose `stages` list named
   only the four generic models of ADR 0033. A stage that no configuration
   registers cannot be chosen by a run, so neither the domain's governed
   diagnostics nor its timing-curated models could be selected in the product.
   The Runs view has had a pipeline-profile selector since ADR 0020; it had
   nothing maintenance-shaped to offer it.

2. **The generic classifier set its label from every row.** With no explicit
   target, `ClassificationModel` labels a record by whether its measure falls in
   the top quarter, and it computed that quartile over the whole table before
   splitting off the held-out fifth. The threshold is part of the model, so
   taking it from every row reads the outcomes the model is about to be scored
   on. Observed on a table whose last two periods were multiplied by 50, the
   threshold moved from 40.00 to 47.00 — the held-out values alone decided what
   counted as "top quarter" in training.

ADR 0040 had already established that an input's timing governs whether it may
enter a maintenance model. The same principle had not been applied to the
*label*, nor had the engine's own configuration been checked against the ADRs
that described it.

## Decision

1. **The shipped configuration registers every stage this repository ships.**
   `config.json` names the two maintenance stages beside the four generic models,
   and adds a `maintenance` profile holding `maintenance_governance` and
   `maintenance_risk`.

2. **Registering is not enabling.** The `default` profile stays empty, so an
   ordinary run behaves exactly as it did before. ADR 0039's opt-in decision is
   unchanged: what changes is that the opt-in is now expressible. Making these
   stages automatic would be a further behaviour change needing its own record.

3. **The maintenance stages stay out of the `models` profile.** The generic
   models are exploratory and say so; the maintenance models enforce the
   contract's input timing. Running both under one name would hide which verdict
   came from which set of rules.

4. **A derived label's threshold is computed from the training rows alone.** The
   split is taken first, the quartile second. Changing a held-out outcome can no
   longer move the threshold, the training labels, or the scaler fitted on them.
   An explicitly named target column is unaffected: it was never derived from the
   measure.

5. **The shipped registry is tested, not asserted.** `tests/test_stages.py` loads
   the real `config.json` rather than a fixture, and fails if a profile names an
   unregistered stage, if a shipped stage stops loading, or if the default profile
   stops being empty.

## Consequences

The `maintenance` profile is selectable from the Runs view with no frontend
change, because the profile selector reads the registry from `/api/pipelines`.
The bilingual strings it needs (`runs.profile` and its help text) already ship in
English and Arabic.

The classifier's reported threshold now differs from previously recorded runs
whenever the measure's distribution shifts across the split — which is exactly
the case where the old figure was wrong. Scores on such data will generally be
lower and are the first honest ones. The four modelling tests that assert the
classifier's behaviour pass unchanged, so nothing else depended on the leak.

Point 4 was found by reading the code against ADR 0040's own principle, and
confirmed by running the two tables above rather than by inspection. The
regression test fails against the previous ordering.

What this does not do: it does not bind the maintenance KPI register to a run or
to the executive view, and it does not make the maintenance profile the default.
The KPI register's missing-value policy is a separate defect, recorded in ADR
0042.
