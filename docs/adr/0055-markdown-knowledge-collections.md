# ADR 0055: Markdown knowledge collections, searched and cited

- Status: accepted
- Date: 2026-10-19
- Relates to ADR 0044 (the vault directory is configuration) and ADR 0022
  (reports in the reader's language).

## Problem

The owner asked for an MBA 9226 Business Analytics knowledge base to be
retrievable through Agentic OS, with citations, without regressing anything.

Two findings shaped the answer.

**There is no retrieval layer to extend.** A search of `server/`, `scripts/`
and `api/` for embeddings, vector stores, FAISS, Chroma, pgvector, cosine
similarity, semantic search and reranking returns nothing.
`docs/OBSIDIAN_INTEGRATION.md` records this as deliberate: vault reading,
embeddings and graph retrieval are absent because "shipping stubs would
violate the no-fake-features rule". `server/datasets.py` ingests tabular data
into one canonical table and is the wrong shape for prose. The `brain/` notes
are curated by hand and checked by `scripts/brain_check.py`, not searched.

**The content cannot live in this repository.** It is course material naming
an institution, a group, a team and an instructor. `CLAUDE.md` is explicit:
the repository is public, and course files and personal data belong in the
git-ignored `private/` folders. `docs/GITHUB_SYNC.md` already records five
remote branches publishing twenty such files, unresolved. Committing this
knowledge base would repeat that leak deliberately.

## Decision

**`server/knowledge.py`**: a folder of Markdown is a collection. Each file is
split on its heading hierarchy, so every passage carries the path that leads
to it and can be cited as `Source: <document>, <section>`. Tables, fenced
blocks and formula lines are never cut - a KPI definition separated from its
formula is worse than a passage that is slightly too long. A document's
`collection.json` supplies its declared metadata.

**Retrieval is deterministic keyword scoring.** The rarity of each matched
word, doubled when the word is in the heading path, scaled by how much of the
question the passage covers. No embeddings, no model, no tokens, no new
dependency, and every score explainable from the words that produced it.

**Content location is configuration.** The default root is the git-ignored
`private/knowledge/`; `AGENTIC_OS_KNOWLEDGE_DIR` overrides it, exactly as
`AGENTIC_OS_VAULT_DIR` overrides the vault. The mechanism ships publicly; the
course material never does.

**`GET /api/knowledge`** reports what is indexed, from where and at which
SHA-256. **`GET /api/knowledge/search`** returns passages with citations. Both
are owner-scoped behind the existing `requires("read")`. The store is rebuilt
only when a file's size or timestamp moves, so re-importing the same bytes
changes nothing.

Retrieved text is **data, never instructions**, the same rule the repository
already applies to dataset contents, the runtime `vault/` and fetched web
content.

## What was measured, including what failed

The ten acceptance questions, scored against the section each should reach:

| Scorer | Top-1 exact | In top-3 |
| --- | --- | --- |
| Rarity x coverage (**adopted**) | **8/10** | 8/10 |
| Okapi BM25, b=0.75 | 6/10 | 8/10 |
| Okapi BM25, b=0.3 | 6/10 | 8/10 |
| Okapi BM25, b=0.0 | 5/10 | 8/10 |

BM25 is the textbook answer and it is worse here. Its length normalisation
pushes down the long glossary passage that holds the formula reference, and a
corpus of 73 passages of very uneven length is not what its averages assume.
It was implemented, measured and removed rather than kept because it is
standard.

**The scorer was chosen against those ten questions, so they no longer measure
generalisation.** This is the same contamination recorded in ADR 0054, named
here for the same reason: a number produced by tuning against a set is not
evidence about anything else.

The two questions missed at top-1 are instructive rather than fixable by
tuning. "What **causes** data leakage in predictive maintenance?" returns the
section on causal claims, because `causes` has a higher rarity weight in this
corpus (3.05) than `leakage` (2.05) - a question word that is a content word
here. The passage that answers it is third. No keyword scorer distinguishes
the two senses, and tuning until it did would be fitting to the question.

## Consequences

- The system can answer MBA 9226 questions from the indexed Markdown and cite
  the section each answer came from, through its own API.
- Nothing retrieves across collections it should not: a filter naming an
  unknown collection returns nothing rather than silently widening.
- A deployment with no knowledge folder starts normally and reports an empty
  list.
- Callers should read the top three passages, not the first. The assistant's
  `search_knowledge` tool does exactly that: it quotes the best three with
  their citations, so a 100 KB collection costs a few hundred tokens instead
  of being injected whole, and it says it found nothing rather than answering
  from memory. It is declared in `server/tools.py`, dispatched in
  `server/assistant.py`, listed in `SERVER_ONLY` because the command-line
  interface has no collections, and absent from `DESTRUCTIVE`. Its three
  messages - found, nothing, no collection loaded - ship in English and
  Arabic.
- `tests/test_knowledge.py` covers chunking, citation, idempotent re-import,
  re-indexing on changed bytes, Arabic retrieval, and the acceptance
  questions. Its fixtures are synthetic; the test touching the real
  collection skips when the private folder is absent, the shape the
  PostgreSQL tests already use.
