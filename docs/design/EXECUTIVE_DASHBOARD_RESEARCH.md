# Executive dashboards and Claude integration

Reviewed 19 October 2026 for Asset Reliability / موثوقية الأصول and
Miyaar / معيار. This records the development integration; no hosted
artifact, paid account, connector or production service was activated.

## What can be integrated

| Capability | Appropriate project use | Boundary |
| --- | --- | --- |
| Claude Code project skill | The existing `/dashboards` workflow now covers executive SaaS views and sourced file exports. | Instructions for development, not application runtime code. |
| Claude Code subagent | `dashboard-analyst` now preloads `dashboards` and follows the project's APIs, RTL and evidence checks. | Its tool permissions and model selection remain explicit in the agent file. |
| Claude Code artifact | Optional review/export page when the session actually supports publishing. | Hosted delivery does not supply FastAPI, product tenancy or approval services. |
| Claude Dashboards template | Optional account-hosted dashboard work where the beta is enabled. | Account/plan/admin settings apply; it is not a package installed into this SaaS. |
| Anthropic design skills | References for purposeful hierarchy, visual critique and an isolated artifact prototype. | Their scaffolding stack does not override this application's design system or build constraints. |

Project skills live in `.claude/skills/`; Claude Code can invoke
`/dashboards`. Subagent frontmatter can preload a project skill using
`skills`, which is now set on the existing analyst. Other coding harnesses
can read these Markdown files without claiming Claude Code activation.
[Skills documentation](https://code.claude.com/docs/en/skills),
[subagent documentation](https://code.claude.com/docs/en/sub-agents).

Anthropic describes Claude Code artifacts as hosted pages with no backend.
Their publishing capability depends on the session; local MCP servers can
help prepare a page but are unavailable to its published runtime. Our
integration therefore keeps the SaaS application separate and detects the
actual publishing tools instead of assuming a tool schema.
[Claude Code artifacts](https://code.claude.com/docs/en/artifacts).

The Dashboards template is a hosted beta on eligible paid plans, subject
to capabilities and organization settings. Researching it does not enable
it for this account. [Artifact and template availability](https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them).

## Adopted design practice

Anthropic's frontend design guidance emphasizes subject-specific decisions,
intentional hierarchy and screenshot-based critique. For this industrial
decision workspace, that means a readable operating picture, evidence and
next actions using the approved Miyaar tokens, rather than a generic
marketing hero. [Official frontend design skill](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md).

The official artifact builder scaffolds React 18, Tailwind, shadcn and
Parcel. Those choices can serve an isolated prototype, but the existing
SaaS uses React 19, CSS tokens, lazy views and SVG charts. Its workflow was
reviewed as a reference; its scripts were not run in this repository.
[Official web artifact builder](https://github.com/anthropics/skills/blob/main/skills/web-artifacts-builder/SKILL.md).

## Concrete repository integration

- `.claude/skills/dashboards/SKILL.md`: delivery-route selection,
  evidence-first planning, deterministic export, hosted capability checks
  and verification.
- `.claude/skills/dashboards/references/saas-workflow.md`: code-grounded
  API map, measure/filter semantics, executive layout, RTL and acceptance.
- `.claude/agents/dashboard-analyst.md`: preloaded project skill and a
  consistent implementation/review handoff.

The existing application contracts are the implementation base:
`frontend/src/shared/api.ts`, `types.ts`, `server/app.py`,
`server/maintenance/kpis.py` and the query DSL. The executive endpoint
`/api/runs/{id}/executive` computes filtered measures and separates them
from whole-run findings/model evaluation. The older `/kpis` endpoint stays
run-wide. Preserve those scopes and the source evidence in every view.

An executive view should establish the selected run, period, population,
freshness and approval state; show a small set of supported measures; then
show the driver breakdown, limitation and next action. Each value keeps
its formula, unit, coverage and evidence path. Stable asset identity and
prediction-time inputs are required before adding asset-history, risk or
remaining-life claims.

Arabic and English carry the same information and interactions. Logical
layout properties, readable mixed-direction IDs/numbers, chart tables,
keyboard focus, responsive behavior, dark/light modes and reduced motion
are acceptance requirements. Current design tokens and the verifier's
bundle gates govern production code.

## How to invoke it

In a Claude Code session opened at this repository, use the existing
command with a real run or an authorized file. These are example requests,
not evidence of an executed dashboard:

```text
/dashboards Redesign the executive view for the selected run. Use its real
KPI register and evidence. Show unavailable measures and coverage. Support
English and Arabic RTL, retain human approvals, and verify the UI budget.
```

```text
/dashboards طوّر لوحة تنفيذية للتشغيل المحدد من مؤشراته الفعلية. وضّح
الفترة والفئة المقاسة والبيانات غير المتاحة، واربط الأرقام بأدلتها.
ادعم العربية من اليمين إلى اليسار والإنجليزية، وحافظ على موافقات الإنسان.
```

For a portable file, the skill uses `scripts/analyse.py` and the existing
offline `render.py`. When a hosted artifact is explicitly requested and
available, use the current tool's documented publishing instructions and
record its actual returned link. Keep course/client content private and
never place dataset rows or credentials in prompts, bundles or artifacts.

Changed calculations/API behavior need their own ADR and meaningful
synthetic tests. A skill/agent file alone does not make an executive
dashboard or a product superagent implemented. Current test results and
release acceptance remain in [README — Testing](../../README.md#testing).
