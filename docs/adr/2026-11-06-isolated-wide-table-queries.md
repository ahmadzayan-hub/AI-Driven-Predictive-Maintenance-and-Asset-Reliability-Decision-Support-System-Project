# Isolated wide-table projection and exact summaries

## Context

PR #93's opt-in CSV index stores each row as a JSON array in SQLite. Its
existing reader returns every column, and acceptance checks compute totals in
caller code. This is not a public upload API or a production analytics path.
The next bounded slice should make a wide table useful without loading all
rows or changing the shared dataset engine while separate feature work exists.

## Decision

Add `server.experimental_query` as a separate trusted-backend reader. Do not
change the existing ingestion/page contract, public routes, authorization,
production storage, deployed worker or `server.datasets`.

- Select 1–32 unique known column names in caller order. Projected pages keep
  original ordinals and the existing columns/rows/next response shape.
- Summaries scan the complete permitted index in one consistent read
  transaction. Return rows scanned and, for each selected column, numeric,
  blank and invalid counts plus exact decimal sum/min/max strings. No mean,
  grouping, distinct count, sample-based estimate or percentile is implied.
- Accept only plain finite decimal text for numeric summaries. Unsupported
  currency, separators, exponents and non-finite tokens count as invalid,
  never as zero. Blank/whitespace cells have their own count. A valid numeric
  token that exceeds the numeric safety budget fails the operation.
- Use exact bounded coefficient/scale arithmetic instead of binary floats or
  Decimal's default rounding precision. Empty numeric populations have null
  aggregates. Do not infer numeric locale, units or KPI meaning.
- Enforce column, metadata, record, output and total-scan budgets. Validate
  record sizes in SQLite before materializing the JSON text in Python. A
  budget overrun or corrupt index fails the whole operation without a partial
  result labelled complete. Errors do not echo cell contents.
- Open only an existing database using SQLite read-only mode, use one explicit
  snapshot and close the connection on both success and error. Missing paths
  must not create a database. Callers remain responsible for authorizing the
  database path; this module does not establish tenant isolation itself.

Default budgets allow 1 MiB of column metadata, 4 MiB per encoded JSON row,
8 MiB of compact ASCII-escaped page output, and 64 MiB scanned per page.
A complete summary permits 10 million rows / 2 billion encoded JSON bytes by
default; finite hard caps remain enforced. JSON representation can exceed CSV
source size. Numeric safety limits are 1,024 token characters, 1,000 digits and
500 fractional places. The module defines all adjustable and hard bounds.

## Verification and limits

Tests cover wide projections and pagination, independent exact totals,
large/fractional and cancelling numbers, missing and invalid cells, explicit
budgets, malformed indexes, read-only behavior, connection closure and snapshot
consistency. The opt-in `scripts/benchmark_pr93_queries.py --run` reproduces a
300 MB synthetic spool/index/projection/summary check with independent arithmetic
oracles and temporary cleanup. Measured results belong in README Testing.

JSON-array storage still reads and decodes each entire permitted row. Projection
reduces returned data, not disk I/O into true columnar storage. A summary remains
a linear scan. Python allocation checks do not measure whole-process RSS or
prove 300 MB throughput. This slice does not establish production cleaning/KPI
equivalence, authenticated multipart storage, public large uploads, UI support,
34-challenge application acceptance or production readiness.
