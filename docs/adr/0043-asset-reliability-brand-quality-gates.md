# ADR 0043: Distinctive brand integration with explicit agent-evidence gates

Date: 2026-10-18. Status: proposed for review.

## Context
The default shell used a placeholder letter A. The maintenance prototype is intentionally fictional. Agent evaluations exist but were not an explicit named CI step, so it was easy to mistake a successful preview build for general agent quality.

## Decision
Introduce a small original SVG identity inspired by the generated railway/AI artwork and deploy it in the shell and maintenance prototype without introducing new packages, mock outcomes or production asset claims. Maintain bilingual labels already present. Use the project tokens, motion reduction support and accessible navigation.

Add the deterministic classifying-agent evaluation command to CI. This checks the labelled synthetic suites and their declared recall floors, but is not a live-provider evaluation or validation of every individual specialist stage.

## Consequences
- SVG vector graphics remain lightweight, scalable, cacheable, and do not distort mobile/tablet layouts.
- The repository README can show a trustworthy identity without presenting fictitious dashboards as a running product.
- A successful test suite establishes its bounded test contract, not field reliability, savings, causal identification or production readiness.
- No new platform routes, data flows, LLM permissions or implicit deployments are introduced; GitHub/Vercel previews still build on branch pushes.
