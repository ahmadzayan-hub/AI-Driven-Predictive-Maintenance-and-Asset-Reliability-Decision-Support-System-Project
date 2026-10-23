# RMD Evidence and Insights

An integrated private evidence workspace at **RMD Evidence / أدلة RMD** in the
existing application. Actual source files and source-specific acceptance
registers belong outside Git and public frontend bundles.

## Reuse and extension map

| Need | Existing platform reused | Extension |
| --- | --- | --- |
| Persistence and recovery | SQLite/PostgreSQL SqlStore, atomic writes, backup/restore | Private packs, original bytes, extraction artifacts, mapping and immutable analysis snapshots |
| Permissions | Managed identity and organization membership intersection | Fresh scope checks on every evidence read, mutation, citation, download and bound report |
| Data ingestion | Existing DatasetError conventions and authenticated request client | Bounded workbook and genuine controlled Word extraction preserving physical locators |
| Mapping and joins | Existing column-mapping interaction and record-query conventions | Reviewed per-sheet grain/header/column/date/missing-value mappings; relationship proposals preserve one-to-many source entities |
| Calculations | Server-side deterministic analysis contracts and maintenance metric definitions | Grain-specific counts, reconciliation, completeness, observed history, conflicts, readiness and proposed follow-up |
| Dashboard | Lazy React views, shared tokens, SVG charts, Dialog and translation packs | Four connected evidence views and authorized records/clauses |
| Assistant | Existing assistant workspace and approved model gateway | Ephemeral reference replies and tightly allowlisted aggregate narration |
| Reports and decisions | Existing run store, artifact hash, approvals and vault publishing | Snapshot replay and specialized evidence review run; populated export tables |

## Primary journey

Create a private pack → import workbook/procedures → inspect extraction coverage
and originals → confirm each sheet's physical header and grain → map columns
and date/missing-value policy → calculate a dated snapshot → inspect a finding,
records or clause → record investigation decisions and management actions →
review the exact generated report → approve or reject publication → open the
server-confirmed result.

The four views retain the selected pack and analysis. A saved snapshot carries
its own population and source/mapping revisions: later mapping changes affect a
new analysis, not old figures. Counts describe records in the selected scope.
Summary rows are separate from work orders, events and reconciliation rows.
Confirmed links preserve the underlying source entities and review history.

## Main implementation contracts

| Component/service | Existing type or API | States and recovery |
| --- | --- | --- |
| RmdView / PackWorkspace | GET/POST /api/rmd/packs; GET pack | Loading, empty, permission/error, retry; creator identity never comes from the request body |
| ImportSource / SourceInspector | POST raw sources; GET source/download; PUT mapping | Bounded file validation, coverage warnings, read-only original, explicit confirmation, stale-revision conflict and draft-preserving retry |
| EvidenceChartCard / RecordsDialog | Stored charts/calculations; POST analysis records/query | Table matches chart; missing fields have readable detail fallbacks; unknown evidence IDs fail closed |
| Knowledge clauses and digest | GET pack/knowledge; GET source | Search, no matches, cited physical locator, supplied authority/applicability uncertainty and coverage |
| Investigation decisions | GET/PATCH links; POST incidents | Proposed, confirmed, rejected; version checks and append-only review history; no automatic incident merge |
| Action register | GET/POST/PATCH actions | Derived from a permitted snapshot priority; suggested owner/date basis; closure requires evidence |
| RmdAssistantPanel | POST pack/assistant | Explicit pack/analysis context, retained draft, cancellation/error retry, ephemeral authorized citations; no private reference transcript |
| Report review | POST analysis/review-run, then existing run APIs | Replay failure, durable idempotent creation, real progress/state, exact artifact approval, rejection or confirmed publication |
| Executive/action exports | GET analysis/export?format=html or csv | Immutable snapshot/filter identity, calculation references and chart tables; authorized download does not publish |

All evidence routes are under /api/rmd/packs/{pack_id}. Responses, including
errors and downloads, use private no-store headers. A source ID is not a
filesystem path. Source-identical files in different packs do not share grants.
Run/detail/approval, list, event and vault routes also enforce the bound pack.

The specialized report workflow has evidence, replay, report and publish tasks.
The existing run engine preserves client-step versus background-worker
semantics. In client mode the Runs view must remain open to advance publication
to its approval gate. A refresh recovers its durable run; retries reuse the
analysis-bound run instead of creating duplicates.

## Operating controls

Source originals and converted artifacts are held in the existing private
database. Protect that database and operator backups using the deployment's
existing storage controls. Do not place private sources in static assets or the
legacy shared Markdown directory. A local install has one local owner; hosted
identity requires explicit personal ownership or organization membership.

Legacy Word conversion in hosted identity mode requires
RMD_SANDBOXED_DOC_CONVERTER pointing to an operator-controlled converter.
The converter must provide process/filesystem/network isolation appropriate to
untrusted documents. Conversion itself disables macros/external updates,
isolates its profile, removes application credentials and preserves converted
artifacts and tool provenance. Converted page images remain available for
authorized visual review; image-based content is not silently counted as read.

AGENTIC_OS_RMD_MODEL_AGGREGATES=1 is an explicit operator policy permitting
verified aggregate count narration through the configured gateway. The default
is deterministic, offline-capable answers. This setting never permits raw
records, filenames, source clauses or user-entered question text in the model
projection. Source requirements, applicability decisions, management proposals
and engineering authorization remain distinct.

## Delivery and acceptance

Implemented: private ingestion/persistence, citations/search, reviewed mapping,
snapshot calculations, record relationships/review history, supported actions,
four UI views, contextual assistant, snapshot exports and governed report gate.

Omitted by the owner's instruction on 22 October: supplied document digests, image-appendix review,
authority/applicability determinations, comparison-source identification and
the actual workbook baseline checks. These can be assessed after a later import.
No actual evidence is replaced by demo
data. Synthetic test fixtures are explicitly labeled.

Observed with explicitly synthetic inputs: real API-backed import, mapping,
calculation, source-row and clause drill-down, action export, durable reload,
contextual assistant and exact-artifact publication pass in English and Arabic
on desktop and phone. Evidence opens from the tested headline with one action.
The approval controls were activated entirely by keyboard. Tested layouts had
no page overflow at 1440, 768, 390 and 320 pixels; automated accessibility scans
passed on the tested views, dialogs and report states, with both theme
renderings covered. Phone testing exposed a scroll-containment defect that
covered the review action with bottom navigation; the corrected journey passes.
Synthetic rendered captures are available in the linked CI run's temporary
artifact. Exact test counts, measured bundle sizes and the run link are in
[README.md#testing](../README.md#testing).

Still measurement-dependent: manager comprehension within ten seconds,
independent screen-reader/manual WCAG assessment, and actual-workload
LCP/CLS/INP. Automated scans cover their tested states, not complete WCAG
conformance. The stricter first-load allocation is preserved; lazy RMD views
increase the total bundle allocation, documented in the UI plan. No live
deployment or real-source acceptance is claimed.

Future work: automatic OCR with reviewed visual coverage, advanced engineering
models after the readiness gate, and deployment-specific native packaging.
No prediction or report approval autonomously authorizes maintenance or safety
decisions.

## Final interface review

Reviewed with the instructions-only RMD UI/UX Pro Max adaptation and the React
component checklist. This is a source review plus the recorded automated browser
observations, not a manual screenshot or assistive-technology assessment. The
upstream design CLI and style database were not installed. Existing platform
tokens, local fonts and React/Vite architecture take precedence; no RTA approval,
official branding or new operational imagery is asserted.

Browser evidence uses explicitly synthetic workbook/procedure fixtures on
`codex/rmd-evidence-insights-20261022`, combined revision `b2174dcc` and navigation
correction `29ab16d1`. The desktop viewport is 1440 × 900 and phone viewport
375 × 812; the overview also checks widths 768, 390 and 320. Both locales and
light/dark overview renderings are covered. Evidence is in the README-linked
acceptance runs, under the `rmd-synthetic-checks` artifact's
`frontend/test-results` directory. All results below apply only to that scope.

The final combined acceptance on `52389750` also passes after preserving main's
P2 controls and chart scales through `6fec34b7`. Deadline workers retain the
actual requester's context, as recorded in the
[integration decision](adr/2026-10-23-rmd-runtime-context.md). Current run links,
counts, measured bundle sizes and the separate aggregate-CI scope are in README.

| ID | Priority | Screen/file location | Observed evidence | User consequence | Change or retained behavior | Test | Result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| UX-01 | P2 | App and RMD feature folder | Typed React components, shared Dialog/charts/tokens, lazy routes; independent pack/action reads and obsolete-read cancellation | Existing workflows and initial loading remain usable | Retain stack, direct imports and existing components; no new runtime dependency | Source inspection, typecheck and measured build | PASS, inspected scope |
| UX-02/13 | P2 | RMD styles and shared assets | Semantic tokens and current local typography; no new logo, font or operational photo | Consistent identity without invented asset evidence | Retain existing product assets | Source diff review | PASS, source-only |
| UX-03/14 | P1 | RMD API, App, assistant/source panels | Pack checks on protected reads/writes; identity-keyed workspace, aborted late replies and fresh grants on re-entry | Private evidence remains scoped | Retain server authorization and in-memory draft policy | Separate-user/org, revocation, erasure and component regressions | PASS, tested boundaries |
| UX-04 | P1 | Report review and existing ApprovalCard | Actual awaiting-approval response, exact report read gate, keyboard activation, confirmed publication path | Approval and publication remain distinct decisions/states | Reuse artifact-bound server gate | Real-API bilingual desktop/phone journeys | PASS, synthetic |
| UX-05/06 | P1 | Findings, readiness, source inspector and assistant | Unavailable measures explain missing inputs; component failures preserve drafts and suppress stale results | Missing evidence and failures remain visible | Retain explicit asynchronous and evidence states | Calculation/service/component checks and browser drill-down | PASS, tested cases |
| UX-07/08 | P1 | RMD overview, dialogs and report journey | English/Arabic journeys pass; checked widths do not overflow; phone action remains above navigation | Phone and RTL work can reach review | Corrected scroll containment in 7f8be777 | rmd.spec.ts and synthetic captures | PASS, stated viewport/state scope |
| UX-09/10/11 | P2 | Dialogs, controls, typography | Keyboard approval and automated accessibility scans pass; manual screen-reader, text growth, orientation and target-box audit were not executed | Additional assistive-technology issues may remain | Retain visible focus, labelled controls and shared dialog behavior; perform manual assessment | Automated checks completed; manual assessment absent | NOT TESTED for remaining manual criteria |
| UX-12 | P1 | Evidence charts, record dialog and exports | Chart tables and source-row drill-down use server snapshot values; exports retain population/calculation identity | Figures can be inspected without inferring incident totals | Retain accessible tables and authorized drill-down | Analytics/export tests and real-API evidence checks | PASS, synthetic |
| UX-15 | P2 | Lazy RMD views and shared shell | Exact-byte bundle gate passes; no comparable production latency or Web Vitals study | Download limits are measured; runtime speed remains unproven | Retain lazy routes and documented total allocation | Hosted production build/budget | PASS for bundle; NOT TESTED for production latency |
| UX-16 | P2 | App sidebar / overview.spec.ts | Old sidebar expectation omitted RMD; duplicate shield conflicted with destination identity | Navigation needs a distinct, tested destination | Include RMD in expectation; reuse search icon | Follow-up sidebar, Miyaar and subsequent full aggregate rerun pass | PASS, corrected scope |

No critical authorization or evidence-integrity result is inferred from a
screenshot. Manual comprehension timing, formal accessibility conformance and
production acceptance remain open as described above. Review responsibility:
Codex implementation lead, with the recorded independent source reviews and
hosted test evidence.
