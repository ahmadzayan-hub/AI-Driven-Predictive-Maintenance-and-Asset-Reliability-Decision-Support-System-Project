# Reading test: facilitator kit

Companion to the [protocol](2026-10-21-manager-reading-test-protocol.md).
Everything a facilitator needs to run one session in about an hour. Results
go in the git-ignored `private/` folder, never in this repository.

## 1. Two builds, side by side

The "before" build is `efb6eb1` (before the redesign); "after" is `main`.

```bash
git worktree add ../reading-test-before efb6eb1
(cd ../reading-test-before && npm --prefix frontend ci && npm --prefix frontend run build \
  && python scripts/serve.py --local-only --port 8001) &
python scripts/serve.py --local-only --port 8002 &   # current main, after `npm --prefix frontend run build`
```

Each build keeps its own data folder; load the participant's file into both
before the session, through **Datasets → Add a dataset**, and run one
analysis with the maintenance profile on each. Remove the worktree afterwards
with `git worktree remove ../reading-test-before`.

Counterbalance: P1 and P3 start on the old build, P2 and P4 on the new one.

## 2. Task cards (read aloud; show the card)

| # | English | العربية |
| --- | --- | --- |
| 1 | What is availability for the last period, and is it on target? | ما نسبة الجاهزية في الفترة الأخيرة، وهل تحقق الهدف؟ |
| 2 | Which group of measures looks worst, and which figure tells you? | أي مجموعة من المؤشرات تبدو الأسوأ، وما الرقم الذي يدل على ذلك؟ |
| 3 | How many records is the first-time fix rate computed on? | على كم سجلًا يُحسب معدل الإصلاح من المرة الأولى؟ |
| 4 | Start a new analysis on this file. | ابدأ تحليلًا جديدًا لهذا الملف. |
| 5 | Which asset measures have no target set? | ما مؤشرات الأصول التي لم يُحدَّد لها هدف؟ |
| 6 | On the phone: open the dashboard and read the downtime per record. | على الهاتف: افتح لوحة المعلومات واقرأ قيمة «التوقف لكل سجل». |

Do not point at the screen or name a menu. If a participant is stuck for two
minutes, record "not completed" and move on.

## 3. Scoring sheet (copy per participant into `private/`)

| Participant | Build | Task | Seconds | Answer | Correct / partly / wrong | Clicks | "Where is…" moments | Confidence 1–5 | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | old | 1 | | | | | | | |

"Correct" means it matches the figure the register computed for that file;
note the figure beforehand from the run's evidence.

## 4. Two questions at the end

1. "On the new screens, what did the colours tell you?" Write the answer down
   word for word. Anyone who reads a group colour as good or bad is a design
   defect to fix, whatever the timings say.
2. "What would you remove?"

## 5. Consent line (read before starting)

"We are testing the screens, not you. I will time each task and note what you
say. Nothing that identifies you or your organisation will be kept outside a
private folder, and I will not record audio or video unless you agree
separately."

## 6. Afterwards

Summarise per task: median seconds and errors on each build, the colour
answers, and what you would change. Mark it as four people on their own data,
moderated by someone who knows the design, so not a statistical result.
