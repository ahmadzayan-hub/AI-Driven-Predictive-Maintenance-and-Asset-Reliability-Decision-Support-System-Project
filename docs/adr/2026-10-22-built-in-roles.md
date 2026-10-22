# Built-in Hermes, agents and consultants when no model plays the role

Date: 2026-10-22 · Status: Accepted (owner request, 22 October: "if no local
models please use the built-in model", then "develop that agents and consultants
too are built-in")

## Context

The model roles (ADR 2026-10-21) are optional. With no model configured or
reachable, which is production's state today, the planner carried no plan, no
stage carried a note, and the report had no orchestrator and consultant section.
The owner wants every role present whether or not a model is reachable.

## Decision

1. A role nobody plays is played by the **built-in writer**: fixed rules over the
   same verified findings, with no language model. Hermes' plan names the fixed
   order and the stages whose titles guard quality, privacy, validity or risk;
   each agent's note reads back its own verified claims; the consultant asks the
   standard question (open each figure's calculation, confirm the snapshot) and
   then one question per risk rule that a finding triggers (coverage, prediction,
   finance, operations, causation, anomalies), quoting that finding; Hermes' brief
   says what to check first and how to weigh the consultants.
2. Every built-in sentence is fixed text in English and Arabic and carries no
   digit of its own; the only figures are the quoted findings. The same
   `grounded()` guard still runs over every note.
3. The report's caution line says which it was: written by language models, or by
   the platform's built-in rules with no language model. Each note is labelled
   `built-in`. A model configured for one role and the built-in writer for another
   mix freely; the health map shows the author of each.
4. `AGENTIC_OS_BUILT_IN_ROLES=0` switches the fallback off, restoring the earlier
   behaviour (no roles, no section). `/api/health` reports the switch as
   `model_map.built_in_fallback`.

## Consequences

- Every report now has the section, so approvers see the same questions in demo
  and in production without a model, and a model's notes slot into the same place
  when one is configured.
- The built-in consultant is rules, not judgement: it raises the questions a
  reviewer should always ask, triggered by what the findings say. It is labelled
  as such and never claims to be a model.
- Runs do slightly more work (string rules only; no network).

## Verification

`tests/test_orchestration.py` (`RoleSelectionTestCase`, `BuiltInRolesTestCase`):
nothing configured means the built-in writer plays every role; the switch turns it
off; an unreachable model falls to it; the plan names the order and guarding
stages in both languages; the consultant raises the standard question then the
triggered rules, quoting the finding, and is always grounded; a whole run with no
model carries plan, notes, consultant and brief labelled `built-in` with the
built-in caution, in English and Arabic; a model beside the built-in writer keeps
the model caution. `tests/test_model_gateway.py`: the health map shows the
fallback and its switch.
