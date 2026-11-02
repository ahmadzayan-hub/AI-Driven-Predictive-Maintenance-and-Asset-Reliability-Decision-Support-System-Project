> Historical Stitch design brief, 25 October. Its proposed token values do not
> override the approved 26 October palette in the application. Current DESIGN.md
> and the implemented tokens govern conflicts; preserve evidence and approval safeguards.

# Design System: MIYAAR | معيار
## Executive Asset Reliability & Decision-Support Workspace
**StitchDesign semantic reference • 25 October 2026 • review candidate**

### Purpose and source of truth
This is the canonical **Stitch-oriented visual brief** for generating consistent MIYAAR screens. It specifies presentation and interaction, **not** a new backend, production guarantee, engineering finding, or authorization to deploy. The implementation source of truth is the existing application: `frontend/src/shared/styles/tokens.css`, `frontend/src/app/App.tsx`, `frontend/src/features/*`, the FastAPI contracts, persisted run/evidence stores, and `AGENTS.md` / `CLAUDE.md`. Where this visual brief and working code differ, verify the code and record an ADR before changing behavior.

References inspected: the user's three Stitch screenshots and HTML exports (`code.html` for Data & Analysis, `code(1).html` for Reports & Outputs, and `code(2).html` for Decision), plus the supplied Team 3 Power BI/report reference and the source-to-product mapping in `docs/design/2026-10-25-stitch-three-screen-reference.md`. Their embedded people, figures, hash strings, control signals and compliance labels are **illustrations only**. Do not import them as live data.

## 1. Visual Theme & Atmosphere
A **restrained, evidence-first industrial executive desk**, not a generic admin template and not a sci-fi autonomous control room. Think precise reliability engineering with editorial clarity: one decision at a time, legible charts, explicit evidence and quiet surfaces.

- **Density:** 7/10 on analysis workbenches; 5/10 on Decision and Reports. Prefer information within view, but never compress real data into unreadable text.
- **Variance:** 5/10. Controlled, asymmetric 8:4 or 7:5 grids with clear reading order. Avoid repetitive equal card grids and oversize hero illustrations.
- **Motion:** 2/10. Static when idle; brief transitions only when a genuine navigation, filter, drawer, request, validation, or stage transition occurs.
- **Mood:** calm, authoritative, technical, approachable, bilingual; one primary action per immediate decision.
- **Opening hierarchy:** compact scope/freshness/context → three or four **measured** KPI cards → one **actual data** chart → clear review queue and approved next actions. No oversized greeting, avatar orbit, or faux agent heartbeat.

## 2. Color Palette & Roles
Use **one action accent** throughout. The status colors below are *semantic exceptions*, not alternative decorative accents. Preserve token values already in the working app; do not introduce a second incompatible palette by copying the Tailwind CDN theme from a Stitch HTML mockup.

| Descriptive name | Light hex | Role and implementation token |
| --- | --- | --- |
| Chalk Workspace | `#F3F5F6` | Application canvas, `--bg` |
| Document White | `#FFFFFF` | Core cards, reports, chart fields, `--surface` |
| Soft Data Shelf | `#F5F4F0` | Quiet nested surfaces, `--surface-sunken` |
| Slate Ink | `#24303B` | Major text and measured values, `--text` |
| Muted Slate | `#52616D` | Metadata, tooltips, explanations, `--text-muted` |
| Division Line | `#D7DDE1` | 1px passive separators, `--border` |
| Interaction Border | `#71808B` | Focusable inputs and visible controls, `--border-strong` |
| Deep Navigation Slate | `#163443` | Navigation background, not an additional CTA accent |
| Decision Navy | `#334E68` | **Sole action accent**: filled primary CTA, active selection and focus, `--accent` |
| Navy Wash | `#E9EEF1` | Active selection fill and subtle interactive backgrounds, `--accent-soft` |

**Status only:** Verifiably passed `#0F7A55`, caution/unknown `#8A6100`, confirmed failure `#B3323F`, with their corresponding existing soft background tokens. Never use green for a hypothetical benefit, red for a mere category, or blue to imply measured performance. Success means a returned and traceable success state, not an attractive color.

**Dark variant:** reuse existing `--bg: #20252B`, `--surface: #2A3038`, `--text: #EBEEF2`, `--text-muted: #B8C1CC`, `--accent: #9EBAD4`, `--border: #47515C`. Check contrast independently. Never use pure black, electric violet, neon cyan, glowing primary buttons, rainbow gradients or glass-card stacks.

## 3. Typography Rules
- **Primary:** the existing bundled **Dubai** typeface only where available and appropriately licensed for this application. If unavailable, keep the current vetted Arabic/English fallbacks `'Segoe UI', Tahoma, 'Noto Sans Arabic', system-ui, sans-serif`. Do **not** upload third-party font binaries, add a new CDN dependency, or imply government approval.
- **Display:** 32px/40px, 650–700 weight, for a report title when space permits. Never a page-height hero.
- **Section heading:** 24px/32px, 600 weight; subordinate section heading 17px/24px, 600.
- **Body:** 15–16px, 1.5 line-height English and approximately 1.65 Arabic. Narrative line length about 60–65ch.
- **Labels:** 13px/18px, 500–600; 12px only for secondary metadata that maintains readable contrast. Avoid tiny 9–10px dense mock labels.
- **Numbers:** 24–32px tabular figures in KPI cards; system monospace only for asset IDs, timestamps, exact numeric columns and code. Never drop currency code, unit, meaningful precision or negative sign to fit a card.
- **Arabic:** full RTL text direction from locale, logical spacing/alignment, **zero letter spacing** for Arabic script, readable long phrases, and `bdi` / `dir="auto"` for mixed identifiers. Do not reverse chronological or technical plot axes merely because the page is RTL.
- **Anti-patterns:** imported Inter from the mockups, dashboard serif typography, all-caps explanatory paragraphs, verbose headings and fabricated branded official seals.

## 4. Component Stylings
**Navigation.** Exactly three primary destinations: **Decision / القرار**, **Data & Analysis / البيانات والتحليل**, and **Reports & Outputs / التقارير والمخرجات**. Existing routes, bookmarks, browser history and secondary tools remain reachable in a contextual disclosure. Use the existing Miyaar mark and one consistent icon family.

**Primary buttons.** Decision Navy fill, white text, 8–10px radius, visible keyboard focus, at least 44×44px targets. Hover is a modest surface shift; press translates by no more than 1px. Secondary buttons are flat/outlined, never competing with the main action. No new autonomous actuation actions.

**Evidence-backed KPI.** Neutral surface, hairline border, 8–12px radius, one dominant figure and concise label, unit, period and status. Put formula, denominator, source, coverage, freshness, missingness, and criteria in an accessible native disclosure. Comparison arrows and targets appear **only** when validated by the backend. Show missing information as “Not available / غير متاح” or “Not assigned / غير معيّن”, not as zero.

**Charts.** Native React/SVG or the existing chart primitives backed by actual API aggregates, readable axes and legend, precise units, keyboard-accessible numeric table, drill-down and accessible descriptions. Keep the time axis LTR even within RTL. Mark descriptive, predictive and scenario series distinctly. A spectral FFT is allowed only if real waveforms and a verified calculation path exist; otherwise show no fabricated spectrum.

**Findings and decisions.** One clear actionable finding per row with severity only if grounded, provenance, explanation, source drill-down, approval state and next permitted action. “Suggested” must never be displayed as “approved”, “realized”, or “dispatched”.

**Agent collaboration.** Use actual recorded Hermes/stage events, never simulated RPC terminals. Show real started/failed/completed state, evidence and human handoff. An unavailable model should show an honest recoverable error, not fake generated text, confidence, green quorum or live dots.

**Reports.** On desktop, a quiet selected-report index sits beside the real document inspector. Selectable report tabs operate on the stored report sections and retain keyboard/ARIA relationships. Use readable bilingual sections and proof of actual approval only if the record supplies it; no invented signature, PDF/A-3 seal, hash or verified audit badge.

**Forms, loading and failures.** Persistent labels above inputs, inline explanations and errors beneath, visible focus rings. Skeletons match genuine pending component geometry and stop when the request resolves. No confetti, invented green “done” messages, or decorative progress bars. Empty states explain the next permitted upload/filter step.

## 5. Layout Principles and Three Screen Briefs
Use CSS Grid and existing logical properties. Keep content within a **1440px maximum canvas**, 24px desktop gutters, 16px tablet gutters, 12–16px phone spacing. Use 8px modular spacing with compact 4px substeps. Elevation is rare and functional: drawers and modal layers may cast shadows; ordinary KPI cards need only borders or section dividers.

### Decision / القرار
An executive **evidence-and-decision canvas**, not a permanently expanded glowing agent network. Compact context metadata, up to four source-backed KPIs and a legible chart sit in the opening. The next area is a split reading order: priority findings (wider) plus a real evidence/approval inspector (narrower). Agent collaboration is contextual and expandable, bound to a selected run and its actual events. All intervention actions are human approved; no direct DCS/SCADA dispatch.

### Data & Analysis / البيانات والتحليل
Technical analyst workbench. Compact dataset scope, status and mapping context; measured KPIs; a primary actual chart; related trend, diagnostic or distribution chart only where supported; searchable/filterable source table with explicit complete values. An evidence drawer can show the actual selected calculation, record provenance and quality checks. Use a desktop 8:4 chart/context split only when both data areas exist. Do not include fixed turbine vibration measurements, asset classifications or arbitrary alarm limits from the HTML examples.

### Reports & Outputs / التقارير والمخرجات
Professional review desk. On desktop use a **5:7 index/inspector layout**: report section list at the left and the genuine selected Markdown/document content at the right. Report metadata and publication state are taken from the stored run. Never treat an attractive document frame as a verified signed report. Keep actual download, print, evidence and human publication controls unchanged.

**Responsive:** at widths below **768px**, primary regions stack into a single reading column. Exception: the product's existing compact opening KPI *mini-grid* may retain **two columns at 320px or 390px** when all complete values and units visibly fit; otherwise stack. On 768–1023px, side inspectors collapse as needed. Full tables may scroll **inside their own labelled region**, but the page itself must never scroll horizontally. Drawers fit 100dvh and support Escape, focus trapping and focus return.

## 6. Motion & Interaction
The domain is consequential engineering. **No perpetual movement by default**, even though some generic Stitch design systems favor looping motion. A moving status indicator may exist only while a real request/event is in progress and must stop when complete or disconnected.

- Existing `--motion-fast: 140ms ease` and `--motion-medium: 220ms ease` govern navigation, drawer, selection and load transitions.
- Limit animation to GPU-friendly `transform` and short, non-obscuring opacity on nonessential surfaces; text never temporarily falls below contrast requirements.
- Do not animate a numeric KPI as if data were changing. Do not auto-generate “agent deliberation”, pulses, artificial logs or stage progress.
- Use reduced-motion and the user's saved motion preference as hard overrides. Keyboard and touch actions must respond synchronously with real state changes or explicit pending feedback.
- Preserve visible layout geometry while loading; avoid layout shift and oversized hero sequences.

## 7. Anti-Patterns (Never Do)
- **Never** present demonstration telemetry, synthetic test rows or Stitch placeholder numbers as live operations. Ban hard-coded “94.8% consensus”, “$1.42M realized savings”, “14/14 certified”, “100% deterministic validation”, “zero hallucinations” unless a real bounded source proves the **exact specific claim**.
- **Never** import the mocked `confirmDispatch()` browser alert as a real work-order/DCS action. No write-endpoint workaround, anonymous authority or simulated authenticated PIN.
- **Never** use an imaginary approver name, signature, timestamp, revision, lineaged hash, verified source count, or published state.
- **Never** label ISO or IEC “certified/compliant” because it is printed in a UI design. Version, asset applicability, licensed limits and verification are separately established.
- No chat-landing-page hero, enormous orb, orbiting avatars, decorative telemetry, faux live feed, or endless agent spin.
- No neon gradients, glowing outlines, glassmorphism, excessive shadows, washed-out gray data, serif UI, pure black, or a second decorative action color.
- No extra large equal-three-card feature grid, filler copy, random inspirational taglines, emojis in controls, or abstract images to replace engineering charts.
- No CDN Tailwind/Google Fonts transplant, inline `onclick`, static backend imitation, new global framework, uncontrolled API/model costs or new dependencies solely for styling.
- No graphical values without their true units and a table equivalent; no invented comparisons, owner assignments or savings.
- No hard-coded English-only screen; no reverse of a technical diagram or chronological time axis.
- No direct rebranding as an RTA or Dubai Government approved/endorsed product.

## 8. Google Stitch Generation Brief
**Generate exactly three visually related screen concepts from this DESIGN.md: Decision, Data & Analysis, Reports & Outputs.** Maintain one palette, one typographic hierarchy, existing Miyaar identity, consistent controls and understandable Arabic RTL equivalents. Use the three supplied HTML/screenshots as *composition references*, not as data or functionality to copy.

For every numerical field and activity log, render a visually neutral **“Data from connected run”** placeholder or clearly visible **“Illustrative design / تصور توضيحي”** state in mockups. Never attach fake verification labels to placeholders. Annotate where verified API data, permission checks, source evidence and human approval will connect; do not invent those endpoints.

Deliver paired desktop and mobile views with context → 4 KPIs → real-data-chart slot, source-evidence drill-down, and report index/inspector. Motion demonstrations must be optional, bounded, and tied to state. The generated output is a **design specification** until independently integrated and browser tested.

## 9. React Implementation and Acceptance Contract
Implementation stays in the existing React 19/TypeScript/Vite frontend and FastAPI backend. Reuse tokens, i18n packs, route parsing, `ExecutiveOverview`, `DashboardView`, `RunsView`, `ReportDocument`, `RunTimeline`, and existing authorization/report stores. Preserve Hermes Desktop work, Supabase/configuration, source datasets and database schemas. Do not import new APIs merely to match a Stitch screenshot.

Required pre-merge proof: same-dataset **before/after running application** screenshots in English and Arabic at 320px, 390px, tablet and desktop; keyboard/accessibility review against WCAG 2.2 AA; `python scripts/verify.py --quick` and `python scripts/verify.py --e2e` on the final SHA; existing unchanged JS/CSS bundle budgets; test of upload → mapping → analysis → chart → evidence → human review → saved report → reload → export; skipped checks and blockers explicitly disclosed. A passing design review alone is not a passing application test.

**Delivery state:** design policy for review. This file is neither evidence of UI deployment nor permission to merge or publish. Use a GitHub review branch and an explicitly approved release gate.
