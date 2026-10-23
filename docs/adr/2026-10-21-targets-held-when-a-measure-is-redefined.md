# Targets are held for review when a measure is redefined

Date: 2026-10-21 · Status: Accepted

Closes the open item in the
[register correction](2026-10-21-register-availability-and-pooled-reliability-measures.md):
"stored target policies are not migrated".

## Context

Until 21 October the register published operating over planned hours as
"availability"; it now means `1 - downtime / planned`, and the old quantity
is utilisation. A display target saved for the old meaning (say "good at
95%") now judges a different number and could colour it good or bad on a
basis nobody chose. The earlier record declined to rewrite stored targets,
because the intent behind a stored number cannot be known. Stored policies
carry no date or version, so the server could not tell an old target from a
new one.

## Decision

1. **Each measure has a definition number.** `Kpi(definition=...)` is raised
   whenever what a measure means changes. `availability` is 2; every other
   measure is 1. The number is returned with each measure.
2. **A target carries the definition it was set for.** The optional rule
   field `definition` must be a whole number from 1 to the measure's current
   definition. Absent means 1, so every policy saved before this change keeps
   its stored form and its revision hash.
3. **An older target gives no verdict.** If a rule's definition is below the
   measure's, the assessment is `unassessed` with reason code
   `target_outdated` and a reason in the reader's language asking for review.
   The thresholds and source are still reported, so the reviewer sees what
   was set. Nothing is rewritten or deleted.
4. **Saving a target from the editor reviews it.** The editor stamps the rule
   it saves with the measure's current definition, and only when that is
   above 1; every other rule is sent back exactly as stored, so editing one
   target never silently re-confirms another.
5. **The reason is shown on the card**, on the dashboard and on Assets, not
   folded into the evidence; the Assets "no target set" note excludes these
   measures, which do have a target.

## Consequences

Any availability target saved before this change stops colouring the figure
until someone saves it again in the target editor. A future change of meaning
to any measure needs only its definition raised, and its targets are held the
same way. API clients that send rules without a stamp get definition 1, which
for availability is the cautious reading.

## Verification

Python: a legacy availability target gives `target_outdated` in English and
Arabic, a stamped one judges again, an unaffected measure is unchanged, stamps
are validated (0, 3, a string, a boolean, a fraction are refused) and a legacy
policy keeps its revision; through the API, an unstamped target is held, a
stamp above the current definition is refused with 422, and a stamped save
restores a verdict. Frontend: the editor stamps only the saved rule; the card
shows the review reason outside the evidence fold. Each was watched failing
first. The `metric-colors` browser spec now seeds its availability target with
definition 2, as a target set today would be.
