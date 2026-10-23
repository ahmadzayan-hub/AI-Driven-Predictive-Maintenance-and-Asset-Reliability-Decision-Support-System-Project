# Hosted open-source models for the hosted site

Date: 2026-10-22 · Status: Accepted (owner request, 22 October: "Ollama
unreachable from Vercel. Solve this by using online or cloud based open
source LLMs like Ollama")

## Context

The agents' model role was designed for Ollama on the operator's machine. A
serverless deployment cannot reach a laptop, so on the hosted site the agent
role had no open-source model. The gateway also assumed any Ollama host was
local: it reported `local_only`, refused failover, skipped the proxy and sent
no credential, all wrong for a hosted endpoint.

## Decision

1. **Hosted Ollama endpoints are supported.** `OLLAMA_HOST` may point at a
   hosted service that speaks Ollama's chat API; `OLLAMA_API_KEY`, when set,
   is sent as a bearer token. Whether a given service accepts it, and which
   models it hosts, is for the owner to confirm with that service.
2. **Only a loopback host counts as local.** `localhost`, `127.*` and `::1`
   keep every guarantee a local model had: first in priority, reported as
   `local_only`, never failing over to a hosted provider, kept off any proxy.
   Any other host is hosted: it ranks after Claude and OpenAI, may fail over,
   uses the proxy like other providers, and is reported as leaving the machine.
3. **Groq remains the no-change option.** It already serves open-source
   models through `GROQ_API_KEY` and `GROQ_MODEL`; `AGENTIC_OS_AGENT_MODEL=groq`
   puts the agent notes on one.

## Consequences

- The agent role can run on an open-source model on the hosted site, through
  a hosted Ollama endpoint or Groq.
- A hosted model receives the same verified sentences as any provider, never
  dataset rows, and its notes are grounded the same way.
- Nothing changes for a local Ollama.

## Verification

`tests/test_model_gateway.py` (`HostedOllamaTestCase`): a hosted endpoint
sends the bearer key and uses the proxy; it is not local and ranks after
Claude; it may fail over while a local one may not; the status never shows
the key. No live call: no hosted endpoint is reachable from the development
container.
