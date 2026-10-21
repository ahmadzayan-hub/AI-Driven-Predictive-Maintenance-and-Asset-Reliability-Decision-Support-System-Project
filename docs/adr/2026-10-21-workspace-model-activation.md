# Explicit hosted model activation and bounded workspace decisions

Date: 2026-10-21

Status: accepted

## Context

The owner asked to activate and test the workspace agents and language models,
including open conversation and the analysis, asset and approval journeys.
The existing production Vercel health endpoint reports a deterministic provider
and no agent runtime. The local profile has an Ollama model and worker, but no
configured conversation runtime. These are separate deployments.

## Decision

Add an optional Vercel AI Gateway adapter to the existing model boundary.
Require both an explicit AI_GATEWAY_MODEL and a server-side AI Gateway key or
deployment OIDC token. Preserve the priority of configured Ollama, Anthropic and
Groq providers. Re-read the credential mapping per request for token rotation.
Keep secrets out of health, replies and logs. The exact configured model wins
over broad router aliases. No new package is required.

Use the existing LangGraph adapter locally when enabled by the operator. Pass
the gateway's structured-output function to its bounded tool loop; keep plain
ask compatibility for older gateways. General questions can close with a reply
without unnecessary tool calls. Existing ToolBox validation, privacy checks,
tool limits and independent human approvals remain authoritative. Pydantic AI
remains an alternative adapter, not a second concurrent planner for a message.
An unavailable gateway response is a runtime failure, not a declined task;
report it without making a second slow request to the same model.

Only a small explicit set of read-only help/status shortcuts may bypass model
interpretation. Broad matches such as "explain" must still reach the model:
they can refer to a general question rather than an existing report.

AI_GATEWAY_MODEL is selected in Preview for acceptance using the live catalog.
Production promotion remains a separate explicit owner approval under AGENTS.md.
Do not change authentication, expose local Ollama, buy credits, or enable all
installed models merely because they exist. A smaller model that fails bilingual
quality checks must not become the workspace default.

## Verification

Use synthetic inputs for live model probes and disposable workspaces for
workflow tests. Record measured latency and actual reply source, distinguish
configuration from a successful reply, and retain failures in the acceptance
record. The optional model_probe script makes no network request without
--live, sends no workspace data, and reveals no credential. Actual test counts
and measured results belong in README.

Sources: [Vercel OIDC](https://vercel.com/docs/ai-gateway/authentication-and-byok/oidc),
[Chat Completions](https://vercel.com/docs/ai-gateway/sdks-and-apis/openai-chat-completions),
the live model catalog, and existing ADRs 0007, 0019, 0021 and 0055.
