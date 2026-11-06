## 15. Existing individual customer-churn assignment
<!-- kb: domain=mba.9227.individual; evidence=DOCUMENT_REPORTED_RESULT; limits=academic_case|not_rmd_operational_rule -->


Source: S06, six-page DOCX, inspected as an existing report. Status: DOCUMENT_REPORTED_RESULT, except checked arithmetic. This section preserves what the report contains; it does not generate new assessed findings.

### 15.1 Existing case and findings

| Item | Existing report content |
|---|---|
| Dataset | E-commerce Customer Churn, attributed to Samuel Semaya on Kaggle |
| Size | 3,941 records, 11 source variables |
| Business question | Which characteristics and behaviours are associated with churn, and which retention action should management prioritise? |
| Overall observed churn | 674 / 3,941 = 17.10% |
| Priority historical segment | Early-tenure, Mobile-preference customers with the complaint context used in the proposed pilot |
| Segment records | 254 |
| Segment observed churn | 172 / 254 = 67.72% |
| Share of observed churn | 172 / 674 = 25.52% |
| Existing recommendation | Controlled complaint-recovery pilot for eligible active customers, human contact within 24 hours, resolution/onboarding and a capped offer when appropriate |
| Evaluation intent | Compare with a control or credible baseline before scaling |

The ratios above were recomputed and match the report's rounding. Segment membership, Power BI filters, DAX and the raw dataset were not independently reproduced.

### 15.2 Reported preparation and data limits

- Category text was standardised and analytical groups were created.
- The report records 576 missing cells across tenure, distance and recency.
- Missing numeric values were retained, with Unknown groups where relevant.
- It records 671 repeated profiles, retained because there is no customer identifier proving duplication.
- Removing exact repeated profiles reportedly changes overall churn to 16.33% and segment churn to 66.18%.
- Complete records reportedly show 15.16% overall churn.
- No observation date, churn date, intervention costs, customer revenue or lifetime value is available in the stated dataset.
- No treatment-outcome evidence supports a measured causal effect or ROI.

Source: S06, pp. 3 and 6.

### 15.3 Existing Key Influencers results

| Influence reported in the document | Displayed likelihood |
|---|---:|
| Tenure 0 to 6 months | 4.58× |
| Complaint | 3.00× |
| Mobile preference | 2.75× |
| Cashback at or below 124.39 | 2.42× |
| Single marital status | 2.24× |

These are reported associations from a visual, not treatment effects. The historical 67.72% rate is not a future forecast. Do not infer that changing any listed characteristic causes churn to fall. [S06, p. 5]

### 15.4 Review status and academic boundaries

The document's primary KPI is target-segment churn in a fixed evaluation window, using treatment-control comparison when feasible. It assumes no target reduction. [S06, p. 6]

The report still contains an official-submission-date placeholder and a logo placeholder in its extracted cover text. Its AI-use declaration says Codex organised/formatted supplied material and refined language while retaining existing figures, screenshots and recommendation. That declaration is a statement in the artifact; it does not independently establish instructor approval or compliance.

The inspected brief's AI restriction remains controlling. For any further assessed work, provide permitted clarification, language support or review without producing prohibited assessed findings on the student's behalf. Do not mark this assignment “Ready to submit” from the DOCX alone. The PBIX, approval evidence, final formatting and applicable instructor permission remain necessary checks.

The individual churn case is separate from Olist G02. Never merge their datasets, figures, target populations, interventions or approval records.
