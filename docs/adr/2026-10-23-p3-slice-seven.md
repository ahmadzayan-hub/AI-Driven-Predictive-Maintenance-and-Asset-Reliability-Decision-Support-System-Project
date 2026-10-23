# P3 slice seven: the minor findings, closed where the code could close them

Date: 2026-10-23 · Status: Accepted (assessment findings A16, A17, A19, B17,
B18, B19, B20, G12, G13, G14, G15 and U17 in
`docs/audits/SAAS_PLATFORM_ASSESSMENT.md`; the P3 list of section 3 of
`docs/implementation/DELIVERY_ROADMAP.md`. U8 and U20 stay with the owner.)

## Decisions

1. **Shares are signed and associations carry n (A16).** A group that
   moved further than the total is said to have done so ("more than the
   whole, because other groups moved the other way"); one that moved
   against it is said to have done so; the association claim states the
   signed correlation and the rows it was computed over.
2. **The anomaly rule is robust and its minimum is stated (A17).** Each
   period is judged against the trend fitted on the other periods, one at
   a time (the furthest first, then left out of the next trend), against a
   robust spread (1.4826 × the median absolute gap, floored at 5% of the
   series' scale) with a threshold of 3. An obvious spike stands out at
   four periods, which the limitation claim names as the minimum; a
   straight or ordinarily noisy series flags nothing. The rule is its own
   calculation (`c_anom_rule`).
3. **Structure has a floor, and a season two trials (A19).** Clustering
   must beat the silhouette k-means reaches on uniform noise with the same
   size and ranges by 0.05 (`c_noise`, `separation_in_noise`); the seasonal
   model holds out two seasons when four exist and says how many it held.
4. **One CSP source, PATCH preflighted (B17).** The shell policy is built
   once in `application_content_policy` and `vercel.json` is held to it by
   test; CORS already allowed PATCH and a preflight test now proves it.
5. **Liveness for everyone, detail for a reader (B18).** `/api/health`
   answers status, name and version to anyone; the model names, the role
   map, the problems, the execution state and the call ledger only to a
   signed-in reader. Local mode signs everyone in, so nothing changes
   there; on a hosted deployment an anonymous probe learns nothing it can
   fingerprint.
6. **Published paths are relative and the frontmatter is escaped (B19).**
   `published_path` reads `Reports/<note>.md` (or `store:…`), never the
   server's folder; the publish summary says the same; the dataset name in
   the report's YAML frontmatter is JSON-quoted, so a quote or a newline in
   a file name cannot add a field.
7. **One handler, no unused extras (B20).** A `ConnectorError` is answered
   by one application-level handler in the error envelope; the two copied
   mappings are gone (the speech mapping keeps its `Retry-After` and stays
   where it is). `uvicorn[standard]` became `uvicorn`: uvloop, httptools,
   websockets and watchfiles were never imported; the lock was recompiled
   with the recorded command, and the `httpx` note now says the gateway
   uses it at runtime.
8. **Orchestration failures are recorded (G12).** A model that raises
   leaves `orchestration_problem` on the task result (and on the
   reporter's, for the consultants) and in `engine.orchestration_problems`,
   which the health detail lists; a run still never fails for it.
9. **Grounding reads words and refuses causes (G13).** `grounded()` reads
   quantity words ("doubled", "a dozen", "one in five", "نصف") as the
   figures they state and refuses a note whose quantities are not in the
   facts; it also runs the claims lint's causal check on the note. "one",
   "third" and "quarter" are not read as figures, because as a pronoun, an
   ordinal and a period they are prose. Two built-in sentences were
   reworded so the built-in writer passes its own checks in both
   languages, which a test now holds.
10. **Acceptance names a known reviewer (G14).** A plan may list
    `reviewers`; otherwise the repository's committers are the known
    reviewers; `validate_plan` refuses any other name.
11. **Tool arguments are held to the schema (G15).** The catalogue's
    `inputSchema` now names `run_id` where the executor accepts it; after
    dropping unknown arguments and reading scalars as text, as before, the
    tool box validates what remains against the schema, so a value outside
    an enum or a missing required argument is refused rather than passed.
12. **The voice toggle keeps one name (U17).** `aria-label` is "Voice
    dictation" in both languages with the state in `aria-pressed` and the
    action in `title`; the shortcut hint reads ⌘ K on Apple hardware and
    Ctrl K elsewhere; keyboard focus on a field draws a 2 px ring.

## Consequences

- `tests/test_p2_slice_seven.py` covers each decision; the runtime, agent
  team, orchestration, analytics and modelling suites were updated where
  the contract changed (the two built-in sentences, the known reviewer, the
  shared toggle name).
- Open: U8 (domain-neutral asset copy) and U20 (the navy rail) are owner
  decisions; the standards lint blind score; the model half of G8.
