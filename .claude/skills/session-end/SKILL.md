---
name: session-end
description: Close a working session on Agentic OS. Append the session's entry to session-logs.md, update project-progress.md, keep durable lessons in Memory.md, update the brain notes the work touched (with wikilinks), check the brain, then commit and push to the working branch. Use before a session ends, when the user says "wrap up", "end session" or "log this", or when the Stop hook asks for it.
---

# Session end

The goal is that the next session, or a teammate, can pick up exactly here. Write facts, not impressions: every claim in these files must come from something that happened in this session.

## 1. Gather the facts

- The session id: the `abcd1234` shown in the session briefing.
- What changed: `git log --oneline <start>..HEAD`. The start commit is in `.claude/state/sessions/<session id>.json` (`start_head`); without it, use the commits you made in this conversation.
- What was verified: only tests and checks that actually ran in this session, with their real counts.
- What was decided, what is still open, and what is blocked.

## 2. Append to `session-logs.md`

Add one entry at the end, in this shape:

```markdown
## YYYY-MM-DD · `abcd1234` · <branch>

**Goal:** what the user asked for, in one line.

- **Done:** each result, with its commit (`7091b76`).
- **Verified:** for example "616 Python tests passed with PostgreSQL; CI run 43 green".
- **Decisions:** each one, with its reason, and the ADR if one was written.
- **Open / next:** what the next session should do first.
- **Blockers:** anything waiting on the user or on access.
```

The backticked session id in the heading is what the hooks look for. Without it, the Stop hook will ask again, and SessionEnd will add an automatic entry.

## 3. Update `project-progress.md`

- Move finished items to *Done*, with a date. Set milestone statuses, and change *Now* and *Next* to match reality.
- Update the *Last updated* line.
- Never mark something done that was not verified.

## 4. Update `Memory.md`

Keep only what a future session needs and cannot get quickly from the code: user preferences, environment quirks, conventions and standing decisions.

- Update an existing line rather than adding a near-duplicate.
- Delete lines that are no longer true.
- Keep the file under about 150 lines.

## 5. Update the brain

- Edit the notes this session's work touched, such as `brain/Projects/Agentic OS.md` for a new feature, or the matching concept note for a design change.
- Set their `updated:` date to today.
- A genuinely new concept, dataset or decision gets a new note from `brain/_templates/Note.md`, linked from [[Home]] and from at least one related note.
- Use `[[wikilinks]]` for every connection. Do not create a note that only restates another.
- If the user's goals or preferences changed, update `brain/User.md`.
- Run `python scripts/brain_check.py --strict`. It must report no broken links, missing fields or missing sources.

## 6. Commit, push, and merge to `main`

The owner gave standing permission on 18 October for every session to end on
`main`, because the team and the course instructors read the repository there.
This replaces the earlier "working branch only" rule. Nothing else in the Git
rules changes: no force-push, no history rewriting, no branch deletion.

1. Commit the tracking files, with a message such as
   `Session log: <date>, <one-line summary>`.
2. Push the working branch: `git push origin HEAD:refs/heads/<branch>`.
3. **Fetch first** — `main` moves between sessions, and more than once in a
   single day. `git fetch origin`, then ask what *content* it has that you
   lack, not what commits:

   ```bash
   git diff --name-status origin/main HEAD | grep '^D'   # files only on main
   git diff --stat origin/main HEAD                      # everything that differs
   ```

   Comparing commits (`git log origin/main --not HEAD`) always lists the
   previous merge commits, because a merge commit on `main` is not an
   ancestor of the branch it merged. That looks alarming and means nothing.
   The tree is the truth.
4. **If `main` has work you lack, integrate it before merging**, or the merge
   silently drops it. Take the files, renumber any colliding ADR, keep the
   course material out, and run the checks. ADR 0047 records how and why.
5. Merge, keeping both parents so nothing is rewritten:

   ```bash
   TREE=$(git rev-parse HEAD^{tree})
   M=$(git commit-tree "$TREE" -p origin/main -p HEAD -m "Merge: <summary>")
   git push origin "$M:refs/heads/main"
   ```

   `origin/main` is the first parent, so the push is a fast-forward and needs
   no force. A rejection means `main` moved again: fetch, integrate, rebuild
   the merge commit. Never force it through.
6. Confirm both refs and that the trees match:
   `git diff --quiet origin/main HEAD`.

- Never force-push, and never commit secrets, `.env` files, course files or
  personal data. The merge is additive; it is not a licence to rewrite.

## Rules

- Do not invent test counts, scores or results. Write "not run" when a check did not run.
- A session that changed nothing still gets a one-line entry if a decision was made; otherwise it needs no entry.
