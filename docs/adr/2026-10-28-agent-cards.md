# Agent cards: what each stage shows, and what the script budget allowed

Date: 2026-10-28 · Status: Accepted (the "agent cards per stage" item of the
interface list in `project-progress.md`; it follows
`docs/adr/2026-10-28-live-pipeline.md`). The owner asked for the card's content
to be decided, and for the script budget to be trimmed before the card was
added.

## Decision: what a stage card shows

Each stage of a run is one card in the run timeline
(`frontend/src/features/runs/RunTimeline.tsx`). It shows, in order:

1. **The stage and its agent**, by its title in the run's language, with its
   state mark and state word (existing).
2. **Its one-line result** (`summary`, existing).
3. **Its evidence, as counts:** how many claims the stage made, and how many of
   its checks passed (for example "2 claims · 1 of 2 checks passed"). A stage
   that produced neither shows no evidence line.
4. **The inspect action**, which opens the stage's evidence (existing).

The stage running now is named and marked by the live pipeline decision.

Not shown: the stage's full claim list, its raw calculation, its model
parameters. Those stay behind the inspect action, so the timeline stays short.

## What was built, and what was not

- **Built:** the evidence line in both languages, from data the run already
  stores. No server change.
- **Visual cards, amended the same day:** each stage row is a bordered card,
  its edge coloured by its state. The rules live in the analytics stylesheet,
  which loads with the runs view, not on first load: the first-load stylesheet
  stays at 10.46 of 10.5 KB, and the stylesheet total is 34.3 of 35 KB.

## Budget

The script total was 257.0 KB, over its 257 KB ceiling, after the timeline's
additions. It was brought back under the ceiling by:

- removing five unused string keys in both languages: `miyaar.mode`,
  `miyaar.noReply`, `miyaar.governance`, `miyaar.context` and `nav.workspace`.
  They were checked against every source file and test;
- the evidence line itself costs about 100 bytes compressed.

The script total is 256.9 of 257 KB after this slice. The ceiling was not
raised. Further script growth needs either a product decision about a view,
or a raised ceiling with its own record.

The remaining string keys that look unused are built at runtime
(`event.*.failed`, from `${code}.failed`) or are used by a test
(`brand.description`), so they stay.

## Tests

- `frontend/src/features/runs/RunTimeline.test.tsx`: the stage running now is
  named and marked (English and Arabic); the approval wait is not a line of its
  own; the evidence line reports claims and passed checks.
- `runs.spec.ts`, `a11y.spec.ts`, `arabic.spec.ts` and `dashboard.spec.ts` pass
  on desktop and phone (28 cases).
