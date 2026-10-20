---
type: concept
aliases: []
tags: [security]
status: active
updated: 2026-10-20
review_every_days: 30
sources: [server/auth.py, server/storage.py, docs/adr/2026-10-20-published-note-tenant-isolation.md]
---

# Tenant isolation

Tenant isolation keeps each ordinary caller within the resources owned by their authenticated subject.

## Resource boundary

- Ownership checks apply to reads as well as mutations. Another owner's resource is not made discoverable by a different error response.
- Published notes inherit ownership from their run; approval to publish does not make a report visible to every customer.
- A file on disk cannot bypass the authorized database record for a published note.
- Explicit platform-administrator capabilities are distinct from ordinary ownership.
- The current owner model does not by itself implement an accepted commercial organization hierarchy.

## Related

- [[Managed identity]] supplies the authenticated principal.
- [[Scoped dashboards]] binds displayed evidence to its run and context.
- [[Business report exports]] retains ownership during downloads.
- [[Soul]] keeps private data out of tracked notes.
- [[Home]] connects the security cluster.
