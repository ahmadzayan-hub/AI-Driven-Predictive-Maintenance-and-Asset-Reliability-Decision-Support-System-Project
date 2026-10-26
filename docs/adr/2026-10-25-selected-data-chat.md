# 2026-10-25 — Selected data chat

Status: explicit dependency of the isolated UI integration candidate.

The workspace assistant had personal-memory actions and report headlines but no
selected data binding or bounded aggregate tool. A user question about railway
signaling age was routed by the LLM to saved-memory recall. A successful general
model answer therefore did not establish data-grounded chat.

Add an explicit owner-scoped report selector and read-only analytical service.
The session persists dataset ID, canonical source SHA-256, analysis revision and
query filters. No latest-report default exists. Selection is stored in a reserved
session serialization field, separated from personal agent preferences; existing
session storage needs no migration. The same per-session lock orders selection
and message processing. Selection requires read and write access as well as exact
session/run/source ownership; admin inspection does not confer cross-owner data
selection. Private RMD and joined-source reports are excluded from this increment.

Supported bilingual data questions precede memory and LLM routing. A strict
structured request schema whitelists aggregate metrics and one normalized railway
signaling class filter; no code, SQL, arbitrary columns or generated plans run.
The existing KPI register supplies arithmetic, denominator and missing policies.
Age uses the named source field's finite nonnegative observations, reported as
mean/minimum/maximum/count in years, with record grain explicitly distinguished
from unique physical assets. Spelling aliases select actual matching source
categories rather than rewriting source labels. Unrecognized cohorts, predictions
or requested operations abstain instead of silently returning a fleet total.

Every answer states deterministic provenance, selected report/dataset/filter,
formula, coverage and hashes. Recheck ownership, source digest and analysis
revision after computing. Changed/deleted/revoked sources produce no figures.
No rows or aggregate replies are automatically passed to a later model context.
LLM explanation is absent, not implied by a configured Qwen connection.

Bounds: strict request schemas, existing filter validation plus bounded serialized
filters, capped source/table size and a small metric allowlist. These bounds do
not relax the local model memory guard. No source data, model, report approval or
industrial action is modified. Only the user-selected session context and normal
conversation transcript are persisted.

Alternatives rejected: let a model guess an arbitrary query; infer the latest
report; search personal memory for asset measurements; treat a repeated asset ID
as a certified physical identity; return an unfiltered total when a requested
cohort cannot be parsed. Natural-language support is deliberately bounded and
does not promise arbitrary analysis questions.

Verification: real temporary-store API tests cover the exact screenshot query,
English/Arabic arithmetic, ownership/revocation, changed/deleted sources,
selection serialization, missing/empty denominators, invalid requests, disabled
or timing-out model gateways and preservation of ordinary conversation behavior.
Component checks exercise explicit selection, restoration and failed saves.
Exact integration checks are in README. Browser, hosted CI and trained-model
acceptance remain separately stated.
