# ADR 0039 — Structural detectors run as a governed stage

**Status:** Accepted
**Date:** 2026-10-17

## Context

`server/detectors.py` (ADR-less, shipped 2026-10-17) finds structural problems a
dataset's own documentation does not admit: a key that identifies nothing, columns
that all encode one split, a rate that is a placeholder for a subgroup, a name
promising a scale its values do not use, a total that is not its parts, periods too
uneven to compare.

Those findings only matter if they reach the reader. A diagnostic that returns a
list to its caller can be dropped between the detector and the report, and the
reader never learns that the figure above was computed on a key that identifies
nothing. The engine already has a mechanism for evidence that cannot be dropped:
the ADR 0020 stage contract, whose results are chained by provenance, audited by
the Validation Expert for evidence and jargon, and embedded in the report the
approval gate binds to.

The maintenance product (ADR 0036) needs this most, because its headline claims
are exactly the ones the structural findings restrict.

## Decision

1. **The detectors run as a stage**, `server/maintenance/governance.py`, registered
   through the existing ADR 0020 plugin seam. Each finding becomes a calculation
   carrying the numbers it fired on, and a claim citing that calculation. Nothing
   bypasses provenance, validation or the report.

2. **Claims ship in English and Arabic.** A high-severity finding is a `warning`
   and a medium one a `limitation`, so the report distinguishes a restriction on
   what may be concluded from a qualification of it.

3. **The stage does not fail the run by default.** A structural finding restricts
   what may be concluded; it is not a reason to refuse to compute. `fail_on_high`
   inverts this for a pipeline feeding an automated decision.

4. **It reports what it did not check.** The identity and leakage detectors are
   quadratic in the columns, so above a cell budget they are skipped and each skip
   is a named quality check. A diagnostic stage that hides its own gaps is worse
   than none.

5. **It is opt-in, not default.** Registering it is a configuration decision, so
   existing installations are unchanged. This ADR records the design; enabling it
   by default would be a separate behaviour change.

6. **A finding is keyed by the function that produced it.** Anything consuming
   findings matches them to detectors by that name, and a mismatch produces a
   quality check that fails while reporting it found nothing — which happened, and
   is now covered by a regression test in both suites.

## Consequences

A structural finding now travels as evidence rather than as a note. On the Team 3
maintenance panel the stage produces 16 calculations, 14 claims and 7 quality
checks, and `stages.validate_result` accepts the output unchanged.

The separation of `server/detectors.py` from `server/maintenance/` is preserved and
load-bearing: the detectors stay domain-agnostic and transfer to data nobody has
seen, while the stage supplies the maintenance framing, the bilingual text and the
policy. A second domain would add its own stage over the same detectors.

The cell budget means a very wide table silently loses the two most valuable
detectors unless the operator reads the quality checks. That is the cost of not
letting a stage run for minutes; the skip is reported by name so it is visible
rather than silent.

## Registering it

```json
{"stages": [{"path": "server.maintenance.governance.MaintenanceGovernance",
             "options": {"fail_on_high": false}}]}
```

or `AGENTIC_OS_STAGES=server.maintenance.governance.MaintenanceGovernance` for the
default options.
