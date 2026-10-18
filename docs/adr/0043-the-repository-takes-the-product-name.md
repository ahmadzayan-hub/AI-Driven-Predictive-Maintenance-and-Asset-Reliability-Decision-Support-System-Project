# ADR 0043 — The repository takes the product's name

**Status:** Accepted
**Date:** 2026-10-18

## Context

ADR 0036 gave the product its title and drew a deliberate line around it: point 4
kept "existing package, storage, API, export and repository identifiers", and said
in as many words that the change "does not rename the remote repository, local
folder or deployment". The reasoning was sound at the time — replacing every
occurrence would confuse the product with the engine, and could break installations
that address the old identifiers.

Two things have changed since.

First, the owner renamed the GitHub repository anyway. On 17 October a squashed
snapshot of the Desktop working copy was pushed into a new repository, and that
repository was then renamed to
`AI-Driven-Predictive-Maintenance-and-Asset-Reliability-Decision-Support-System-Project`.
The API confirms the rename rather than a copy: the previous name returns
`Moved Permanently`, and the repository is not a fork.

Second, the audience changed. The capstone's readers — teammates, instructors and
examiners — look for the product's title, not for the engine's. A repository named
after the engine is a small obstacle in front of every one of them.

The cost of the move is low and known. GitHub keeps redirecting the old name, so
existing clones, the CI run links already cited as evidence, and the two merged
pull requests all keep resolving.

## Decision

1. **The repository named after the product is the project's home.** The working
   branch `claude/agentic-os-final-project-53j6ql` is pushed there, carrying the
   whole history. `origin` in a working copy points at it.

2. **ADR 0036 point 4 is reversed for the repository identifier only.** Package,
   storage, API, export and deployment identifiers are unchanged, and so is the
   local folder name. This record reverses one clause of an earlier decision; it
   does not edit ADR 0036, which stays as it was written.

3. **`ahmadzayan-hub/agentic-os-final-project` is not deleted and not rewritten.**
   It receives this one commit, so that anyone who opens it lands on a tree whose
   records name the new home, and it stops being a push target after that. Its
   history, its two pull requests and the CI runs cited in
   `docs/design/VALIDATION.md` remain valid evidence at their existing URLs.

4. **Historical links are left alone.** A CI run, a commit link or a session-log
   entry records where something happened. Rewriting those URLs to the new name
   would make the record claim a history the new repository does not have. Only
   forward-looking pointers move: how to clone, where to open a pull request,
   which repository to import into Vercel, and the repository fact in `Memory.md`
   and the brain.

5. **The orphan `main` in the new repository is left as it is.** It holds the
   single squashed `first commit` with no ancestor in common with the project.
   Removing it or forcing the real history over it would be a rewrite, so it
   stays until the owner decides, and the default branch moves to the working
   branch instead.

## Consequences

Two owner actions on GitHub, which no session here can perform — this environment
has no authenticated GitHub CLI:

- Set the new repository's default branch to
  `claude/agentic-os-final-project-53j6ql`. Until then its landing page shows the
  orphan snapshot rather than the project.
- Re-point the Vercel project's Git integration. **The deployment keeps building
  from the old repository until this is done**, so a push to the new home will
  not reach `agentic-os-final-project.vercel.app`. ADR 0036's decision to leave
  the deployment URL unchanged still stands; only the source repository moves.

CI will begin running in the new repository on the first push, against a workflow
that has never run there. Its first result is unverified at the time of writing.

What this does not do: it does not rename the local folder, the Vercel project,
the storage keys or the export filenames, and it does not certify anything about
the product the name describes.
