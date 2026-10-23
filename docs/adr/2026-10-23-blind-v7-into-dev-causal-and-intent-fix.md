# blind_v7 moves into dev, and the causal and intent rules are fixed against it

- Status: Accepted 2026-10-23
- Date: 2026-10-23
- Follows [new labelled cases from real use](2026-10-20-labelled-cases-from-real-use.md),
  which listed what `blind_v7` still missed and said that whoever fixes the
  rules must move the set into dev first and ask for a new blind set.

## Decision

1. **`blind_v7` is dev data now.** In `evals/causal.json` and
   `evals/intent.json` its 50 and 57 cases were appended to `dev`. Each keeps
   its original `source` and gains "moved into dev on 2026-10-23 before the
   rules were fixed against it, so no longer independent". The `blind_v7`
   key is gone.
2. **No blind split, no blind floor, for causal and intent until `blind_v8`
   arrives.** `scripts/evaluate_agents.py` declares no `blind` entry for
   those two suites, with a comment saying a new independent set is pending.
   Their blind floors (0.60 and 0.61) are removed from `evals/floors.json`
   because the split they judged no longer exists; no other floor changed,
   and the dev floors stay at 1.0 over the enlarged dev sets. Jargon
   `blind_v6` and standards `blind_v1` are untouched and still floored.
3. **The rules were changed as linguistic families, not sentences.**
4. **One causal case is set aside as a contested label**, not fixed (below).

## What changed in the rules

**Causal wording (`scripts/claims_lint.py`).**

- Soft causal verbs: bred, spawned, fuelled, fostered, provoked,
  precipitated, engendered. "Induced" is left out because an induced current
  is physics; "bred in the depot" is a description, not a cause.
- Nominal origin: "the product of", "a by-product of", but not "the product
  of the two rates".
- Tracing an effect to an origin: "can be traced back to deferred
  inspections". Tracing a figure to its source, register, row or document is
  what this repository asks for and stays negative, and so does "cannot be
  traced to them" (identifiability, from the 2026-10-20 record itself).
- Pseudo-clefts that name a cause: "is what pushed", "is what ultimately
  killed". "That is what happened" and "is what we measured" stay negative.
- A sentence-opening passive participle clause gives a reason: "Having been
  starved of grease, the points machine locked up."
- Arabic: "أفضى ... إلى" and "أسفر ... عن" beside "أدى ... إلى"; attribution
  with "عزا / يعزو ... إلى"; the Arabic pseudo-cleft "هو ما دفع / جعل / أدى".
  Paying an amount ("دفع المقاول المبلغ إلى المورد") stays negative.
- Denials are not claims: "nothing in the data suggests", "no evidence
  that", "we make no claim about cause", "لا يوجد ما يشير", "دون ادعاء".

**Intent (`assistant.understand`).**

- Chat shorthand is read as the words it stands for before any rule ("wat",
  "u", "ur", "pls", "plz", "r"). Whole tokens only, so "u-bolts" is kept, and
  the note, goal, name or search term stored is taken from the person's own
  words.
- Help: "how does this tool work", "what's in your bag of tricks / toolbox",
  "what commands do you understand", "no idea where to begin" when it ends
  the clause, and the Gulf and Levantine "ايش اللي تقدر تساعدني فيه".
- Remember: "don't let me forget", and the Arabic wanting-you form
  ("ابغاك تحفظ", "عايزك تفتكر"), where "تفتكر" means remember only after
  "I want you"; alone it still asks "do you remember?".
- Recall: "do you still have that bit / info about", "شو المحفوظ عندك",
  "إيش كنت قلت لك عن".
- Forget: scrap, discard, ditch, bin, get rid of, a saved preference, and
  the Gulf "شيل"; "من الذاكرة" at the end is no longer read as the topic.
- Clear history: "our / this / my thread", and "نظّف" with a history noun.
  "Reset the thread tension" and "نظف القطار" stay chat.
- Stop recording: the plural "المحادثات".
- Start a run: "kick off / launch a run or study", "take the X file and",
  "شغّل لي دراسة", "سوّ لي تحليل".
- Run status: a job or run that someone started ("did that job I started
  earlier finish"), "has the pipeline finished", "شو صار بالتشغيل اللي
  بدأناه". "Did the job interview finish early" and "التشغيل التجريبي للخط"
  (a line's trial operation) stay chat.
- Explain the report: "read me the prescriptive bit"; each section name now
  also selects its section.

## The contested causal case

"The fault in the traction motor accounts for the 40 percent rise in
unplanned maintenance cost." The lint's own contract (its docstring) names
"accounts for" as association wording that observational data supports, and
on 2026-10-20 an earlier "accounts for" case was removed for the same reason.
Wording alone cannot tell a share ("the North region accounts for the rise")
from a cause. The case is kept, unscored, under `contested` in
`evals/causal.json` with that reason in its `source`, so the judgement can
be reversed by moving it back.

## Measured, before and after

`python scripts/evaluate_agents.py` with the rules at the previous commit
and at this one, on the same files.

| Suite and split | Before | After |
| --- | --- | --- |
| Causal, the 50 ex-`blind_v7` cases | recall 60% (15 of 25), precision 88%, 2 false alarms | recall 96% (24 of 25), precision 100%, 0 false alarms |
| Causal, enlarged dev (155 scored) | recall 89% (70 of 79), precision 97% | recall 100%, precision 100% |
| Causal, holdout (32) | recall 100%, precision 100% | recall 100%, precision 100% |
| Causal, `probe_v5` (32, adversarial, unfloored) | recall 44% (7 of 16), precision 100% | recall 56% (9 of 16), precision 100% |
| Intent, the 57 ex-`blind_v7` cases | macro recall 61%, 35 of 57 correct | macro recall 100%, 57 of 57 |
| Intent, enlarged dev (331) | macro recall 93%, 309 of 331 | macro recall 100%, 331 of 331 |
| Intent, holdout (60) | macro recall 77%, macro precision 90% | macro recall 83%, macro precision 93% |

The one ex-`blind_v7` causal miss in the "after" column is the contested
case. Older holdouts (causal `holdout_v1` to `v3`, intent `holdout_v1` to
`v3`) stay at 100%. No dev, holdout or other stored case of any suite
changed for the worse. On the project's 372 Markdown files the new lint
flags two more sentences than before, both in the 2026-10-20 record where it
quotes the missed phrases ("the product of", "bred"); it flags one fewer
("we make no claim about cause").

## Reading it honestly

- **These are dev numbers, not blind ones.** The rules were changed while
  looking at the 50 and 57 sentences, so 96% and 100% say only that the
  families cover what they were written for. They are not evidence of how
  the rules do on sentences nobody fitted to. That number comes from
  `blind_v8`, written independently and scored once.
- **The intent holdout rose from 77% to 83%** (4 of 60 more correct). This
  session did not read the holdout before scoring it, but earlier rounds
  did, so it is a second dev score in the sense the evaluation script
  describes, not a blind one. It is a hint that the families generalise a
  little, within the noise of a 60-case set.
- **Precision was kept by testing negatives next to each family:** a figure
  traced to its register, a person who cannot be traced, a cleft that only
  reports, a product of numbers, paying an amount, a job interview, a sewing
  thread, cleaning a train, and a line's trial operation. They are in
  `tests/test_evals.py` alongside one new example of each family.
- **The intent gap is still a long tail.** The 2026-10-20 record found that
  intent fixes barely generalised to an unseen set; nothing here shows that
  has changed. A model behind the rules (ADR 0019) or a much larger labelled
  set remains the honest next step.
- **What `blind_v8` must judge:** the causal and intent rules as of this
  commit, scored once, with the score stored before any further fix. Its
  floor is a person's decision, set from that first score.

## Limits

- One session wrote the fixes and the negative examples; nobody else has
  reviewed the labels of the moved cases.
- A sentence-opening "Having been ..." clause is now always flagged. A
  purely temporal one ("Having been inspected in May, the unit returned to
  service") would be a false alarm; none is in any stored set.
- Shorthand expansion covers a short list of common tokens, not spelling in
  general.
