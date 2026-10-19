# تسليم اللوحة التنفيذية / Executive dashboard handoff

19 أكتوبر 2026 / 19 October 2026

## العربية — الاستخدام والحدود

تجمع النظرة التنفيذية أدلة تحليل محدد داخل معيار. يُعدّ **وكيل معيار التنفيذي**
موجزًا حتميًا من محرك الحسابات (`source: engine`)؛ لا يحتاج إعداد الموجز إلى
استدعاء نموذج لغوي، ولا يشخّص أصلًا أو ينفّذ صيانة أو يعتمد نشر تقرير.

1. افتح **لوحات المعلومات** واختر تحليلًا له جدول منظَّف. لبدء تحليل صيانة،
   استخدم **تحليل بيانات الصيانة**؛ يختار هذا المسار إعداد تحليل الصيانة الموجود.
   تظهر المؤشرات المنضبطة التي تدعمها أعمدة البيانات، مع بيان المؤشرات غير المتاحة.
2. حدّد الفترة والمرشحات. تعرض النظرة عدد السجلات المحددة وإجمالي سجلات التحليل.
   تُعاد حسابات المؤشرات وأولويات المراجعة لهذا النطاق. افتح **فحص الأدلة**
   داخل المؤشر لقراءة الصيغة والبسط والمقام والمجتمع المقاس وتغطية السجلات
   وسياسة البيانات المفقودة. القيمة غير المحددة لا تُستبدل بصفر.
3. راجع **قرارات تحتاج إلى الاهتمام**. يفتح **عرض الأدلة** المرجع المحدد في
   سجل الأدلة وينقل التركيز إليه. يفتح فحص المجموعة سجلاتها مع الاحتفاظ
   بالمرشحات في العنوان، وتبقى هذه الاختيارات بعد إعادة التحميل؛ فتح الرابط
   يظل خاضعًا لصلاحيات الوصول إلى التحليل.
4. اضغط **إعداد الموجز التنفيذي** لعرض أسئلة المراجعة المستندة إلى الأدلة.
   من **تنسيق التقرير** اختر **تقرير HTML**، وهو الخيار الافتراضي، أو
   **مستند Word (.docx)**، ثم اضغط **تنزيل التقرير**. ملف Word مستند DOCX
   فعلي قابل للتحرير، وليس ملف HTML أُعيدت تسميته. يستخدم التصدير نطاق الموجز
   المُعدّ ومرشحاته ولغته ووقت مراجعته ومعرّف مراجعة محتواه؛ يعيد الخادم التحقق من الصلاحيات وحداثة
   اللقطة. عند تغيّر التحليل يُرفض التصدير بالحالة `409`: اضغط **تحديث النظرة
   التنفيذية**، ثم أعد إعداد الموجز والتصدير. تغيير النطاق أو اللغة يخفي الموجز
   السابق ويتجاهل نتائج التصدير الجاري؛ ويمكن استخدام **إلغاء التصدير** أثناء الانتظار.
5. لإنشاء نسخة PDF، اضغط **طباعة / حفظ بصيغة PDF**، واسمح بالنوافذ المنبثقة
   لهذا الموقع إذا حجب المتصفح نافذة المعاينة. يستخدم المسار تقرير HTML للنطاق
   المُعدّ نفسه، ثم يفتح مربع الطباعة الأصلي في المتصفح؛ اختر **حفظ بصيغة PDF**
   هناك. هذا ليس تنزيل PDF مباشرًا، ولا يُحفظ ملف بمجرد فتح مربع الطباعة.
   تحديث النظرة يعيد قراءة التحليل الموجود ولا يجلب قياسات حية جديدة.
   التنزيل والطباعة لا ينشران التقرير ولا يتجاوزان الموافقة البشرية.

**جودة النماذج** والنتائج المخزنة تخصان **التحليل الكامل**. لا تعيد مرشحات اللوحة
تدريب النماذج أو تقييمها. عند وجود بطاقات تقييم، تُعرض الأدلة وخطوط المقارنة
والقيود؛ وعند غياب التقييم أو عدم دعم الهدف، لا تُختلق درجة أداء. سجلات العمل
المرصودة وحدها لا تثبت احتمال عطل مستقبلي أو العمر المتبقي أو وفورات سببية.
تدعم الواجهة الإنجليزية والعربية من اليمين إلى اليسار والوضعين الفاتح والداكن،
مع جداول للأرقام ومسارات لفحص السجلات.

### معجم مؤشرات الصيانة / Controlled KPI glossary

التعريفات التالية من [سجل المؤشرات في المصدر](../../server/maintenance/kpis.py).
تُطبَّق على النطاق المحدد بالمرشحات، ثم على المجتمع الخاص بكل مؤشر؛ لا يكفي
تشابه اسم عمود في ملف آخر لاعتماد تعريفه.

| المؤشر بالعربية | English name | التعريف الحسابي المبسّط | المجتمع والوحدة أو قيد التفسير |
| --- | --- | --- | --- |
| نسبة أوامر العمل الوقائية | Preventive share of work orders | مجموع الأوامر الوقائية ÷ مجموع الأوامر الوقائية والتصحيحية، مضروبًا في 100. | جميع السجلات المقاسة؛ نسبة مئوية. المقام ليس عدد الأوامر المنجزة. |
| معدل الإصلاح من المرة الأولى | First-time fix rate | مجموع الإصلاحات من المرة الأولى ÷ مجموع الأوامر التصحيحية، مضروبًا في 100. | السجلات التصحيحية فقط (`Work_Order_Type=Corrective`)؛ نسبة مئوية. لا تدخل القيم الصفرية الشكلية في السجلات الوقائية. |
| معدل تكرار الإصلاح | Repeat repair rate | مجموع الإصلاحات المتكررة ÷ مجموع الأوامر التصحيحية، مضروبًا في 100. | المجتمع التصحيحي نفسه؛ نسبة مئوية. لا يُفترض أنه متمّم مؤشر الإصلاح من المرة الأولى دون التحقق من بيانات المصدر. |
| نسبة أوامر العمل المتأخرة | Overdue share of work orders | مجموع الأوامر المتأخرة ÷ مجموع الأوامر المنجزة، مضروبًا في 100. | جميع السجلات المقاسة؛ نسبة مئوية. المتأخر رصيد في لحظة والمنجز نشاط خلال فترة؛ ليست نسبة إغلاق للأوامر. |
| الجاهزية | Availability | مجموع ساعات التشغيل الفعلية ÷ مجموع ساعات التشغيل المخططة، مضروبًا في 100. | جميع السجلات المقاسة؛ نسبة مئوية. هذا هو التعريف الحالي، وليس تلقائيًا «المخطط ناقص التوقف ÷ المخطط»، ولا متوسط عمود `Availability_Pct`. |
| التوقف لكل سجل | Downtime per record | مجموع ساعات التوقف ÷ عدد السجلات ذات قياس التوقف المتاح. | ساعة لكل سجل مقاس، وليس إجمالي التوقف خلال شهر؛ اختلاف عدد السجلات قد يغيّر الإجمالي. |
| الخسارة لكل ساعة توقف | Loss per downtime hour | مجموع خسارة الإنتاج ÷ مجموع ساعات التوقف. | عملة المصدر لكل ساعة توقف، على السجلات المقاسة في الحقلين؛ يلزم توثيق أساس تقدير الخسارة. |
| تكلفة الصيانة لكل ساعة تشغيل | Maintenance cost per operating hour | مجموع تكلفة الصيانة ÷ مجموع ساعات التشغيل الفعلية. | عملة المصدر لكل ساعة تشغيل، على السجلات المقاسة في الحقلين؛ تحقّق من نطاق التكاليف قبل مقارنة المواقع أو العقود. |

**قراءة الأرقام:** تُحسب المعدلات بقسمة مجموع البسط على مجموع المقام، لا بمتوسط
نسب الصفوف؛ وتُضرب النتيجة في 100 للمؤشرات المئوية. يعرض فحص الأدلة أسماء
الأعمدة والصيغة الفعلية، بحيث يمكن إعادة حساب الرقم.

**قراءة التغطية:** تستخدم المؤشرات الثمانية الحالية سياسة `exclude`: يُستبعد
السجل الذي ينقصه عدد صالح في أي حقل تقرؤه الصيغة من البسط والمقام وعدّ السجلات
المقاسة، ويُذكر ضمن `records_unmeasured`. أما `records_excluded` فيعني سجلات
خارج مجتمع المؤشر أصلًا، مثل العمل الوقائي في مؤشر الإصلاح التصحيحي. الصفر
المسجّل قياس صالح؛ الخانة الفارغة ليست صفرًا. لا تُستخدم سياسة `zero` لأي من
هذه المؤشرات؛ ولا يصح اعتمادها إلا إذا صرّح التعريف بأن الفراغ يعني عدم حدوث
شيء وفق توثيق المصدر. المجتمع الفارغ أو المقام الصفري ينتجان قيمة غير محددة،
لا أداءً مثاليًا.

**قراءة العملة:** حقلا المال الحاليان هما `Production_Loss_USD`
و`Maintenance_Cost_USD`. تحقّق من عملتهما ونطاقهما في المصدر؛ لا يحوّل النظام
العملات، ولا يغيّر اختيار العربية أو الإنجليزية العملة أو القيمة المالية.

### التطوير والتسليم

داخل Claude Code في هذا المستودع، استخدم [المهارة `/dashboards`](../../.claude/skills/dashboards/SKILL.md).
يحمّل [الوكيل `dashboard-analyst`](../../.claude/agents/dashboard-analyst.md)
هذه المهارة مسبقًا. مثال: `/dashboards راجع النظرة التنفيذية للتحليل المحدد،
وتحقق من نطاق المؤشرات وأدلتها والعربية RTL مع الحفاظ على الموافقات.` هذه تعليمات
لأداة التطوير، منفصلة عن وكيل الموجز داخل التطبيق. نشر Claude Artifacts المستضافة
مشروط بتوفر الأداة والحساب والصلاحيات؛ **لم يُفعّل نشر مستضاف بهذا التكامل**.

قبل القبول النهائي: يلزم التحقق من هوية الأصول والتوقيت وتوفر المدخلات وقت القرار
والأهداف والأفق الزمني، ثم تقييم تنبؤي زمني مقابل خط أساس؛ ومراجعة مهندس مختص
لتعريفات المؤشرات والأولويات والمصطلحات العربية. ويحتاج النشر الفعلي إلى قبول بيئته
المحددة، بما يشمل الهوية والعزل وقاعدة البيانات والاستعادة والمراقبة والأداء.
نتائج التحقق الحالية مرجعها [README — Testing](../../README.md#testing).

## English — operating handoff

Open **Dashboards**, choose an analysis with a cleaned table, then select the
period and filters. **Analyse maintenance data** starts the existing maintenance
profile. The executive endpoint calculates supported controlled KPIs and review
priorities for the selected records. Each measure exposes its formula,
numerator, denominator, population, measured/excluded coverage and missing-data
policy; unavailable evidence remains explicit.

Use **View evidence** to focus the referenced calculation, or inspect a group
to open its records. Filters remain in the address and survive reloads; access
still requires permission to the run. **Prepare executive brief** reveals
evidence-backed questions. **Report format** defaults to **HTML report**; select
**Word document (.docx)** for a genuine editable DOCX file, then choose
**Download report**. The Word file is not renamed HTML. Both exports use the
prepared brief's scope, filters, language, revision timestamp and content revision
identifier. The server
rechecks access and rejects a changed snapshot with `409`; **Refresh overview**,
prepare the brief again, then retry. Changing scope or language hides the old
brief and discards pending export results. **Cancel export** stops waiting for
an in-flight export in the interface.

**Print / Save as PDF** opens a print preview for the same prepared scope.
Allow popups for this site if the browser blocks the preview. Choose **Save as
PDF** in the browser's native print dialog; this is not a direct PDF download,
and opening the dialog alone does not save a file. Refresh reads the existing
analysis rather than collecting live telemetry. Downloads and printing do not
publish a report or satisfy an approval.

The briefing is deterministic engine output. It does not call an LLM, execute
maintenance, publish a report or satisfy an approval. Stored findings and model
quality remain labelled **Whole analysis**; filtering does not retrain or
re-evaluate them. Missing or unsupported evaluations receive no invented score.
English, Arabic RTL, both themes, evidence tables and record drill-through are
part of the implemented interface.

For development, invoke the linked `/dashboards` skill; `dashboard-analyst`
preloads it. These project instructions are separate from the application's
executive agent. Hosted Claude Artifacts remain conditional and were not
activated. Predictive acceptance still needs suitable asset/timing/target data,
chronological evaluation and engineering review. Production acceptance belongs
to the configured deployment, including identity, tenancy, database, restore,
monitoring and performance checks. See the canonical [testing record](../../README.md#testing).

Implementation rationale: [ADR 0058](../adr/0058-executive-dashboard-agent-and-scoped-evidence.md).
Claude integration and source research: [Executive dashboard research](EXECUTIVE_DASHBOARD_RESEARCH.md).
