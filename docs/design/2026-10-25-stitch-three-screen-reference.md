# Miyaar: three Stitch screens are design references, not operational evidence

Date: 2026-10-25. Review branch: `codex/miyaar-reference-ux-20261025`.
Input: three user-supplied screenshots plus their exact companion HTML exports: `code.html`, `code(1).html`, `code(2).html`. Images/HTML were inspected from the user attachments; they are not shipped as application code or as live screenshots. The authenticated Google Stitch project itself did not become available through an MCP session.

## Screen-to-existing-product map

| Attached design | Concrete reference and reusable interaction | Existing Miyaar real source | Result / scope |
| --- | --- | --- | --- |
| Data & Analysis (`code.html`, `screen.png`) | Context row, four concise ingest metrics, time-series + FFT panels, searchable anomaly table, evidence slide-over and accessible numbers table | `DatasetsView`, `DashboardView`, `RunsView`, `charts.tsx` and existing filtered record drill-down | Retain actual sources, mapping, run/chart tables and evidence. This branch's phone bar-label change shows complete API-backed category names. No new SCADA, sensor streaming, FFT or Parquet claim. |
| Reports & Outputs (`code(1).html`, `screen(1).png`) | Left selectable report queue, right governed document inspector, bilingual output, source checks, approval state | `RunsView` section tabs, `ReportDocument` trusted renderer, approved report state, export APIs | **Implemented** a source-backed responsive report-index/preview split on the existing real report sections, preserving roving ARIA tabs, exact content and approval. A signed PDF/A-3 claim or cryptographic seal is **not** added. |
| Decision (`code(2).html`, `screen(2).png`) | Concise decision context, four evidence-backed KPIs, human gate, contextual agent process and selective workflow inspection | `OverviewView`, `CommandCentre`, `ExecutiveOverview`, `AgentCollaboration`, `ApprovalCard`, `RunTimeline` | Keep the already-merged decision-first reading order and recorded-stage visualisation. Never introduce a simulated DCS control-plane or fabricated live consensus. |

## Concrete issues visible in the HTML itself

1. **No real backend binding for the illustrated values.** All three exports embed example data and fixed labels: 4,820 records, 38 channels, 0.14 s sync, 94.8% quorum, USD 1.42M \"realized\" savings and numerous \"14/14 verified\" badges. None proves those measurements, agents, savings or validations exist in Miyaar's backend.
2. **Fake agent lifecycle.** `code(2).html` simulates deliberation with a client `setTimeout` and inserts a message that repeats fixed quorum figures. The `confirmDispatch()` handler produces a browser alert claiming that a work order was sent to DCS, rather than evidence of an authenticated command or a verified transaction. This must **never** be used as a production control or evidence mechanism.
3. **Misleading sign-off.** `code(1).html` includes fixed named approvers, signed timestamps, cryptographic hashes and PDF/A-3 export labels without application-backed signatures in the supplied file. The existing managed identity, actual report approval states and saved-report hash must remain authoritative. Do not display signed or published when merely previewed.
4. **Unvalidated technical thresholds and standards.** `code.html` and `code(2).html` show hard-coded ISO 10816-3 vibration levels, engine-room fault mode decisions and \"100% IEC 62443\" compliance tags. The cited ISO 10816-3:2009 was withdrawn/superseded by ISO 20816-3:2022 according to ISO [ISO 20816-3](https://www.iso.org/standard/78311.html). `code(1).html` cites ISO 55001:2014, which is withdrawn in favour of [ISO 55001:2024](https://www.iso.org/standard/83054.html). No benchmark threshold should be inferred from a mock without machine classification, licensed text and owner confirmation. Standards references are not proof of certification.
5. **Engineering semantics.** The screenshot mixes high-risk operational telemetry, incident state, long-horizon predictions, hypothetical intervention curves and monetary benefits. These must be individually labelled as observation, deterministic derived value, model inference or unverified scenario; these categories cannot share one \"live verified\" status.
6. **UI export constraints.** These HTML examples load Tailwind from CDN, Google Fonts and remote images, contain hard-coded mock identities, and use inline JS onclick handlers. Copy/pasting them into Vite would bypass i18n, governance and the existing bundle budget. Only patterns are reused with existing React components/CSS tokens.

## Adopted design criteria

- Three primary destinations remain Decision / القرار, Data & Analysis / البيانات والتحليل, Reports & Outputs / التقارير والمخرجات. Existing deep links, routes, source-based charts, full-value tables and accessible language tags remain.
- Active run/report metadata, measured KPIs and one prominent chart precede secondary details; dense spectral diagnostics are shown only when actual data and necessary algorithm exist.
- Selected report section and its actual content appear adjacent on desktops in a two-column document inspector; phone layout stacks sections and document without horizontal scrolling.
- A visible human approval gate and truthful status come from the stored run, **not** invented agent names, passwords, timestamps or \"cryptographic\" decorations.
- Never change Supabase, Hermes integration, identity, databases, hosting, numerical methods, report export or safety-critical control paths for a visual imitation.
- Prefer the existing source-backed design system and bilingual copy. The visual source does not authorize any RTA logo, official government stamp or external licensed font.
- Fresh app before/after screenshots, exact-head tests and asset budgets must precede any release claim. The supplied Stitch screenshots are references, not screenshots of a running Miyaar deployment.

## Verification gates and rollback

For this branch run `python scripts/verify.py --quick` and `python scripts/verify.py --e2e` on the final SHA, including existing Run approval/persistence/reload/export, Arabic and English, 320px/390px/tablet/desktop, accessibilities and unchanged size budgets. In `frontend/e2e/runs.spec.ts`, section selection is checked against a real run, its current language and the preserved report state; `frontend/e2e/executive.spec.ts` covers the narrow data chart fix.

No test result, production deployment, direct model invocation, ISO certification or live DCS actuation is claimed by this review document. Roll back source styling/markup/tests with new revert commits on this branch, never rewriting history.
