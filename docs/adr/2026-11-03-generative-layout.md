# Generative layout: a plan per dataset, validated and grounded (slice 1: server)

Date: 2026-11-03 · Status: Accepted for slice 1. The owner set the controlling
requirement on 2 November 2026: an LLM-designed, data-specific interface, not a
fixed dashboard with numbers substituted.

## Context

Miyaar's sources differ: maintenance records, contracts, budgets, mixed files.
The owner asked that each authorised dataset get the interface that suits it,
designed by a language model from the data's profile and the user's objective.
Brand, navigation, permissions and accessibility stay fixed. Every number must
come from a computed result, and no model output may run as code.

## Decision

1. **A declarative plan, version 1** (`server/layout_plan.py`).
   - A plan holds an objective and 1 to 10 sections.
   - Each section has a unique id, a registered component, an English and
     Arabic title and purpose, a span of 1 to 3, allowed interactions, and a
     binding.
   - Components: `kpi`, `trend`, `ranking`, `comparison`, `distribution`,
     `table` and `gap`.
   - A binding is a query of the existing query engine (`server/query.py`:
     named aggregates, filters, at most two groupings), or a column list for
     `table`. There are no expressions, URLs, scripts or remote components.
2. **Profiling, with no values sent.** The planner sees field names, types,
   roles, fill counts and distinct counts only. It never sees row values,
   category labels or ranges. The fingerprint hashes the schema, so a refresh
   of the same schema keeps it.
3. **Capability assessment.** These analyses are supported or refused with a
   reason:
   - `descriptive`
   - `trend`: needs a recognised date column;
   - `ranking`: needs a text column with 2 to 50 groups and a measure;
   - `distribution`
   - `forecast`: always refused by the planner. It needs a validated model
     result, so no curve is ever drawn from nothing;
   - `predictive_risk`: needs the risk-ranking stage to have succeeded;
   - `prescriptive`: needs the scenario stage to have succeeded.

   An unavailable analysis that matters appears as a `gap` section with its
   reason, never as an invented figure.
4. **Validation rejects the whole plan.** It rejects:
   - unknown keys, components or properties;
   - a wrong version or duplicate ids;
   - missing Arabic text;
   - links, markup or templates in text;
   - a component whose capability is unavailable;
   - a trend not grouped by the date column.

   It then **grounds** every binding by running it through `query.aggregate`
   or `query.records` against the real table. A binding that does not
   execute, such as an invented field, rejects the plan with the query's own
   reason. A partly valid plan is never rendered.
5. **Planners.**
   - The configured model is asked through the existing `ModelGateway.ask_json`
     only when the caller allows it and the run's privacy checks
     (`run_blocks_model`) allow it.
   - Otherwise, or when the model's plan fails validation, a deterministic
     **rule planner** derives a plan from the same profile.
   - The response says which planner was used (`source`: `model` or `rules`)
     and why.
6. **API.** `POST /api/runs/{id}/layout` with `{objective, use_model}` takes
   the read permission and has the same ownership and 404 rules as the
   table's query endpoints. It returns `plan`, `source`, `notes`, `problems`,
   `capabilities` and `fingerprint`.

## What this slice does not do yet

- **Interface:** the renderer and its cross-filtering, Jarvis scope,
  pinning, undo and restore of earlier views.
- **Persistence:** versioning plans in the store, which needs a schema
  migration.
- **No real model run:** no end-to-end run with a real provider has happened.
  No model is configured in this environment, so every plan produced here
  came from the rule planner. The model path is tested only with recorded
  fake answers, and is not claimed as working against a provider.

## Verification

`tests/test_layout_plan.py`, 11 tests, all on synthetic data:

- Four schemas (maintenance, contracts, budget, and an unseen training
  schema) produce four different grounded layouts. Trends appear only where
  there is a date, and every plan names the missing forecast as a gap.
- Eleven hostile or invented plans are rejected whole: an unknown component,
  an invented field, a link, markup, a template, an extra key, a duplicate id,
  a trend on text, a gap for an available capability, missing Arabic, and an
  unknown aggregate. A wrong version and an extra top-level key are also
  rejected.
- A recorded valid model plan is used and labelled with its provider, and
  the payload sent carries no category values.
- A recorded invalid plan is never rendered, and the rule planner is used.
- Prompt-injection text in a field name changes no binding.
- With no model, no permission, or a provider failure, the response says so.
- An empty table gives only a gap section.

`tests/test_query.py` adds two checks:

- an API test on a real run;
- the endpoint is added to the tenancy tests: another owner gets a 404, and
  a viewer and an admin can read.
