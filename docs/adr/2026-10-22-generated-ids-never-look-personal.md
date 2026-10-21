# Generated ids never look like a person's number

Date: 2026-10-22 · Status: Accepted (found while testing every agent and model
path at the owner's request, 22 October)

## Context

Two full test runs on 21 and 22 October each had one Python failure that did
not repeat. Repeating `test_the_runtime_is_shown_notes_but_never_a_row`
reproduced it: 3 failures in 40 runs, every one with the assistant answering by
rules because "Personal data was detected". The test holds no personal data.

The engine's ids are 12 hexadecimal characters. About 1.5% contain a run of
digits the personal-data detector reads as a phone number (10 or more digits)
or an account number (12 or more), for example `28560517940e`. The
assistant's notes name the latest run by its id, and the privacy guard scans
those notes before any model or agent runtime sees them. So in about one
conversation in seventy the model and runtime were refused for no reason.

## Decision

`server.runs.random_id` draws again whenever an id contains 8 or more
consecutive digits, a margin below both patterns. The demo's fixed-id
generator applies the same rule. The detector and the privacy guard are
unchanged: they stay conservative, and the platform's own ids simply stop
resembling the data they guard against.

## Consequences

- No generated id trips the detector (0 of 20,000 sampled, against about 300
  before). Ids keep their length and format; existing stored ids are untouched.
- The demo keeps its run id `5fe5d44a8391`.
- Other identifiers (session ids, hashes) are not in the assistant's notes and
  are not changed here.

## Verification

`tests/test_runs.py` (`GeneratedIdsTestCase`): 5,000 ids, none trips the
detector, and the rule rejects the ids that used to trip it. The previously
flaky test passed 200 of 200 repeated runs.
