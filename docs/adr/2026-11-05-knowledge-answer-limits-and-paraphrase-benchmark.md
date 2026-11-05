# Knowledge answers state their limits; paraphrase benchmark and a rejected stemmer

Date: 2026-11-05 · Status: Accepted · Follows [evidence-aware knowledge](2026-11-04-evidence-aware-knowledge.md)

## Context

Appendix D of the Analytics handover asks every knowledge answer to carry its scope
and qualification. Ask Miyaar quoted passages with a label, but did not say in words
what the label means. The acceptance report also showed that the retriever is
lexical, and QA13 needed a keyword-rich wording.

## Decision

1. **Limits in words.** When quoted passages carry limits or a non-current status,
   Ask Miyaar adds "Limits that apply to these passages" (Arabic: «قيود تنطبق على هذه
   المقتطفات») with one line per limit, once each: synthetic educational data, not
   validated predictions of future failure, not RMD operational performance, an
   academic case, not an RMD rule or threshold, historical status to recheck, a dated
   requirement, a proposal, superseded or unresolved. A collection without directives
   gets no block. An unknown code is shown as written, never dropped.
2. **Paraphrase benchmark.** `evals/knowledge_paraphrase/cases.json` holds 18 held-out
   paraphrases (16 English, 2 Arabic) written before any change; they avoid the
   source's key terms. `tests/test_knowledge_paraphrase.py` keeps the floors at the
   measured baseline.
3. **Stemmer rejected.** A light rule-based stemmer (English plural, -ing, -ed; Arabic
   definite article) was tried once against the frozen set and reverted:

| Scorer | Top 1 | Top 3 | Top 5 | MRR | Acceptance failures |
|---|---|---|---|---|---|
| Current lexical scorer | 7/18 | 11/18 | 15/18 | 0.516 | 0 of 45 |
| With the light stemmer | 4/18 | 9/18 | 13/18 | 0.398 | 2 (K24, QA02) |

## Consequences

- The set has now been used for one decision. Any scorer change tuned against it
  needs a new held-out set before a claim of improvement.
- Misses remain at top 5: P-K11 (twelve requirements), P-QA12 (money saved by upkeep),
  P-QA13 (this year's progress). A semantic layer or synonym map is a separate,
  measured decision.
- No model is involved. The limits text comes from the directive codes, so it cannot
  claim a qualification the source does not carry.
