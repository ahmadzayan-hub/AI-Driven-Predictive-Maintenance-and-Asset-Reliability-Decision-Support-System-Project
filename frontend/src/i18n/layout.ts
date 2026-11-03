import { definePack } from './pack'
export const layoutMessages = definePack({
  heading: 'Designed for this data', objective: 'What do you want to understand?', redesign: 'Redesign',
  designing: 'Designing…', model: 'Designed by {name}', rules: 'Rule-based design · no model used',
  why: 'How it was designed', earlier: 'Earlier layouts', version: 'Version {n} · {time}', restore: 'Restore',
  pin: 'Pin', pinned: 'Pinned', unavailable: 'Not available yet', failed: 'The layout could not be designed. The last valid layout is kept.',
  noValue: 'No value', rows: '{n} records', loading: 'Calculating…', error: 'This section could not be calculated.',
  happening: 'What is happening', expected: 'What is expected', decide: 'What to decide', proposed: 'Proposed · awaiting your review',
  evidence: 'View evidence', review: 'Review and decide', noDecision: 'No decision is proposed by this analysis.',
  riskReady: 'A risk ranking is available for the assets in scope.', selected: 'Selected: {name}', drivers: 'What drives it',
  sample: 'Records behind it', clear: 'Clear selection', askCost: 'What is total maintenance cost?', askFailures: 'How many failures?', askTotal: 'What is the total {column}?', askSplit: 'What is the total {column} by {group}?',
  jarvisScope: 'Ask Miyaar answers for this selection.', jarvisOnly: 'Ask Miyaar has no calculated question for this selection yet.',
}, {
  heading: 'مصمَّم لهذه البيانات', objective: 'ما الذي تريد فهمه؟', redesign: 'إعادة التصميم',
  designing: 'جارٍ التصميم…', model: 'صمّمه {name}', rules: 'تصميم بالقواعد · دون نموذج',
  why: 'كيف صُمِّم', earlier: 'تصاميم سابقة', version: 'الإصدار {n} · {time}', restore: 'استعادة',
  pin: 'تثبيت', pinned: 'مثبَّت', unavailable: 'غير متاح بعد', failed: 'تعذّر التصميم. أُبقي آخر تصميم صالح.',
  noValue: 'لا قيمة', rows: '{n} سجل', loading: 'جارٍ الحساب…', error: 'تعذّر حساب هذا القسم.',
  happening: 'ماذا يحدث', expected: 'ماذا يُتوقع', decide: 'ما القرار', proposed: 'مقترح · بانتظار مراجعتك',
  evidence: 'اعرض الأدلة', review: 'راجع واتخذ القرار', noDecision: 'لا يقترح هذا التحليل قرارًا.',
  riskReady: 'ترتيب المخاطر متاح للأصول ضمن النطاق.', selected: 'المحدد: {name}', drivers: 'ما الذي يحركه',
  sample: 'السجلات خلفه', clear: 'إلغاء التحديد', askCost: 'ما إجمالي تكلفة الصيانة؟', askFailures: 'كم عدد الأعطال؟', askTotal: 'ما إجمالي {column}؟', askSplit: 'ما إجمالي {column} حسب {group}؟',
  jarvisScope: 'يجيب «اسأل معيار» عن هذا التحديد.', jarvisOnly: 'لا يوجد لدى «اسأل معيار» سؤال محسوب لهذا التحديد بعد.',
})
