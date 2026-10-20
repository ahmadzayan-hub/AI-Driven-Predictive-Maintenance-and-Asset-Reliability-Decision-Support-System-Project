# Run requests allow the bounded local model step to finish

Date: 2026-10-21 · Status: Accepted

## Reproduced failure

The local sample analysis displayed the bilingual server-timeout error during
narration. `advanceRun` inherited the generic ten-second request deadline,
although the configured model gateway can wait sixty seconds. Aborting the
browser request did not cancel the server's stage. A manual retry found that
stage completed and resumed the pipeline, demonstrating an uncertain client
outcome rather than a failed calculation.

## Decision

Use a bounded ninety-second transport deadline for advancing a run, reading
its detail, pause/resume/cancel, and approval decisions. These operations
serialize behind the active stage (ADR 2026-10-20-atomic-run-operations), so
even a read or control can legitimately wait for narration. The extra time
allows the sixty-second inference window plus commit and response overhead.
Keep the generic ten-second deadline and existing upload/chat/voice limits.

Keep the existing single run scheduler, uncertain-outcome read reconciliation,
and human publication gate. Do not automatically replay failed POSTs or extend
the model's inference limit. This change adds no dependency or new UI text;
the existing English/Arabic error remains for a genuinely unresponsive server.

## Verification and boundaries

Fake-clock API regressions reproduce the old premature abort, accept a response
after sixty-five seconds, retain the ninety-second upper bound without replay,
and preserve the short health timeout. Existing scheduler tests cover duplicate
submissions and uncertain-decision reconciliation. Build, budget and actual
local browser-run results are recorded in README.md under Testing.

This corrects the local client's deadline mismatch. It does not increase a
hosting provider's function limit or establish capacity under multiple queued
model requests. Those require separate deployment and execution changes.
