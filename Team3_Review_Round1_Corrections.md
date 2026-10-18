# Team 3: review round 1, what to change before 21 October

Prepared on 16 October 2026 for Ahmed Zaian, Ali Elraey, Ahmed Rashed, Khaled Amer and Malak Philippe. Owners updated on 17 October 2026 to the roles agreed at the kickoff: Ahmed Zaian, Agentic OS and the AI part, and the upload; Ahmed Rashed, the BI dashboard; Malak Philippe, data preparation and the final presentation; Ali Elraey, operations; Khaled Amer, cost and financial insights.

Four reviewers checked the report, the deck, the briefing clip and the Power BI kit:

- a figures auditor;
- a brief-compliance reviewer;
- an analytics subject-expert reviewer;
- an accessibility reviewer.

Every figure in this memo was recomputed from `Group_9226_Team_3_Enterprise_Dataset.csv` with the same split and models as the report, before it was written here. Where a reviewer's number differed from the recomputation, the recomputed one is used and the difference is noted.

Page numbers are the rebuilt PDF's, where the executive summary is page 3. **Owners** follow Appendix D of the report. The report and the deck are the team's shared documents, so their wording is yours to change. Paste the edits below into the shared report and deck, then the files are rebuilt.

## Where it stands

- **Automatic gates:** 10 of 16 pass. The score went 50.0% (round 1, 10 gates) → 56.2% (round 2, 16 gates, six of them added from round-1 findings) → 62.5% (rounds 3 and 4). All six failing gates are team items:
    - the `.pbix`;
    - the highlighted `[Add…]` items in the report and deck;
    - the stockout and row-average wording (sections 2 and 3);
    - the AI-use line in the deck.
- **Brief:** of 118 requirements, 82 are met, 20 partly met and 16 not met. The one blocker is the missing `.pbix`; the other unmet items mostly follow from it.
- **Figures:**
    - The report carries all 30 dashboard register values.
    - Every number in the deck and the clip is sourced in the report.
    - The deck's one worked figure (7.5 h) now shows its working, and the arithmetic holds.

## 1. Already fixed in the rebuilt files

**Deck** (`Group_9226_Team_3_Presentation.pptx`):

- Alt text reads as sentences. Table cells used to run together, as in "Reactive7988.1 y219 h"; they are now separated, as in "Reactive; 798; 8.1 y; 219 h".
- Every slide has a real title, so screen readers, the outline view and PowerPoint's accessibility checker find 15 titled slides.
- File properties are corrected: author, dates, 15 slides, 15 notes pages and a 16:9 size.
- **Mirror this one in the shared deck:**
    - Slide 9's footer now shows the working: "Critical gap: 24.4 h − 16.9 h = 7.5 h per record × 862 critical records × about $2,500 per hour ≈ $16M".
    - The 7.5 h appeared nowhere in the report; 24.4, 16.9, 862 and $16 million all do.

**Report** (`Group_9226_Team_3_Report.pdf`, still 24 pages):

- It is a tagged PDF in English, so headings, lists, tables and the figure reach screen readers. It also has bookmarks for every section and appendix.
- Figure 1 has a text alternative that lists all 12 quarterly values.
- Hyphenated words are no longer split at line ends. Text extraction had read them as "DecisionSupport", "spareparts" and "1DIVIDE".
- Page numbers now match the PDF's own pages: the cover is page 1, the contents page 2 and the executive summary page 3. The contents page is updated to match.

**Clip** (`motion/team3-briefing.mp4`, `.txt`, `.poster.png`):

- The stockout scene now says "Corrective records with a stockout average twice the downtime … An association, not a cause." It used to say "A spare-parts stockout doubles a corrective outage".
- The transcript cites report sections, not working files, and keeps the on-screen words apart from the sources.
- The poster is the title frame.

**Power BI kit** (`Team3_PowerBI_Kit.zip`, `BUILD_GUIDE.md`):

- Page 1 has a decision statement and the reporting period.
- Page 2 has the 12-quarter downtime trend (the report's Figure 1).
- Page 4 has cards for Total Orders, First-Time Fix % and Repeat Repair %, which `Expected_Values.csv` checks there.
- The visual count is corrected to ten types, plus text boxes.

## 2. Blockers

### B1. The `.pbix` does not exist yet

**Owner:** Ahmed Rashed (model, measures and pages).

1. Build it in Power BI Desktop from `Team3_PowerBI_Kit.zip`, following the updated `BUILD_GUIDE.md`.
2. Save it as `Group_9226_Team_3_Dashboard.pbix` with the data imported.
3. Tick all 30 rows of `Expected_Values.csv`.
4. Test the slicers, drill-through and back buttons.
5. Open it on a second computer without the source folder.

Until it exists, the package has two of its three files.

### B2. The row-average lesson does not hold as written (analytics R1-01, R1-05)

**Owner:** Malak Philippe.

The weighted register values are right. The "average of row rates" comparison is not like for like, for two reasons:

- The 985 preventive records store placeholder rates: a first-time-fix rate of 0 and MTBF equal to their operating hours.
- The stored SLA score is a different measure.

| KPI | Row average, all 5,000 records | Row average, records where the rate is defined | Weighted register |
| --- | --- | --- | --- |
| First-time fix | 64.7% | 80.6% (4,015 corrective records) | 76.6% |
| Repeat repair | 15.6% | 19.4% | 23.4% |
| MTBF | 342.5 h | 310.8 h (records with a failure) | 313.3 h |
| SLA | 75.8% is the mean of min(1, target ÷ actual), a capped ratio | Not applicable | 46.1% of records met their target (45.7% of corrective records) |

Like for like, the gaps are +4.0 points, −4.0 points and −2.5 h, not −11.9, +7.8 and +29.2.

**Executive summary, finding 1.** Replace it with:

> **Every KPI comes from one weighted register.** 46.1% of records met their SLA target. First-time fix is 76.6% and repeat repair 23.4% of corrective orders, and MTBF is 313.3 hours. Row averages would mislead: 985 preventive records store placeholder rates, and the stored SLA score is a capped ratio, a different measure from the share of targets met.

**Page 8, "One rule for every KPI" table:**

- Add the "records where the rate is defined" column above.
- Label the 75.8% as "mean of a capped target ÷ actual score (a different measure)".

**Recommendation 1, evidence.** Replace "SLA overstated by 29.7 points" and "understate first-time fix by 11.9 points" with:

> 985 preventive records hold placeholder rates, so row averages over all records distort first-time fix (64.7% against 76.6% weighted).

**Deck, slide 4** (Malak Philippe with Ahmed Rashed, who presents it):

- The title "Measured correctly, service is weaker than reported" and the "29.7 points" call-out rest on the same comparison.
- Suggested title: "One register, one rule: summed numerator ÷ summed denominator".
- Keep the register column. Footnote the 75.8% as a different measure.

### B3. Stockouts go with repeated failure; the data cannot show they lengthen outages (analytics R1-02, R1-03)

**Owner:** Ali Elraey.

The 44.5 h against 22.2 h is right. What it means is not "stockouts double outages":

- **Failures:** among corrective records, those with a stockout average 3.6 failures against 1.86, and 5.7 corrective orders against 2.53.
- **Downtime per failure:** almost the same, 12.4 h against 12.0 h.
- **Where stockouts occur:** only in records with three or more failures. That is 5.5% of records with 3 failures, 22.8% with 4 and 30.0% with 5.
- **Who has them:** these records are older (9.9 against 8.0 years) and in worse condition (70.7 against 76.8).
- **Criticality:** stockouts are not concentrated on critical equipment. 15 of the 84 are critical (17.9%), against 17.4% of all corrective records.
- **What the critical gap is:** repair time. Corrective MTTR is 16.0 h for critical equipment against 11.0 h at every other level. Failures per record are the same at every level (1.85 to 1.93).

**Executive summary, finding 5.** Replace it with:

> **Stockouts mark the records that fail most; lead time shows no link to downtime.** The 84 corrective records with a stockout averaged 44.5 hours of downtime against 22.2, but they also had about twice the failures (3.6 against 1.86 per record), and downtime per failure is almost the same (12.4 against 12.0 hours). The data cannot show that stockouts lengthen outages.

**EDA, page 10 heading.** Change "Lead time does not drive downtime, but stockouts do" to:

> Lead time shows no link to downtime; stockouts go with repeated failure

Then add the evidence above.

**Insight 8.** Use the same association wording.

**Decision requested, "Shorten critical outages: keep critical spares on site, so stockouts stop doubling outages, and escalate faster."** Replace it with:

> Shorten critical outages: find why critical repairs take about 16 hours against 11 at every other level, and escalate faster.

**Recommendation 4:**

- Recast it as finding why critical repairs take 16 h (escalation, skills, access).
- Keep critical spares only as a small test.
- Remove the stockout link from its rationale.

**Deck:**

- **Slide 7 title:** change "No failure mode dominates; stockouts double the outage" to "No failure mode dominates; stockouts go with repeated failure".
- **Slide 7 body and notes, and slide 13 (action 4) and its notes:** remove "double" wherever it refers to stockouts. For example, "Stockouts double downtime" becomes "Critical repairs take 16 h against 11 h".

## 3. Major: analysis

### R1-04. Per-record gaps mix in preventive records (Ali Elraey)

Preventive records have no failures, downtime or loss by construction, and their share differs between the groups compared:

- **Age bands:** 63.8% of records are corrective at 0–5 years, against 97.6% at 15–20 years.
- **Strategies:** 92.5% are corrective for Reactive, against 75.2% for Condition Based.

The direction holds, but the magnitude roughly halves on corrective records alone.

| Comparison | All records (as in the report) | Corrective records only |
| --- | --- | --- |
| MTBF, 0–5 to 15–20 years | 460 → 204 h | 298 → 201 h |
| Loss per record, 0–5 to 15–20 years | $26,501 → $83,610 (3.2×) | $41,545 → $85,625 (2.1×) |
| Reactive against Condition Based: failures per record | 2.09 against 1.32 | 2.25 against 1.75 |
| Reactive against Condition Based: MTBF | 219 against 363 h | 203 against 275 h |
| Reactive against Condition Based: loss per record | $62,030 against $39,543 (+57%) | $67,073 against $52,606 (+27%) |
| Reactive against Condition Based: maintenance cost per record | +32% | +18% |
| Illustration: Reactive at the Condition Based loss rate | $17.9M | $10.7M (738 records) |

**Fix:**

1. Add a corrective-only column to the age and strategy tables.
2. Use the like-for-like figures in the summary, Insights 5 and 7, the illustration, and Recommendations 3 and 8.
3. State the unequal preventive share as a limit.
4. Deck:
    - Slide 6: change "Loss per record triples…" to "Loss per corrective record doubles from the newest to the oldest equipment".
    - Slide 10: change "Reactive maintenance loses 57% more…" to "Reactive records lose 27% more per corrective record".

### R1-06. The downtime model is not shown against a fair baseline (Ahmed Zaian)

Mean absolute error on 2026 records:

| Method | Error |
| --- | --- |
| Linear model | 10.08 h |
| Training mean | 12.03 h |
| Training median | 11.78 h |
| Mean by work-order type | 8.56 h |
| Median by type | 8.28 h |
| Mean by type and criticality | 8.36 h |
| Linear model with order type as an input | 8.43 h |

A rule by order type beats the model, because preventive records have 0 h of downtime.

**Fix:**

- Add the order-type baseline row.
- Change the downtime model from "Executed, secondary" to "Tried; no better than a rule by order type".
- Remove "beats a naive estimate by about two hours" and the 16% claim, or say they hold only against the overall mean.
- Say whether the order type is known before the work, and why it is left out.

### R1-07. Lead with corrective-only results (Ahmed Zaian)

No preventive record has two or more failures, so the all-record AUC partly measures telling preventive from corrective records apart. On the 792 corrective 2026 records:

- **Base rate:** 61.1%.
- **AUC:** 0.696 for the model, 0.684 for the supplied Failure_Probability and 0.667 for condition score.
- **The model's gain over the supplied score:** a 95% interval of −0.010 to +0.035. That includes zero. On all records it is +0.001 to +0.036.
- **Top-10% precision (80 records):** 90.0% against 87.5%.

**Fix:**

- Lead the summary, the classifier table and Recommendation 5 with the corrective-only figures and the 61.1% base rate.
- Say the gain is not distinguishable from the supplied score.
- If the primary model was chosen after seeing both test AUCs, say so.

### R1-08. Timing of the sensor inputs is asserted, not shown (Ahmed Zaian)

The data has one date per record and no reading time, so "known before the work order" for temperature, vibration, pressure and condition score is an assumption.

Dropping those four inputs lowers the AUC from 0.746 to 0.683 (all records), and from 0.696 to 0.635 on corrective records. They carry most of the signal, so their timing matters.

**Fix:**

- Label their timing "assumed", and report the sensitivity run above.
- Change "Sensors give early warning" (Insight 12) to "same-record association".
- Delete the sentence "Sensor readings therefore carry early-warning information".

### R1-09. Team and shift: only Team A's gap exceeds sampling noise (Ali Elraey)

Each team and shift cell holds 576 to 649 records, about ±4 points at 95%. The night-against-day gaps:

| Team | Gap | p |
| --- | --- | --- |
| A | −7.5 points | 0.008 |
| B | −1.3 points | 0.65 |
| C | −2.3 points | 0.42 |
| D | −1.6 points | 0.57 |

Across the eight cells, χ² is 8.7 on 7 degrees of freedom (p = 0.28), so they spread no more than chance.

**Fix:**

- Show each cell's n and the ±4-point band.
- Change "Night shifts meet SLA less often than day shifts in every team" to "Only Team A's night gap exceeds sampling noise, and it is the largest of eight cells".
- Word Recommendation 6 as "verify Team A nights".

### R1-10. Appendix A lacks four measures the register checks (Ahmed Rashed)

Add these rows from the kit's `DAX_Measures.dax`:

| Measure | DAX | Unfiltered value |
| --- | --- | --- |
| Downtime per Record | `DIVIDE([Total Downtime Hours], [Records])` | 18.2 (24.4 for Critical; 44.5 and 22.2 for corrective records with and without a stockout) |
| Loss per Record | `DIVIDE([Production Loss], [Records])` | $45,776 ($62,030 for Reactive; $26,501 for 0–5 years) |
| Scored Records | `CALCULATE([Records], NOT ISBLANK(Fact_Maintenance[Model_Rank]))` | 996 |
| Action Queue Hit Rate % | `DIVIDE(CALCULATE(SUM(Fact_Maintenance[Repeat_Failure]), Fact_Maintenance[Model_Rank] <= 100), [Action Queue Records])` | 85.0% |

## 4. Major: the brief

| # | What | Owner | Fix |
| --- | --- | --- | --- |
| F2 | The AI-use disclosure (p.20) has placeholders and too narrow a scope | Ahmed Zaian, all five | Say how each check was validated. Name every other tool, or say none was used. Widen the scope to the DAX, Power Query and theme kit, the model code and run, the deck, Figure 1 and the build scripts. |
| F3 | The deck has no AI disclosure; the announcement asks for it in the presentation | Malak Philippe | Add a line under "Thank you" on slide 15, such as "AI assistance: Claude (Anthropic) for data checks, drafting and build scripts; full disclosure in the report, p.20", and the validation sentence in the notes. |
| F4 | Dashboard section and slide 5 describe a file that does not exist | Ahmed Rashed | After B1, add the six page screenshots: one captioned contact-sheet page in the report (it can go to 25 pages) and thumbnails in the slide-5 cards. |
| F5 | Model figures not yet rerun in the team notebook (p.6, 14, 23, 24) | Ahmed Zaian; Malak Philippe for the governance notebook | Rerun them and give the notebook names. If anything differs, update `Model_Scores.csv`, `Expected_Values.csv`, the report and the deck together. |
| F6 | The instructor email is unconfirmed (p.7, slide 3) | Ahmed Zaian | Give the date and the reply, or send the email now. Until then, slide 3 says "to be raised". The brief asks for consultation before changing the scenario or rewriting source values. Say the team changed neither. |
| F7 | The PBIX totals are unconfirmed (p.8, p.22) | Ahmed Rashed | After B1, confirm the four totals and remove both markers. |
| F8 | Slide 3 says "13 KPI formulas"; the report names ten | Malak Philippe | Confirm the count from the notebook and make the two agree. |

## 5. Minor

- **R1-11 (Ali Elraey):**
    - Change "Age is the strongest pattern" to "Age is one of three comparable gradients, with condition score and vibration". Their correlations with downtime are 0.37, −0.34 and 0.34, and permutation importance ranks age sixth.
    - Add n = 85 beside the 15–20 year figures.
- **R1-12 (Ali Elraey):**
    - Say that 2026 holds 996 records on 12 dates, against about 2,000 on 24 dates in each earlier year. The last record date is 25 December 2026.
    - Add SLA to the stability sentence. By quarter it ranges from 39.5% to 51.8%, with no significant trend (+1.7 points a year, p = 0.17). The reviewer computed p = 0.07; the recomputation gives 0.17.
- **R1-13 (Khaled Amer):** after the 4.5× sentence, add: "Production_Loss_USD is the dataset's own valuation: about $2,500 per downtime hour at every criticality level ($2,496 to $2,555), basis not documented." Add "(association)" to summary findings 3 to 5.
- **R1-14 (Malak Philippe):** "repeat-failure record" means two or more failures within one record. Call it a "multi-failure record" in the text, the tables and Power Query step 8.
- **F9 (Ahmed Rashed):**
    - p.12: model scores are columns of Fact_Maintenance, merged on Record_ID, not a related table.
    - p.13, dashboard page 2: "by class" should be "by strategy".
    - "Eleven visual types" should be "ten".
    - Insight 11 should point to page 2 and Insight 12 to page 6.
    - The refresh text needs "with the trailing backslash".
- **F11 (Malak Philippe):** add three rows to the check table:
    - "Data types: all 60 columns parse to their intended type", once the notebook confirms it;
    - "Inventory continuity: not applicable, no opening or closing stock fields";
    - "Source quality: no quality indicator in the data; completeness is the only measure".
- **F12 (Malak Philippe):** give slides 10 and 14 45 seconds each. Take 15 seconds from slide 2 and 15 from slide 11. Reword slide 10's note to "the briefing totals 15 minutes".
- **F13 (Malak Philippe):** slide 2 lists five questions and the report seven. Label them as five themes with their question numbers, or show all seven.
- **Critical-gap hours (Ali Elraey; review round 2):** the report (p.18) and slide 9's notes say "about 6,400 fewer downtime hours". That is right on unrounded figures: 7.45 h × 862 = 6,421 h. But slide 9's footer now shows 24.4 − 16.9 = 7.5 h, and 7.5 × 862 = 6,465, which reads as "about 6,500". Write "about 6,400 hours (7.45 h per record × 862 critical records)" in the report, so the two agree.
- **Briefing date:** confirm "25 October 2026" on the cover and slide 1 against Moodle, or remove it.

## 6. How the next round is checked

When the shared report and deck are updated:

1. Rebuild the files with the build tools.
2. Run the gates: `python3 scripts/review_gate.py capstone-plan.json`.
    - The stockout and row-average gates pass once the wording in section 2 is gone.
    - The AI-use gate passes once slide 15 has its line.
3. The analytics and brief reviewers then check sections 2 to 5 again.

Upload only the three files: the `.pbix`, the `.pptx` and the `.pdf`. Leave the kit, the build tools, this memo, the checklist and the clip out of the upload.
