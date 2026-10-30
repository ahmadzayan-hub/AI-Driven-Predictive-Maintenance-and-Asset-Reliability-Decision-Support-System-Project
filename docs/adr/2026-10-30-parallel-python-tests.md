# The Python suite runs in parallel

Date: 2026-10-30 · Status: Accepted (the owner asked to speed up the
operating procedures). Tooling only: no product behaviour changes.

## Context

`scripts/verify.py` ran the Python suite in one process. With 2,391 tests it
took about 520 to 560 seconds of a 540-second check, after the other steps
had been made to run side by side (`fff75b5`). The suite is CPU-bound and the
machine has four cores. The PostgreSQL tests are the obstacle: they drop and
recreate the tables of one shared test database, and two files create roles,
which belong to the whole server.

## Decision

1. **A runner, `scripts/run_python_tests.py`.** Test files go on a queue,
   heaviest first (a PostgreSQL file counts four times its size), in batches
   of three; one worker per CPU takes the next batch and runs it as a plain
   `python -m unittest` process, so every test runs exactly as under
   `discover`. It prints one combined `Ran N tests` and `OK`/`FAILED (...)`
   line, and a failed batch's whole output above it; it exits 1 on any failure.
2. **A database per worker, when the server allows it.** With `PG_TEST_URL`
   set, worker 1 uses that database and workers 2 to 4 copies named after it
   (`agentic_test_w2` ...), created when missing. Each copy is connected to
   before it is used. The two files that create roles always run together in
   one batch.
3. **A safe plan otherwise.** When a copy cannot be created or refuses the
   user, every PostgreSQL file runs in one batch on one worker, in order, as
   in the serial run; the other files still run in parallel. The runner says
   which plan it used.
4. **`verify` runs it.** Its Python step calls the runner, and it reads the
   last counts in the output, so a failed batch printed above cannot replace
   the combined figures. CI keeps `unittest discover -v`, whose full log it
   uploads.

## Measured (this container, 4 CPUs, PostgreSQL 16)

| Run | Python step |
| --- | --- |
| Serial `unittest discover` (before) | about 520 to 560 s |
| Runner, safe plan (this container) | 189 s, 2,391 tests, 19 skipped |
| Runner, a database per worker | not measured here: the server trusts the `dev` user only on `agentic_test`, and widening that was refused by this session's security rules |

A partial trial with copies before the access check stopped early on the
refused copy, so it is not counted. CI's database trusts local connections,
so the copies apply there.

## Consequences

- A full `verify` falls from about nine minutes to about four here. The Python step waits for the production build (about 8 s), because some tests read `frontend/dist`, which the build empties and rewrites; the first full run without that wait failed in the Python step.
- To get the per-worker plan locally, the database operator adds
  `host agentic_test_w2,agentic_test_w3,agentic_test_w4 dev 127.0.0.1/32 trust`
  beside the existing `agentic_test` line (Memory.md, PostgreSQL tests).
- A test that relies on another file having run first would now show it; none
  did across three full runs with the same 2,391 tests and 19 skips.
- Parallel load exposed one timing flaw (amendment, same day):
  `test_rate_limit_survives_restart` sends two requests that must fall in one
  60-second limit window, and a slower restart let them straddle its end. The
  test now starts at least ten seconds before a window ends. No product code
  changed.

## Tests

`tests/test_run_python_tests.py`: every file runs once; role files share one
batch; without copies every PostgreSQL file shares one; batches start
heaviest first; copies named after the database; a refused copy means the
safe plan. `tests/test_verify.py`: the last counts are read.
