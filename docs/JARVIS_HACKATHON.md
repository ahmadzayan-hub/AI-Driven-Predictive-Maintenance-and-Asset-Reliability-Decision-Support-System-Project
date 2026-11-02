# Jarvis OS hackathon walkthrough

This is a synthetic maintenance decision demonstration. No RTA operational dataset, model response, savings or safety result is claimed.

Use existing installed frontend dependencies and the project Python environment. Build with `npm --prefix frontend run build`. Run `python scripts/serve_jarvis_demo.py --data-dir <NEW-absolute-disposable-directory> --port 8017`, then open `http://127.0.0.1:8017/?workspace=jarvis`. Keep the terminal running. The launcher refuses an existing data directory, starts no worker, installs nothing and downloads no model. It keeps generated synthetic artifacts for inspection. Original Miyaar data is not used. Do not point it at production configuration.

1. **Input:** open the synthetic workspace, expand Data for this chat, load reports and explicitly use `SYNTHETIC_RTA_review.csv`.
2. **AI function:** ask the suggested maintenance-cost question. A bounded bilingual parser selects the existing deterministic KPI tool. No LLM contributes.
3. **Output:** inspect cost 500 with undeclared currency, coverage, formula, dataset hash and report reference. Ask the availability follow-up: `(500 - 30) / 500 × 100 = 94%`. These are computed synthetic observations, not predictions. Unsupported prediction requests abstain. Switching to `SYNTHETIC_missing_hours.csv` produces undefined availability, not a made-up percentage.
4. **RTA value:** discuss the potential for traceable maintenance prioritisation. Review the proposed source/completeness check, tick the acknowledgement and confirm the tab-local review. This does not create a work order or approve/publish a report.

Arabic: اختر التقرير الاصطناعي، واسأل «ما إجمالي تكلفة الصيانة؟»، ثم «ما هو التوافر؟». راجع الصيغة والمصدر والحدود قبل تأكيد المراجعة المحلية. الأرقام اصطناعية محسوبة ولا تثبت وفورات أو سلامة تشغيلية. تغيير السؤال أو التقرير يصفر المراجعة.

Audio starts muted. Enable audio controls only when appropriate. Browser microphone recognition can transmit to its provider and requires explicit consent; never dictate confidential data. A final transcript remains editable until Calculate is clicked. Stop interrupts pending queries and capture. Read-aloud requires a local device voice and otherwise reports unavailable. No actual microphone, Arabic voice or local/cloud LLM acceptance is implied.

The normal Miyaar toolbar also opens Jarvis for the signed-in owner's completed analyses. Existing source/ownership restrictions and permissions still apply. The synthetic entrance refuses a normal hosted server. Keep the production database backup, target verification, migration and managed-auth gates separate from this feature.

For the unified executive workspace, open Dashboards in the same local app, choose `SYNTHETIC_RTA_review.csv`, and open Breakdown by `Asset_ID`. Connect this view to Jarvis, ask the cost question, then click the `SYN-C` bar. The old answer is cleared; explicitly reconnect the current scope and ask again to obtain 80 from one of three records. Save this view and reopen the dashboard to verify the existing saved-view flow. Overview, Breakdown, Trend, Distribution, Relationship and Records remain available for the dated synthetic fixture. On phones the assistant stacks above the charts; on wide screens it sits alongside them. The app preserves report review, approval and source navigation.

Browser QA: start the synthetic launcher, then `node node_modules/@playwright/test/cli.js test --config playwright.jarvis.config.ts` from the frontend directory. CI sets JARVIS_DATA_DIR to a new temporary directory so Playwright starts its own synthetic server. Set PLAYWRIGHT_EXECUTABLE_PATH only to an existing reviewed browser if needed. Screenshots contain synthetic content only.
