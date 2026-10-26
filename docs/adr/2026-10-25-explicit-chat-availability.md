# Explicit chat availability and bounded failure replies

The workspace context panel distinguishes a connected server from usable model
inference. Session snapshots include bilingual configuration/resource status.
Reading status never loads a model or proves a successful model response. Existing
local Ollama admission requires available physical RAM of at least 3 GiB; unknown
memory fails closed. This port excludes model-specific budget experiments, new
providers, installation, model activation and runtime configuration.

Provider failure, unusable structured output and missing configuration produce
explicit rules-origin replies without exposing exceptions or credentials. Failed
model responses cannot turn contextual or negated words into guessed report or
memory actions. Existing explicit commands, ownership and confirmation remain.
There is no automatic retry. Selected-data calculations precede model routing and
remain available without a language model.

Validation uses synthetic temporary stores and mocked gateways for resource
refusal/recovery, malformed output, exception redaction, persistence and command
boundaries. These tests make no claim of real inference, language quality or
predictive accuracy. Exact integration results and remaining gates are in README.
