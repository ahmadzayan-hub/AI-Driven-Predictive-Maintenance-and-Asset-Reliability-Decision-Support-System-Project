# 0055 — Opt-in local model and Whisper runtime

Date: 2026-10-19

## Context

The owner requested installation and activation of the tools needed for working
chat and voice. Browser recognition may depend on a remote browser service;
installing Whisper without an application transport would not improve it.
The inspected Windows laptop has roughly sixteen gigabytes of memory and an
Intel integrated GPU, so CUDA dependencies and large inference stacks are not
appropriate defaults.

## Decision

- Keep the standard-library analytics core and the existing governed tool,
  authentication, ownership, dataset and approval contracts.
- Add an explicitly enabled local speech adapter. `requirements-voice.txt`
  pins faster-whisper; its CTranslate2 CPU/int8 runtime and bundled PyAV avoid
  requiring Torch, CUDA, or a system FFmpeg installation. All weights and
  tokenizers must exist locally before serving requests. Requests cannot
  download a model. Optional SDKs for the existing examples remain optional.
- Download the multilingual small weights explicitly from Systran at a pinned
  revision. Keep model binaries, vendor checkouts, recordings and validation
  logs out of Git. Use the account's cache for weights.
- Expose authenticated capability discovery and session-owned transcription.
  Read raw supported audio bodies with a byte ceiling, bound decoded duration,
  reject silence and unsupported containers, serialize CPU inference, and
  return safe English/Arabic errors. The client records slightly below the
  server duration ceiling to allow container and timer overhead. Audio and
  transcripts are not persisted by transcription.
- Preserve browser recognition when the optional adapter is unavailable.
  Local recording needs explicit consent and a user gesture. Text becomes an
  editable draft; neither a transcription nor playback submits a chat action.
  Cancelling discards the client result, but already running CPU inference
  holds its concurrency slot until it completes.
- `scripts/local_runtime.py` installs, checks and starts an explicitly local
  profile, with loopback bindings, a persistent optional connector worker,
  Whisper and an Ollama model. The first existing Qwen3 installation returned
  reasoning or empty text in real probes; the local profile instead selects
  the instruction-only Qwen3 4B Instruct 2507 with bounded local context after
  bilingual acceptance. Gemma 3 failed conversation-history routing, and the
  small Qwen2.5 candidate failed Arabic quality checks. Other installed local
  models can be selected explicitly with `--model`; cloud tags are refused.
  Prewarm the selected model before accepting requests and limit the local
  profile to a 4096-token context, six CPU threads and a one-minute inference
  timeout; the browser allows response overhead. Installation alone is not
  acceptance: actual provider and audio probes must be reported.
- Stop only the launcher's owned worker on shutdown. On Windows a venv
  redirector can have the actual Python worker below it, so stop the exact
  live child PID tree with a bounded operation instead of terminating only
  the redirector. Never match unrelated processes by name.
- Add opt-in bounded model timeouts and the provider's thinking control.
  Ollama requests bypass ambient proxies so local context is not sent to an
  HTTP proxy. Hosted providers retain their existing behavior. Browser access
  to the microphone is permitted only for the application's own origin.
- Make conceptual maintenance questions and follow-ups explicit chat cases in
  a compact intent prompt. Native JSON syntax alone proved insufficient: a
  real instruction-model response placed its answer inside arguments, so
  schema-constrained fields are required. Remove the duplicate current user turn from that
  context while preserving prior conversation. Label recent conversation and
  saved memory separately, including the empty saved-memory case. Expose
  explicit model-facing saved-memory tool names and normalize them back to
  existing internal actions; user commands, stored data and action responses
  retain their original names. Few-shot wording alone did not establish
  reliable routing in actual probes. Use an Ollama native JSON
  schema for intents only, requiring top-level action/arguments/reply and a
  nonempty chat reply; free-form report narration and hosted request contracts
  stay unchanged. Legacy gateways can continue exposing ordinary `ask`.
  Explicitly non-thinking local intents use a smaller bounded output budget.
  Reject a missing or blank model chat reply and retain the
  fallback reason, so a stock fallback cannot masquerade as a model answer.
  Non-chat action confirmations stay deterministic and governed.
- Lazy-load the additional voice implementation, translations and discovery.
  Keep the initial script, stylesheet, chunk and font budgets unchanged. Allow
  total cross-view JavaScript to reach 170 KB gzipped (previously 165 KB) for
  the actual recorder, lifecycle protection and transport. No new browser
  runtime dependency, stylesheet or font is introduced. This explicit feature
  allowance is not a claim that the code has zero download cost.

## Consequences

Local chat and voice can be tested without metered cloud credentials. Their
accuracy and latency depend on the model, language, audio and hardware. A
browser microphone/device acceptance check remains separate from generated
and public-audio probes. Managed hosted identity/database credentials and
production acceptance are still required for a multi-user SaaS deployment.
See [local setup](../LOCAL_AI_SETUP.md) and [README testing](../../README.md#testing)
for commands, produced evidence and limitations. No installation proves
prediction validity, billing, or every future product feature.
