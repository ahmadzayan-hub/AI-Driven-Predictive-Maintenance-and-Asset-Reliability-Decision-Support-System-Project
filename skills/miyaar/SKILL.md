---
name: miyaar
description: Use Miyaar's governed analytics tools and verified report summaries. استخدم أدوات معيار للتحليلات المنضبطة وملخصات التقارير المتحققة.
---

Miyaar remains a web application. This package adds its existing stdio MCP
tools to Hermes; it does not embed the website or start a web server.

Discover the available Miyaar tools first. The default package exposes only
`help` and connects no workspace. A list of capabilities in a help reply is
not an access grant. Never edit configuration, install dependencies, enable
tools, connect storage, or invoke another process to bypass the listed scope.

For a configured workspace, this first package permits only `help`,
`run_status` and `explain_report`. All other tool opt-ins are rejected, including
memory, preferences, starting runs, knowledge search and agent scorecards.
Do not bypass that restriction through the legacy MCP server or other tools.
Opening a configured workspace reads its memory file even without `recall`,
and SQLite initialization may migrate schema/create WAL files. These startup
effects require explicit approval; a read-tools list does not prevent them.

Raw dataset rows,
private references and secrets must not enter model context. Quote verified
report headlines with their run identifiers. Do not invent maintenance
results from the bundled sales sample. Starting runs and approving/publishing
remain outside this package, in the web application. Report errors and
uncertain outcomes without widening access or changing configuration.

يبقى معيار تطبيق ويب؛ تضيف هذه الحزمة أدواته إلى Hermes عبر MCP ولا تشغّل
خادم ويب. ابدأ باكتشاف الأدوات المتاحة. الوضع الافتراضي يتيح المساعدة فقط،
ولا يمنح وصف القدرات في رد المساعدة صلاحية إضافية. لا تعدّل الإعدادات ولا
تفعّل أدوات أو تصل بيانات أو تشغّل عملية أخرى لتجاوز النطاق المعتمد.
لا ترسل صفوف البيانات أو المراجع الخاصة أو الأسرار إلى النموذج. اقتبس
العناوين المتحققة مع معرّف التشغيل، ولا تعرض عينة المبيعات كدليل صيانة.
تسمح هذه الحزمة فقط بالمساعدة وحالة التشغيل وشرح التقرير؛ وترفض تفعيل
أدوات الذاكرة والتفضيلات وبدء التحليل والبحث في المعرفة وبطاقات الوكلاء.
عند ربط مساحة عمل، يُقرأ ملف الذاكرة حتى دون أداة الاسترجاع، وقد تُحدّث
قاعدة SQLite مخططها وتنشئ ملفات WAL. هذه الآثار تحتاج موافقة صريحة؛
قائمة أدوات القراءة لا تمنعها. يبقى بدء التحليل والموافقة والنشر في تطبيق
الويب. أبلغ عن الأخطاء دون توسيع الصلاحيات أو تغيير الإعدادات.
