---
type: concept
aliases: []
tags: [interface]
status: active
updated: 2026-10-20
review_every_days: 30
sources: [docs/adr/0059-executive-business-document-exports.md, docs/adr/0058-executive-dashboard-agent-and-scoped-evidence.md]
---

# Business report exports

Business report exports turn an authorized executive evidence snapshot into readable documents without changing approval state.

## File guarantees and limits

- The supported business outputs include standalone HTML and a genuine editable Word document; Print / Save as PDF uses the browser dialog.
- The export is bound to the prepared timestamp and content revision. A changed snapshot requires refresh.
- Filters, populations, limitations and whole-run model scope survive the format change.
- Exporting is neither publication approval nor permission to reveal source rows.
- Arabic direction and pagination need document-level review in addition to structural tests.

## Related

- [[Scoped dashboards]] supplies the prepared context.
- [[Evidence and claims]] supplies traceable references.
- [[Approval gate]] retains publication authority.
- [[House style]] guides the document presentation.
- [[Home]] links reporting to the product.
