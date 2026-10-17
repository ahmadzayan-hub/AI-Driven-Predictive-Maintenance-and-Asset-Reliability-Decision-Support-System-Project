import { definePack } from '../../i18n/pack'

export const intakeMessages = definePack({
  'intake.goal': 'Analyze my dataset, explain its quality and limitations, and produce an evidence-based report',
  'intake.required': 'Upload a file, paste CSV, or choose a stored dataset before starting.',
  'intake.wait': 'Wait for the file to finish uploading before starting the analysis.',
  'intake.sheet': 'Workbook sheet',
  'intake.sheetHelp': 'Select the sheet to analyze. Each selected sheet is stored as its own dataset; join related sheets by their keys when needed.',
  'intake.columns': 'Review column roles before analysis',
  'intake.workflow': 'Upload → review columns → start the agents → explore the dashboard. The agents profile, clean, analyze and validate your data automatically after Start run. Reports wait for your approval.',
  'intake.limits': 'Supported tabular files: CSV/TSV, Excel (.xlsx/.xlsm), JSON and JSON Lines. Limit: 4 MB uploaded, 50,000 rows and 500 columns; 10 MB after conversion. PDF, images, Parquet and old .xls files need conversion first.',
  'intake.models': 'Choose the models profile to include baseline-tested regression, classification, clustering and seasonal analysis. Unsuitable data produces limitations, not invented predictions.',
}, {
  'intake.goal': 'حلّل بياناتي واشرح جودتها وقيودها وأنتج تقريرًا يستند إلى الأدلة',
  'intake.required': 'ارفع ملفًا أو الصق CSV أو اختر مجموعة بيانات محفوظة قبل البدء.',
  'intake.wait': 'انتظر اكتمال رفع الملف قبل بدء التحليل.',
  'intake.sheet': 'ورقة المصنّف',
  'intake.sheetHelp': 'اختر الورقة المراد تحليلها. تُحفظ كل ورقة تختارها كمجموعة بيانات مستقلة؛ اربط الأوراق ذات الصلة بمفاتيحها عند الحاجة.',
  'intake.columns': 'راجع أدوار الأعمدة قبل التحليل',
  'intake.workflow': 'ارفع البيانات ← راجع الأعمدة ← ابدأ الوكلاء ← استكشف لوحة البيانات. يفحص الوكلاء البيانات وينظفونها ويحللونها ويتحققون منها تلقائيًا بعد بدء التشغيل. تنتظر التقارير موافقتك.',
  'intake.limits': 'الملفات الجدولية المدعومة: CSV وTSV وExcel ‏(.xlsx/.xlsm) وJSON وJSON Lines. الحد: 4 ميغابايت عند الرفع و50,000 صف و500 عمود؛ و10 ميغابايت بعد التحويل. يجب تحويل PDF والصور وParquet وملفات .xls القديمة أولًا.',
  'intake.models': 'اختر ملف models لإضافة الانحدار والتصنيف والتجميع والتحليل الموسمي مع المقارنة بخط أساس. تُعرض قيود البيانات غير المناسبة بدلًا من اختلاق تنبؤات.',
})
