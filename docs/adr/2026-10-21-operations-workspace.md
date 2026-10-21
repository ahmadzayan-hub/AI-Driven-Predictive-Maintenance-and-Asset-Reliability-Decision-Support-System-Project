# An operations workspace for authorized maintenance and prospective validation

Date: 2026-10-21

Status: accepted

## Context

The [competitive assessment](../assessments/2026-10-21-saas-competitive-benchmark.md) found a missing connection between a reviewed analytical finding, authorized maintenance, and a recorded outcome. The owner asked to implement the assessment's remediations, retaining professional, restrained animation and equal English/Arabic support.

## Decision

Add a lazy `#/operations` workspace, placed first in the existing navigation and on the phone shortcut bar. Keep the assistant as the initial route and preserve all existing analytics views. The workspace uses the real organization, membership, site, asset, work-order, readiness and prospective-validation APIs; it contains no demonstration records or simulated communications.

The workflow is an evidence-linked draft, an explicit maintenance authorization, work in progress, and a recorded outcome with labor and parts. Report publication and maintenance authorization remain separate decisions. Authorization displays the saved assignment, priority and due date. Unsaved scheduling changes must be saved first; changes after authorization require a new decision. Technicians see progression controls only for their assigned work. The server remains authoritative for every permission and transition.

Requests carry idempotency identifiers and expected versions. An uncertain response never triggers an automatic mutation retry. Version conflicts tell the reader to refresh and review before submitting again. Form input stays in memory while switching sections; switching organization, signing out or reloading discards it. No operational payload is saved in persistent browser storage or an offline mutation queue. Authorization loss removes previously displayed organization data on refresh.

Organization JSON imports require an explicit file selection, a bounded preview and a separate import action. Exports are organization-scoped records for review and interoperability, not a claim of external CMMS synchronization. A truncated work queue discloses its scope and links recovery to the full export. Readiness displays observed configuration and records, with a visible missing-worker message; it is not a release or commercial-readiness score.

Prospective validation is a second lazy child, fetched when that section is first opened. Protocols are fixed before server-timestamped predictions. The interface requires model and baseline probabilities, preserves missing metrics as unmeasured, and displays denominators and descriptive intervals. Outcome recording requires source evidence and an explicit final-adjudication acknowledgement; backend chronology checks remain decisive. Neither a repair outcome nor a validation score proves causal financial savings.

All messages ship in typed English/Arabic feature packs. Existing tokens, native controls, explicit labels, RTL layout and reduced-motion settings apply. The only ongoing animation represents a pending request; no graph or animation dependency is added. The extra operations and validation chunks justify a measured aggregate interface allowance while preserving initial-load, largest-chunk and font ceilings; final measurements and the reviewed allowance are maintained with the verifier and UI plan.

## Validation and limits

Component journeys cover evidence-linked creation, explicit authorization, completion, Arabic transport, role-specific controls, uncertain-response retries, version conflicts, import preview and prospective registration/adjudication. Browser journeys run the real local backend in both languages on desktop and phone, checking persisted state, independent publication approval, chronological validation registration, accessibility and overflow. Exact executed results belong in README's testing record.

These checks establish local implementation behavior. They do not establish hosted recovery, independent field predictive accuracy, vendor write-back, technician offline synchronization, paying-customer outcomes or production readiness. Integration and trial evidence must be collected in an authorized pilot.

The reviewed aggregate allowances are 205 KB gzipped JavaScript and 25 KB CSS. The final feature build measured 202.9 KB and 24.3 KB; initial JavaScript remained 98.7 KB against 100 KB, largest lazy chunk 18.1 KB against 30 KB, initial CSS 10.0 KB against 10 KB, and fonts 119.4 KB against 120 KB. The extra allowance covers lazy operations/validation workflows; it does not relax the initial-load, per-chunk or font ceilings.
