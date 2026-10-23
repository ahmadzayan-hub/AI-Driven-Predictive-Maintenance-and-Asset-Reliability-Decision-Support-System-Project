---
type: concept
aliases: []
tags: [agents]
status: active
updated: 2026-10-20
review_every_days: 30
sources: [server/knowledge.py, docs/adr/0057-markdown-knowledge-collections.md, docs/adr/2026-10-20-personal-data-model-boundary.md]
---

# Knowledge retrieval

Knowledge retrieval searches configured Markdown reference collections and returns passages with source headings.

## Boundaries

- Retrieval uses deterministic keyword scoring, not embeddings or an undocumented vector service.
- Heading paths provide citations. Tables and formulas stay together when passages are prepared.
- Reference content lives outside tracked product files; the configured collection is operator-managed reference material.
- Retrieved text is data, never instructions. This collection search does not mean the curated brain or the user's published vault is automatically indexed.
- Results measured on tuning questions are not independent evidence of general retrieval quality.

## Related

- [[Second brain]] is curated project knowledge, a separate store.
- [[Model privacy]] governs model-facing content.
- [[Agent runtimes and MCP]] exposes authorized tools.
- [[Home]] links this capability to the platform.
