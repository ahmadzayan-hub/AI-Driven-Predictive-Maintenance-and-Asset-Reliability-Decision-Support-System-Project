---
type: concept
aliases: [Approval-gated publishing]
tags: [governance, agents]
status: active
updated: 2026-10-23
review_every_days: 60
sources: [docs/OBSIDIAN_INTEGRATION.md, server/runs.py, docs/adr/2026-10-23-database-publication-target.md, docs/implementation/PLATFORM_RELEASE.md]
---

# Approval gate

A report is published only after a person approves it. The approval is bound to the exact report hash and reviewed destination. Rejected runs publish nothing. A changed destination requires a new pending review, with the previous request superseded without inventing a human decision. Web and Android clear their read confirmation. Refresh cannot publish or legitimize changed content; altered content requires a new governed analysis.

On approval, the run writes the report, with escaped provenance frontmatter, and its run log. Local `vault` mode keeps physical Obsidian notes as well as SQL copies. Serverless `database` mode writes SQL notes with the approval and run state in one transaction, without filesystem access; existing authorized routes retrieve them. Only confirmed state and a returned path establish publication. Physical local writes are not an atomic filesystem transaction. Runtime notes hold user data and stay separate from this [[Second brain]], which is curated project knowledge committed to the repository.

The gate is the product's version of a rule in [[Soul]]: people approve consequential actions.

## Related

- [[Governed pipeline]]: the gate is its final task.
- [[Hermes orchestrator]]: it holds the gate.
- [[Agent runtimes and MCP]]: no tool, framework or editor agent can approve on a person's behalf.
- [[Managed identity]]: establishes who may approve a run.
- [[Tenant isolation]]: keeps published notes within their run owner boundary.
