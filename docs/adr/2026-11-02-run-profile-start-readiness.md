# Run creation waits for profile metadata to settle

Date: 2026-11-02

## Evidence

After PR81 merged, the macOS WebKit phone job in run `41446105867` timed
out in the late-start-response journey. The retained trace shows an enabled
Start run button at input time, then a newly inserted Pipeline profile field
in the post-click snapshot. No POST `/api/runs` occurred. The test waited for
a creation response that never began; this was not slow backend processing.
The same source tree had passed the preceding platform run, so the failure
depends on metadata arrival timing.

## Decision

Keep Start run disabled and busy while the optional profile request is pending.
Guard direct form submission too. Enable it only after the result or failure
has settled, when insertion of the profile picker is complete. An older server
without this optional endpoint retains the existing default-profile fallback.
The existing bounded request timeout applies; do not add retries or silently
change the selected profile, dataset or goal.

## Verification

Component regressions hold the metadata promise and exercise both success and
failure. The real browser late-response journey now also holds profile metadata,
checks that submission is disabled, releases metadata, and then exercises its
original delayed creation response, destination preservation and durable run.
Keep the original browser timeout and assertions. No production state changes.
