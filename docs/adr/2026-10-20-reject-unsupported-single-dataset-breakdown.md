# Refuse a join-only breakdown option on a single dataset

Date: 2026-10-20
Status: Accepted

## Context

ADR 0030 defines the run creation `breakdown` option as a text column from
the merged table, overriding the saved mapping's dimension. The request
model accepts this field independently of `joins`, but the engine only
persisted and applied it when a merge was declared. A caller could therefore
receive HTTP 201 for a single-dataset run whose grouping ignored its request.

## Decision

Reject a nonblank `breakdown` when no joined datasets are supplied. The
engine checks this before run quota checks or dataset, run and task writes.
The existing API error handler returns HTTP 422 with an English or Arabic
explanation directing single-dataset callers to the saved column mapping.
Omitted and blank optional values keep their existing behavior.

This preserves both established contracts: single datasets use the
snapshotted mapping dimension from ADR 0025, and merged datasets can use
the run-level override from ADR 0030. It introduces no inferred grouping
and no new single-run mapping semantics.

Single-dataset API clients that previously sent this option must upload the
dataset, save its column mapping with the desired `dimension`, and create
the run with `dataset_id` and no `breakdown`. The executive and metric-color
browser fixtures follow that flow, explicitly mapping Site as the grouping,
month as the date, and Downtime_Hours as the main measure. Their metric and
missing-value assertions stay unchanged.

## Validation

Synthetic API regressions exercise sample, inline and uploaded-data paths,
omitted and empty joins, both response languages, unchanged durable rows
and quota usage after rejection, successful subsequent admission, and a
single-dataset run that retains its original mapping after that mapping
changes. Existing joined-breakdown and Arabic joined-run regressions
cover the unchanged supported path.
