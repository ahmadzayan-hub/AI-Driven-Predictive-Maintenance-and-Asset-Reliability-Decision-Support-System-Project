---
name: dashboards
description: >-
  Analyse authorized data with the governed pipeline and build executive
  decision dashboards with traceable figures. Use for the Asset Reliability
  SaaS dashboard, KPI scorecards, Arabic RTL views, evidence-led dashboard
  redesigns, or a sourced standalone HTML export. Reuse real run APIs and the
  existing React design system; use hosted Claude artifacts only when that
  capability is actually available and requested.
---

# Dashboards

Build a dashboard that helps its reader decide what deserves attention and
shows the evidence behind that decision. The assistant can explain verified
results; calculations and authority remain in the governed server pipeline.

## Choose the delivery route

| User's outcome | Route |
| --- | --- |
| Develop or redesign this SaaS | Read [the SaaS workflow](references/saas-workflow.md), then extend the existing React views and run-scoped APIs. |
| Analyse a file and hand over a portable dashboard | Use the deterministic analysis and offline renderer below. |
| Create a Claude-hosted artifact | Check the capabilities exposed by the current session, then follow their returned instructions. Read the [research and integration boundaries](../../../docs/design/EXECUTIVE_DASHBOARD_RESEARCH.md). |

Claude Code skills are project instructions. The existing
`dashboard-analyst` development agent preloads this skill; that does not
register a new SaaS runtime agent or install an Artifact SDK. Product agent
behavior belongs in the existing server runtime/tool contracts and its tests.

## 1. Establish the decision and evidence

Record the reader, decision, selected run or input, period, population, unit,
comparison and output language. Use the task's current run selection and
available project context; ask only for information that blocks the work.

For every proposed card or chart, identify its source before drawing it:

- Run ID and calculation/KPI key, or a register reference for a file export.
- Formula, unit, population, numerator/denominator and missing-value policy.
- Data coverage and any failed checks, unavailable measures or limitations.
- A comparison only when both populations and periods are comparable.
- A proposed action and its actual supported next step. A recommendation
  remains advisory until the existing human approval workflow authorizes it.

Use ratios of sums rather than averages of row rates. Show record counts and
per-record comparisons when coverage differs. Missing or unmeasured data is
not a measured zero. Show a target, risk score, forecast or asset-health
indicator only when its definition and evidence exist.

## 2. SaaS implementation

Follow [references/saas-workflow.md](references/saas-workflow.md) for the API
map, executive hierarchy, English/Arabic behavior and acceptance checks.
Reuse `frontend/src/shared/api.ts`, its types, existing state and the
run's authorization boundary. Read the actual DTO before changing a view.

Use the current semantic tokens in
`frontend/src/shared/styles/tokens.css`, the project decisions in
`design-system/agentic-os/MASTER.md` and the dashboard page rules. Keep
charts as accessible SVG with a table of the same values. Preserve lazy
views and feature translation packs. The current bundle budget is enforced
by `scripts/verify.py`; measure it rather than copying an old budget figure.

The official Anthropic design skills are useful references for deliberate
hierarchy and critique. Their artifact scaffolding stack is for an isolated
prototype, not an instruction to replace this application's build system.
Do not introduce a CDN, font, chart library or runtime dependency without
the project's recorded reason and an actual budget check.

## 3. Deterministic analysis and offline handover

Run from the project root with the project Python environment. Replace the
example paths; put course/client input, aggregates and outputs in an
authorized directory outside the public repository.

```bash
python scripts/analyse.py path/to/data.xlsx --suggest --out path/to/review/analysis.json --csv-dir path/to/review/aggregates
python scripts/analyse.py path/to/data.csv --mapping path/to/mapping.json --goal "Which maintenance problem deserves review?" --language ar --out path/to/review/analysis.json
```

`--suggest` accepts the suggested mapping; inspect it before relying on it.
The CLI uses a deterministic gateway and exports calculations, sourced
claims, failed checks, chart data, headlines and prepared aggregates. It
does not send dataset rows to a model. Read the warnings and limitations
before choosing the figures. Aggregates can still be confidential.

```bash
python .claude/skills/dashboards/render.py --analysis path/to/review/analysis.json --write-spec path/to/review/spec.json --out path/to/review/dashboard.html
python .claude/skills/dashboards/render.py --spec path/to/review/spec.json --check
python .claude/skills/dashboards/render.py --spec path/to/review/spec.json --out path/to/review/dashboard.html
```

The existing renderer supports `kpis`, `bars`, `line`, `table` and `text`.
Every numeric section needs its source. It produces one offline HTML file
with SVG, source references, table equivalents, English/Arabic, themes and
print styles. The file is a snapshot; a live refresh claim needs a working
data path and observed refresh behavior.

## 4. Claude-hosted output, when available

Current Anthropic documentation describes Claude Code artifact publishing
and a hosted Dashboards beta. Availability depends on the signed-in
account, plan, organization settings and current surface. Check the actual
session's tools; use only their documented schemas. Do not assume a
Dashboard `type_url`, call an invented SDK or claim publishing succeeded
without a returned URL. When no publishing capability exists, hand over
the local file and its evidence instead.

A hosted artifact does not provide this SaaS's FastAPI backend, tenancy or
approval engine. Its published page cannot call this project's local MCP
server. Preserve those services in the application. External publishing
must be within the user's authorized scope; local implementation and
review do not require a new permission question.

## 5. Verification and handover

For an offline export:

```bash
python scripts/figures_check.py --register path/to/review/aggregates/calculations.csv --value-column value --label-columns ref,name --doc path/to/review/dashboard.html --reference path/to/review/analysis.json --reference path/to/review/aggregates/trend.csv --reference path/to/review/aggregates/by_group.csv --sourcing-only
```

Include only reference files the analysis actually produced. Inspect the
rendered page and its tables; a matching number alone does not prove a
correct denominator or population. For a submitted deliverable, apply the
existing `review-loop` gates. For a SaaS change, follow the verification
matrix in the SaaS workflow and report the commands that actually ran.

Return the implementation/output paths, selected run or source, decisions
supported, formulas and limitations, measured verification, and remaining
acceptance work. Never send raw rows to a model, expose credentials or
private course data, invent evidence, hide failed checks, or turn an
association into a causal finding.
