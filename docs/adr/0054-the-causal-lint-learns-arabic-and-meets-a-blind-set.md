# ADR 0054: The causal lint learns Arabic word order, and a blind set shows what it is worth

- Status: accepted
- Date: 2026-10-19
- Supersedes nothing. Extends ADR 0027 (agents are measured).

## Problem

`scripts/claims_lint.causal_phrases` is the Tier 0 gate that stops a deliverable
claiming a cause from observational data. On blind holdout v4 it scored **69%
recall**: it missed nearly a third of causal claims. Five cases failed, and
**four of the five were Arabic**. Reports ship in Arabic (ADR 0022), so the gate
was materially weaker in one of the two languages it is supposed to cover.

The misses were not random. Each named a construction the pattern list did not
have:

| Construction | Example |
| --- | --- |
| Arabic verb-subject-object | `خفّض التدريب الجديد زمن التوقف` |
| Arabic attribution with `يعود … إلى` | `يعود تراجع الدقة إلى نقص البيانات` |
| `نتيجة` followed by a noun | `جاء نتيجة تحديث النظام` |
| Arabic force on a measure | `يدفع تكاليف النقل إلى الأعلى` |
| English nominalised cause | `The impact of the rule was a 15-minute cut` |

One false positive came from the opposite direction: a hedge that explicitly
refuses to confirm was read as a claim.

## Decision

Add one pattern per construction class, not one per failing sentence.

The important one is word order. The existing Arabic rule required a word before
the verb, with a comment that a sentence-opening verb "only reports a change".
That is an English assumption: **verb-subject-object is Arabic's default order**,
so a verb opening a sentence is ordinary, and `verb + subject + a further noun
phrase` claims an effect. A change is still only reported when what follows the
subject is a measure or a circumstance (`زاد الإنتاج بنسبة 12%`,
`زاد الإنتاج في الربع الأخير`), so only the position immediately after the
subject is tested; prepositions inside the noun phrases themselves are ordinary
Arabic and are ignored.

`cannot confirm` joins the hedge list, and the nominalised-cause pattern refuses
a complement that defers the effect rather than asserting it ("is still being
assessed").

## What this is worth, measured

- dev: 100% recall, 100% precision (69 cases), unchanged.
- blind holdout v4: recall **69% → 100%**, precision 92% → 100%.

**That holdout number is contaminated and must not be read as generalisation.**
The method in ADR 0027 is that dev finds the fix and the holdout says whether it
generalises. Dev was already at 100%, so it offered no signal; the only failing
cases were in v4, and they were read before the patterns were written. The floor
in `evals/floors.json` is therefore **left at 0.68** rather than raised to the
measured 1.0: a floor set from a contaminated measurement would lock in tuning.

## The finding that matters more

`evals/causal.json` gains **`probe_v5`**: 32 cases written *with* the new
patterns in view, deliberately choosing causal constructions the patterns do not
name (`نجم عن`, `أفضت … إلى`, `بفضل`, `جرّاء`, `فاقم`, `عزّز`, "was behind",
"attributable to", "stems from", "gave rise to", "brought down", "translate
into").

On that set the lint scores **6% recall** — one causal claim in sixteen — at
100% precision.

`probe_v5` is **not** a blind holdout and is not comparable with v1–v4, which
were written from the label definitions only. It is an adversarial worst case,
and it is recorded as such in every case's `source` and asserted by
`tests/test_evals.py`. It says one thing clearly:

> A regex phrase list catches the constructions it names and essentially nothing
> else. Causal language is an open class in both languages, so each round of
> tuning raises the score on the set in hand without raising the capability.

The honest reading of the whole series — 67% → 69% → 100% across v3, v4 and the
tuned v4 — is that the rules have been tracking their test sets, not learning
causation. `project-progress.md` already carries the next step as Next item 4:
put a model behind the rules, with the rules as a cheap high-precision prefilter
and the model as the recall layer, scored on a set written by someone who has
not seen either.

## Consequences

- Arabic deliverables now get the same gate as English ones, which they did not
  before. That is a real gain regardless of what the probe says.
- Precision stays at 100% on every set, so the gate still does not cry wolf.
- Nobody should quote the 100% on v4 as the lint's accuracy. The number to quote
  is "100% on the set it was tuned against, 6% on constructions it was not".
- No product behaviour changes: the lint is a review-loop tool, not a pipeline
  stage. Publishing and the approval gate are untouched.
