# ADR 0060: A Tier 0 lint for what a reporting standard would refuse

- Status: accepted
- Date: 2026-10-19
- Extends ADR 0027 (agents are measured). Companion to `scripts/claims_lint.py`.

## Problem

The owner asked for agents built on finance, PMI and ISO asset-management
standards, to review the deliverables. Two findings shaped a smaller answer.

**The roster is already seven agents, and only some are measured.** Labelled
suites exist for intent, column roles, personal data, router, raw-data guard,
jargon, causal wording and figures. The four LLM reviewers are scored only
against three seeded memos, and `project-progress.md` records that they "were
already near their ceiling, so the prompt changes are not proven on held-out
memos". Three more unmeasured agents would make that worse, and ADR 0027 is the
rule they would break.

**The same day showed what unmeasured confidence is worth.** The causal lint
reads 100% on the holdout it was tuned against and 6% on `probe_v5` (ADR 0056).

So: one deterministic checker that can be measured, rather than three agents
that cannot.

## What the standards actually require

Read from secondary sources - vendor guides, a BSI implementation guide, an
ICAI opinion, professional commentary - and **not** from the standards
themselves, which are paywalled. Anything quoted in a graded deliverable should
cite the primary text.

- **ISO 55000 / 55001.** 55000 is the overview and is not certifiable; 55001
  holds the auditable requirements. Asset management is the coordinated activity
  to *realise value from assets*, explicitly not a synonym for maintenance.
  **Line of sight** is the connection from top management's direction down to
  asset decisions; the **SAMP** bridges corporate objectives to asset management
  objectives (Cl. 6.2.1). Clause 6 reportedly draws the most audit findings, for
  weak line of sight and poor performance measurement.
- **PMI PMBOK 7.** Twelve *principles of project management* - not "delivery
  principles" - alongside eight performance domains. Only Stewardship, Team and
  Stakeholders were verifiable in the sources found.
- **IAS 16.** Two component types: a physical part, and a non-physical component
  representing a **major inspection or overhaul**. Day-to-day servicing and
  repairs go to profit or loss (para 12); an inspection component depreciates to
  the next inspection and the previous one is derecognised.

## Decision

`scripts/standards_lint.py`, Tier 0: no model, no tokens, no dependency. Five
classes, each from a published rule and each already named in the team's own
pre-submission gate:

| Class | What it refuses | Rule |
| --- | --- | --- |
| `optimisation` | a ranking called optimal, optimised, maximised or minimised | ISO 55001 Cl. 6 - a ranking is not a solved allocation |
| `realised_benefit` | a saving asserted as obtained rather than proposed | the gate's "no realised savings without evidence" |
| `capitalisation` | a cost total silent on how overhaul is treated | IAS 16 para 12 |
| `grain` | a count of observations described as assets | the dataset's grain: 5,000 observations, 180 assets |
| `line_of_sight` | a recommendation carrying no objective, owner or measure | ISO 55001 Cl. 6.2.1 |

`capitalisation` is exempted when the sentence states the treatment, because
saying it is what the standard asks for: the compliant sentence must not be
punished. `line_of_sight` is judged by what a recommendation carries rather than
by a phrase. English and Arabic throughout. Like `claims_lint`, it finds
**wording, not truth**, and a flagged sentence may be accepted in the plan.

**PMBOK and the ISO clause questions go into `brief-compliance-reviewer` as a
rubric, not into new agents.** That reviewer already checks a deliverable
against its brief and rubric; a standards rubric is exactly that, and a separate
agent would overlap it.

**No finance agent.** Whether an overhaul is a capitalisable component is an
IAS 16 judgment needing the primary standard and an accountant. The honest
automatable slice is the phrase check above; a model guessing it would produce
confident accounting advice, which is worse than none.

## What this is worth, measured

`evals/standards.json`, 36 dev and 24 holdout cases, scored by
`scripts/evaluate_agents.py --suite standards`: **100% recall and 100% precision
on both splits.**

**That holdout is not blind and its number should not be trusted.** Every case
in it says so in its own `source` field: it was written by the same session that
wrote the patterns. The floor is set at **0.9, not the measured 1.0**, for the
same reason - a floor taken from a self-written set would lock in the author's
blind spots. A session that has not seen these patterns should write a blind set
and re-measure; until then the honest claim is "it catches the classes it names,
in the wordings its author thought of".

Two defects were found by the suite rather than by reading: the verb patterns
missed third-person forms (`optimises`, `minimises`), and a literal **backspace
character** stood where a word boundary was meant, so `TREATMENT` silently
matched nothing. A test now asserts no pattern carries a control character.

## Consequences

- A deliverable can be checked before a reviewer reads it, at no cost, for the
  five failures this project has actually made.
- The roster gains no agent. `motion-designer` has no role in the three graded
  deliverables and should justify its place or be retired - the owner's call,
  not recorded as a decision here.
- The lint does not read PDFs or decks itself; it reuses `figures_check.read_text`,
  so it covers whatever that covers.
