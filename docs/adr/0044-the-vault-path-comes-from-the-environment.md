# ADR 0044 — The vault path comes from the environment

**Status:** Accepted
**Date:** 2026-10-18

## Context

Approved reports are published as Markdown into a folder an owner opens in
Obsidian (`docs/OBSIDIAN_INTEGRATION.md`). The folder was chosen by
`config["vault_dir"]`, falling back to the repository's own `vault/`.

That is the wrong place to name it. An owner's real Obsidian vault is a machine
path — on this workspace, `C:\Users\<name>\OneDrive\Documents\Obsidian Vault` —
and `config.json` is tracked in a public repository. Writing the path there
would publish a user name and a directory layout, which the Soul's rules forbid
and which would be wrong on every other machine anyway. So the capability
existed and could not be used: reports could only ever land in `vault/`, and an
owner had to copy them out by hand or open a second vault.

The same expression was also written out three times, in `server/app.py`,
`server/worker.py` and `scripts/mcp_server.py`. The worker's docstring promises
"a worker wired to the same database and vault as the API", and nothing enforced
that; three copies of a default are three chances to drift.

## Decision

1. **`resolve_vault_dir(env, config, root)` in `server/runs.py` is the one
   place that answers the question**, and the API, the worker and the MCP
   server all call it. The promise that they publish to the same folder is now
   a function, not a comment.

2. **The order is `AGENTIC_OS_VAULT_DIR`, then `config["vault_dir"]`, then
   `<root>/vault`.** The environment wins because it is the layer that is not
   committed. Nothing changes for a deployment that sets neither, which
   includes every test and CI.

3. **`~` is expanded.** Owners write `~/Documents/Obsidian Vault`, and an
   unexpanded tilde would silently create a folder actually named `~`.

4. **A relative path resolves against the repository, not the working
   directory.** The worker and the MCP server are started from wherever an
   operator happens to be; resolving against the process's directory would
   scatter published reports across the filesystem depending on how each was
   launched.

5. **A blank or whitespace-only value is treated as unset**, not as the current
   directory. An empty environment variable is how a shell says nothing, and
   `Path("")` is `.`, which would publish into whatever directory the server
   started in.

## Consequences

An owner points the engine at their own vault without touching a tracked file:

```bash
AGENTIC_OS_VAULT_DIR="~/OneDrive/Documents/Obsidian Vault" python scripts/serve.py
```

The variable is documented in `.env.example` and in the Obsidian guide. The
engine already creates `Reports/` and `Runs/` under the vault with
`mkdir(parents=True)`, so the folder does not need to exist first.

This is a path an operator supplies, and it is trusted exactly as
`DATABASE_URL` is: whoever sets the server's environment can already choose
where it writes. It is not reachable from a request, a dataset or a model, and
nothing in a run can redirect it. Publishing is still approval-gated and still
bound to the artifact hash; this changes where an approved note lands, never
whether it is written.

What this does not do: it does not read a vault, watch one, or sync. Those
remain deliberately absent for the reasons `docs/OBSIDIAN_INTEGRATION.md`
gives, and a future reader must still treat note content as untrusted data.

Seven tests in `tests/test_runs.py` cover the order, the expansion, the
repository-relative resolution, the blank value and the engine actually
receiving the resolved path.
