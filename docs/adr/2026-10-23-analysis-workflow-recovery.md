# Analysis workflow recovery and human-review guidance

Date: 2026-10-23. Status: proposed for review.

## Problem

The existing React analysis view treated a failed dataset-list request as an
empty list and silently hid a failed run-history request. A user could mistake
an unavailable service for missing work. The publication gate correctly required
opening the exact report and confirming it was read, but disabled controls did
not explain that sequence.

## Decision

Keep the existing React views, shared run store, APIs, Hermes pipeline and
artifact-bound publication gate. Distinguish loading, successful empty results
and failed list reads. Offer explicit read-only retries, retain the question,
selected dataset and last successfully loaded rows, and describe retained rows
as potentially stale after an error. Do not retry creation or publication.

Keep demo mode view-only and explain it with the existing translated notice.
Show failed attempts to open a run even when the creation form is hidden.
Retain a stored-dataset navigation preset as a selectable reference when it is
absent from a later list; the server still validates it when starting a run.

Explain the next required review step next to the exact report, in English and
Arabic, and associate that guidance with the confirmation checkbox and publish
button. Opening or reading a report never publishes it. Server confirmation
remains authoritative; changed artifact versions still reset consent.

## Verification and limits

Regression coverage exercises loading versus empty versus failed reads, GET-only
retries, retained questions and presets, stale run history, read-only demo errors,
and the existing report-read consent gate. Browser regressions exercise both
languages, keyboard retry, narrow-screen overflow and automated accessibility.
Execution results must be reported separately; committing tests is not proof
that the browser or hosted deployment passed them.

No backend, schema, model provider, credentials, deployment settings, dependency
or product source changes. Hosted identity and database readiness are not solved
by this interface work. This patch neither enables a provider nor approves a
production release. Roll back with a new revert commit rather than rewriting
history. Existing public course assets remain untouched.
