# Confirmed key corrections in joins

Date: 2026-11-06 · Status: Accepted · Follows [typo candidates](2026-11-06-separator-keys-and-typo-candidates.md)

## Context

The join preview now names unmatched keys one letter from a joined key (`PMP-03` and
`PUMP-03`) but never merges them. The owner needs a way to confirm a slip without editing
the source file.

## Decision

1. A keyed join may declare `corrections`: up to 50 pairs `{"from": main key, "to": joined
   key}`, each main key once, on a one-column key only. Anything else is refused with a
   reason in English and Arabic.
2. A correction is applied only to a row that found no match on its own, and only when its
   `to` names a key the joined dataset holds; a correction to a missing key refuses the join.
   The row's own value is never rewritten in the table.
3. The join record counts `corrected` rows and keeps the pairs; the report adds a cited
   fact: "N rows matched … only through K key corrections the owner declared", with examples.
   The corrections are part of the run's stored declaration, so they are in its identity
   and its audit.
4. In the join builder, each named candidate has a button "Read PMP-03 as PUMP-03". Nothing
   is declared until it is pressed; the preview then needs refreshing, as after any change.

## Consequences

- Tests: validation of the pairs, refusal of a correction to a missing key, a governed run
  whose report states the corrected rows and passes every validator check, and the builder
  adding a correction only on a press, in both languages.
- Not done: removing one correction from the builder (clearing the join removes all), and
  corrections on composite keys.
