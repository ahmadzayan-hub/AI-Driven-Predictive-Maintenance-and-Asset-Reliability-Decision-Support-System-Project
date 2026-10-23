# Free open-source model providers and a task-to-model map

Date: 2026-10-22 · Status: Accepted (owner request, 22 October: "develop cloud
open free LLM models to use permanently in the platform, with mapping all AI LLM
models for all tasks")

## Context

The gateway reached Ollama, Claude, OpenAI, Groq and the Vercel AI Gateway, and a
model role could name one of them. Free hosted open-source models were limited to
Groq and a hosted Ollama. Nothing showed, in one place, which model served which
task, and the summary and chat always used the single default provider.

## Decision

1. **Four more providers on the chat-completions contract:** OpenRouter, NVIDIA
   NIM, Mistral and Cerebras. Each needs its key and an explicit model id; free
   model ids rotate, so none is chosen in code.
2. **One task map:** `AGENTIC_OS_TASK_MODELS` assigns a configured provider to
   each of five tasks: `narration`, `chat` (including intent), `hermes`, `agents`
   and `consultants` (several joined with `+`). A role's own variable still wins;
   an unmapped task uses the default; an unknown task or unconfigured provider is
   reported, never guessed.
3. **The map is visible:** `/api/health` returns `model_map`, every task with the
   provider that serves it now, `built-in` where no model is used, and the
   problems found.
4. Unchanged: models see verified sentences only, write words only, fail over once
   to the next hosted provider, then the built-in template.

`docs/FREE_OPEN_MODELS.md` records the researched free tiers, a recommended map
and its daily capacity.

## Consequences

- The platform can run every model role on free open-source models.
- Free limits are small and change without notice; the capacity estimate in the
  reference is a planning figure, not a guarantee.
- Free tiers may keep prompts; client data needs a paid, no-training tier.

## Verification

`tests/test_model_gateway.py` (`FreeOpenModelsAndTaskMapTestCase`): each provider
needs key and model; each request reaches its URL with its key; the map sends
narration, chat and intent to their providers; a wrong task or provider is
reported; roles and the health map follow the map, and an empty configuration
shows `built-in`. No live call: these hosts are not reachable from the
development container.
