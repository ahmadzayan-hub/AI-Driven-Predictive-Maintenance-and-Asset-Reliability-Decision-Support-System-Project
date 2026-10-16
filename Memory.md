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

- `ahmadzayan-hub/agentic-os-final-project`, public; the old name `ahmadzayan-hub/11` redirects, and cloud sessions still address it as `11`.
- Working and default branch: `claude/agentic-os-final-project-53j6ql`. `main` is behind; leave the default alone until after the capstone.
- Production: `https://agentic-os-final-project.vercel.app`, behind Vercel Authentication.
- Test counts are maintained in one place only, `README.md`.

## Environment gotchas

- **Python:** `python3 -m pip install -r requirements.txt`. `pip` alone may target another interpreter. If PyJWT conflicts with Debian's copy, first run `python3 -m pip install --ignore-installed PyJWT cryptography`.
- **PostgreSQL tests:** run `service postgresql start`. In a fresh container, create the role and database first: `su postgres -c "psql -c 'create role dev login superuser'"`, then `su postgres -c "createdb -O dev agentic_test"`. Add a `host agentic_test dev 127.0.0.1/32 trust` line above the other host lines in `pg_hba.conf`, then reload. Run with `REQUIRE_PG=1 PG_TEST_URL=postgresql://dev@127.0.0.1:5432/agentic_test python -m unittest discover tests`.
- **End-to-end tests:** build first (`npm --prefix frontend run build`), then `PLAYWRIGHT_EXECUTABLE_PATH=/opt/pw-browsers/chromium npm --prefix frontend run e2e`. The screenshots spec rewrites `docs/screenshots/`, Overview and Datasets included, with reduced motion so no capture lands mid-transition: run `git checkout -- docs/screenshots` unless updating them on purpose.
- **npm lockfile fixes:** `npx -y npm@latest update --package-lock-only <pkg>`. npm 10.9's `audit fix` crashes, and `--legacy-peer-deps` silently drops `@testing-library/dom`.
- **Docs are tested:** `tests/test_docs.py` checks pipeline counts and the dataset limits quoted in README, user_guide and KNOWN_LIMITATIONS (4 MB uploaded, 10 MB as CSV, 50,000 rows). Write "72 megabytes", not "72 MB", in README.
- **Dataset limits (ADR 0024):** uploads stop at 4 MB because Vercel refuses request bodies over 4.5 MB. Workbooks are read with the standard library in `server/datasets.py`. Build test workbooks with `tests/xlsx_builder.py`; `python -m tests.xlsx_builder frontend/e2e/fixtures/regional-sales.xlsx` rewrites the end-to-end fixture.
- **End-to-end database:** every spec and both viewports share one database, and datasets are content-addressed per owner. Give each spec its own table, accept "already stored" where it can happen, and use `exact: true` for short button names that run goals may contain.
- **Vercel:** `vercel.json` pins `"framework": null`, because the FastAPI preset breaks the `/api` rewrites.
- **Cloud sessions:** uploads and uncommitted files do not survive a new container. The harness's Stop hook requires everything committed and pushed.
- **One command for every check:** `python scripts/verify.py` (`--quick`, `--e2e`; set `PG_TEST_URL` and `REQUIRE_PG=1` for PostgreSQL). Quote its PASS lines, never older counts.
- **Lighthouse:** serve with `python scripts/serve.py --local-only --port 8011` and run `npx lighthouse` from `frontend/` with `CHROME_PATH=/opt/pw-browsers/chromium`; recipe in `.claude/skills/verify/SKILL.md`. Never `pkill -f` a pattern that also appears in your own command line: it kills the shell (exit 144).

## Conventions

- A behaviour change gets an ADR in `docs/adr/`, numbered next; ADRs are never edited to fit later facts.
- Every user-facing string exists in English and Arabic (`frontend/src/i18n/`, `assistant.py`).
- KPIs are ratios of sums, never averages of row rates ([brain/Concepts/Weighted KPIs.md](brain/Concepts/Weighted%20KPIs.md)). Check what a row rate holds before comparing: the capstone's preventive rows store placeholder rates.
- Commit messages explain why, in a descriptive body.
- Interface work: read `design-system/agentic-os/MASTER.md` first (its *Agentic OS decisions* section wins), then ask the vendored skill one focused question: `python3 .claude/skills/ui-ux-pro-max/scripts/search.py "<concern>" --domain ux`. Its search can miss; `references/quick-reference.md` has every rule. Components use tokens, never raw hex.
- Seven design skills come from `nextlevelbuilder/ui-ux-pro-max-skill` at `56ea9cf`, each with a `PROVENANCE.md`. For the app, only ui-ux-pro-max and design-system's token advice apply: ui-styling's shadcn/Tailwind and slides' CDN Chart.js break ADR 0023. design's logo, identity and icon generators send prompts to Gemini, AtlasCloud or MuAPI and need a key: never give them data.

## Standing decisions

- Capstone: the record is the unit of analysis, and loss per downtime hour is about $2,500. The capstone documents are private and shared with the team, never committed.
- Hooks only record and remind; skills make the edits. Brain notes are public project knowledge.
- Interface (ADR 0023): the session opens on the assistant, with the Overview one click away; the phone bar holds five places; JavaScript at most 100 KB gzipped (92 KB at phase 1). Labels the tests rely on ("Runs", "Workspace") stay until phase 3.
- Serving (ADR 0023 amendment): the FastAPI server gzips everything outside `/api/` and marks `/assets/` immutable, as `vercel.json` does. API responses are never compressed (BREACH). Fonts sit at 119.4 of the 120 KB budget, so a new weight needs a budget decision.
- Other coding agents read `AGENTS.md`. Change it in the same commit as a rule in `CLAUDE.md`.
- Motion: `.claude/skills/motion` renders sourced explainers to MP4 with Playwright and `ffmpeg`. A 17-second 1080p clip takes about a minute. `render.mjs --check` refuses a figure without a source. Claude Motion itself is a hosted claude.ai beta on Team and Enterprise plans with no API, so it cannot be installed. Subagents load at session start, so `motion-designer` cannot be called in the session that adds it.
- Column mapping (ADR 0025): `server/mapping.py` holds all reading rules. A run copies the mapping into `runs.mapping_json`. Unmapped data must keep running exactly as before, and the tests check it. Stage outputs are not in the API, so tests read `app.state.store.get_tasks()`. JavaScript sits at 96.7 of 100 KB: code-split before adding views.
- Capstone files are built outside the repository and sent to the user as files.
    - **Report:** one tagged PDF with bookmarks, from the shared report's Markdown export, with pandoc and Chromium. Pages are numbered as the PDF counts them.
    - **Deck:** slide renders, with titles and alt text.
    - **Build scripts:** these went to the user as `Team3_Build_Tools.zip`.
    - **Wording:** the report and deck text is the team's. Corrections go to them as a memo with verified figures, never as silent edits.
- Agent team (`docs/AGENT_TEAM.md`):
    - **The loop:** the main session runs `review-loop`, because subagents cannot start subagents. New agent files load only at the next session start; until then, run a general-purpose agent told to follow the file.
    - **Reviewer figures:** recompute them before passing them on. Turn each checkable finding into a gate.
    - **`--reset`:** `review_gate.py --reset` archives the old rounds.
    - **Local models:** Ollama downloads are blocked by this environment's proxy, so `consult.py` is tested only against a stub.
- Uneven periods (ADR 0026): a total over periods or groups of different sizes moves with the record count. The pipeline gives the per-record change, and dashboards show per-record charts. The capstone's 2026 months hold 83 records against 167, so totals fall while loss per record is flat.
- Claude Dashboards: build them with the Dashboard artifact type (`Artifact` `list`, `scope: "types"`). Data goes in as small aggregate files uploaded as assets, and every figure is marked `data-source`/`data-field`. Do not render or screenshot the result unless asked.

## Open questions

- Has the asset-ID email gone to the capstone instructors, and what was the reply?
- What time does Moodle close on 22 October? (The report is 24 pages with its appendices, so the page question no longer matters.)
