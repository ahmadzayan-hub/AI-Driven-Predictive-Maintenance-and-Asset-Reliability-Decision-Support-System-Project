# Isolate browser fixtures and budget complete sequential journeys

Date: 2026-10-21

Status: accepted

## Context

The full assessment verification exposed shared-memory assumptions between the
desktop and mobile Playwright projects. An interrupted earlier journey left
records behind: the assistant's static text selected two notes, and the session
journey counted unrelated notes as its own fixtures.

Retained traces also showed complete, sequential journeys exhausting the default
30-second test deadline while their individual assertions were succeeding. The
workspace reached approval at 29.84 seconds before its final accessibility audit;
the join journey reached approval at 32.08 seconds and started its download at
32.54 seconds; the screenshot sequence started its second-language analysis at
30.28 seconds. These observations identify a cumulative harness deadline, not a
measured server outage or permission to relax product responsiveness targets.

## Decision

Bind assistant and session-journey memory assertions to unique fixture text and
the exact keys returned by their own save requests. Continue checking creation,
declined deletion, category visibility, editing, deletion and the unchanged
surviving record. The Arabic audit uses project-specific fixture text. Tests must
not pass by selecting the first ambiguous record or by weakening expected counts.
The workspace approval journey likewise identifies its uniquely named run and
exact approval card, so an earlier interrupted run cannot satisfy or ambiguate
its keyboard-publication assertion.

The phone navigation check names all five approved shortcuts and verifies that
Operations opens directly, while Overview and Memory remain reachable through
More with focus returned to its trigger. This follows the Operations workspace
decision; waiting longer for a removed Overview shortcut would not fix it.

Give only the affected compound journeys an explicit total budget: 120 seconds
for comprehensive English/Arabic view audits, 60 seconds for the six-page
dashboard audit and session lifecycle, and 90 seconds for the assistant,
workspace, Arabic cockpit, joined-data download and desktop screenshot
sequences. The global default, individual
assertion limits, accessibility rules, geometry checks and publication checks
remain unchanged. Screenshot-only mobile coverage retains its existing budget.
After isolation was repaired, focused traces showed the assistant reaching its
saved-record assertion at 29.47 seconds after a successful pipeline, and the
session lifecycle reaching its final assertions at 36.52 seconds. Those two
complete journeys therefore also receive scoped cumulative budgets; the exact
fixture assertions remain intact.

## Validation and limits

Rerun the complete browser suite after these changes; report actual outcomes in
README's testing record. The local review wrapper has a separate process budget
for the complete Python, unit, build and browser run on Windows. Neither that
wrapper nor these journey budgets establish a hosted latency objective. Runtime
performance and customer task timing still require representative measurements.
