# RMD evidence workspaces and governed report review

Date: 2026-10-22  
Status: Implemented with synthetic acceptance; supplied-source study omitted by owner instruction.

## Problem

Maintenance evidence combines procedures and operational records at different
grains. A flat upload or shared knowledge directory loses source authority,
record relationships and collection isolation. Counts alone cannot support
reliability rates, engineering closure or predictions.

## Decision

Extend the existing FastAPI, SQL store, React feature folders, semantic tokens,
charts and approval engine. Add no frontend or Python application dependency.
Use standard-library bounded OpenXML readers and an explicitly controlled
LibreOffice subprocess for genuine legacy Word conversion.

Keep source bytes, private extraction artifacts, reviewed mappings, immutable
mapped records and source versions in private SQL tables. Include these tables
in operator backup/restore. Personal erasure retains shared organizational
evidence; organization erasure removes its evidence and bound reports. Operator
backups and user exports remain separate operations.

Authorize packs by exact personal ownership or fresh organization membership
and platform permission, including metadata, clauses, originals, exports and
linked run/list/vault/event paths. Platform administration is not an RMD grant.
Legacy unscoped Markdown is available only to the local owner. Explicit public
classification and a separate model-use grant are required for runtime access.
Redact historical reference-bearing transcript replies on retrieval.

Preserve physical rows, cells, duplicate headings, hidden data, formulas,
available cached values and unresolved interpretation. Require reviewed header
rows, sheet grains, column letters, date policy and missing-value policy before
analysis. Never automatically consolidate source rows into incidents. Persist
proposed/confirmed/rejected links separately from source facts and canonical
human-created groupings.

Calculate on the server. Every result records population, filters, units,
calculation version and supporting record identifiers. Snapshots retain exact
mapping revisions and policies. Unavailable reliability measures explain their
missing prerequisites. Recommendations propose management follow-up, owners
and due-date bases without authorizing engineering action.

Expose four connected, lazy-loaded bilingual views: executive, investigations,
knowledge and readiness. Reuse chart components with equivalent tables and
protected evidence dialogs. Use a separate contextual panel in the existing
assistant workspace: excerpts go directly to authorized readers, never durable
chat or a model. Optional operator-approved model narration receives only a
whitelist of verified numeric counts with fixed labels; questions, identifiers
and operational narrative are excluded.

An explicit Review report operation replays immutable calculations and creates
a genuine run, artifact and completed evidence/replay/report tasks. This
specialized workflow does not claim the generic forecasting pipeline executed.
The existing publication task, hash-bound human approval and confirmed vault
write complete the run. Export is a download and does not imply publication or
maintenance authorization.

Snapshot replay uses the same deterministic calculation version over the
preserved mapped records. It checks snapshot reproducibility and tampering;
independent method review, source applicability and engineering closure are
separate assurances.

## Consequences and verification

The standard-library parser is deliberately bounded and does not execute
workbook formulas. Text/table extraction cannot certify image appendices or
the current applicability of a supplied procedure. Retain visual-review and
authority uncertainty. Hosted legacy conversion must use an operator-configured
isolated converter; macro/link controls alone are not OS network isolation.

Synthetic ingestion, calculation, service, authorization, lifecycle and
publication regressions exercise the implementation. Actual source baselines
must be checked after the original inputs become available. UI build, browser,
accessibility, budget and usability measurements are separate recorded gates;
untested targets remain pending. See [RMD_EVIDENCE.md](../RMD_EVIDENCE.md).

## Measured lazy-view allocation

Hosted UI Budget Fast on review revision 96456aa7 measured 98.9 KB first-load
JavaScript, 240.9 KB for all scripts, a 15.9 KB largest lazy chunk, 10.0 KB
first-load CSS, 32.2 KB total CSS and 119.4 KB fonts. The additional four views,
private source inspector, protected evidence dialog, translations and scoped
assistant arrive lazily. There are no new runtime dependencies or fonts.

Keep the first-load JavaScript, first-load CSS, lazy-chunk and font ceilings.
The initial RMD branch allocation was 244 KB total JavaScript and 32.5 KB total
CSS. Before integration, main advanced to bfa00d79 with decision inputs, decision
records and layout fixes. Preserve that work and allocate 248 KB total
JavaScript and 33.5 KB total CSS to the combined capability. The allocation
retains the decision-input script allowance and accommodates its lazy styles;
the combined production build must pass the exact-byte gate. Observed sizes
are recorded in README.md#testing after measurement. This is an explicit
total-download tradeoff; it is not evidence of LCP/CLS/INP performance, which
needs separate browser measurement.

New PostgreSQL evidence DDL and direct API grants are protected atomically at
store startup: enable RLS and revoke PUBLIC/available anon/authenticated roles.
The committed initial-schema mirror and additive SQL migration carry the same
tables and restrictions. No production migration is performed by this change.

## Integration on 23 October

Preserve main through 986b168c, including its analytics safeguards, idempotent run
creation and stage/runtime deadlines. The deadline worker must copy the caller's
context variables: the merged assistant uses a request-scoped principal for
knowledge authorization. Without propagation, permitted runtime lookups lose
their requester and fail closed. A regression first reproduces that failure for
two principals, then verifies each sees only its own permitted collection and
the administrator does not inherit the session creator's grant. No permission
is broadened, and the caller's context is reset after each operation.
The integration correction is recorded in the
[23 October context decision](2026-10-23-rmd-runtime-context.md).
