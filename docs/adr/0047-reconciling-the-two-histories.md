# ADR 0047 — Reconciling the two histories in one repository

**Status:** Accepted
**Date:** 2026-10-18

## Context

ADR 0043 moved the project's home to the repository named after the product.
That repository had been created from a squashed snapshot whose single commit,
`27f9928`, shares no ancestor with the project's history. ADR 0043 pushed the
real 112-commit history onto `claude/agentic-os-final-project-53j6ql` there and
left the orphan `main` alone, as removing it would have been a rewrite.

`main` did not stay still. Between 17 and 18 October, four pull requests were
merged into it, all branching from the snapshot rather than from the project:

| PR | What it added |
| --- | --- |
| #1 | Railway Asset Manager: domain screening, role mapping and tests |
| #2 | Team 3 role contribution folders and upload guidance |
| #3 | Team 3 CODEOWNERS review mapping |
| #4 | Bonus SaaS: opt-in governed maintenance AI and railway asset screening |

So one repository held two unrelated lines. Neither could fast-forward into the
other. Against the project's branch, `main` had 43 files the project lacked, 34
it modified, and 5 it was missing.

Two further collisions. `main` had added `docs/adr/0041-rail-asset-manager-screening.md`
and `0042-opt-in-maintenance-profile.md` while the project's line had already
used 0041 and 0042 for the shipped registry and the missing-value policy: the
same numbers for different decisions. And `main`'s `config.json` had, quite
independently, registered the two maintenance stages and added a `maintenance`
profile — the same change ADR 0041 made here, arrived at separately.

### What else those pull requests carried

A commit titled "Add files via upload" copied the contents of the git-ignored
`private/` folder into the repository root and published it. On a **public**
repository this placed the 5,000-row course dataset, a readiness file holding
all five registration numbers, teammates' names in several files, the private
project assessment with its probe scripts and output, the capstone workbook and
a presentation. Of the 14,930 lines those four pull requests added, roughly
14,470 are that material.

This contradicts the rule in `CLAUDE.md`, `AGENTS.md` and `brain/Soul.md`: the
repository is public, and course files, registration numbers and other people's
personal data never go in it.

## Decision

1. **Take the engine work; refuse the rest.** Six files carry genuinely new,
   well-made code and are brought onto the project's history as ordinary
   commits: `server/rail_asset_decisions.py`, `server/maintenance/rail_stage.py`,
   their two test modules, `docs/roles/rail-asset-manager.md` (checked and free
   of personal data) and the two decision records. Nothing else is taken.

2. **The colliding records are renumbered, not rewritten.** 0041 becomes
   **0045** and 0042 becomes **0046**, each carrying a line saying where it came
   from. The decisions themselves are unchanged. Renumbering the newer pair is
   the one choice that leaves both sets of reasoning intact; editing either
   decision to fit would break the rule that an ADR is never edited to suit
   later facts.

3. **`config.json` keeps the convergent change and adds the rail stage.** Both
   lines had registered the maintenance stages; the merged file registers seven
   stages and a `maintenance` profile of three. `tests/test_stages.py` pins that
   membership on purpose, so a stage joining the profile fails the suite until a
   record says it should — which is how this addition was noticed.

4. **The course material is refused by name, permanently.** `.gitignore` now
   blocks `Group_9226_*`, `Team3_*`, `/roles/`, the private assessment and its
   probe output, and the capstone tools, each anchored so `docs/roles/` is
   unaffected. Verified by copying the real dataset to the repository root and
   confirming Git does not see it.

5. **`main` is left exactly as it is.** It is not deleted, rewritten or merged.
   It is no longer a working line, and the project continues on
   `claude/agentic-os-final-project-53j6ql`.

## Consequences

The ignore rule stops a repeat; **it does not undo the disclosure.** The files
are in a public repository's history and remain fetchable by commit even after a
later commit deletes them. Only the owner can contain that, and only by making
the repository private, or by rewriting its history, or by deleting and
recreating it. No session here will force-push or rewrite history, so this
record states the exposure rather than quietly closing it. No credential was
among the published files; a scan found none. The dataset and the five
registration numbers should be treated as disclosed, and the teammates told.

Taking the code without the history means the four pull requests are not
ancestors of anything here. Their authorship survives in `main`, which is why
`main` is kept rather than deleted.

The rail screening stage is registered but, like the other two maintenance
stages, reachable only through the opt-in `maintenance` profile. The `default`
profile stays empty, so an ordinary run behaves exactly as before.

Verified: the two ported test modules and the shipped-registry suite run 40
tests with 0 assertion failures; the 12 errors are the known Windows
temporary-file cleanup race, with no other exception type in the output.
