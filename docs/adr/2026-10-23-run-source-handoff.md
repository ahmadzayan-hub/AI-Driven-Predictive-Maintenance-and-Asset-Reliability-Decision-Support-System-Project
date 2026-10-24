# Explicit run source reference for a governed handoff

Authenticated run detail exposes nullable `dataset_id`, taken from the existing
stored run reference. This is a source identifier, not proof of data suitability,
an approved recommendation, assignment authority or work-order execution rights.
Existing run ownership and live RMD-pack access checks still run before the HTTP
response. No dataset rows or additional source contents are returned.

Ordinary dataset-backed runs return their actual identifier. RMD review runs
return null, because their evidence packs are not operations datasets. Older
servers may omit the field; the frontend contract treats missing as unknown and
must not guess from a display name or stages. The UI handoff navigates to the existing operations route with the exact run ID.
The destination re-reads authenticated run detail and fails closed on absent/null
source, invalid state or denied access before showing the draft. Existing
organization permissions and explicit human actions remain required. No automatic draft,
assignment, approval, execution, source conversion or role grant occurs here.

Synthetic API tests cover the selected source, foreign-owner/anonymous denial
and genuine RMD review runs with null source identity. No schema change,
production activation, provider call or RMD-to-dataset bridge is included.


The source-linked draft keeps its run ID read-only until the user clears the
context. Asset, source column, title, rationale, assignee and due date are not
inferred. Source columns start empty for this handoff. Context is reset on route
or account changes; stale async responses cannot repopulate another source.
The base dataset is explicitly distinguished from report filters, report
approval and execution authorization. Navigation performs reads only.

The bilingual operations browser lifecycle now starts with UI upload, readiness,
analysis and report inspection rather than an API-created analysis. It checks
exact source navigation, no draft creation on navigation, separate authorization
and recorded outcome/evidence. Unit regressions cover null/missing source, denied
foreign access, organization viewer permissions and context reset.


## Narrow interface allocation

The combined specialist-runtime, Dubai typography and source-handoff production
measurement was 99,539 initial and 252,693 total gzip JavaScript bytes. The old
total cap of 252,000 is exceeded by 693 bytes (0.27%). Removing the redundant
Operations eyebrow/introduction did not close this gap; evidence limitations,
access validation and accessibility must not be removed merely to fit a cap.
The owner-authorized implementation therefore allocates exactly 253,000 total
JavaScript bytes to the source handoff. First load remains 100,000, each lazy
chunk 30,000, initial CSS 10,500 and total CSS 33,500 bytes. The separately
approved original-font allocation is unchanged. An exact-boundary regression
rejects 253,001 bytes. This allocation does not apply to the preceding runtime
PR and does not authorize other budget increases or production activation.
