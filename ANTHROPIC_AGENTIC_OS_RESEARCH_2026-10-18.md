# Anthropic research for the Agentic OS implementation prompt

Researched: 2026-10-18. Only official Anthropic engineering articles and Claude Code documentation informed the external recommendations below. Documentation is rolling: implementation must check the installed Claude Code version and actual capabilities. This note is advice, not evidence that the project implements a feature.

## Interpretation of the owner's image

The image names five disciplines: Prompt Engineering, Vibe Coding, Context Engineering, Loop Engineering and Harness Engineering. Its operating layer includes plugins, agents, skills/templates/scripts, commands, MCP/tools, memory/session logs/project progress and local/API/subscription model access. It also names an Agentic Knowledge OS.

Use that as the owner's organizing taxonomy. It is not an official Anthropic product architecture. In this project, loop engineering means the bounded action/observation/evaluation cycle; harness engineering means the environment, tools, state, permissions and verification machinery around that cycle. Vibe coding means rapid exploratory iteration that must pass the same implementation gates.

## Findings and application

| Source | Relevant guidance | Application here |
| --- | --- | --- |
| [Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps), 24 March 2026 | Separate construction from evaluation; define assessable criteria; inspect behavior in a browser. The later experiments remove scaffolding when it ceases to help. | Reuse the main implementer and existing independent reviewers. Measure added orchestration and remove unnecessary coordination. Do not mandate a fixed population of agents or periodic context resets. |
| [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents), 26 November 2025 | Persistent feature records, environment setup, incremental work and clear handoffs support progress across sessions. | Reuse the board/logs; add a small machine-readable task ledger and reproducible startup/verification only where missing. Preserve failed and incomplete items honestly. |
| [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents), 29 September 2025 | Select relevant context, retrieve detail when needed, and preserve essential state through notes and compaction. | Keep core instructions short. Load task-specific skills, ADRs and evidence by reference. Keep durable knowledge distinct from transient run state. |
| [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents), 19 December 2024 | Choose predictable workflows for defined work and flexible agents where adaptation is needed. Complexity introduces cost and latency. | Preserve deterministic computation and governance. Add a bounded planner for genuinely multi-step assistance. The older article is conceptual guidance, not a mandate to adopt its historical tooling. |
| [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents), 9 January 2026 | Evaluate outcomes and execution traces; use suitable graders and inspect failures. | Extend existing synthetic suites with complete user journeys, failure recovery and independent review. Preserve unseen cases and report variation for stochastic runs. |
| [Claude Code best practices](https://code.claude.com/docs/en/best-practices) | Give work a verifiable outcome, scope investigations and use session/context controls deliberately. | Each feature has acceptance checks, concrete evidence and a handoff. A screenshot alone does not validate persistence or authorization. |
| [Skills](https://code.claude.com/docs/en/skills) | Skills support on-demand procedures and slash-command invocation; existing custom commands remain supported. | Prefer project skills for new workflows and reuse current commands. Avoid duplicate definitions or collisions with built-ins. |
| [Subagents](https://code.claude.com/docs/en/sub-agents) | Specialized definitions separate context, instructions and tool permissions. | Keep reviewers narrow and read-only. Inspect actual installed support for loading and delegation rather than relying on old repository statements. |
| [Plugins overview](https://code.claude.com/docs/en/plugins) | Plugins package components for installation/loading; standalone skills, agents, hooks and MCP servers also work without them. | Inventory plugins and verify loading. A nested folder is not evidence of activation. Package only when reuse benefits from it. |
| [Hooks](https://code.claude.com/docs/en/hooks-guide) | Lifecycle automation can execute repeatable checks; Stop hooks need protection against recursive continuation. | Test Windows/Linux interpreter resolution, hook inputs, timeouts and bounded stop behavior. Keep authoritative SaaS security checks in server code. |
| [Memory](https://code.claude.com/docs/en/memory) | Project instructions and learned memory have different roles; instruction text is not enforced configuration. | Keep CLAUDE.md authoritative here, preserve the cross-agent agreement with AGENTS.md, and use the existing brain and memory files deliberately. Enforce permissions in tooling/server controls. |
| [MCP](https://code.claude.com/docs/en/mcp) | Tool connections have configuration, scopes and authentication requirements. | Use minimal approved connectors, document data boundaries, and verify tool discovery without exposing credentials. |
| [Costs](https://code.claude.com/docs/en/costs) | Usage depends on model, context, tools and billing setup. | Keep local-model, server-API and developer-subscription configuration distinct; record actual usage where available and do not assume a subscription includes SaaS API capacity. |

## Existing project mismatch to investigate

`.claude/plugins/README.md` describes a plugin nested inside `.claude/skills/` and claims automatic loading. Current official documentation describes explicit installation or local plugin loading and distinguishes standalone skills from packaged plugins. Correct the instructions after checking the installed CLI. Do not replace a documentation claim with another untested activation claim.

## Research boundaries

No model quality, price, hosting availability or installation was tested. No external agent service, plugin or SDK was installed. This research does not authorize production changes or sending repository/customer data to a provider. The companion prompt turns the recommendations into project-specific acceptance checks.
