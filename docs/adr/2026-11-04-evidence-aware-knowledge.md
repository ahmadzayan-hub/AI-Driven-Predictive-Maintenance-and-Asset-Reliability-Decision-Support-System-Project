# Evidence-aware knowledge: the RMD V2 MBA 9227 and Analytics packs

Date: 2026-11-04 · Status: Accepted · Builds on [ADR 0057](0057-markdown-knowledge-collections.md)

## Context

The owner supplied two handover files (MBA 9227 and Group 9226 data analytics) with
evidence labels, a correction history, synthetic data and acceptance cases (K01 to K28,
QA01 to QA20). They must be reachable through the existing knowledge, retrieval and
citation mechanism, keep their evidence status and superseded values, keep academic
cases apart from RMD operational rules, and not put owner-only information in a
publicly readable repository. Retrieval filters cannot protect Git history.

## Decision

1. **Directives, not a new engine.** `server/knowledge.py` reads `<!-- kb: key=value; ... -->`
   lines under a heading: `domain`, `evidence`, `status` (current, superseded, unresolved),
   `synthetic`, `sources`, `limits`, `record`. A directive covers its heading and the
   headings below it, is removed from the quoted text, is bounded and whitelisted, and
   ignores unknown keys. A passage with no directive behaves exactly as before.
2. **Superseded is history.** A superseded passage is returned only when the question is
   about corrections (wording such as provisional, superseded, outdated, still current;
   Arabic equivalents) or the caller passes `include_superseded=true`. Otherwise it is
   never a current answer.
3. **Scope on every hit.** Each hit carries domain, evidence status, source ids, limits,
   synthetic flag and a one-line label. `/api/knowledge/search` accepts `domain` and
   `include_superseded`; Ask Miyaar prints the label after the citation. The collection
   description states synthetic, version, source SHA-256, withheld sections and that
   it has no operational authority.
4. **Public and private copies.** `scripts/build_knowledge_packs.py` writes the public
   departmental copy to `knowledge/rmd-v2-*` (owner profile and identifiers left out,
   legal name shortened to the working name, private file-library links removed, a
   guard fails the build on an identifier, email or credential-shaped string) and the
   complete handover to git-ignored `private/knowledge/*-complete`, readable by the
   local owner only. Both stay `model_context_allowed: false`.
5. **Dataset aggregates are public.** The pack quotes aggregate figures from a synthetic
   educational dataset; no rows are included. If the owner prefers them private, move
   the analytics pack's sections 5, 6 and Appendix E to the private copy.
6. **Acceptance.** `tests/test_rmd_knowledge_packs.py` runs the cases at retrieval level
   against the bundled packs with the handover's own acceptance sections excluded.
   `tests/test_rmd_knowledge_reconciliation.py` reconciles the quoted aggregates to the
   workbook when it is present with the documented SHA-256 and, always, checks the
   engine's ratio-of-sums definitions on an invented table. Results are recorded in
   [RMD_KNOWLEDGE_ACCEPTANCE.md](../RMD_KNOWLEDGE_ACCEPTANCE.md).

## Consequences

- The retriever stays lexical. Paraphrases that share no words with the evidence can
  miss it (QA13 needed a keyword-rich wording). The acceptance report records this; a
  semantic layer is a separate decision.
- The cases prove the evidence is retrievable and correctly labelled, not that a model
  answers correctly. Model behaviour is not exercised and is not claimed.
- A new handover version is a rebuild, not a patch: stable file names, a source hash in
  the manifest, and the superseded record kept.
- The private copies appear in an owner's unscoped search on their own machine; use the
  `collection` filter to search one pack.
