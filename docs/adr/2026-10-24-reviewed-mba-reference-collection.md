# Reviewed MBA reference summaries in the existing knowledge loader

- Status: proposed for review
- Date: 2026-10-24
- Extends: ADR 0057; preserves the personal-data/model boundary.

## Problem

The owner requested source-grounded MBA method references inside Miyaar.
The original source inventory, books, slides, dataset rows and private audit
contain material that must not be copied into a public knowledge collection.
The current retrieval mechanism already supports cited Markdown passages and
per-collection access; a new retrieval stack is unnecessary.

## Decision

Publish only reviewed original summaries, method guidance, schema-level cards,
bibliographic identifiers and explicit partial coverage under
`knowledge/mba-analytics/`. Do not publish source extraction, source documents,
personal filenames, local paths, records or private reports. This narrow
publication scope follows the owner's explicit authorization and does not
reinterpret historical source-material restrictions as republication rights.

Default `knowledge.load()` combines operator-private collections with reviewed
bundled collections using the same parser, keyword scorer and citations.
An explicit root or `AGENTIC_OS_KNOWLEDGE_DIR` stays exclusive, including an
empty/missing root. Bundled IDs win collisions only in default lookup, so a
private document cannot replace a reviewed public collection under its ID.
The API uses the same resolution as the existing assistant lookup.

The reviewed collection is publicly readable but keeps
`model_context_allowed: false`. No grant, tenant check or model-bound filter is
relaxed. No provider/model call, plugin execution, training, production change
or dataset processing is introduced. The reference is not proof that an agent
has used it or that the project analysis is valid.

## Verification and limits

Tests cover source lookup in both languages, default inclusion, exclusive
overrides, ID collisions, source/coverage links and model-context exclusion.
Existing knowledge/access and documentation checks remain applicable. Lookup
acceptance examples are regression checks, not a general retrieval benchmark.

The source review is partial. The public bibliography excludes private source
identities and links back by stable source ID and page locator. Separate
empirical-review findings inform generic comparison safeguards; this task did
not recompute their project results. Required course exports and optional video
are kept distinct. There is no automatic analytical-stage invocation of this
reference; actual invocation needs run evidence.

If source lookup exposes private records, a bundled identity can be replaced,
an explicit override searches unexpected material, or model-bound lookup admits
this collection, the change fails acceptance. No deployment or merge is part
of this decision.
