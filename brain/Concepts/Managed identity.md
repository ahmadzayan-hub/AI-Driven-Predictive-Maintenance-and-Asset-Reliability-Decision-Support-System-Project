---
type: concept
aliases: []
tags: [security]
status: active
updated: 2026-10-20
review_every_days: 30
sources: [server/auth.py, docs/adr/0002-authentication.md, docs/adr/0053-dedicated-supabase-schema-and-auth-bootstrap.md]
---

# Managed identity

Managed identity verifies the caller through a configured provider and enforces permissions on the server.

## Enforcement

- Hosted requests use verified JWT identity; local mode deliberately represents a single local owner.
- Required production authentication must fail closed when its configuration is absent.
- Server permissions govern reads, writes, approval and administration. Hiding a button is not authorization.
- A working local login or a test token is not evidence of a completed hosted provider round trip.

## Related

- [[Tenant isolation]] determines which resources a caller may access.
- [[Approval gate]] adds artifact-specific human authority.
- [[Release acceptance]] includes hosted identity verification.
- [[Soul]] prohibits homemade password substitutes.
- [[Home]] indexes the security concepts.
