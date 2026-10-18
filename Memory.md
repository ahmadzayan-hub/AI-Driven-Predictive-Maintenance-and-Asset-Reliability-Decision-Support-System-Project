# Memory

Durable facts a future session needs and cannot get quickly from the code. The session-end skill maintains this file: update lines in place, delete what is no longer true, and keep it under about 150 lines. The linked brain notes carry the detail.

## The user

- English and Arabic: reply in the language of the request. More in [brain/User.md](brain/User.md).
- Wants finished, verified work: run the tests and report real counts. Short progress notes, then the result.
- Works with four capstone teammates; shares work as links they can review and edit.

## Non-negotiable rules

Full list: [brain/Soul.md](brain/Soul.md).

- No secrets in Git, logs, screenshots or client bundles. A key pasted into a chat is compromised and must be rotated.
- Raw datasets never go to a model.
- No force-push, no history rewriting, no branch deletion. No production deploy and no push to another branch without explicit permission. No pull request unless asked.
- Never fabricate screenshots, URLs, test counts or scores.
- The repository is public, so course files, registration numbers and teammates' details stay out.

## Repository

- Product name: **AI-Driven Predictive Maintenance and Asset Reliability Decision-Support System SaaS Project** (17 Oct, ADR 0036). English/Arabic interface labels: Asset Reliability / موثوقية الأصول. Agentic OS remains the engine. The frontend assistant persona is Miyaar / معيار (ADR 0053); backend identifiers and evidence remain intact. Public scope and milestones: `docs/PROJECT_CHARTER.md`; the course study and owner details stay in `private/project-study-2026-10-17/DELIVERY_PLAN.md`. This is a display-name change, not a remote repository, folder or deployment rename.
- Private execution guide: `private/project-study-2026-10-17/AI_Driven_Predictive_Maintenance_SaaS_Playbook.md`. The current team delivery tree is `private/capstone/`, located during the 17 October project review; older references to `team3-capstone/team3-capstone/` are stale. Report/deck candidates and the Power BI kit exist; a completed PBIX/model notebook was not found in the inspected delivery folders.
- Maintenance design (ADR 0037): the owner chose the executive overview. Open `?design=maintenance` on the React app for an isolated bilingual preview using fictional fixtures; no API/model calls or durable review actions. Handoff: `docs/design/MAINTENANCE_UI_SPEC.md`. The static preview browser suite uses `playwright.preview.config.ts`, independently of the Python-backed e2e suite.
- Real intake (ADR 0038): `#/runs?source=upload`, also linked from the preview and Overview. File readiness is enforced, mapping can be reviewed before analysis, and successfully parsed workbooks expose sheet selection. The computed run dashboard uses uploaded data; maintenance preview fixtures remain separate. Setup and worker instructions: `docs/DATASET_ANALYTICS.md`.
- Project review (17 October): `private/project-review-2026-10-17/PROJECT_ASSESSMENT.md` contains reproduced release blockers, prioritized remediation and capstone/pilot acceptance gates. Do not describe the hosted authorization or fatal governance policy as verified until those findings are resolved. This was an assessment, not a product-code fix or deployment.
- UI/agent advice (18 October): `private/UI_AGENT_IMPROVEMENT_PLAN_2026-10-18.md` is the proposed implementation backlog. New role-selection code and ADR 0040 exist after the assessment; recheck current implementation and tests before repeating fixes. Advice-only inspection did not close release gates.
- Claude handoff (18 October): `private/CLAUDE_CODE_UI_AGENTS_HARNESS_PROMPT.md` is the researched implementation prompt, matching the owner's operating/knowledge OS image. Official sources and applicability notes: `private/ANTHROPIC_AGENTIC_OS_RESEARCH_2026-10-18.md`. Prompt creation is not implementation or plugin activation.
- **Home repository (ADR 0043):** `ahmadzayan-hub/AI-Driven-Predictive-Maintenance-and-Asset-Reliability-Decision-Support-System-Project`, public. `ahmadzayan-hub/agentic-os-final-project` and `ahmadzayan-hub/11` both redirect to it, so old clone URLs, the two merged pull requests and the CI run links cited in `docs/design/VALIDATION.md` keep resolving; cloud sessions still address the project as `11`. Clone into a *short* folder: the repository name alone is 93 characters.
- Working and default branch: `claude/agentic-os-final-project-53j6ql`. `main` is behind; leave the default alone until after the capstone.
- Production: `https://agentic-os-final-project.vercel.app`, behind Vercel Authentication.
- Test counts are maintained in one place only, `README.md`.

## Environment gotchas

- **This Windows workspace:** declared server dependencies are installed in `.venv`; use `.venv/Scripts/python.exe` with `PYTHONUTF8=1`. Browser tests select `PYTHON_EXECUTABLE`, then the project venv, then `python3`. Real API/browser intake checks now run here. Full Python verification still fails, including locked SQLite files during test cleanup and CRLF fixture mismatches; do not treat this as a green backend suite. Windows Playwright teardown may need stopping the exact test-server PIDs after every case finishes before the runner exits; never stop unrelated servers or run both backend suites against the same `.tmp` folder.
- **Python:** `python3 -m pip install -r requirements.txt`. `pip` alone may target another interpreter. If PyJWT conflicts with Debian's copy, first run `python3 -m pip install --ignore-installed PyJWT cryptography`.
- **PostgreSQL tests:** run `service postgresql start`. In a fresh container, create the role and database first: `su postgres -c "psql -c 'create role dev login superuser'"`, then `su postgres -c "createdb -O dev agentic_test"`. Add a `host agentic_test dev 127.0.0.1/32 trust` line above the other host lines in `pg_hba.conf`, then reload. Run with `REQUIRE_PG=1 PG_TEST_URL=postgresql://dev@127.0.0.1:5432/agentic_test python -m unittest discover tests`.
- **End-to-end tests:** build first (`npm --prefix frontend run build`), then `PLAYWRIGHT_EXECUTABLE_PATH=/opt/pw-browsers/chromium npm --prefix frontend run e2e`. The screenshots spec rewrites `docs/screenshots/`, Overview and Datasets included, with reduced motion so no capture lands mid-transition: run `git checkout -- docs/screenshots` unless updating them on purpose.
- **npm lockfile fixes:** `npx -y npm@latest update --package-lock-only <pkg>`. npm 10.9's `audit fix` crashes, and `--legacy-peer-deps` silently drops `@testing-library/dom`.
- **Docs are tested:** `tests/test_docs.py` checks pipeline counts and the dataset limits quoted in README, user_guide and KNOWN_LIMITATIONS (4 MB uploaded, 10 MB as CSV, 50,000 rows). Write "72 megabytes", not "72 MB", in README.
- **Dataset limits (ADR 0024):** uploads stop at 4 MB because Vercel refuses request bodies over 4.5 MB. Workbooks are read with the standard library in `server/datasets.py`. Build test workbooks with `tests/xlsx_builder.py`; `python -m tests.xlsx_builder frontend/e2e/fixtures/regional-sales.xlsx` rewrites the end-to-end fixture.
- **End-to-end database:** every spec and both viewports share one database, and datasets are content-addressed per owner. Give each spec its own table, accept "already stored" where it can happen, and use `exact: true` for short button names that run goals may contain.
- **Vercel:** `vercel.json` pins `"framework": null`, because the FastAPI preset breaks the `/api` rewrites.
- **Cloud sessions:** uploads and uncommitted files do not survive a new container. The harness's Stop hook requires everything committed and pushed.
- **Windows console (native, not the container):** `scripts/verify.py` dies printing its own status mark, because the console encodes to cp1252 (`UnicodeEncodeError: '�'`). Any script printing non-ASCII needs `PYTHONUTF8=1` — but `python -I` ignores that, so write to a file instead, or keep output ASCII. Subprocess spawning is also blocked: 253 tests error with `_Py_HashRandomization_Init: failed to get random numbers`, on the pristine remote tree as well as on a working copy. Compare a branch against a fresh clone of the same commit before blaming a change for either.
- **Syncing this working copy to GitHub (18 Oct):** two remotes. `origin` is the home repository above; `canonical` is `agentic-os-final-project`, which received the history up to ADR 0043 and is no longer a push target. The repository that `origin` names began as a squashed one-commit snapshot and was renamed to the product's title; its `main` still holds that orphan `first commit`, which is left alone. Push the working branch to `origin`, never force. `gh` is not logged in, but git's Windows Credential Manager holds a working token, so `git push` over HTTPS succeeds.
- **Publishing to Obsidian (ADR 0044):** `AGENTIC_OS_VAULT_DIR` chooses where approved reports are written, beating `config.json`'s `vault_dir`, which beats the repository's `vault/`. Set it in the environment, never in `config.json`: that file is tracked and public, and a vault path holds a user name. `~` expands; a relative path resolves against the repository so the server, the worker and the MCP server agree. Obsidian is installed here and `brain/` and `vault/` are registered as vaults; the owner's own vault is `OneDrive\Documents\Obsidian Vault`.
- **Line endings (18 Oct):** `.gitattributes` pins `* text=auto eol=lf`, with fonts, images, PDFs, workbooks, MP4s and zips marked binary. Both repositories already stored LF, so adding it renormalised nothing. It removes the trap that made two `test_api.py` fixture comparisons fail on Windows and made Git report unstaged files that nothing had touched.
- **One command for every check:** `python scripts/verify.py` (`--quick`, `--e2e`; set `PG_TEST_URL` and `REQUIRE_PG=1` for PostgreSQL). Quote its PASS lines, never older counts.
- **Blocked hosts:** the proxy blocks designsystem.dubai.ae, dubaifont.com and fontsquirrel.com. Google Fonts, fonts.gstatic.com, raw.githubusercontent.com and PyPI work. A variable font prints into a PDF as Type 3; make static instances with fontTools (`varLib.instancer`).
- **Lighthouse:** serve with `python scripts/serve.py --local-only --port 8011` and run `npx lighthouse` from `frontend/` with `CHROME_PATH=/opt/pw-browsers/chromium`; recipe in `.claude/skills/verify/SKILL.md`. Never `pkill -f` a pattern that also appears in your own command line: it kills the shell (exit 144).

## Conventions

- UI handoff (ADR 0029): `docs/design/AGENTIC_UI_SPEC.md`; editable designs at https://www.figma.com/design/nLdKZ5cVOtRMTWEvhCJSEK. Current delivery targets a PWA on Windows, Android and iOS; native signing/store packages are separate. See `docs/design/VALIDATION.md` before claiming runtime verification.

- A behaviour change gets an ADR in `docs/adr/`, numbered next; ADRs are never edited to fit later facts.
- Every user-facing string exists in English and Arabic (`frontend/src/i18n/`, `assistant.py`).
- KPIs are ratios of sums, never averages of row rates ([brain/Concepts/Weighted KPIs.md](brain/Concepts/Weighted%20KPIs.md)). Check what a row rate holds before comparing: the capstone's preventive rows store placeholder rates.
- Commit messages explain why, in a descriptive body.
- Interface work: read `design-system/agentic-os/MASTER.md` first (its *Agentic OS decisions* section wins), then ask the vendored skill one focused question: `python3 .claude/skills/ui-ux-pro-max/scripts/search.py "<concern>" --domain ux`. Its search can miss; `references/quick-reference.md` has every rule. Components use tokens, never raw hex.
- Seven design skills come from `nextlevelbuilder/ui-ux-pro-max-skill` at `56ea9cf`, each with a `PROVENANCE.md`. For the app, only ui-ux-pro-max and design-system's token advice apply: ui-styling's shadcn/Tailwind and slides' CDN Chart.js break ADR 0023. design's logo, identity and icon generators send prompts to Gemini, AtlasCloud or MuAPI and need a key: never give them data.

## Standing decisions

- Capstone: the record is the unit of analysis, and loss per downtime hour is about $2,500. The capstone documents are private and shared with the team, never committed.
- **Every session ends on `main` (standing permission, 18 Oct).** The team and the course instructors read the repository there, so the working branch is pushed and then merged to `main` with both parents kept. **Fetch first**: `main` moved three times in one day on 18 October, each time with work that had to be integrated before merging or it would have been dropped, and each time with an ADR number collision. Never force; a rejected push means `main` moved again. Procedure: step 6 of the `session-end` skill.
- Hooks only record and remind; skills make the edits. Brain notes are public project knowledge.
- Interface (ADR 0023): the session opens on the assistant, with the Overview one click away; the phone bar holds five places; views other than the chat load on demand from `src/app/lazyViews.tsx` (ADR 0028); the budget is 100 KB of JavaScript on first load, 160 KB in all and 30 KB per view chunk, and CSS 10 KB on first load and 16 KB in all (ADR 0032), gzipped. The main `en.ts`/`ar.ts` load with the shell, so a lazily loaded view keeps its strings in a typed `messages.ts` pack read with `usePack` (ADR 0035). Labels the tests rely on ("Runs", "Workspace") stay.
- Serving (ADR 0023 amendment): the FastAPI server gzips everything outside `/api/` and marks `/assets/` immutable, as `vercel.json` does. API responses are never compressed (BREACH). Fonts sit at 119.4 of the 120 KB budget, so a new weight needs a budget decision.
- Other coding agents read `AGENTS.md`. Change it in the same commit as a rule in `CLAUDE.md`.
- Motion: `.claude/skills/motion` renders sourced explainers to MP4 with Playwright and `ffmpeg`. A 17-second 1080p clip takes about a minute. `render.mjs --check` refuses a figure without a source. Claude Motion itself is a hosted claude.ai beta on Team and Enterprise plans with no API, so it cannot be installed. Subagents load at session start, so `motion-designer` cannot be called in the session that adds it.
- Roles: the `owner` role carries admin permission and reads runs across owners by design, so tenancy tests use `analyst`. Live sources and the event stream are strictly per owner, admins included (ADR 0034).
- Live data e2e: the e2e server reads "remote" files from `frontend/e2e/.tmp/sources` at the reserved `https://fixtures.invalid/` host (`AGENTIC_OS_CONNECTOR_FIXTURES`); specs write the file themselves. Never set that variable outside tests. Real fetches cannot be tested here: the environment's proxy is the only way out, and connectors refuse proxies by design.
- Committing one milestone out of a mixed working tree: `git diff <file> > p`, keep the wanted hunks, `git apply --cached p`; then test the staged tree alone with `git checkout-index -a --prefix=<scratch>/tree/` and a symlinked `frontend/node_modules`.
- Column mapping (ADR 0025): `server/mapping.py` holds all reading rules. A run copies the mapping into `runs.mapping_json`. Unmapped data must keep running exactly as before, and the tests check it. Stage outputs are not in the API, so tests read `app.state.store.get_tasks()`.
- Capstone files are built outside the repository and sent to the user as files.
    - **Team workspace:** a private repository `ahmadzayan-hub/team3-capstone`, created by the user (this session's GitHub app gets 403 on repository creation). Its `.github/project/` JSON plus the Project setup workflow create labels, milestones and issues; `people.json` holds the usernames to assign. The public Agentic OS repository never holds course files, names or registration numbers.
    - **Report:** one tagged PDF with bookmarks, from the shared report's Markdown export, with pandoc and Chromium. Pages are numbered as the PDF counts them.
    - **Deck:** slide renders, with titles and alt text.
    - **Build scripts:** these went to the user as `Team3_Build_Tools.zip`.
    - **Wording:** the report and deck text is the team's. Corrections go to them as a memo with verified figures, never as silent edits.
- Agent team (`docs/AGENT_TEAM.md`):
    - **The loop:** the main session runs `review-loop`, because subagents cannot start subagents. New or edited agent files load only at the next session start; until then, run a general-purpose agent on the same model, told to follow the file. A named agent asked which instructions it has can misreport, so compare prompts with these controlled runs.
    - **Reviewer figures:** recompute them before passing them on. Turn each checkable finding into a gate.
    - **`--reset`:** `review_gate.py --reset` archives the old rounds.
    - **Local models:** Ollama downloads are blocked by this environment's proxy, so `consult.py` is tested only against a stub.
- Uneven periods (ADR 0026): a total over periods or groups of different sizes moves with the record count. The pipeline gives the per-record change, and dashboards show per-record charts. The capstone's 2026 months hold 83 records against 167, so totals fall while loss per record is flat.
- Measurement (ADR 0027): every classifying agent has a suite in `evals/` and a floor in `evals/floors.json`, checked by `tests/test_evals.py`.
    - **Fixes from dev only:** read dev misses (`evaluate_agents.py --misses`), never holdout ones. After a round, move the holdout into dev and get a new blind set from an agent that has seen only the label definitions.
    - **Reviewers:** run them on `evals/reviewers/` A, B and C, save the replies under `runs/`, then `score_review.py --summary`. The LLM reviewers sit near 100% on these memos, so the next memos must be harder.
    - **Rules found the hard way:** a figure checker that derives figures must stay off tables and count one quantity once; the capstone dashboard and the figures holdout each caught one.
- Capstone style (17 Oct): the report and deck are styled when built, with the house style's print variant (`tools/doc_theme.py` and `restyle.py`; `STYLE.md` in the build-tools bundle). The team's text and slides stay untouched, and the previous files are kept in `final/previous-style/` in the scratchpad. Typeface (the user's choice, 17 Oct): IBM Plex Sans with IBM Plex Sans Arabic (OFL) for the house style, report, deck and Power BI theme. Setting `DUBAI_FONT_DIR` rebuilds in Dubai, which cannot be fetched here.
- RTA and Dubai style facts (searched 17 Oct):
    - **Colours:** RTA publishes no colour codes. Red is its primary, kept beside blue. The logo red is about #EC1C24 by a third-party estimate. Our #C8102E is Pantone 186, the UAE flag red, so the style is "RTA-inspired", never official.
    - **RTA's typeface:** a private commission (29LT and Swiss Typefaces, 2016). Never use copies from free-font sites.
    - **Dubai Government's typeface:** the Dubai font; entities were directed to use it in official correspondence. It is free from dubaifont.com and ships with Windows 10 and later. Do not redistribute it, and do not take it from GitHub mirrors.
    - **Open (OFL) Arabic–English fonts:** IBM Plex Sans Arabic with IBM Plex Sans; Readex Pro (co-designed by Nadine Chahine, who led the Dubai font); Noto Sans Arabic or Noto Naskh Arabic with Noto Sans; Tajawal; Almarai. The "RTA Fleet" style guide (RTA Blue #073EEB, RTA Gold #FFB715) belongs to a US company.
- House style: `.claude/skills/rta-style/` (`tokens.json` → `build.py` → `tokens.css`) gives the user's executive-dashboard look in colours, type and layout only: never a logo, an organisation's name or its data, and never presented as official. The capstone Claude Dashboard (Q36TKj9qBNYv7o9qZTCH3V) wears it from version 2 of its page file.
- Claude Dashboards: build them with the Dashboard artifact type (`Artifact` `list`, `scope: "types"`). Data goes in as small aggregate files uploaded as assets, and every figure is marked `data-source`/`data-field`. Do not render or screenshot the result unless asked.

## Open questions

- Has the asset-ID email gone to the capstone instructors, and what was the reply? **The evidence is now established (17 Oct):** all 180 `Asset_ID` values map to exactly one `Record_Date`, all 180 mix more than one `Asset_Class`, and the widest age span inside one value is 18.6 years, so there is no asset panel. Recorded as trap 1 in the capstone workspace's `Memory.md`.
- **Answered (18 Oct), by the owner:** Moodle submission closes **Thursday 22 October 2026** and the team presents on **Sunday 25 October 2026**, demonstrating the presentation, Agentic OS and the SaaS platform. The course PDFs still read "To be announced"; these dates come from the owner as team contact. The 25 October demonstration makes a working platform a dated deliverable, not only a roadmap.
- The capstone workspace now has its own operating system (`CLAUDE.md`, `Memory.md`, `project-progress.md`, `session-logs.md` and `tools/`), separate from this repository's. Course files, names and registration numbers stay there; `inputs/` and `team3-capstone/` are ignored here.
