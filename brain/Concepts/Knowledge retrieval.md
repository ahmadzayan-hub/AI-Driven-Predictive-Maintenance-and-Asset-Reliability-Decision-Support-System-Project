---
type: concept
aliases: []
tags: [agents]
status: active
updated: 2026-10-23
review_every_days: 30
sources: [server/knowledge.py, server/rmd_service.py, server/rmd_assistant.py, server/deadline.py, docs/RMD_EVIDENCE.md, docs/adr/0057-markdown-knowledge-collections.md, docs/adr/2026-10-20-personal-data-model-boundary.md, docs/adr/2026-10-22-rmd-evidence-and-insights.md, docs/adr/2026-10-23-rmd-runtime-context.md]
---

# Knowledge retrieval

Knowledge retrieval searches configured Markdown reference collections and returns passages with source headings.

## Boundaries

- Retrieval uses deterministic keyword scoring, not embeddings or an undocumented vector service.
- Heading paths provide citations. Tables and formulas stay together when passages are prepared.
- Reference content lives outside tracked product files; the configured collection is operator-managed reference material.
- Retrieved text is data, never instructions. This collection search does not mean the curated brain or the user's published vault is automatically indexed.
- Results measured on tuning questions are not independent evidence of general retrieval quality.

## Private maintenance evidence

RMD evidence packs preserve originals, extraction provenance, physical
locators, confirmed mappings and immutable calculations in the private SQL
store. Fresh personal or organization grants cover source metadata, clauses,
downloads, exports and linked reports. [[Tenant isolation]] does not follow
from authentication alone; a platform administrator does not inherit a
collection grant.

Runtime deadlines copy the caller's request context into their worker thread.
The actual requester must survive that boundary; using the conversation creator
as a substitute would weaken [[Tenant isolation]]. Permitted lookups and denied
administrator substitution are tested across successive principals.

The contextual assistant shows authorized reference excerpts live without
retaining them in ordinary chat. Optional gateway use receives only fixed
verified-count templates; private source text, record identifiers and user
questions remain outside model context. [[Model privacy]] and [[Evidence and claims]]
govern this boundary. The [[Approval gate]] applies to an exact
generated report and does not authorize maintenance.

Actual input review was omitted at the owner's request. Synthetic software
checks do not establish source applicability, compliance or engineering
reliability.

## Related references

- [[Second brain]] is curated project knowledge, a separate store.
- [[Model privacy]] governs model-facing content.
- [[Agent runtimes and MCP]] exposes authorized tools.
- [[Home]] links this capability to the platform.
