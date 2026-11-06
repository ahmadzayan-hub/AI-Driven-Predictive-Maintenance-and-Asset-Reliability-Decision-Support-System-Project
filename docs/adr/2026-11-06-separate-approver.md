# Separate approver for analyses

Date: 2026-11-06 · Status: Accepted · Owner brief, Phase 3: separate permissions for analysing, publishing and authorizing; nothing approves its own work

## What was already true

AI never holds an approval:

- Model-driven specialist tools are refused any grant that includes publish, approve, delete
  or shell (`server/tools.py`).
- The conversational tools can start a run and read its status, but have no approval tool.
- MCP publishing waits for a person (`server/mcp.py`).
- Publication approval needs the `approve` permission. It binds to the report's content hash
  and is refused when the destination changed.

The gap: the `analyst` and `owner` roles carry both `write` and `approve`. The person who
started an analysis could approve their own report.

## Decision

A setting, `AGENTIC_OS_SEPARATE_APPROVER` (off by default), separates the duties. When on:

- Approving a run's publication by the run's own starter is refused with 403, code
  `self_approval`, in the report's language. Nothing changes: the approval stays pending and
  nothing is published.
- Approving an executive export (`/api/runs/{id}/executive/reviews`, decision `approved`) is
  refused the same way.
- An approval with no named approver is refused.
- The starter may still reject: stopping one's own report is never blocked.

It is off by default, so a one-person workspace and every existing deployment behave as
before. Turning it on is the operator's decision.

## Limits

- Runs are private to their owner. Today the only other person who can reach a run is a
  platform administrator (`admin`). A workspace reviewer role, so a colleague in the same
  organisation can approve, needs a tenancy decision and is not built.
- The rule compares account subjects. One person with two accounts is not detected.
- Motion script approval (`/api/motion/jobs/{id}/script-approval`) and the RMD evidence-pack
  workflow keep their own rules and are not changed here.

## Tests

`tests/test_separate_approver.py`, 9 cases:

- off by default;
- the starter refused with no state change;
- an unnamed approver refused;
- another approver recorded;
- the starter may reject;
- the Arabic message;
- the setting values;
- the API returns 403 `self_approval` while a platform approver publishes;
- without the setting the starter approves.
