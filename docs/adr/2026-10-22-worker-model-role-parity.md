# Background workers honor the configured model roles

Date: 2026-10-22

Status: accepted

## Context

The API constructed ModelRoles and exposed the selected Hermes, specialist and
consultant models in health. The production build_worker path constructed its
RunEngine without roles. Consequently background runs omitted orchestration and
specialist model notes despite the API advertising their configuration. A real
local fictional run exposed the discrepancy after chat had been repaired.

## Decision

Construct ModelRoles from the worker's explicit environment and plain gateway,
before applying an optional narration router, matching API construction. Pass
active roles into the worker engine. Preserve built-in roles when configured
models are absent and honor AGENTIC_OS_BUILT_IN_ROLES=0. Model failures remain
bounded, figures stay calculated, raw rows stay out of model requests and human
approval remains required. Existing reports are not rewritten.

Apply the shared personal-data boundary to role requests as well as narration:
scan outgoing goal/facts and suppress role handoffs when persisted or current
privacy/merge evidence flags personal data. Authorized human reports retain
their evidence. This is necessary before enabling the previously disconnected
worker roles; no raw rows are added to model prompts.

The live run also exposed severe memory pressure with both local weights retained.
Hermes did not complete full planning requests within the deadline even after
freeing memory. The owner explicitly selected Qwen for all local roles. The
private local profile therefore uses the installed instruction-only Qwen3 4B tag
for chat, narration, orchestration, specialist notes and a local consultant.
These are distinct prompts using one model, not independent model providers.
Keep the existing startup prewarm, cache behavior and bounded inference deadline.
For explicit non-reasoning Ollama roles, bound plans, consultant questions and
closing briefs to a concise response with a 240-token ceiling and a 45-word
instruction. The earlier reasoning-sized budget could exhaust the deadline for
a short briefing. Chat and narrative budgets and hosted defaults are unchanged.
Use an unnumbered paragraph: a live consultant response introduced numbered
list labels absent from its evidence and was correctly rejected by grounding.
Change the requested format, not the numeric validator.

This does not assert that a configured
provider answered, install a model, enable cloud credentials or bypass the
numeric grounding checks. Live acceptance must inspect stored authors and the
report rather than rely solely on health or completed task counts.

## Verification

The production worker builder regression executes a whole fictional run with
mocked model transport and verifies the distinct Hermes and Qwen model tags,
stored plan and specialist notes, final Hermes brief, and pending publication
approval. Another case checks the default built-in writer and explicit disable
without model traffic. Both regressions reproduced missing roles before the fix.
Live results and limitations are recorded in README.md#testing.

Worker privacy regressions exercise sensitive goals and a personal grouping label,
checking all captured requests after the run rather than trusting an assertion
inside the model callback (role failures are intentionally caught).
