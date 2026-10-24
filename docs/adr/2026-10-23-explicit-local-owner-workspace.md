# Explicit local-owner workspace independent of Supabase

Date: 2026-10-23. Status: accepted for local development only.

## Context

The owner requested faster real local testing without Supabase or repeated
sign-in. ADR 0002 already provides a credential-free LocalIdentity; the project
forbids homemade password authentication. A fixed default password would add a
weak shared secret without making a publicly exposed owner safe.

## Decision

Reuse LocalIdentity, existing workspace-owner permissions and SQLite. The
explicit `scripts/local_workspace.py` launcher opts in to
`AGENTIC_OS_LOCAL_WORKSPACE=1`, keeps its data separate from existing stores and
binds only to loopback with proxy header handling disabled. Before storage is
opened, reject hosted identity/database/model configuration instead of stripping
credentials or disabling REQUIRE_AUTH. The guarded app refuses non-loopback
peers and Host values, foreign Origin, cross-site Fetch Metadata and forwarding
headers. Existing hosted paths and Supabase RLS are not altered.

No password verifier, login session, privileged account or credential is created.
The interface uses its existing honest local mode. Other local processes and
OS users remain trusted; this is not a secure multi-user or hosted profile.
Transparent local proxies cannot be distinguished from a trusted local client,
so tunnels, reverse proxies and network publication are unsupported.

Local-profile memory uses the existing DbMemoryBackend so the existing backup
format includes it. The CLI never overwrites a backup and restores only to a
new empty workspace. Old local-mode memory files are not silently imported or
changed. Existing database approval/audit/ownership contracts remain intact.

No model is installed, started or downloaded. The existing deterministic
calculation/report path remains honestly labelled; an LLM must be explicitly
configured as a local model. Cloud fallback is refused. This profile uses the
existing browser-driven run execution, not scheduled worker execution.

## Evidence and consequences

Synthetic tests exercise owner entry, actual dataset analysis, restart,
durable write throttling, memory/run backup and executable restoration. Attack
cases cover remote peers, DNS rebinding, Host/Origin, forwarded headers, public
bindings and hosted configuration refusal. Hosted authentication regression
and existing backup tests remain required. No real-user credentials or model
provider calls are needed to test this change. See [the local guide](../LOCAL_WORKSPACE.md).

## Windows console compatibility (24 October)

The bilingual launcher configures stdout and stderr as UTF-8 with replacement
handling, following the existing verifier convention. A redirected Windows
cp1252 stream otherwise rejects the Arabic startup banner before Uvicorn runs.
This changes output encoding only, not workspace validation, loopback binding,
proxy refusal, hosted authentication or durable storage/backup behavior.
The regression uses a real cp1252 TextIOWrapper and isolates the already-built
interface prerequisite. The platform workflow includes the launcher and its
regression path so changes receive native Windows Edge and macOS WebKit checks.
