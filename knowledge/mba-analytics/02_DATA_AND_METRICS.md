# Data, metrics and analytical grain — البيانات والمؤشرات

## Source-backed principles

The analytics process connects business goals to collection, storage, preparation, analysis, visualization and delivery. The lectures add governance, collaboration and iteration across these activities. [S015](SOURCE_INDEX.md#s015), pp9–10,14–20; [S037](SOURCE_INDEX.md#s037), pp5,7–11,18–25.

Phillips separates a metric's **business meaning**, **operational counting rules** and **technical implementation**. Representatives from the business, analytics and engineering functions should agree these definitions; a data dictionary records them. [S005](SOURCE_INDEX.md#s005), pp167–169. The book's duplicated/deduplicated-cookie wording is inconsistent, so use the three-level definition principle without copying that ambiguous counting example.

The Power BI lecture uses facts and dimensions in a star model. It warns that the wrong relationship key can create a many-to-many relationship and stresses correct date types. [S039](SOURCE_INDEX.md#s039), pp3,8–9. The managerial text also stresses consistent reporting scopes and dimensions when reconciling daily and monthly reports. [S007](SOURCE_INDEX.md#s007), pp150,153–155.

More records or more variables do not guarantee more useful information. The introductory data book warns about poor quality, cost, overfitting, misleading relationships and questions chosen without business purpose. [S006](SOURCE_INDEX.md#s006), pp13–15.

## Proposed metric contract

Before calculating a KPI, record the fields below. This contract operationalizes the cited definition/governance principles; it is not a copied course template.

| Field | Required evidence |
|---|---|
| Decision and owner | Who can act, and what action the metric informs |
| Unit of observation / grain | One row means one event, asset, transaction, period or another explicitly defined unit |
| Business definition | Plain-language meaning and population |
| Operational definition | Numerator, denominator, exclusions, deduplication, period and aggregation rules |
| Technical definition | File hash, sheet/table/column, calculation version and filter logic |
| Units | Currency, time, energy, quantity and percentage convention; unknown stays unknown |
| Time | Event time, recording time, prediction cutoff and reporting period where available |
| Quality | Missingness, invalid values, key uniqueness, joins and coverage checks |
| Interpretation | Direction of improvement, relevant uncertainty and known limitations |
| Approval | The named human who accepts the definition for this analysis |

Do not infer a currency from a business context. Do not treat a numeric ID as a quantity. Do not average percentages or rates without checking the denominator and intended weighting. Do not label a column MTBF or MTTR as hours unless the source dictionary supplies that unit. These are proposed safeguards; the inspected material does not establish the definitions for Team 3.

## Proposed quality workflow

1. Freeze file identity and parse the entire authorized input; record sheet/row/column coverage and parse failures.
2. Inspect schema and candidate grain before joining or aggregating. Test business keys and join cardinality, then reconcile row counts and totals before and after joins.
3. Count blanks separately from missing-like strings. Confirm whether values such as `None` are categories, missing data or literal text before changing them.
4. Investigate outliers and impossible values with the owner. Keep the original values and a transformation log. Do not erase a genuine rare event just because it is inconvenient.
5. Compare the cleaned data with the original and challenge at least one cleaning decision before acceptance.

The course explicitly asks for a cleaning report, changes before/after and a challenged correction. [S041](SOURCE_INDEX.md#s041), pp7–9. Phillips warns that outliers may be important and that a fashionable or overly complex model should not dictate the analysis. [S005](SOURCE_INDEX.md#s005), p162.

## Schema-level reference scope

The [dataset cards](10_DATASET_SCHEMAS.md) describe six course dataset schemas and their interpretation limits. They expose no records, identifiers, exact dates or distributions. Unknown units and collection/generation provenance remain unknown. A schema card is not evidence of a valid label, sufficient forecast history or an asset panel.

The Power BI lecture's Wide World Importers files are referenced in the slides but were absent from the reviewed source collection. [S039](SOURCE_INDEX.md#s039), p6. They are not supplied by these references.
