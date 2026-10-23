---
type: concept
aliases: [Approval-gated publishing]
tags: [governance, agents]
status: active
updated: 2026-10-23
review_every_days: 60
sources: [docs/OBSIDIAN_INTEGRATION.md, server/runs.py, docs/adr/2026-10-22-release-gate-slice-two.md, docs/adr/2026-10-22-release-gate-slice-three.md]
---

# Approval gate

A report is published only after a person approves it. The approval is bound to the exact hash of the report it was given for, so a report changed afterwards needs approving again. Rejected runs publish nothing.

On approval, the run writes two notes into the runtime `vault/` folder: the report, with provenance frontmatter, and its run log. That vault holds user data and is git-ignored. It is separate from this [[Second brain]], which is curated project knowledge committed to the repository.

The gate is the product's version of a rule in [[Soul]]: people approve consequential actions. Since 22 October 2026 the approver must open the exact report and say they read it before approving, and the gate completes the run's decision record with who decided, what and when; no stage writes that part.

## Related

- [[Governed pipeline]]: the gate is its final task.
- [[Hermes orchestrator]]: it holds the gate.
- [[Agent runtimes and MCP]]: no tool, framework or editor agent can approve on a person's behalf.
- [[Managed identity]]: establishes who may approve a run.
- [[Tenant isolation]]: keeps published notes within their run owner boundary.
