# Upload your dataset and run the agents

The application analyzes your own tabular datasets through its governed
pipeline. Start at **Upload & analyze your data** in the maintenance preview,
or **Overview → New analysis** in the normal workspace.

## Run locally on Windows

From the project folder, with the declared dependencies installed in `.venv`:

```powershell
$env:PYTHONUTF8 = '1'
npm.cmd --prefix frontend run build
& .venv/Scripts/python.exe scripts/serve.py --local-only --port 8000
```

Open <http://127.0.0.1:8000/#/runs?source=upload>. Local mode is for this
computer. A hosted workspace uses the existing managed sign-in and owner
isolation.

## From file to findings

1. **Choose a file.** Use a header row and one consistent record per row.
   Alternatively paste CSV or choose an already stored dataset.
2. **Choose the workbook sheet**, if more than one is available after upload.
   The sheet picker sends the selected sheet to the server. Each sheet is a
   separate dataset. A cover sheet is skipped: the first sheet that looks
   like a table is read, and the picker marks the others "not a table".
3. **Review column roles before analysis.** Check measures, dimensions and
   dates, then save the mapping. Select the main measure and grouping that
   answer your question. Text identifiers are dimensions, not amounts to sum.
   Related stored datasets can be joined using explicit keys.
4. **Write your goal.** For example: “Compare downtime by site and month, show
   missing values, and identify the largest recorded maintenance costs.”
5. **Choose a pipeline profile.** The default runs the governed analysis
   stages. Choose `models` for additional regression, classification,
   clustering and seasonal analysis, with comparisons against baselines.
6. **Select Start run.** Keep the run open while the agents profile, clean,
   analyze and validate. Progress and errors are visible. Pause and resume
   use the saved run state.
7. **Read the report and open its dashboard.** Inspect calculations, filters,
   tables and the cleaned-data download. Figures are computed from your run.
   Review the evidence before approving publication.

To continue processing after closing the browser, start the existing worker
in a second terminal using the same project/configuration:

```powershell
$env:PYTHONUTF8 = '1'
& .venv/Scripts/python.exe scripts/worker.py
```

The worker also stops for approval. It does not publish automatically.

To have the same worker re-measure the classifying agents (confusion matrices
and recall) on a schedule, set `AGENTIC_OS_EVAL_INTERVAL_SECONDS` (at least
60; off by default). Each measurement is appended to `data/eval-ledger.jsonl`
and a regression or a broken recall floor is logged on standard error. It
changes no rule. `python scripts/agent_loop.py status` shows the trend.

For API clients, choose a single dataset's grouping through
`PUT /api/datasets/{id}/mapping` with the desired `dimension` and a role
for every column, then create a run with that `dataset_id`. The run keeps
a snapshot of the saved mapping. A retried `POST /api/runs` with the same
`Idempotency-Key` header (or `idempotency_key` in the body) returns the run
already made, as a 200 marked `idempotent_replay`, instead of a second run.
The `POST /api/runs` field `breakdown`
is only for runs with `joins`; a nonblank value without joins returns
HTTP 422 instead of silently ignoring the choice.

## Supported inputs and meaningful results

| Input | Support |
| --- | --- |
| CSV / TSV / delimited text | `.csv`, `.tsv`, `.tab`, `.txt`; UTF-8 or UTF-16 |
| Excel | `.xlsx`, `.xlsm`; one selected worksheet per upload; macros are not executed |
| JSON | Tabular JSON records; JSON Lines / NDJSON |
| Limits | 4 MB uploaded; 50,000 rows; 500 columns; 10 MB canonical CSV |
| Convert first | Old `.xls`, PDF, images, Parquet and other unlisted formats |

Formula cells need saved results; missing cached values produce warnings.
Nested or non-tabular JSON needs restructuring. Empty, malformed and oversized
files produce an error rather than starting a sample analysis.

Uploading successfully does not guarantee that every kind of analysis is
appropriate. Trends need dates and sufficient history; classification needs
suitable labels; domain KPIs need agreed units and populations. Read the model
cards and limitations. The fictional maintenance preview's condition scores
and equipment are not measurements from uploaded files. The actual report and
dashboard use the uploaded dataset's schema and calculations.

Data is read and analyzed on the server. Dataset rows are not sent to a
language model. See [known limitations](KNOWN_LIMITATIONS.md) and
[the intake decision](adr/0038-dataset-intake-to-analysis.md).

## البدء بالعربية

افتح رابط الرفع ثم اختر العربية من شريط التطبيق. ارفع ملفًا جدوليًا، واختر
ورقة Excel عند الحاجة، وراجع أدوار الأعمدة قبل الضغط على **بدء التحليل**.
يعمل الوكلاء تلقائيًا أثناء فتح صفحة التحليل، وتظهر النتائج في التقرير ولوحة
البيانات. للتشغيل بعد إغلاق المتصفح، شغّل العامل الخلفي بالأمر الموضّح أعلاه.
ينتظر نشر التقرير موافقتك في الحالتين.

في واجهة API، احفظ تقسيم مجموعة البيانات الواحدة عبر
`PUT /api/datasets/{id}/mapping` بتحديد `dimension` ودور لكل عمود، ثم
أنشئ التشغيل باستخدام `dataset_id`. يحتفظ التشغيل بنسخة من التعيين
المحفوظ. وإعادة إرسال `POST /api/runs` بالترويسة نفسها `Idempotency-Key` (أو الحقل `idempotency_key` في المتن) تعيد التشغيل الذي أُنشئ من قبل برمز 200 مع العلامة `idempotent_replay` بدلاً من إنشاء تشغيل ثانٍ. حقل `breakdown` في `POST /api/runs` مخصص للتشغيل مع `joins`؛
وتُرفض القيمة غير الفارغة دون دمج برمز HTTP 422.

الصيغ المدعومة هي CSV وTSV وExcel ‏(.xlsx/.xlsm) وJSON وJSON Lines.
الحدود: 4 ميغابايت عند الرفع، و50,000 صف، و500 عمود، و10 ميغابايت بعد
التحويل. يلزم تحويل PDF والصور وParquet وملفات .xls القديمة أولًا.
تعتمد صلاحية التنبؤات ومؤشرات الصيانة على جودة البيانات وتعريفاتها وتقييم
النموذج، وليست مضمونة بمجرد رفع الملف.
