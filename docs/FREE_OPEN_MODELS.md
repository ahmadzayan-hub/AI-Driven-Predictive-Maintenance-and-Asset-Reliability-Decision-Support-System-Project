# Free open-source models, and which task each one serves

Researched 22 October 2026. Free tiers change often and the figures below come
from dated third-party trackers, not contracts: confirm each one on the
provider's own pricing and limits page before relying on it.

## Providers the platform can use

| Provider | Variables | Free tier (as reported, Oct 2026) | Notes |
| --- | --- | --- | --- |
| Groq | `GROQ_API_KEY`, `GROQ_MODEL` | About 30 requests/minute and 1,000/day per model; tokens per minute often the tighter limit; no card | The steadiest free option; fast |
| OpenRouter | `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` (a `:free` id) | 20 requests/minute; 50/day, or 1,000/day after a one-time 10-credit purchase | Many open models; free ids can be withdrawn without notice |
| Ollama Cloud | `OLLAMA_HOST=https://ollama.com`, `OLLAMA_API_KEY`, `OLLAMA_MODEL` | A light free plan; limits not published per model | Same chat API as local Ollama; model names drop the local `:cloud` suffix |
| NVIDIA NIM | `NVIDIA_API_KEY`, `NVIDIA_MODEL` | About 40 requests/minute for developer-programme members; no official increase on that tier | OpenAI-compatible |
| Mistral | `MISTRAL_API_KEY`, `MISTRAL_MODEL` | A free plan is reported; terms not verified here | Open-weight and proprietary models |
| Cerebras | `CEREBRAS_API_KEY`, `CEREBRAS_MODEL` | Conflicting reports: one says no permanent free tier since 16 July 2026 | Supported, not recommended for free use |

Claude (`ANTHROPIC_API_KEY`) and OpenAI (`OPENAI_API_KEY` + `OPENAI_MODEL`) remain
available as paid options. Each provider needs an explicit model id: free model
ids rotate, so none is chosen in code.

## The task map

One variable assigns a provider to each AI task:

```
AGENTIC_OS_TASK_MODELS=narration=groq,chat=groq,hermes=openrouter,agents=ollama,consultants=openrouter+nvidia
```

| Task | What the model does | Recommended free provider | Why |
| --- | --- | --- | --- |
| `narration` | Phrases the report's executive summary from verified facts | Groq | One call per run; fast |
| `chat` | Understands chat requests (intent) and answers in conversation | Groq | Needs low latency |
| `hermes` | Plans the run and writes the approver's brief | OpenRouter | Two calls per run; a larger model helps |
| `agents` | Each stage's note on its own findings | Ollama Cloud | The most calls per run (up to 17) |
| `consultants` | Independent risks and questions before the report | OpenRouter + NVIDIA | Two different model families give two views |

A role's own variable (`AGENTIC_OS_HERMES_MODEL`, `AGENTIC_OS_AGENT_MODEL`,
`AGENTIC_OS_CONSULTANTS`) still wins over the map. A task that is not mapped uses
the default provider. A provider named in the map but not configured is reported
under `model_map.problems` in `/api/health` and skipped. When a provider fails,
the next configured hosted provider answers once, then the built-in template.

## A different model per role

Any entry can name a model as well as a provider, as `provider:model`. Everything
after the first colon is the model id, so ids that contain colons stay whole. One
local Ollama can then serve Hermes with one model and the agents with another:

```
OLLAMA_MODEL=qwen3
AGENTIC_OS_TASK_MODELS=narration=ollama,chat=ollama,hermes=ollama:hermes3,agents=ollama:qwen3,consultants=anthropic+openai
```

The same form works in the role variables (`AGENTIC_OS_HERMES_MODEL=ollama:hermes3`)
and for hosted providers (`openrouter:another/model:free`). The provider must still
be configured (for Ollama, `OLLAMA_MODEL` set); the model named must exist there
(`ollama pull hermes3`). `/api/health` shows each role with its model.

### Everything on one laptop, at full capacity

1. `ollama pull hermes3` and `ollama pull qwen3`, then start Ollama with
   `OLLAMA_MAX_LOADED_MODELS=2` so both models stay loaded instead of swapping, and
   `OLLAMA_KEEP_ALIVE=30m` so they are not unloaded between runs.
2. Export, in the terminal that starts the platform (it does not read a `.env` file):
   `OLLAMA_MODEL=qwen3`, `OLLAMA_THINK=0`, `AGENTIC_OS_MODEL_TIMEOUT_SECONDS=60`,
   `OLLAMA_NUM_THREAD` set to the number of performance cores, the Claude and OpenAI
   keys and model ids, and the task map above.
3. `python scripts/serve.py --local-only`, then open `/api/health` and check
   `model_map`: hermes `ollama:hermes3`, agents `ollama:qwen3`, consultants
   `anthropic` and `openai`.

The laptop must have memory for both models at once; `ollama ps` shows what is
loaded. Speed depends on the machine and was not measured in this repository.

## Capacity of the free tiers

With every role on, one analysis makes about 22 model calls: up to 17 agent notes,
a plan, two consultant reviews, a brief and the summary. With the recommended map
and the reported limits:

- OpenRouter carries 3 calls per run (plan, brief, one consultant). At 50 free
  requests a day that is about 16 runs a day; after the one-time credit purchase,
  about 330.
- Groq carries the summary and chat. At about 1,000 requests a day, chat volume,
  not analyses, sets its limit.
- Agent notes depend on Ollama Cloud's unpublished light limits; move `agents` to
  Groq if they run out.

For a demo or a capstone presentation this is ample. For production use, plan on a
paid tier for at least the busiest task.

## Data and terms

- Every model receives verified sentences (findings and figures already
  calculated), never dataset rows, and its numbers are checked against those
  facts.
- Free tiers may log prompts or use them to improve models. Read each provider's
  data terms before sending anything confidential, and keep client data on a paid
  tier with a no-training commitment.

## Sources

- OpenRouter, "Free LLM API in 2026: 13 Options Ranked and Compared": https://openrouter.ai/blog/tutorials/free-llm-apis-compared/
- "Free LLM API Tiers in October 2026": https://dev.to/tariqnasser/free-llm-api-tiers-in-october-2026-whats-left-and-how-i-chain-them-227l
- "Free LLM API Tiers (2026): Limits Verified Daily": https://gravity.fast/data/free-llm-api-tiers/
- OpenRouter free-tier limits: https://www.truefoundry.com/es/blog/openrouter-rate-limits-your-free-tier-depends-on-what-youve-already-paid
- Ollama Cloud documentation: https://docs.ollama.com/cloud.md
- NVIDIA developer forum on NIM free-tier limits: https://forums.developer.nvidia.com/t/request-for-nvidia-nim-api-rate-limit-increase-40-200-rpm/375340
