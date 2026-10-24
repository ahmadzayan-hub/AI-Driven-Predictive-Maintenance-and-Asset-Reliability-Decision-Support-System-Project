# KPI cards expose review context without inventing metadata

Date: 2026-10-24. Status: local candidate on main 99ca49ab; not published or deployed.

## Context

The owner asked to adapt supplied dashboard references while ensuring each number has evidence, an insight and an accountable action owner. The executive cards already expose a controlled formula, measured coverage and assessment. The current RunExecutive contract supplies a run identity, selected-scope snapshot and analysis update, but no independently declared reporting window, observation-freshness policy or verified per-KPI review assignment. Advisory owner strings describe proposed roles, not assignments.

## Decision

- Extend the existing KPI card and its evidence disclosure; do not replace the dashboard or change API/schema, authentication, model rules, fonts or dependencies.
- Display an explicit period/owner/freshness limitation beside each value. Within evidence, show source dataset/run and the exact filtered evidence reference while retaining the existing analysis-update header. Never rename that timestamp as observation freshness.
- Ask who reviews this specific metric without offering a fake save. This read-only view creates no assignment or maintenance authority. Source-bound clarification persistence remains a separate backend contract.
- Reuse existing evidence navigation and focus handling for the matching filtered `executive.kpi.{key}` register entry. Do not link unrelated or whole-run evidence as that metric. The existing open-analysis action remains available when a matching entry is absent.
- Route rendered numeric values and meters through a finite-value guard. Null, undefined, NaN and infinities remain unavailable; a measured zero remains zero. Preserve governed assessment reasons, currency semantics, coverage and missing-data policy.
- Use existing Dubai/theme tokens, bilingual copy and native disclosures; add no motion. On small phones use one KPI column and wrapping action controls.

## Verification and limits

Frontend component/i18n tests, full frontend tests, typecheck, build and interface budget are checked; exact counts belong in README Testing. The browser launch was blocked by the execution sandbox before page navigation, and escalation also failed at sandbox setup. No screenshot, rendered contrast, responsive-browser or hosted acceptance is claimed. Full Python/brain verification was not run in this frontend-only materialization. No production data, API write, release amendment or public repository write was performed.
