# Obsidian Second-Brain Integration

Agentic OS publishes approved analytics knowledge into an
Obsidian-compatible vault folder. Obsidian is a knowledge destination the
user controls — never the production database or a source of system
instructions.

## What is implemented

- The vault is a plain markdown folder: open it directly in Obsidian
  (`Open folder as vault`). It is the repository's `vault/` unless you
  point the engine somewhere else, which is how you publish straight
  into a vault you already keep (ADR 0044):

  ```bash
  AGENTIC_OS_VAULT_DIR="~/Documents/Obsidian Vault" python scripts/serve.py
  ```

  `AGENTIC_OS_VAULT_DIR` wins over `vault_dir` in `config.json`, which
  wins over `vault/`. Prefer the variable: `config.json` is tracked in a
  public repository and a vault path usually holds your user name. `~` is
  expanded, a relative path resolves against the repository, and the
  folder is created if it does not exist. The server, the worker and the
  MCP server all read the same setting, so they publish to one place.
- Approving a run's publish step writes exactly two notes:
  - `vault/Reports/<goal-slug>-<run-id>.md` — the full report with YAML
    provenance frontmatter (`type`, `run`, `generated`, `status:
    approved`, `dataset`, `lang`) and a `[[run-id]]` wikilink to its log.
    An Arabic report (`lang: ar`) reads right-to-left in Obsidian when
    its right-to-left setting is on.
  - `vault/Runs/<run-id>.md` — the run log: goal plus every specialist
    stage and its outcome, backlinking the report.
- Write-back is **approval-gated on the server** and bound to the exact
  artifact hash; rejected runs write nothing (covered by tests).
- Notes are never overwritten: filenames embed the unique run id.
- The vault is excluded from git — published knowledge is user data.

## What is deliberately NOT implemented

- A packaged Obsidian plugin (`apps/obsidian-bridge`), vault *reading*/
  retrieval, sync, conflict handling, embeddings, and graph retrieval.
  Building those honestly requires the Obsidian plugin runtime and a
  retrieval stack; shipping stubs would violate the no-fake-features rule.
- Perpetual autonomous self-improvement. The honest loop implemented is:
  every run's validation results and stage outcomes are captured in the
  run log note, so lessons accumulate in the vault for *human* review.

## Extension path

The publish step (`RunEngine._publish`) is the single integration point.
A future plugin can watch `vault/Reports/` via the official Vault API;
retrieval should treat note content as untrusted data and never as
instructions (see `docs/SECURITY_THREAT_MODEL.md`).
