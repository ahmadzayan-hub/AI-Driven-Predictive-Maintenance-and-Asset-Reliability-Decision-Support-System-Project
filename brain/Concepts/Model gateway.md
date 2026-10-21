---
type: concept
aliases: [Narrator, Provider-neutral gateway]
tags: [architecture, ai, agents]
status: active
updated: 2026-10-21
review_every_days: 60
sources: [server/model_gateway.py, server/routing.py, docs/adr/0017-choosing-the-narrator.md, docs/adr/2026-10-21-run-request-timeout.md, docs/adr/2026-10-21-workspace-model-activation.md, .env.example]
---

# Model gateway

Language models in [[Agentic OS]] phrase facts that have already been verified. They never see a dataset row and never produce a number.

- **Default:** deterministic templates, so tests and CI need no credentials.
- **Optional narrators, all configured server-side:** a local Ollama model, which is preferred when set because nothing leaves the machine; Claude; Groq; or an explicitly selected Vercel AI Gateway model with a server credential. Deployment OIDC is read on each request; no model is selected just because a Vercel token exists.
- **Routing:** an optional router picks the narrator for each report, and the report prints why. A choice the deployment cannot reach is refused and reported, never silently swapped.
- **Keys** stay on the server, never in a client bundle, log or screenshot.
- **Activation is deployment-specific:** the local model does not configure the hosted app. A healthy API alone does not prove a model answered; acceptance records the reply source, bilingual quality and latency in README.
- **Local run timing:** the browser allows ninety seconds for run detail, advance and controls, covering the gateway's sixty-second inference window and response overhead. An uncertain POST is not automatically replayed; [[Governed pipeline|run]] state is reconciled by reading it.

This is where two rules in [[Soul]] are enforced in code: raw data never goes to a model, and secrets stay out.

## Related

- [[Agent runtimes and MCP]]: the chat's optional agent loop uses this gateway as its model.
- [[Decision log]]: decisions 0017 and 0019.
- [[Model privacy]]: checks the facts and labels before provider submission.
- [[Knowledge retrieval]]: supplies cited reference context through a separate collection contract.
