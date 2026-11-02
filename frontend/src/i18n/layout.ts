import { definePack } from './pack'
export const layoutMessages = definePack({
  heading: 'Designed for this data', objective: 'What do you want to understand?', redesign: 'Redesign',
  designing: 'Designing…', model: 'Designed by {name}', rules: 'Rule-based design · no model used',
  why: 'How it was designed', earlier: 'Earlier layouts', version: 'Version {n} · {time}', restore: 'Restore',
  pin: 'Pin', pinned: 'Pinned', unavailable: 'Not available yet', failed: 'The layout could not be designed. The last valid layout is kept.',
  noValue: 'No value', rows: '{n} records', loading: 'Calculating…', error: 'This section could not be calculated.',
}, {
  heading: 'مصمَّم لهذه البيانات', objective: 'ما الذي تريد فهمه؟', redesign: 'إعادة التصميم',
  designing: 'جارٍ التصميم…', model: 'صمّمه {name}', rules: 'تصميم بالقواعد · دون نموذج',
  why: 'كيف صُمِّم', earlier: 'تصاميم سابقة', version: 'الإصدار {n} · {time}', restore: 'استعادة',
  pin: 'تثبيت', pinned: 'مثبَّت', unavailable: 'غير متاح بعد', failed: 'تعذّر التصميم. أُبقي آخر تصميم صالح.',
  noValue: 'لا قيمة', rows: '{n} سجل', loading: 'جارٍ الحساب…', error: 'تعذّر حساب هذا القسم.',
})
