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
4. اضغط **إعداد الموجز التنفيذي** لعرض أسئلة المراجعة المستندة إلى الأدلة، ثم
   **تنزيل الموجز وأدلته (JSON)** لحفظ لقطة النطاق واللغة الحاليين. تغيير النطاق
   يخفي الموجز السابق حتى يُعدّ مجددًا. تحديث النظرة يعيد قراءة التحليل الموجود؛
   لا يجلب قياسات حية جديدة. التنزيل لا ينشر التقرير ولا يتجاوز الموافقة البشرية.

**جودة النماذج** والنتائج المخزنة تخصان **التحليل الكامل**. لا تعيد مرشحات اللوحة
تدريب النماذج أو تقييمها. عند وجود بطاقات تقييم، تُعرض الأدلة وخطوط المقارنة
والقيود؛ وعند غياب التقييم أو عدم دعم الهدف، لا تُختلق درجة أداء. سجلات العمل
المرصودة وحدها لا تثبت احتمال عطل مستقبلي أو العمر المتبقي أو وفورات سببية.
تدعم الواجهة الإنجليزية والعربية من اليمين إلى اليسار والوضعين الفاتح والداكن،
مع جداول للأرقام ومسارات لفحص السجلات.

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
evidence-backed questions. Its JSON download is the current run/filter/language
snapshot, and changing scope hides the previous prepared brief. Refresh reads
the existing analysis rather than collecting live telemetry.

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
