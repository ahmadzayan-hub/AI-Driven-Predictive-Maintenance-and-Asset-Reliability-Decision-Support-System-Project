# Team 3: submission checklist

Built on 16 October 2026 from the team's shared report (revision 37) and deck. Moodle closes on 22 October; the team uploads on 21 October.

## The three files

| File | State | Notes |
| --- | --- | --- |
| `Group_9226_Team_3_Report.pdf` | Release candidate | 24 A4 pages: a cover, a contents page, then pages numbered 3 to 24, as the PDF counts them. The brief recommends 20 to 25. Tagged for screen readers, in English, with bookmarks. Drafting notes are removed. Items the team still owes are highlighted in amber, listed below. |
| `Group_9226_Team_3_Presentation.pptx` | Release candidate | 15 slides, 16:9, with a title, speaker notes and alt text on every slide. Each slide is a picture of the designed slide, so text is edited in the shared deck and the file is rebuilt. |
| `Group_9226_Team_3_Dashboard.pbix` | **To build** | A `.pbix` file can only be saved by Power BI Desktop on Windows. `Team3_PowerBI_Kit.zip` has everything needed: Power Query, DAX measures, theme, model scores, the build guide and `Expected_Values.csv`. |

## Reconciliation: report, deck and Power BI kit

The brief requires the three files to show the same totals and model metrics. Checked on 16 October:

- **Power BI expected values:** all 30 rows of `Expected_Values.csv` agree with the report. Three MTBF values appear in the report rounded to whole hours: 219.0 as 219, 363.2 as 363, and 204.0 as 204.
- **Deck against report:** the deck has 163 distinct numbers. Every one is in the report, either exactly or in a shorter form, such as $26,501 shown as $26.5k.
- **Recomputed from the dataset:**

  | Figure | Recomputed value | As stated in the report and deck |
  | --- | --- | --- |
  | Critical-outage gap | 7.45 h per record × 862 records = 6,421 h, worth $16.1M | "about 6,400 h", "7.5 h", "roughly $16 million" |
  | Reactive-loss gap | $17.94M | "$17.9M" |
  | Quarterly means in Figure 1 | Read straight from the CSV | Fleet average 91,074 h ÷ 5,000 records = 18.2 h |

**Once the `.pbix` exists:** Ahmed Rashed checks each row of `Expected_Values.csv` against the dashboard. If any value differs, fix the dashboard, not the report.

## Still owed by the team

Each item below is highlighted in the PDF. None of them could be filled in honestly without the team's own files or facts.

**Report**

| Section | Item | Owner |
| --- | --- | --- |
| Cover | A registration number for each member | Each member |
| Methodology and governance | The notebook file name | Malak Philippe |
| Unresolved exceptions | The date the email to the instructors was sent, and their reply | Ahmed Zaian |
| Transformations, Appendix B | The Power Query step list, exported from the Advanced Editor | Malak Philippe |
| One rule for every KPI, Appendix A | Confirmation that the PBIX cards show the same totals | Ahmed Rashed |
| Dashboard design | Check the section against the finished PBIX, and add one captioned screenshot per page | Ahmed Rashed |
| Source and refresh | Confirm that the PBIX opens on a second machine | Ahmed Rashed |
| AI applications, Appendix C | Rerun the model notebook to reproduce the figures, and add the notebook file name | Ahmed Zaian |
| Appendix B | The notebook output for each governance check | Malak Philippe |
| AI usage disclosure | How each check was validated, and every other AI tool used (one row each) | Ahmed Zaian, with all five |
| Appendix D | Each member confirms their own row | All five |
| Appendix E | Any extra references, or delete the placeholder line | Malak Philippe |

**Deck**

- Slide 3, data: replace "[confirm date]" with the date the email was sent.
- Slide 5, dashboard: add backup screenshots of the PBIX pages.

## Review round 1 (16 October)

Four reviewers checked the files. The changes they call for in the team's text, each with verified figures and suggested wording, are in `Team3_Review_Round1_Corrections.md`. Two of them change headline findings: the row-average comparison (section B2) and the stockout wording (section B3). The build fixes are already in these files.

## Rebuilding after edits

Edit the shared report and deck, not these files. Then ask Claude to rebuild both, in a session with the repository and the dataset attached. `Team3_Build_Tools.zip` holds the build scripts:

- **Report:** export the shared report as Markdown to `report_rev37.md`. `make_report.sh` then builds one tagged PDF twice, so the contents page carries real page numbers. It needs pandoc, Node with Playwright, and Chromium. Two paths at the top of the scripts point to the dataset and to the repository's `frontend/` folder; change them for a new machine.
- **Deck:** `render_slides.mjs` renders each slide, then `build_pptx.py` builds the `.pptx` from the images.
- **Reconciliation:** `reconcile.py` checks the report and the deck against `Expected_Values.csv`.
