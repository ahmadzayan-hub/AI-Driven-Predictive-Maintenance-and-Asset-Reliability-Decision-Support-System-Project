# Isolate the Langflow MCP example from real Miyaar workspaces

**Status:** Proposed example; no Langflow registration or live activation.
**Date:** 2026-11-05
**Extends:** ADR 0021 and the 24 October scoped Hermes package decision.

## Context

The owner requested GitHub-first integration of selected open-source tools.
Miyaar already has a restricted stdio MCP launcher. Replacing its runtime or
adding Langflow as an application dependency would duplicate existing behavior
and broaden the operational and data-sharing scope. The active isolated-worker
PR is separate work and is not changed by this example.

Langflow v1.13.1 accepts MCP command/args/env configuration. Import or discovery
can start the command, and its parser drops unknown fields such as `disabled`.
A file that appears disabled is therefore not a safe activation boundary.

## Decision

Add one explicit example launcher under `examples/langflow`, with a print-only
configuration mode and a separate synthetic-serving mode. Reuse the existing
MCP implementation and its restricted tool set. Seed only the engine's built-in
synthetic data into newly created temporary SQLite storage, advance it without
a model to the human approval gate, and never approve or publish it.

The launcher accepts no real workspace/configuration paths. Clear inherited
application and provider settings and refuse network/subprocess activity in
that child process. Keep stdout reserved for JSON configuration or MCP messages.
Do not edit auto-discovered MCP files, profiles, core behavior, dependencies or
deployment configuration. The generator does not register or activate anything.

## Evidence and limits

Tests exercise the actual stdio process, synthetic report, bilingual responses,
direct-call allowlist, temporary-storage cleanup and hostile ambient settings.
An optional official MCP client test verifies only that installed SDK's protocol
interoperability. Exact versions and results belong in README testing.

Pinned Langflow parser/client references and operator instructions are in
`examples/langflow/README.md`. Langflow is not installed here; UI import,
authentication, permissions and full component/flow execution remain unverified.
No new credentials, real workspace reads, model calls or production activation
are authorized by this example. The audit guard is not an OS security sandbox.

Reject this approach if it needs a live workspace, weakens stdio/interpreter
restrictions, exposes action tools, or cannot remain independent of production.
Further integration requires a separately approved local Langflow acceptance
test and explicit data/recipient scope.

## خلاصة القرار

مثال مستقل ببيانات مصطنعة مؤقتة، دون تثبيت Langflow أو تفعيل اتصال أو تغيير
التطبيق. تبقى الموافقة والنشر والأدوات التنفيذية خارج المثال. اختبار البروتوكول
لا يعني نجاح الاستيراد أو التنفيذ داخل Langflow؛ بيانات العمل الحقيقية وإرسال
النتائج إلى نموذج يحتاجان موافقة مستقلة.
