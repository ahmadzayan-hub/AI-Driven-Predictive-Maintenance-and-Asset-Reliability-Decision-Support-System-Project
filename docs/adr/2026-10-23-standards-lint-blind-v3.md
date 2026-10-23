# Standards lint: blind set v2 into dev, families widened, judged on blind set v3

Date: 2026-10-23 · Status: Accepted (the next round named in
`2026-10-23-standards-lint-families-blind-v2.md`; the same process as the
causal and intent fixes of `2026-10-23-blind-v7-into-dev-causal-and-intent-fix.md`).

## Decision

Blind set v2 (40 cases, 32% recall) moved into dev with a source note, and
the five families were widened against its fifteen misses: an optimum as
"the best arrangement the depot can achieve", "the solved allocation", "no
other order could" and the Arabic "أفضل ترتيب", "التوزيع المحلول", "لا يوجد
ترتيب آخر"; a realised benefit as "knocked AED 640,000 off", "earned back
its purchase price", "recouped", and the Arabic "استعادت ثمنه", "خفّضت ...
فواتير"; a cost total whose activity is "inspections", "refits" or "keeping
the fleet running" and whose spend word is "came to" or "totalled", with the
Arabic "نفقات", "الفحوص", "الترميمات", "التشغيل"; a count beside "crossed the
ceiling", "beyond the limit", "in the red" or "risk category", with the
Arabic "عالية الخطورة", "تجاوزت", "السقف", "الفئة"; a recommendation in
"it would be sensible to", "worth considering", "we urge", and the Arabic
"من المستحسن", "يُستحسن", "من الحكمة", "يجدر". Dev (112 cases) and the two
old blind sets score 100%; the holdout keeps its 90% floor with the same
one false alarm.

An independent agent then wrote blind set v3 (40 cases, 22 positives, half
Arabic) from the definitions only, without opening the lint and reading
the stored splits only so that no phrasing repeats. It was scored once
before being stored: recall 14% (3 of 22), no false alarms, which is the
floor (0.13). It was not used to fix anything.

The score is lower than v2's because v3 is a harder set, not because the
rules regressed: it is written in dashboard-tile, slide-bullet and footnote
register ("Amber band: 1,612 pumps (last 12 months)", "Bay allocation:
SOLVED", "Priority order (final) ... leaves nothing on the table", "payback
... was reached in week nineteen", "money the operator no longer spends",
"Next step: swap the brake pads", "placed 735 escalators in the top risk
decile", "absorbed AED 6.4 million", and the Arabic equivalents), where the
breach is carried by layout and idiom rather than by a verb the families
know. Those are the next families. The next fix moves v3 into dev and is
judged on a v4 written the same way.

## Consequences

- `evals/standards.json` has 112 dev, 24 holdout and 40 blind_v3 cases; each
  blind_v3 case also records the class it tests. `evals/floors.json` records
  the blind floor at 0.13; the suite declares blind_v3.
- The honest number to quote for the lint in the field is 14% recall with
  no false alarms: it is a free first pass that never cries wolf, and the
  review loop's reviewers remain the catch for standards wording. Each round
  so far has lifted the previous blind set to 100% and found the next set
  mostly unseen; the families grow, the field is wider than the families.
