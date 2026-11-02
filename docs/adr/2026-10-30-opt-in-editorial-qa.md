# Opt-in editorial QA for selected drafts

Date: 2026-10-30. Status: draft review candidate.

## Decision
The owner requested useful reviewed writing guidance on GitHub before laptop
installation. Add a linked bilingual reference rather than upstream skill
activation, hooks, a global mode or a new model pipeline. Preserve existing
Claude and Hermes work. No approved report, audited claim, data, runtime prompt,
model configuration or dependency changes.

The alternative of installing the packages unchanged was rejected: blanket
style rules can delete technical meaning, and a concise-output preference does
not justify medical assumptions or persistent session behavior.

## Validation and reversibility
A standard-library fixture check and unittest wrapper exercise the documented
synthetic pairs and changed protected tokens. These are teaching tests, not
semantic/model benchmarks. Existing review gates remain mandatory. Remove the
reference and its links with a normal commit if it proves unhelpful; no history
rewrite. GitHub draft review does not authorize merge, deployment, report
approval or activation on the owner's laptop.
