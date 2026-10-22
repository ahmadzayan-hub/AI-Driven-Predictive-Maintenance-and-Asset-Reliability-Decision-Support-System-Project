# A model per role: "provider:model"

Date: 2026-10-22 · Status: Accepted (owner request, 22 October: "I want my local
Hermes model as the orchestrator while a different Ollama model serves the
agents")

## Context

The task map and the role variables named a provider only. Each provider has one
model (`OLLAMA_MODEL`, `ANTHROPIC_MODEL` and so on), so Hermes and the agents could
not both run on the owner's local Ollama with different models.

## Decision

1. Every task map entry and role variable accepts `provider:model`. The provider is
   the text before the first colon, case-insensitive; the model id is the rest, kept
   as written, so `ollama:qwen3:4b` and `openrouter:some/model:free` stay whole.
2. The gateway answers a `provider:model` request from a copy of itself with that
   provider's model replaced. The shared gateway is never changed, so consultants
   running in parallel cannot see each other's model.
3. The provider must still be configured and reachable; otherwise the entry is
   reported in `/api/health` and skipped, as before. Failover, grounding and the
   no-raw-data rule are unchanged. A local Ollama still never fails over to a
   hosted provider.
4. The report and `/api/health` name the role's author as `provider:model`.

## Consequences

- One local Ollama can serve Hermes (`ollama:hermes3`) and the agents
  (`ollama:qwen3`); Claude and OpenAI can be the consultants.
- Two local models need memory for both; Ollama is told to keep both loaded
  (`docs/FREE_OPEN_MODELS.md`).
- The model id is not checked against the provider's catalogue; a wrong id fails at
  the call and the built-in text answers, as for any provider failure.

## Verification

`tests/test_model_gateway.py` (`PerRoleModelTestCase`): the spec splits at the first
colon; two roles reach the same local Ollama with their own models and the shared
gateway keeps its model; role variables keep the model's case and report an
unconfigured provider; a hosted provider takes an override for one task only.
`tests/test_orchestration.py` (`LocalHermesAndAgentsTestCase`): a whole run plans
with `hermes3`, writes agent notes with `qwen3` and credits Hermes in the report.
No live model was called: none is installed or reachable in the development
container.
