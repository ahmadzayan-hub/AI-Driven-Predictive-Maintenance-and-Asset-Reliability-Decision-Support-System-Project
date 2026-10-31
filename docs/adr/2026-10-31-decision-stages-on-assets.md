# The decision stages on the Assets screen

Date: 2026-10-31 · Status: Accepted (the owner chose "Screen for R1–R5" on
31 October 2026).

## Context

R1 to R3 (reliability, risk ranking, what-if scenarios) and R4 (data health)
reached the report and the claims only. R5 (drift) already shows beside a
live-source refresh. The total script budget had 1 byte left, and the owner's
rule is to trim before raising it.

## Decision

1. **The Assets screen**, which already shows the latest maintenance run's
   screening and model evidence, now also shows:
   - the run's data-health line (the cleaner's `cl_health` claim) under the
     source details;
   - one block per decision stage that succeeded and made claims, in the
     order reliability, risk ranking, scenarios: the stage's title and each
     claim's text.
2. **No new interface string.** Titles and claim text come from the server in
   the run's language (`text_ar` on an Arabic run). The three stages'
   summaries are now written in the run's language too.
3. **The room came from trimming**, not a raise: six Operations help strings
   shortened in both languages with the same meaning (partial history, the
   displayed queue, authorization being separate from publication, pilot
   readiness limits, the silent worker). Total script 257,090 of 257,100
   bytes, stable across builds.

## Consequences

- A maintenance manager sees the failure pattern, the ranked assets and the
  interval comparison where they already look at asset evidence, with the
  same advisory wording and approval boundary as the report.
- Claims are shown as text; the ranked table and the scenario tables stay in
  the stage reports. A richer view needs budget room or a recorded raise.
- 10 bytes remain. The next interface change must trim first or record a
  raise.

## Verification

`frontend/src/features/assets/assetEvidence.test.ts` (decision stages in
order, failed or empty stages left out, the health line in the run's
language) and `AssetIntelligenceView.test.tsx` (the blocks render in Arabic,
a failed stage hidden). Three Operations tests updated to the shortened
wording, still checking the same meaning.
