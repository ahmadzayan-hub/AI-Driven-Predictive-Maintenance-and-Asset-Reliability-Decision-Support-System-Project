# Data health: the share of measure values usable as recorded (R4)

Date: 2026-10-31 · Status: Accepted (the owner asked for slice R4 on
31 October 2026).

## Context

The review proposed one figure, before the analysis, that covers
completeness, excluded values and unusual values. A data quality score
already exists (`quality` stage, ADR history in `server/analytics.py`): four
ratios over the raw rows before cleaning, across every column. It cannot see
what the data policy does later: missing-value markers, values that cannot
be read as numbers, and values left out by a declared limit. Changing its
formula would change every past score, so it stays as it is.

## Decision

1. **The cleaner states data health** (`_data_health` in `server/analytics.py`):
   the share of measure cells in the rows kept after cleaning that are usable
   as recorded, as `c_health` (a percentage to one decimal) and
   `c_health_cells` (the counts), with the claim `cl_health` in both
   languages.
2. **Each loss is named:** empty, marked missing (`N/A`, `-`, `غير متوفر`),
   unreadable, and outside a declared limit. Unusual values are still used, so
   they are counted among the usable values and named beside the share, never
   against it.
3. **The report states it first** in the *Data policy applied* section, in the
   run's language.
4. **The cleaner output carries `health`** with the same figures, for any
   later view.
5. Arabic display names and methods are added for both calculations.

## Consequences

- Every run now says, in one line, how much of the measure data it could use
  and why the rest was lost.
- Two scores now exist and answer different questions: the quality score is
  about the raw table across all columns; data health is about the measures
  the analysis reads, after the policy. The report names data health; the
  quality score keeps its own claim.
- Dropped rows (empty and repeated) are reported by `cl_rowloss` as before
  and are not part of the share, which counts cells in the kept rows.
- No interface change and no script budget change.

## Verification

`tests/test_data_health.py` (5 tests): each loss counted and the share
following from them; values outside a limit counting against health; clean
data stating 100% and saying nothing was lost; the report line first in the
policy section in English and Arabic; the validator passing in both languages
with Arabic display names.
