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

Still source-dependent: supplied document digests, image-appendix review,
authority/applicability determinations, comparison-source identification and
the actual workbook baseline checks. No actual evidence is replaced by demo
data. Synthetic test fixtures are explicitly labeled.

Still measurement-dependent: manager comprehension within ten seconds, evidence
within two interactions, mobile Arabic journey, keyboard-only approval,
320-pixel overflow, both themes, WCAG checks and production performance.
Record observed results, environment limitations and unresolved issues in the
delivery log. A designed acceptance target is not a measured outcome.

Future work: automatic OCR with reviewed visual coverage, advanced engineering
models after the readiness gate, and deployment-specific native packaging.
No prediction or report approval autonomously authorizes maintenance or safety
decisions.
