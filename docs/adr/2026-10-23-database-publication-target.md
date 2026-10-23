# Durable publication without a writable serverless vault

Date: 2026-10-23 · Status: Accepted (owner: complete the next development phases).

## Context

The approval gate already stores published notes in SQL, but first creates and
reads physical files. A read-only serverless filesystem therefore prevents
publication before the durable transaction can finish (assessment B13).
An unescaped source name can also add YAML frontmatter keys (B19).

## Decision

Select `database` or `vault` with `AGENTIC_OS_PUBLISH_TARGET`, then
`config.publish_target`. Vercel defaults to `database`; other hosts keep `vault`.
API and worker resolve the same setting. Invalid settings fail startup.

Database publication builds the two Markdown notes in memory and writes them
inside the existing approval/artifact/state transaction. It performs no directory
creation, file writes or readback. The confirmed path is vault-relative, for
example `Reports/<report>-<run>.md`. Existing owned `/api/vault` routes retrieve
the notes. No public/static file or new storage service is introduced.

Local vault mode retains the existing Obsidian files as well as durable SQL
notes. Its physical writes are not an atomic filesystem transaction; failed
local mirroring remains an operator recovery case. Only confirmed server state
indicates success. The approval names its actual destination and storage impact;
a changed destination invalidates an approval. Reject and create a new reviewed
analysis, or restore the reviewed configuration, to recover.

Dataset names use JSON-escaped YAML scalar values. Source spelling, quotes,
Unicode and newlines survive without introducing extra frontmatter fields.

## Verification and boundaries

Synthetic tests refuse every filesystem write, inject a second-note failure,
check owner isolation and rollback, reject changed destinations and reproduce
source-name scalars in both report languages. PostgreSQL and HTTP integration
run in hosted CI. Production deployment is not performed. Remaining B13
request/model-duration work and legacy local path presentation are still open.
