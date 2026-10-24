# Miyaar remains a web app and adds a scoped Hermes portable package

**Status:** Proposed; local preparation only, activation requires owner approval.
**Date:** 2026-10-24
**Extends:** ADR 0021 (existing MCP/tool executor).

## Context

The owner wants the website and installation in Nous Research Hermes Desktop.
Install from Git rejects the repository because it has no plugin artifact.
The current MCP is stdio; the separately owned web process on port 8017 is not
an MCP endpoint. Its checkout and data must remain untouched during Phase 1.

Inspection identified Desktop 0.17.6, Agent 0.21.3 and installed source/build
commit c1488ac947c9bc33fd65ec464548dc9d8edd6122. The matching portable parser
supports root manifests, skills and stdio MCP, but not the newer portable
trust extension in current upstream documentation. Native MCP filters and
untrusted trust settings exist. The live gateway is local; no inference
recipient is inferred from that fact.

## Decision

Add root `plugin.json`, `mcp.json` and a bilingual workflow skill. Reuse
`McpServer`, `ToolBox`, `Assistant` and the existing local run engine; add no
framework, SDK runtime dependency, renderer extension or web integration.

An additive MCP allowlist filters discovery and independently rejects direct
calls. The legacy default remains unchanged. The package's dedicated launcher
starts help-only without storage. Its optional configuration is an explicit
local scope document containing exact absolute data paths and allowed tools;
unknown fields/tools fail before storage opens. Temporary fallback storage is
disabled. No profile file, secret or workspace configuration is discovered.

Review amendment: configured capabilities are limited to `help`, `run_status`
and `explain_report`. Every other opt-in is rejected before storage opens.
The configured Agent still reads its memory file even without a recall tool;
SQLite startup can initialize/migrate schema and create WAL files. These need
explicit file-read/storage-write approval independent of the tool list.
Knowledge search remains excluded because its loader can follow symlinks
outside the configured root. Agent scorecards remain excluded because they
use package evaluation sources, not the configured workspace. Neither existing
facility is repaired or expanded here. Tests were initially held under RAM
pressure. A later bounded synthetic package/MCP dispatch run passed with
network-denial guards; evidence is recorded in README. Live activation remains
outside this verification.

The launcher clears inherited application/provider settings inside its own
child process and uses a provider-free gateway. It avoids `server.app`, which
initializes a default web app/store on import. The configured path uses the
same executor and local-owner semantics, with no hosted authentication claim.
Knowledge search is unavailable in this package. Custom stages/model roles/metric
glossaries are not silently imported; full pipeline parity needs later review.

## Consequences

The repository becomes recognizable as an Agent package without changing web
routes/assets or replacing Miyaar's platform. Installation alone grants no
Miyaar data access through the preview. Plugins are still local executable
code, not OS-sandboxed components. Native client filters supplement the server
allowlist; package metadata is not treated as a security guarantee.

Configured SQLite opening can migrate schema/create WAL files. An approved
synthetic workspace precedes any live sharing. Starting and advancing runs,
memory writes and report approval/publication stay outside this package.
Real data reads, startup storage effects and model forwarding need explicit
scoped approval.

## Verification boundary

Bounded synthetic tests cover transport, denied direct calls, configuration
failure, isolated storage and bilingual help. The installed portable parser
is exercised in scratch space. Counts and commands belong in README.md.
No live profile activation, web build, hosted identity test, model call,
production write, push, merge or deployment is part of this decision.

See [Hermes Desktop preparation](../HERMES_DESKTOP.md) for prerequisites,
current official sources, version differences and the approval matrix.
