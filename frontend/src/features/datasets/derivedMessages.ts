import { definePack } from '../../i18n/pack'

/** Strings of the derived-columns section of the mapping panel (27
 *  October 2026). They ship with the Datasets chunk, not the first load. */
export const derivedMessages = definePack({
  title: 'Derived columns',
  help: 'Computed from the measures with + − × ÷ and brackets, such as cost / hours; a later column may read an earlier one. Empty where a value is missing or a division is by zero.',
  name: 'Column name',
  formula: 'Formula',
  add: 'Add a derived column',
  remove: 'Remove derived column {n}',
  item: 'Derived column {n}',
  fiscal: 'Fiscal year starts in',
  fiscalHelp: 'January means the calendar year. Another month labels quarters FY2026-Q1 and years FY2026, by the year it ends in.',
  limits: 'Allowed range',
  min: 'Lowest',
  max: 'Highest',
}, {
  title: 'الأعمدة المشتقة',
  help: 'يُحسب من المقاييس بـ+ − × ÷ والأقواس، مثل cost / hours؛ ويقرأ اللاحق السابق. يبقى فارغاً حين تنقص قيمة أو يُقسم على صفر.',
  name: 'اسم العمود',
  formula: 'الصيغة',
  add: 'إضافة عمود مشتق',
  remove: 'إزالة العمود المشتق {n}',
  item: 'العمود المشتق {n}',
  fiscal: 'تبدأ السنة المالية في',
  fiscalHelp: 'يناير يعني السنة الميلادية. وأي شهر آخر يسمّي الأرباع FY2026-Q1 والسنوات FY2026 بسنة انتهائها.',
  limits: 'النطاق المسموح',
  min: 'الأدنى',
  max: 'الأعلى',
})
