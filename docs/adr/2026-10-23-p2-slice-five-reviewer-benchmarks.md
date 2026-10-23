# P2 slice five: benchmarks and floors for the three unmeasured reviewers

Date: 2026-10-23 · Status: Accepted (assessment finding G9 in
`docs/audits/SAAS_PLATFORM_ASSESSMENT.md`; the fifth slice of section 3 of
`docs/implementation/DELIVERY_ROADMAP.md`).

## Decision

The brief-compliance, security-privacy and accessibility-i18n reviewers
each get a blind benchmark of their own in `evals/reviewers/` (H, I and J),
labelled before any run, with categories that are the reviewer's whole lane
(`scripts/score_review.py`, `LANES`). Each reviewer ran once as the loaded
subagent, told to open only its memo (and the brief for H); the reply was
saved verbatim under `runs/` and scored. The scores are the floors in
`evals/floors.json` (lane recall, paragraph detection recall, and the most
false alarms allowed), and `tests/test_evals.py` fails when a saved first
run no longer meets them or when a memo's labels drift from its text.

Measured on 23 October: the brief reviewer 75% lane recall with two false
alarms (one of them the benchmark tag in the title, which the brief's own
file-name rule forbids and which is kept as recorded); the security
reviewer 100% with one false alarm (a block it wrote while saying no finding
was needed); the accessibility reviewer 100% with none. The memos are now
dev data for their reviewers: a change to a reviewer's instructions is
measured on a fresh blind memo, as with memos E and F.

## Consequences

- The reviewer loop has a floor for every reviewer it runs, not three of
  six. `evals/reviewers/README.md` records the runs and what each missed.
- Memos H, I and J carry no figure register, so the Tier 0 checker and the
  team score do not apply to them; `summary.json` lists them by lane.
- Open: G8's model half (the opt-in `intent_model` suite needs a provider),
  the interface items, the standards lint blind score.
