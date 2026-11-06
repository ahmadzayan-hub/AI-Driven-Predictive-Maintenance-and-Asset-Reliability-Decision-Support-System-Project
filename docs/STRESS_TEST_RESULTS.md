# Stress test results

Run 2026-11-06: 24 synthetic datasets, 95 of 95 checks pass. Every dataset is invented and seeded (`scripts/stress_datasets.py`); no model is called.

| Dataset | Rows × columns | Run state | Seconds | Checks passed |
|---|---|---|---|---|
| condition_1_to_9.csv | 120 × 6 | awaiting_approval | 0.3 | 5/5 |
| condition_0_to_100.csv | 300 × 5 | awaiting_approval | 0.3 | 4/4 |
| condition_text_grades.csv | 240 × 5 | awaiting_approval | 0.3 | 4/4 |
| condition_reverse_scale.csv | 240 × 4 | awaiting_approval | 0.3 | 5/5 |
| maintenance_50k.csv | 50000 × 9 | awaiting_approval | 19.5 | 3/3 |
| maintenance_defects.csv | 2000 × 9 | awaiting_approval | 0.9 | 2/2 |
| arabic_assets.csv | 240 × 5 | awaiting_approval | 0.3 | 2/2 |
| mixed_dates.csv | 300 × 3 | awaiting_approval | 0.3 | 2/2 |
| formatted_numbers.csv | 200 × 4 | awaiting_approval | 0.3 | 3/3 |
| semicolon_decimal_comma.csv | 150 × 2 | awaiting_approval | 0.2 | 5/5 |
| formula_injection.csv | 80 × 3 | awaiting_approval | 0.2 | 2/2 |
| prompt_injection.csv | 120 × 3 | awaiting_approval | 0.2 | 2/2 |
| wide_300.csv | 120 × 301 | awaiting_approval | 1.6 | 2/2 |
| high_cardinality.csv | 5000 × 3 | awaiting_approval | 0.8 | 2/2 |
| all_text.csv | 60 × 3 | failed | 0.1 | 2/2 |
| single_row.csv | 1 × 2 | awaiting_approval | 0.2 | 1/1 |
| duplicate_headers.csv | 50 × 3 | awaiting_approval | 0.2 | 1/1 |
| na_markers.csv | 300 × 5 | awaiting_approval | 0.3 | 3/3 |
| outliers_negative.csv | 302 × 2 | awaiting_approval | 0.2 | 2/2 |
| sensor_timestamps.csv | 2000 × 3 | awaiting_approval | 0.5 | 3/3 |
| costs_budget.csv | 48 × 4 | awaiting_approval | 0.2 | 3/3 |
| contracts.csv | 150 × 5 | awaiting_approval | 0.2 | 2/2 |
| workbook_cover.xlsx | 120 × 5 | awaiting_approval | 0.3 | 3/3 |
| feature_sweep (maintenance 1,500 rows) | - × - | awaiting_approval | 0.7 | 32/32 |

## Round 1: found and fixed

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

## Round 2: the four open gaps, closed

10. **A 1-is-best grade** (UK and Australian convention): the mapping takes a declared direction per measure (`better`: higher or lower), the Datasets mapping panel offers it, and the designed page then ranks the weakest first. It is declared by the owner, never inferred.
11. **Decimal commas**: a semicolon file was split on its commas ("ST03;17" and "51") because the separator check tied and chose the comma; it now requires the separator to split the header as it splits the rows. The mapping takes a `decimal` mark, the platform suggests "comma" when a column is written that way unambiguously, and the run then reads "12,34" as 12.34.
12. **Ask Miyaar's figures** keep every digit and gain thousands separators (382,031.46).
13. **Plain knowledge questions without a language model**: a real question with a strong match (two or more subject words, at least half of them, and a named term such as P75, G02 or Failure_Probability) is answered from the knowledge base, cited; conversation and general questions ("What is preventive maintenance?") still get the honest no-model reply.

## Gaps found

None: every check passes.
