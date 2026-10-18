# 0055 — Opt-in local model and Whisper runtime

Date: 2026-10-19

## Context

The owner requested installation and activation of the tools needed for working
chat and voice. Browser recognition alone depends on a remote browser service;
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
  Gemma 3 with bounded local context after bilingual acceptance. The small
  Qwen2.5 candidate also failed Arabic quality checks. Other installed local
  models can be selected explicitly with `--model`; cloud tags are refused.
  Installation alone is
  not acceptance: actual provider and audio probes must be reported.
- Add opt-in bounded model timeouts and the provider's thinking control.
  Ollama requests bypass ambient proxies so local context is not sent to an
  HTTP proxy. Hosted providers retain their existing behavior. Browser access
  to the microphone is permitted only for the application's own origin.
- Make conceptual maintenance questions and follow-ups explicit chat cases in
  the intent prompt. Reject a missing or blank model chat reply and retain the
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
