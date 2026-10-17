# Session logs

One entry per working session, oldest first. The session-end skill appends each entry; the SessionEnd hook adds a short automatic one if the skill never ran. Every entry names its session as a backticked id, which is how the hooks tell whether a session was logged. Write facts only: commits, verified results, decisions, what is next.

Entry shape:

```markdown
## YYYY-MM-DD · `abcd1234` · <branch>

**Goal:** …

- **Done:** … (`commit`)
- **Verified:** … (only what actually ran)
- **Decisions:** …
- **Open / next:** …
- **Blockers:** …
```

The first entries were written from the commit history and the session's own record when this log was created on 2026-10-16. They cover one long session, `7ba0117d`, across several days.

## 2026-09-23 · `7ba0117d` · claude/agentic-os-final-project-53j6ql

**Goal:** finish custom agents as plugins, then measure agent frameworks.

- **Done:** custom stages under the same governance, ADR 0020 (`c09e8b3`). Agent runtimes, a tool box, an MCP server and framework examples, ADR 0021 (`de59a02`).
- **Verified:** CI runs 37 and 38 green.
- **Decisions:** the core stays framework-free, and frameworks plug in through three seams.

## 2026-10-02 · `7ba0117d` · claude/agentic-os-final-project-53j6ql

**Goal:** run the project in a browser, then deploy to Vercel.

- **Done:** framework preset pinned in `vercel.json` (`2aeb9fd`). Deployment recorded and verified for a signed-in owner (`7869546`). Frontend audit cleared (`92cf174`).
- **Verified:** CI run 42 green. The production URL serves the app and `/api` behind Vercel Authentication.
- **Decisions:** the FastAPI preset broke the `/api` rewrites, so the framework is `null`. A production deployment needs explicit authorisation each time.

## 2026-10-04 · `7ba0117d` · (no repository changes)

**Goal:** plan the Team 3 capstone from the course files.

- **Done:** analysed the course dataset and created the delivery plan as a private shared document: roles, tracker, timeline, dashboard design, AI plan.
- **Decisions:** the record is the unit of analysis, because asset IDs repeat. KPIs come from one weighted register. Course files stay out of the public repository.

## 2026-10-16 · `7ba0117d` · claude/agentic-os-final-project-53j6ql

**Goal:** open the repository to the team; draft the capstone submissions; set up the project's operating system.

- **Done:**
    - Merged `main` into the working branch (`253ea07`) and cleared the source-map-js advisory (`8a8b376`).
    - Added CONTRIBUTING.md, a PR template and a git-ignored `private/` folder (`7091b76`).
    - Drafted the capstone report and the 14-slide deck as private shared documents.
    - Set up CLAUDE.md, Memory.md, project-progress.md, this log, the second brain (`brain/`), `scripts/brain_check.py`, and the session hooks and skills in `.claude/` (`fe9ef8a`, CI run 44 green).
    - Digested the re-uploaded course files, which were identical to the originals. Computed the remaining capstone analyses: failure-mode Pareto; stockouts and lead time; SLA by team, shift and criticality; strategy and class; final models with baselines, a bootstrap interval, top-10% precision, calibration and permutation importance.
    - Filled the report draft, rebuilt five slides and added a strategy slide (15 in total), and delivered a Power BI kit with Power Query, DAX, a theme and 30 expected values. All of it stays outside the repository.
- **Verified:**
    - Before the operating-system work: 616 Python tests with PostgreSQL (16 optional skips); 37 frontend unit tests; 51 of 52 end-to-end checks run and passed (1 desktop-only skip). CI run 43 green on `7091b76`.
    - After it: 646 Python tests with PostgreSQL (16 optional skips), including 30 new tests for the brain checker and the hooks; docs tests pass; brain check strict-clean; each hook exercised by hand against this repository.
- **Decisions:**
    - Loss per downtime hour is about $2,500 (ratio of sums), not the plan's $2,000 (a row average).
    - Brain notes are public project knowledge; private notes go in `brain/private/`.
    - Hooks only record and remind; the skills edit.
    - Capstone recommendation 8: move reactive equipment to condition-based maintenance (MTBF 219 h against 363 h at the same average age of 8.1 years).
    - The inspection pilot starts with the free condition-score ranking, because the model only matches it in the top 10% of the queue (85% against 86%).
- **Open / next:** build the `.pbix` from the kit; team-owned `[Add]` items; owners rerun their figures; A1 dataset API with ADR 0023; confirm the hooks fire in a fresh session.
- **Blockers:** inviting collaborators is an owner action on GitHub. Power BI Desktop is needed for the `.pbix`.

## 2026-10-16 · `7ba0117d` · claude/agentic-os-final-project-53j6ql

**Goal:** plan the user interface and build it with the ui-ux-pro-max skill.

- **Done:**
    - Vendored the ui-ux-pro-max skill (MIT, commit `56ea9cf`, with `PROVENANCE.md`) and generated the design system into `design-system/agentic-os/`, with repository overrides. Wrote `docs/UI_PLAN.md` (phases 0 to 6, mapped to milestones A1 to A7) and ADR 0023.
    - Phase 0: tokens v2 (navy and blue, amber highlight), bundled Fira Sans and Fira Code, flat brand mark and icons, negative bars from a zero line, a marked forecast boundary (`forecast_from` from the server), and a table of the numbers under every chart.
    - Phase 1: the Overview (key figures, latest findings in their report's language, the approval queue, recent analyses) and the Datasets view (Analyse runs a stored dataset by `dataset_id`). Grouped sidebar; a phone bar of five places with *More*. All strings in English and Arabic.
    - Screenshot spec now captures the new views, with reduced motion; screenshots regenerated. All in `dea3b38`.
- **Verified:** 646 Python tests with PostgreSQL (16 optional skips); docs tests; 52 frontend unit tests; typecheck and build (JavaScript 92 KB gzipped, CSS 7 KB); 60 end-to-end checks, 57 run and pass and 3 skipped by design; axe clean on the new views in English and Arabic; no overflow at 320 px; SBOM licence check clean; brain check strict-clean. CI not yet checked for `dea3b38`.
- **Decisions:**
    - The session still opens on the assistant; the Overview is one click away (ADR 0023).
    - The JavaScript budget rises from 90 KB to 100 KB gzipped, to leave room for phases 2 and 3.
    - The skill's advice never overrides the repository's rules. Its generated `#DBEAFE` border (about 1.2:1), its GSAP motion and its landing-page pattern were overridden.
    - The dataset API's record becomes ADR 0024.
- **Open / next:** confirm CI on `dea3b38`; A1 dataset API with ADR 0024, then interface phase 2 (upload formats, preview, column mapping, deep links). The phone header truncates the agent's name (pre-existing, recorded in KNOWN_LIMITATIONS).
- **Blockers:** none.

## 2026-10-16 · `7ba0117d` · claude/agentic-os-final-project-53j6ql (later)

**Goal:** clone the ui-ux-pro-max skills from GitHub and use them as skills.

- **Done:** re-cloned `nextlevelbuilder/ui-ux-pro-max-skill`. Its HEAD is still `56ea9cf`, so the vendored ui-ux-pro-max is current. Reviewed and vendored the repository's six other skills (banner-design, brand, design, design-system, slides, ui-styling), each with its MIT licence and a `PROVENANCE.md` (`b478983`). Claude Code registered all six.
- **Verified:** offline scripts smoke-tested from their installed paths; the design-system skill loaded through the Skill tool, and its token validator ran on `frontend/src`. It found no hardcoded colours, but a direct search found four it misses (three `rgb(5 8 18 / 0.62)` scrims, one `#fff` switch thumb in `app.css`). Project OS, docs and SBOM tests (63) pass; brain check strict-clean.
- **Decisions:** vendor everything, unchanged. Contain the risks in documentation: design's logo, identity and icon generators call Gemini, AtlasCloud or MuAPI with an API key (`.env` is git-ignored everywhere; never give them data), and ui-styling's shadcn/Tailwind and slides' CDN Chart.js do not apply to the app (ADR 0023).
- **Open / next:** optionally turn the four hardcoded colours into tokens (`--scrim`, `--switch-thumb`); confirm CI on `b478983`; then A1 with ADR 0024.
- **Blockers:** none.

## 2026-10-16 · `7ba0117d` · claude/agentic-os-final-project-53j6ql (colour tokens)

**Goal:** fix the four hardcoded colours the design-system audit turned up.

- **Done:** added `--scrim` and `--switch-thumb` to `tokens.css` (defined once, the same in both themes) and used them for the drawer, dialog and palette scrims and the switch thumb. No raw colour remains in `frontend/src` outside `tokens.css`.
- **Verified:** 52 frontend unit tests; build (JavaScript 92.9 KB, CSS 7.3 KB gzipped); 26 end-to-end checks in the accessibility, Arabic, journey and overview specs, 24 run and pass and 2 skipped by design.
- **Decisions:** both values keep their exact previous colours, so nothing changes on screen and no contrast needed rechecking.
- **Open / next:** A1 with ADR 0024.

## 2026-10-16 · `7ba0117d` · claude/agentic-os-final-project-53j6ql (A1)

**Goal:** start A1, the dataset API, with ADR 0024.

- **Done:** `POST /api/datasets` reads CSV, TSV, Excel, JSON and JSON Lines into one canonical CSV with the standard library (`server/datasets.py`). Datasets record their format and shape. The Runs view has a Sample, Stored and Upload switch with a stored-dataset picker, and the Datasets view adds files. ADR 0024. All in `50babcc`.
- **Verified:**
    - Measured before choosing limits: the slowest stage took 2.9 s at 50,000 rows × 20 columns (5.3 MB).
    - 699 Python tests with PostgreSQL (16 optional skips), 53 of them new.
    - 54 frontend unit tests; typecheck and build (JavaScript 94.1 KB, CSS 7.4 KB gzipped).
    - 66 end-to-end checks: 63 run and pass, 3 skipped by design.
    - Docs tests, SBOM licence check and brain check all clean.
    - CI not yet checked for `50babcc`.
- **Decisions (ADR 0024):**
    - A raw request body, not multipart, so no new dependency.
    - Read workbooks with the standard library rather than openpyxl or pandas.
    - 4 MB per upload, under Vercel's 4.5 MB request limit; 10 MB as CSV; 50,000 rows; 500 columns.
    - Refuse non-UTF-8 CSV rather than guess an encoding.
    - Refuse `DOCTYPE`s, and cap the XML read from a workbook.
    - A repeat upload answers `200` with `created: false`.
- **Defects found on the way:**
    - Inline workbook strings would have picked up whitespace from pretty-printed XML.
    - The CSV row cap rescanned every row each time.
    - The Datasets list flashed to a skeleton after each upload.
    - The three-way switch would have overflowed at 320 px.
    - All four were fixed before the commit.
- **Open / next:**
    - Confirm CI on `50babcc`, including the expected 17 skips.
    - A2, column mapping, with ADR 0025.
    - Interface phase 2: preview, a sheet picker, deep links.
- **Blockers:** none.

## 2026-10-16 · `7ba0117d` · claude/agentic-os-final-project-53j6ql (Codex brief)

**Goal:** draft a prompt for Codex to design and build the agentic interface in React, based on current agentic UI trends on GitHub.

- **Done:**
    - Surveyed agentic interface work on GitHub as of 16 Oct 2026: AG-UI events and interrupts, A2UI v0.9.1, MCP Apps (stable 2026-01-26), assistant-ui, CopilotKit, AI Elements (deprecated end of Nov 2026), React 19.3.1.
    - Wrote `docs/CODEX_UI_PROMPT.md`: a shared brief and six tasks, with the patterns mapped onto Agentic OS. Cross-linked the two older UI prompts.
    - Published the same text as a private page with copy buttons: https://claude.ai/artifact/9XAZ9BZP3Q95vHyTuFpo5T
- **Verified:** docs tests pass. The page rendered at 1366 px (light) and 390 px (dark) with no sideways scroll and no script errors.
- **Decisions:**
    - Take the patterns, not the packages: no CopilotKit, AI Elements or shadcn/ui, per ADR 0023.
    - The run engine stays polling. The interface gets an AG-UI-shaped client adapter, so a streaming transport could replace polling later without UI changes.
    - No reasoning display.
- **Open / next:** run Codex Task 1, the specification, and review it. Consider an `AGENTS.md` pointing Codex to `CLAUDE.md`.
- **CI:** runs 48 (colour tokens) and 49 (A1, `b925fc6`) are green. Run 49's Python step reported `Ran 699 tests ... OK (skipped=18)`, not the 17 the README predicted. The extra skip is the static-files test, which needs a frontend build that CI makes later. The README was corrected to 681 run in CI.

## 2026-10-16 · `7ba0117d` · claude/agentic-os-final-project-53j6ql (deliverables and setup)

**Goal:** complete the Agentic OS setup for full performance, and generate the final capstone deliverables.

- **Done:**
    - Capstone release candidates, built outside the repository and sent to the user:
        - `Group_9226_Team_3_Report.pdf`: 24 A4 pages, a cover, a contents page with real page numbers, and the quarterly downtime chart recomputed from the dataset.
        - `Group_9226_Team_3_Presentation.pptx`: 15 slides with notes and alt text.
        - The Power BI kit, a submission checklist and the build scripts.
    - Reconciled report, deck and kit. All 30 expected dashboard values agree with the report; three MTBF values appear there rounded to whole hours. Every number in the deck appears in the report, exactly or abbreviated. The two illustrative gaps, 6,421 h and $17.94M, recompute from the CSV.
    - Server compresses and caches the built interface as Vercel does, and an unmatched `/api/` path returns 404. Recorded as an ADR 0023 amendment (`a74db6c`).
    - `AGENTS.md` for other coding agents; `scripts/verify.py` and the `verify` skill (`a74db6c`).
- **Verified:**
    - `python scripts/verify.py --e2e` with PostgreSQL passed all 7 steps:
        - 719 Python tests, 16 skipped;
        - the brain check;
        - the type check;
        - 54 frontend unit tests;
        - the build;
        - the budget: JavaScript 92.9 of 100 KB, CSS 7.3 of 10 KB, fonts 119.4 of 120 KB;
        - end-to-end: 63 passed, 3 skipped by design.
    - Lighthouse 13.4.1 mobile, before the change: Performance 86, 87 and 88; LCP 3.4 s.
    - After: 99 in each of three runs, with Accessibility, Best Practices and SEO at 100; LCP 2.0 s, CLS 0. Desktop scored 100 in all four.
    - The SessionStart hook fired live in this session (state file) and after each compaction.
- **Decisions:**
    - Never compress API responses. A token beside caller-chosen text is the shape BREACH needs.
    - Leave the team-owned facts as visible highlighted items in the PDF rather than fill them in. These are the registration numbers, screenshots, notebook names and the instructor email.
    - The `.pbix` must be saved by Power BI Desktop from the kit.
- **Open / next:**
    - Confirm CI on `a74db6c`; the expected Python result is 701 run, `skipped=18`.
    - The team builds the `.pbix` and resolves the highlighted items before 21 Oct.
    - Then A2, column mapping (ADR 0025), with code-splitting of views to recover the 43 KB of script that Lighthouse reports unused.
- **Blockers:** the `.pbix` needs Windows and Power BI Desktop.

## 2026-10-16 · `7ba0117d` · claude/agentic-os-final-project-53j6ql (A2 column mapping)

**Goal:** start A2, column mapping, with ADR 0025.

- **Done:** A2 shipped (`af4d793`).
    - ADR 0025.
    - `server/mapping.py`: reading rules, profile, suggestion and validation.
    - `GET /api/datasets/{id}`, and `PUT` and `DELETE /api/datasets/{id}/mapping`.
    - A mapping copy in each run.
    - Pipeline stages that follow the mapping.
    - A *Columns* panel in the Datasets view: preview, suggestions and an error summary, in English and Arabic.
    - A *Mapped* tag in the list and the Runs picker.
    - The brain note *Column mapping*.
- **Verified:** `python scripts/verify.py --e2e` with PostgreSQL passed all 7 steps:
    - 769 Python tests, 16 skipped, 50 of them new;
    - the brain check;
    - the type check;
    - 60 frontend unit tests;
    - the build;
    - the budget: JavaScript 96.7 of 100 KB, CSS 7.7 of 10 KB, fonts 119.4 of 120 KB;
    - end-to-end: 69 passed, 3 skipped by design. That includes 6 new mapping checks on desktop and phone, axe-clean in English and Arabic, with no sideways scroll at 320 px.
- **Decisions:**
    - Unmapped data runs exactly as before, so old reports reproduce.
    - A suggestion is never applied silently.
    - A decimal comma is refused, not guessed.
    - An ambiguous day or month order is asked, not guessed.
    - The profile reads a 10,000-row sample, which took 1.3 s at the 50,000-row limit; validation reads every row.
    - Pasted CSV ignores a saved mapping of the same content.
- **Defects found on the way, all fixed before the commit:**
    - A currency column of whole dollars was suggested as an identifier.
    - Unique free text became a dimension.
    - An untouched suggestion was reported as unsaved changes.
    - Two buttons shared the name "Analyse …".
    - The panel crashed on a malformed response.
- **Open / next:**
    - Confirm CI on `af4d793`; the expected Python result is 751 run, `skipped=18`.
    - Code-split the views.
    - A3, several datasets per run (ADR 0026).
    - Deep links and the sheet picker.
- **Blockers:** none.

## 2026-10-16 · `7ba0117d` · claude/agentic-os-final-project-53j6ql (motion skill)

**Goal:** research "Claude Code motion", then install it and integrate it as a project subagent for deliverables.

- **Found:**
    - Claude Motion is Anthropic's hosted beta in claude.ai (launched 8 Oct 2026). It is on Team and Enterprise plans only, and off by default on Enterprise. It writes animation as code and exports MP4.
    - There is no API or Claude Code route, so it cannot be installed in a repository.
    - Community skills take the same approach, for example HTML with Playwright and ffmpeg. The one reviewed fetches third-party media at run time, so none was vendored.
- **Done:** `550ae22`.
    - The `.claude/skills/motion` skill:
        - a composition in which each frame is a pure function of time;
        - `render.mjs`, which steps frames in Chromium and encodes H.264 with ffmpeg, refuses figures without a source, and writes a poster, a review sheet and a transcript;
        - English and Arabic examples from the sample dataset.
    - `.claude/agents/motion-designer.md`, the first project subagent.
    - `tests/test_motion.py`, with 7 tests.
    - Updated `.claude/README.md`, the playbook, the README and `Memory.md`.
- **Verified:**
    - Both examples rendered here: 510 frames, 17 s, 1920×1080, 30 fps, yuv420p, about 60 s each.
    - The Arabic sheet was reviewed. It is right to left, with figures isolated so the currency reads "3,583,440 US$".
    - 776 Python tests with PostgreSQL, 16 skipped.
    - CI runs 52 and 53 green (A2 included).
- **Decisions:**
    - Build locally, with no network, audio or third-party assets, rather than vendor a community skill.
    - Course clips are rendered outside the repository.
- **Open / next:**
    - The capstone briefing clip is being rendered by an agent following the `motion-designer` instructions. Subagents load at session start, so `motion-designer` is callable by name from the next session.
    - Confirm CI on `550ae22`.
- **Blockers:** none.

## 2026-10-16 · `7ba0117d` · claude/agentic-os-final-project-53j6ql (agent team, review loop, dashboards)

**Goal:**
- a review super-agent that loops until deliverables are 100% validated, with the subagents it needs;
- free open-source models and tools wherever they do the job, to keep cost near zero;
- Claude Dashboards (Anthropic, 8 October 2026) as an agent for deep analysis and dashboards.

- **Done:**
    - `c63ae28`, the agent team (`docs/AGENT_TEAM.md`):
        - Five read-only reviewer subagents, each on Haiku or Sonnet by job, and `dashboard-analyst`.
        - The `review-loop` skill, with `scripts/review_gate.py` (rounds, stop rules, archived resets) and `scripts/figures_check.py` (glued cells, CSV cells, worked arithmetic).
        - `scripts/analyse.py` and the `dashboards` skill, with an offline renderer.
        - `scripts/consult.py` for free local models.
        - The motion skill's transcripts keep sources apart, and a clip can name its poster.
    - `8e1a177`, ADR 0026: uneven periods are read per record. Also fixed the "against the overall direction" claim and the headline casing; the capstone dashboard run found all three.
    - `61cd23a`, the docs:
        - README, AGENTS.md, CLAUDE.md, the playbook and limitations 22 and 23;
        - a new brain note, *Agent team*;
        - corrections to *Weighted KPIs* and *Team 3 Capstone*.
    - **Capstone review (outside the repository).** Four reviewers ran in round 1; one Haiku reviewer confirmed the fixes in round 2.
        - Gates: 50.0% → 56.2% → 62.5% → 62.5% (16 gates). All ten the session could act on pass; six are the team's.
        - Rebuilt: a tagged PDF with bookmarks and alt text, titled slides with readable alt text and correct metadata, and the clip with associative wording and reader-facing sources.
        - The Power BI guide gained a landing decision, a trend and cards.
        - `Team3_Review_Round1_Corrections.md` went to the user: verified figures and replacement wording, with owners.
    - **Dashboards.** Both were built from aggregates only, with zero unsourced figures:
        - an offline capstone dashboard;
        - a private Claude Dashboard, https://claude.ai/artifact/Q36TKj9qBNYv7o9qZTCH3V, made with the Dashboard artifact type and four attached aggregate files.
- **Verified:**
    - `scripts/verify.py` with PostgreSQL: 818 Python tests, 16 skipped; brain check clean (25 notes); type check; 60 frontend unit tests; build; interface budget (JS 96.7 of 100 KB).
    - End-to-end was not rerun, because no interface changed.
    - Every figure the analytics reviewer cited was recomputed from the dataset before it went in the memo. Two of its numbers differed slightly; the memo uses the recomputed ones.
    - The Claude Dashboard was not rendered, as the artifact type instructs, and no reader has opened it yet.
- **Decisions:**
    - **The loop:** it is a skill, not an agent, because subagents cannot start subagents.
    - **Team text:** the team's shared report and deck are theirs to edit. Corrections go as a memo, not silent edits.
    - **Findings:** each finding a pattern can check becomes a gate.
    - **ADR numbers:** 0026 is uneven periods, so A3 moves to 0027.
- **Open / next:**
    - **The team** (memo): build the `.pbix`; apply the two headline corrections and their highlighted items; then rerun the gates and the analytics and brief reviewers.
    - **Confirm CI** on these commits.
    - **Agent loading:** the new agents load by name from the next session start.
- **Blockers:**
    - `.pbix` needs Power BI Desktop.
    - Ollama models cannot be downloaded here, so local consultation is untested live.

## 2026-10-17 · `7ba0117d` · claude/agentic-os-final-project-53j6ql

**Goal:** measure every agent and LLM reviewer with confusion matrices and raise their recall, honestly; and give the agents' outputs the user's RTA-style look (colours, fonts and themes, with no logo and no RTA data).

- **Done:**
    - `c2c1580`, ADR 0027, agents are measured:
        - Labelled synthetic suites for eight classifying agents (`scripts/evaluate_agents.py`, `evals/`), with confusion matrices, precision and recall, and floors in `tests/test_evals.py`.
        - Fixes from dev misses only. The holdouts for intent, jargon and causal wording were written blind by independent agents.
        - `scripts/claims_lint.py`, a new Tier 0 check for causal wording.
        - The assistant can forget a note by description.
        - A seeded reviewer benchmark (`evals/reviewers/` A, B, C) scored by `scripts/score_review.py`.
        - Figures checker fixes, and reviewer prompts v2 (from A only).
    - `9e21f32`, the house style `.claude/skills/rta-style/`: light and dark tokens tested for AA contrast, wired into the dashboards renderer (`--theme rta`), the clips (`rta`, `rta-dark`) and the evaluation report. No logo, name or data.
    - **Outside the repository:**
        - The evaluation report, published as a private page: https://claude.ai/artifact/LwXdUtQbPwnVWSa2yCEz2B
        - The capstone Claude Dashboard (Q36TKj9qBNYv7o9qZTCH3V) restyled in the house style. The page file is now at version 2 with all 50 data bindings unchanged, and version 1 is in its history.
        - The offline capstone dashboard was re-rendered in the theme (scratchpad).
- **Verified:**
    - `scripts/verify.py` with PostgreSQL: 851 Python tests, 16 skipped; brain check clean (26 notes); type check; 60 frontend unit tests; build; interface budget (JS 96.7 of 100 KB). End-to-end was not run, because no app interface changed.
    - **Blind holdout recall, before → after:** intent 65% → 80% (the intermediate blind set scored 68%); jargon 40% → 83%; router 75% → 90%; privacy 83% → 100%; raw-data guard 50% → 100%; causal wording 67% (new).
    - **Reviewer benchmark:** 24 LLM runs, scored. Lane recall:
        - Tier 0 checker on blind C: 0% → 75%.
        - Analytics reviewer (controlled v1 → v2): A 83% → 100%, B 80% → 80%, C 100% → 100%.
        - Figures auditor: 100% everywhere.
        - Team: A 100%, B 89%, C 100%.
    - The capstone figure gates give the same results with the old and new checker. The offline dashboard check is identical too.
    - The report page was looked at once, desktop light and phone dark, with no horizontal overflow.
- **Decisions:**
    - **Comparing prompts:** named subagents load their instructions at session start, so v1 and v2 were compared as controlled runs, with a general-purpose agent on the same model.
    - **Labels:** B's P06 label (overclaim) was kept although every run called it causal; labels are never changed after results.
    - **Holdouts that informed fixes:** the figures holdout exposed a coincidence (75.2% and 0.752 as two inputs), and the dashboard's table exposed another. Both fixes are general, and the ADR says that holdout is no longer blind.
    - **ADR numbers:** A3 moves to 0028.
- **Open / next:**
    - **Harder reviewer memos:** the LLM reviewers are at their ceiling, so prompt changes cannot be shown yet.
    - **Causal wording:** a new blind set; it is the weakest suite.
    - **Live prompts:** the v2 reviewer prompts take effect for named subagents from the next session.
    - **Confirm CI** on these commits.
    - The brain maintenance due today was not run beyond this session's note updates.
- **Blockers:**
    - Local Ollama models cannot be downloaded here.
    - Hosted narrator models need a rotated provider key, so neither was measured.

## 2026-10-17 (continued) · `7ba0117d` · claude/agentic-os-final-project-53j6ql

**Goal:** apply the RTA style (blue, white and the rest) and the Dubai Government style, without logos, to the capstone report and deck.

- **Done:**
    - **Research:** the Dubai Design System asks for the Dubai typeface in Arabic and English, hierarchy from size and weight, and AA contrast. It tells each entity to use its own colours, so the palette here is RTA blue and white. It allows a substitute typeface.
        - The design system site and dubaifont.com are blocked here.
        - The Dubai font's licence limits redistribution, so Noto Sans (SIL Open Font License) is used, and `DUBAI_FONT_DIR` rebuilds with Dubai.
    - **Repository:** `.claude/skills/rta-style/` gains:
        - a `document` palette with contrast pairs and a role map from the project's default palette;
        - a generated `document.css`;
        - `restyle.py`, which recolours inline-styled HTML by role, checks every text colour against its real background, and never changes a word.
        - Four new tests in `tests/test_rta_style.py`.
    - **Capstone files (outside the repository):** rebuilt with a build-time theme (`tools/doc_theme.py`). The team's text and slides are untouched, and the previous files are in `final/previous-style/`.
        - **Report:** 23 pages, tagged, 20 bookmarks; fonts embedded as TrueType, made as static instances with fontTools.
        - **Deck:** 15 slides with titles and alt text.
        - The Power BI theme in the kit matches, with Dubai first, then Segoe UI.
        - The build-tools bundle gained the style step, the fonts with their licence, and `STYLE.md`.
- **Verified:**
    - Capstone gates, round 5: 62.5%, the same ten pass. The six failures are the team's, unchanged.
    - The slides render with no overflow, and their text is identical to the source.
    - The pages were checked once by eye.
    - Python suite with PostgreSQL: 856 tests, 16 skipped.
    - CI run 57 passed for `66cc76e`.
    - The README count is corrected to 856. It said 851, one short, because the table test was added after that count.
- **Decisions:**
    - The style is applied at build time, never by editing the team's documents.
    - Red is used on white only, never on navy, where it fails contrast.
- **Open / next:**
    - If the team wants the real Dubai typeface, download it from dubaifont.com and rebuild with `DUBAI_FONT_DIR`.
    - The team items and wording corrections from the review memo are still open.

## 2026-10-17 (research) · `7ba0117d` · claude/agentic-os-final-project-53j6ql

**Goal:** find RTA Dubai's official colours and fonts, and professional Arabic–English (RTL) fonts.

- **Done:**
    - Researched the question; the findings are in `Memory.md` under *RTA and Dubai style facts*.
    - **No published RTA colour codes.** The red we use, #C8102E, is the UAE flag red (Pantone 186).
    - **RTA's typeface is a private commission.** The Dubai font is the Dubai Government's.
    - **Open-licence Arabic–English fonts** were verified from Google Fonts' own metadata.
- **Verified:** the licences, designers and weights come from `google/fonts` `METADATA.pb` files. The RTA and Dubai facts come from search results only, because rta.ae, Gulf News, the rebrand agency and dubaifont.com are blocked here.
- **Open / next:** the user chooses the typeface; then the house style and the capstone builds switch to it.

## 2026-10-17 (typeface) · `7ba0117d` · claude/agentic-os-final-project-53j6ql

**Goal:** after the research, the user chose IBM Plex Sans with IBM Plex Sans Arabic for the house style, the report and the deck.

- **Done:**
    - **Repository:** the font stacks in `tokens.json` lead with IBM Plex Sans and IBM Plex Sans Arabic, for both screen and print; `typefaces` records the licences. The clips' RTA theme and the skill's text follow.
    - **Capstone files:**
        - `doc_theme.py` loads Plex Latin and Arabic (static, from @fontsource), and the report body is 10.2 pt.
        - The report and the deck were rebuilt.
        - The Power BI theme names IBM Plex Sans first, then Segoe UI.
        - The tools bundle installs Plex through npm and no longer ships Noto.
- **Verified:**
    - **Gates, round 6:** 62.5%, the same ten pass. The six failures are the team's.
    - **Report:** 23 pages, tagged; IBM Plex Sans is embedded as TrueType, and only ≤ and ≥ fall back.
    - **Slides:** all 15 render with no overflow.
    - **Arabic sample:** renders in IBM Plex Sans Arabic, both weights loaded.
    - `tests.test_rta_style`, `tests.test_motion` and `tests.test_agent_team` pass.
    - CI runs 58 and 59 passed.
- **Open / next:** the team's items from the review memo.
