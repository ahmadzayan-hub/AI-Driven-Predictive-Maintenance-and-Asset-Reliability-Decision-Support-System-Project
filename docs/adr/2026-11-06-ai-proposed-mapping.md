# AI-proposed executive mapping

Date: 2026-11-06 · Status: Accepted · Owner request: "The platform AI models analyse and study the best executive mapping and build the interactive dashboards"

## Context

A dataset's column mapping (which columns are measures, breakdowns and the date, which
way is better, which pair to cross) decides what the designed page, the brief and the
exports show. The rules suggested roles; nothing proposed the executive reading of a
dataset as a whole, and no model was involved.

## Decision

1. `POST /api/datasets/{id}/mapping/proposal` asks the configured model for the executive
   mapping, from a schema-only profile: each column's name, type, fill, distinct count and
   number shape. No value, example or category label is sent. A dataset whose columns the
   rules detect as personal data asks no model at all.
2. The answer must name every column with a known role and pass `mapping.validate` on every
   row. Columns the rules found empty or personal stay ignored whatever the model says.
   Reasons are one plain sentence in English and Arabic, at most 160 characters, with no
   links or markup; a column without a usable reason keeps the rules' reason.
3. Anything else (no model configured, the provider unreachable, an invalid answer) returns
   the rules' suggestion, labelled as the rules', with the reason in the reader's language.
   The reply says which: `source` "model" with the provider, or "rules".
4. The mapping may now keep `cross`, two dimensions to cross. The designed page's matrix
   and the executive brief cross that pair first when it is informative; otherwise the
   planner chooses as before.
5. In the mapping panel, "Propose with AI" fills the form, shows who proposed it (from the
   column names and counts only) and each column's reason. Nothing is saved until the owner
   presses "Save mapping"; the dashboard then follows the saved mapping.
6. Fixed on the way: the panel's save request never sent `better` or `decimal`, so the
   5 November direction and decimal-comma choices were lost when saved from the panel. It
   now sends them, and `cross`.

## Consequences

- Tests (recorded model answers, never a real provider): a valid proposal is used and
  labelled; no cell value reaches the model; five kinds of bad answer fall back to the
  rules with a note; no model or no permission falls back; an empty column stays out; a
  saved pair is validated and crossed first; the endpoint proposes without saving and hides
  another owner's dataset; the panel fills, labels and saves the proposal with `better`,
  `decimal` and `cross`.
- In this environment no model is configured, so every proposal here comes from the rules.
  A real provider's proposals have not been evaluated against expert mappings.
