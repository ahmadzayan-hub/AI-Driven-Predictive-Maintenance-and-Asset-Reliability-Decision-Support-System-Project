# Task-first Miyaar interface

Date: 2026-10-23. Status: source implementation; hosted/runtime acceptance separate.

## Decision

Keep React, TypeScript, existing routes, managed authentication and backend contracts.
Use Miyaar / معيار as the compact shell identity; retain the full product title.
Separate the visible read-only demo notice from the crowded header. The notice is
not a readiness indicator, and demo writes remain forbidden.

A phone has Home, Data, Analyses, Review and More. All existing authorized routes
remain in the drawer. Home leads with one action bound to the selected run ID:
oldest report awaiting review, then active work, then a failed/partial result,
otherwise upload. A demo can inspect its sample, never initiate a write.
The upload, quality, analysis and report sequence describes navigation, not
completed checks. No generic chat action is presented as report-bound discussion.
The existing RMD evidence-specific discussion path is preserved.

Execution, evidence checks, approval and publication are separate states. A run
may finish all non-publish stages while awaiting human review. Existing finished
counts include partially completed runs and are labelled accordingly. Totals,
optional exports and other workflows are native disclosures. KPI performance
legends are collapsed but keyboard-accessible. Measured KPI assessments retain
all existing status and evidence meanings; counts gain no performance verdict.

## Verification and limits

Unit coverage exercises empty, pending, failed, partial, review and completed
states, unknown-versus-zero data, exact-run handoff and read-only mode. The native
legend retains bilingual explanations. Existing phone navigation expectations
are updated and synthetic responsive coverage captures both languages, narrow
portraits, keyboard disclosure and reflow. Browser execution and hosted evidence
must be recorded separately; neither a build nor fixture proves production ready.
No dependency, provider, authentication, source alias or database changes.

## Number ownership follow-up

Workspace counts expose their source endpoint and source-as-of limit, and link
to the corresponding review, dataset or analysis list. No target or assigned
owner is fabricated. Rich metric clarification is a separate contract: the
existing KPI policy endpoint changes display policy, not per-number ownership.
Do not fake a saved assignment or send metric-specific questions to generic
latest-report chat. Broad KPI ownership and clarification acceptance remain open.

## Dubai Style naming

The owner approved the name **Dubai Style** for the next executive-report
presentation preset. It describes an engineering/executive visual approach using
owned design tokens, not official government affiliation, certification or an
RTA-branded product. No restricted logo, licensed font, invented target or implied
authority is introduced. Actual/target/forecast distinctions, units, reporting
period, evidence and owner provenance take precedence over decoration. This wave
records the naming decision; a complete selectable report preset is not shipped
or claimed here and belongs to the separately tested report-format wave.
