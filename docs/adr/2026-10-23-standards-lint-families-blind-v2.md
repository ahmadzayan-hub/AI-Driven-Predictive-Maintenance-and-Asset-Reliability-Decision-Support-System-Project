# Standards lint: rules as linguistic families, judged on blind set v2

Date: 2026-10-23 · Status: Accepted (the open item "the standards lint scores
0% on its blind set"; the same process as the causal and intent fixes of
`2026-10-23-blind-v7-into-dev-causal-and-intent-fix.md`).

## Decision

Blind set v1 (36 cases, written on 22 October from the label definitions
only) scored 0% recall against the first rules, which matched the dev
phrasings and little else. It moved into dev, and the five classes were
rewritten as linguistic families: an optimum in any wording ("ideal
allocation", "most efficient possible", "the best schedule"), a realised
benefit in any verb ("paid for itself", "cut the bill by", "has recovered"),
a cost total read as a maintenance activity plus a spend word plus a money
figure in one sentence (with the treatment words that make it compliant
widened to "split between", "of which", "separately"), a count read as a
count (digits or number words) beside an asset noun with a state or
threshold anywhere in the sentence, and a recommendation in any modal
("should", "ought to", "needs to", "we suggest") judged by the line of sight
it carries. Dev and the old blind set score 100%; the holdout keeps its 90%
floor with one false alarm.

An independent agent then wrote blind set v2 (40 cases, 22 positives, half
Arabic) from the definitions only, without opening the lint, and the set
was scored once before being stored: recall 32%, which is the floor. It was
not used to fix anything. The misses are the next families: "the best
arrangement the depot can achieve", "the solved allocation", "knocked
AED 640,000 off", "earned back its purchase price", "spend on keeping the
fleet running came to", "items of equipment crossed the ceiling", "it would
be sensible to", and the Arabic equivalents. The next fix moves v2 into dev
and is judged on a v3 written the same way.

## Consequences

- `evals/standards.json` has 72 dev, 24 holdout and 40 blind_v2 cases;
  `evals/floors.json` records the blind floor at 0.31; the suite declares
  blind_v2.
- The lint is better on paraphrases and still far from the field: 32%
  recall blind means two of three refused sentences in new wording get
  through. The review loop's reviewers remain the main catch for standards
  wording; the lint is the free first pass.
