---
type: concept
aliases: [Design system v2, UI design system, ui-ux-pro-max]
tags: [interface, design]
status: active
updated: 2026-10-22
review_every_days: 30
sources: [frontend/src/tests/charts.test.tsx, docs/adr/0023-the-analytics-workspace-interface.md, docs/adr/0028-views-load-on-demand.md, docs/UI_PLAN.md, design-system/agentic-os/MASTER.md, frontend/src/shared/styles/tokens.css, .claude/skills/ui-ux-pro-max/PROVENANCE.md, .claude/skills/design/PROVENANCE.md, docs/design/REACT_AGENT_CONNECTIONS_STUDY.md, docs/design/README_ASSETS.md]
---

# Design system

How the interface of [[Agentic OS]] looks and behaves, and where those choices come from. It turns the [[Analytics OS roadmap]] into screens a reader in either language can use.

## Facts

- Generated on 2026-10-16 by the vendored `ui-ux-pro-max` skill (MIT, commit `56ea9cf`) and kept in `design-system/agentic-os/MASTER.md`. The file's *Agentic OS decisions* section overrides the generated values (ADR 0023).
- The Miyaar brand/actions use teal tokens; performance meanings are independent (the 20 October performance-color decision): red bad, blue okay, green good, neutral unassessed/unavailable, always accompanied by words. Targets require a named source and controlled units, following [[Weighted KPIs]]. Amber remains attention such as the [[Approval gate]]. Small semantic text is checked against card backgrounds at 4.5:1 in light, dark and system-dark modes.
- Type: Fira Sans for text and Fira Code for figures, bundled from `@fontsource` (OFL-1.1, Latin only, about 119 KB in five WOFF2 files). Arabic keeps the system stack, because Fira has no Arabic letters.
- Charts stay hand-drawn SVG: bars from a zero line, a marked forecast boundary, and a table of the numbers under each chart. Figures follow [[Weighted KPIs]]. Four of those conventions are held by tests as of 20 October, in `frontend/src/tests/charts.test.tsx`: a value scale that keeps zero, one scale per chart, a mark coloured by its datum rather than its row, and no chart on the dashboard outside a `Figure` carrying its table. Each was watched failing against a deliberate violation before it was kept.
- Navigation: the sidebar groups *Analyse* (Overview, Datasets, Runs) and *Work with* (Workspace, Memory, Activity). A phone's bar holds five places, the last being *More*.
- Budgets are enforced by `scripts/verify.py` and documented in `docs/UI_PLAN.md`; current measurements live in README. The 20 October collaboration decision adds a lazy workflow diagram and inspector, preserving initial-load, chunk and font ceilings.
- Agent motion follows the [[User]] preference for professional restraint: brief observed-stage highlights, clear status words, expandable handoffs/evidence and a pause-view control. The [[Hermes orchestrator]] still sequences stages; the view does not invent message transcripts. System and app reduced motion, interruption and document visibility suppress animation. `docs/design/AGENT_COLLABORATION_MOTION.md` records the study.
- Phases 0 and 1 of `docs/UI_PLAN.md` shipped in `dea3b38`; the [[Analytics OS roadmap]] records the later implemented dataset, model and live-data milestones and their remaining acceptance work.
- Six more skills from the same upstream repository were vendored in `b478983`: design-system, brand, ui-styling, design, banner-design and slides. For the app only ui-ux-pro-max and design-system's token rules apply. ui-styling's shadcn/Tailwind and slides' CDN Chart.js break ADR 0023, and design's logo, identity and icon generators call third-party image services.

## How to use it

Performance values use compact outlined text badges and a wrapping five-state
legend across executive, asset, overview, general dashboard and operations
views. Counts without targets stay neutral; absent measurements say unavailable.
The presentation decision is `docs/adr/2026-10-21-performance-status-presentation.md`.

Read the master file, then ask the skill one focused question with `python3 .claude/skills/ui-ux-pro-max/scripts/search.py "<concern>" --domain ux`. Its advice never overrides [[Soul]]: no third-party requests, no fabricated screenshots, and every string in English and Arabic.

## React graph exploration

The 21 October study in `docs/design/REACT_AGENT_CONNECTIONS_STUDY.md` keeps the existing React/SVG approach for [[Agent collaboration]] and proposes an optional React Flow explorer only when canvas navigation earns its measured cost. Motion is an optional animation tool, not a graph or communication service. The study includes reproducible synthetic build comparisons; production dependencies and the current CSS-motion decision are unchanged.

The connected workspace implementation adds bounded SVG zoom and a stage
inspector without another library. The operations asset inspector reads actual
work history, evidence and completion records; criticality stays separate from
condition. `docs/adr/2026-10-21-connected-agent-workspace.md` records the
responsive behavior and the explicit allocation for lazy-view assets.

The 22 October Arabic report decision applies the [[House style]] only to analysis
output surfaces. A bounded semantic Markdown renderer supports Arabic tables,
numeric isolation and inert untrusted markup. Report language is explicit at
creation and stays fixed independently of the interface language. Calculation
display translations preserve the audited values and identifiers; the source is
`docs/adr/2026-10-22-arabic-rendered-analysis-reports.md`.

## Related

The 22 October repository presentation uses GitHub-native Markdown, a short
product journey and expandable technical/verification references. Original
concept artwork is labelled separately from actual synthetic-session UI
captures, following [[Soul]] and [[Evidence and claims]].
`docs/design/README_ASSETS.md` records provenance and scoped checks; this
documentation redesign does not change the application or certify its CI.

- [[Home]]
- [[Identity]], whose two languages the interface serves equally.
- [[Decision log]], for ADR 0023 and the ADR 0018 accessibility bar it keeps.
- [[House style]]: the look of the agents' outputs, kept separate from the interface.
- [[Accessible motion]]: defines the controls and limits for workflow animation.
- [[Business report exports]]: preserves scope and evidence in portable reports.
