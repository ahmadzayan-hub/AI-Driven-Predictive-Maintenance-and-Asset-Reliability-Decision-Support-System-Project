import { definePack } from '../../i18n/pack'

/** Strings of the derived-columns section of the mapping panel (27
 *  October 2026). They ship with the Datasets chunk, not the first load. */
export const derivedMessages = definePack({
  title: 'Derived columns',
  help: 'A column computed from the measures with + − × ÷ and brackets, such as cost / hours. A later column may read an earlier one. A cell stays empty where a value is missing or a division divides by zero.',
  name: 'Column name',
  formula: 'Formula',
  add: 'Add a derived column',
  remove: 'Remove derived column {n}',
  item: 'Derived column {n}',
}, {
  title: 'الأعمدة المشتقة',
  help: 'عمود يُحسب من المقاييس بالعمليات + − × ÷ والأقواس، مثل cost / hours. يمكن لعمود لاحق أن يقرأ عموداً سابقاً. تبقى الخلية فارغة حين تنقص قيمة أو يُقسم على صفر.',
  name: 'اسم العمود',
  formula: 'الصيغة',
  add: 'إضافة عمود مشتق',
  remove: 'إزالة العمود المشتق {n}',
  item: 'العمود المشتق {n}',
})
