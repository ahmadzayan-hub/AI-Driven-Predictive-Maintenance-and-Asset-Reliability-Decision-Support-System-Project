# Stress test results

Run 2026-11-05: 24 synthetic datasets, 87 of 91 checks pass. Every dataset is invented and seeded (`scripts/stress_datasets.py`); no model is called.

| Dataset | Rows × columns | Run state | Seconds | Checks passed |
|---|---|---|---|---|
| condition_1_to_9.csv | 120 × 6 | awaiting_approval | 0.4 | 5/5 |
| condition_0_to_100.csv | 300 × 5 | awaiting_approval | 0.3 | 4/4 |
| condition_text_grades.csv | 240 × 5 | awaiting_approval | 0.4 | 4/4 |
| condition_reverse_scale.csv | 240 × 4 | awaiting_approval | 0.3 | 3/4 |
| maintenance_50k.csv | 50000 × 9 | awaiting_approval | 21.8 | 3/3 |
| maintenance_defects.csv | 2000 × 9 | awaiting_approval | 1.1 | 2/2 |
| arabic_assets.csv | 240 × 5 | awaiting_approval | 0.3 | 2/2 |
| mixed_dates.csv | 300 × 3 | awaiting_approval | 0.4 | 2/2 |
| formatted_numbers.csv | 200 × 4 | awaiting_approval | 0.3 | 3/3 |
| semicolon_decimal_comma.csv | 150 × 2 | awaiting_approval | 0.3 | 1/2 |
| formula_injection.csv | 80 × 3 | awaiting_approval | 0.3 | 2/2 |
| prompt_injection.csv | 120 × 3 | awaiting_approval | 0.3 | 2/2 |
| wide_300.csv | 120 × 301 | awaiting_approval | 2.3 | 2/2 |
| high_cardinality.csv | 5000 × 3 | awaiting_approval | 1.0 | 2/2 |
| all_text.csv | 60 × 3 | failed | 0.1 | 2/2 |
| single_row.csv | 1 × 2 | awaiting_approval | 0.3 | 1/1 |
| duplicate_headers.csv | 50 × 3 | awaiting_approval | 0.3 | 1/1 |
| na_markers.csv | 300 × 5 | awaiting_approval | 0.4 | 3/3 |
| outliers_negative.csv | 302 × 2 | awaiting_approval | 0.3 | 2/2 |
| sensor_timestamps.csv | 2000 × 3 | awaiting_approval | 0.6 | 3/3 |
| costs_budget.csv | 48 × 4 | awaiting_approval | 0.3 | 3/3 |
| contracts.csv | 150 × 5 | awaiting_approval | 0.3 | 2/2 |
| workbook_cover.xlsx | 120 × 5 | awaiting_approval | 0.3 | 3/3 |
| feature_sweep (maintenance 1,500 rows) | - × - | awaiting_approval | 0.8 | 30/32 |

## Found and fixed in this round

The first pass (23 datasets, 52 checks) found these; each is fixed and held by `tests/test_stress_findings.py`:

1. **Clean data rejected.** Five claims quoted figures they did not cite (contract breach counts, forecast period count, column count, unnamed outlier columns) or read a period label such as 2069 as a figure, so the validator rejected clean runs, including a clean 50,000-row file. Each figure is now cited and labels are declared.
2. **The planted-defects test passed for the wrong reason.** It expected rejection, but the rejection came from defect 1. The defects (duplicate, negative count, n/a cells) are reported for review, and the test now checks that.
3. **"Not applicable", "N/A" and "-" counted as broken numbers** in the data contract; they are missing cells.
4. **A decimal comma "12,34" was read as 1,234.** It is now refused as unreadable rather than misread.
5. **"85%" and "AED 12,000" read as text** in unmapped files; they now read as numbers.
6. **A `Timestamp` column was not the time axis**, and sensor readings were summed. Both fixed.
7. **A grade in words** (Good, Fair, Poor) had no measure; "share graded Poor or worse" is added.
8. **Completeness of 99.84% printed as 100%**; it now shows the decimal.
9. **The 50,000-row generator ran to the year 2069**; extra rows are now extra fleets over the same 24 months.

## Gaps still open

- **condition_reverse_scale.csv**: supports knowing that 1 is best on this file's grade, so the weakest rank first. Observed: no measure or layout section derives it
- **semicolon_decimal_comma.csv**: formatted numbers read as numbers. Observed: read as text: ['Downtime_Hours']
- **feature_sweep (maintenance 1,500 rows)**: Ask Miyaar prints figures with thousands separators. Observed: printed as 382031.46
- **feature_sweep (maintenance 1,500 rows)**: a plain knowledge question is answered without a language model. Observed: {"reply": {"id": 12, "role": "agent", "text": "The language model is not enabled in this server. Workspace commands remain available. An operator must enable th

Why these stay open: a 1-is-best grade needs the file's owner to say so (no safe inference from numbers alone); a decimal comma is refused rather than guessed; the thousands separator and plain-language knowledge routing are interface changes for a later slice.
