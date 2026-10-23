---
type: concept
aliases: [Custom agents, Stage plugins]
tags: [architecture, extension]
status: active
updated: 2026-10-23
review_every_days: 60
sources: [server/stages.py, server/deadline.py, config.json, docs/adr/0020-custom-agents-as-plugins.md, docs/adr/0041-shipped-stages-and-an-honest-threshold.md, docs/adr/2026-10-23-p2-slice-one.md, examples/stages/target_attainment.py]
---

# Custom stages

A domain stage is a file: a class with a role, a title, a place in the [[Governed pipeline]] and a `run(ctx)` method, registered by dotted path.

- It runs on a copy of the context, before provenance, validation and reporting, so its claims face the same validator as a built-in stage.
- Its result shape is checked before anything is recorded, and its IDs must carry its role prefix.
- Profiles choose which custom stages a run includes, and `/api/pipelines` lists what loaded and why anything did not.
- A plugin is trusted Python, not a sandbox. Since 23 October 2026 it runs under a wall-clock limit (`AGENTIC_OS_STAGE_TIMEOUT`, default 120 s); an overrun fails its task and is abandoned on its thread, which keeps a hung stage from hanging the [[Run lifecycle|run]] but stops nothing it does meanwhile.
- **Written is not registered.** A stage can have its decision record, its tests and a working `run(ctx)` and still be unreachable, because nothing selects it: `config.json` has to name it. The maintenance governance and risk stages (ADRs 0039, 0040) were in that state until 18 October, when ADR 0041 registered both and added a `maintenance` profile. The shipped registry is now tested against the real `config.json`, not a fixture, so a profile naming an unregistered stage fails the suite.

This was the route for the modelling methods in the [[Analytics OS roadmap]], which shipped as four plugins on the `models` profile (ADR 0033): regression, classification, clustering and seasonal forecasting, each against a baseline.

## Related

- [[Hermes orchestrator]]: it places custom stages in the run.
- [[Agent runtimes and MCP]]: the other extension seams.
- [[Decision log]]: decision 0020.
