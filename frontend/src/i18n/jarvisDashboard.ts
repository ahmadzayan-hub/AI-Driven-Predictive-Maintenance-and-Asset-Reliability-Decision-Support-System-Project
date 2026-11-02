import { definePack } from './pack'

export const jarvisDashboardMessages = definePack({
  title: 'Jarvis OS · decision workspace',
  help: 'Ask about the same report and filters as these charts. Calculated evidence, with sources and human review.',
  open: 'Connect this view to Jarvis', reconnect: 'Refresh Jarvis scope', close: 'Close Jarvis',
  connecting: 'Connecting the selected scope…',
  changed: 'The view changed. Connect the current scope before asking again; the previous answer and review were cleared.',
  unavailable: 'Jarvis could not connect this scope. The report may be unavailable, incomplete or outside your permissions. Retry after checking the selection.',
  readonly: 'Connecting a report requires permission to create a session and select its data. Charts remain available in read-only mode.',
  scope: 'Current report', mode: 'Recorded analysis · no live telemetry claim',
  loading: 'Opening Jarvis…',
}, {
  title: 'Jarvis OS · مساحة القرار',
  help: 'اسأل عن التقرير والمرشحات نفسها في هذه الرسوم. أدلة محسوبة مع مصادر ومراجعة بشرية.',
  open: 'ربط هذا العرض بـ Jarvis', reconnect: 'تحديث نطاق Jarvis', close: 'إغلاق Jarvis',
  connecting: 'جارٍ ربط النطاق المحدد…',
  changed: 'تغيّر العرض. اربط النطاق الحالي قبل السؤال مجدداً؛ مُسحت الإجابة والمراجعة السابقتان.',
  unavailable: 'تعذر ربط هذا النطاق بـ Jarvis. قد يكون التقرير غير متاح أو غير مكتمل أو خارج صلاحياتك. تحقق من الاختيار ثم أعد المحاولة.',
  readonly: 'يتطلب ربط التقرير صلاحية إنشاء جلسة واختيار بياناتها. تظل الرسوم متاحة في وضع القراءة فقط.',
  scope: 'التقرير الحالي', mode: 'تحليل مسجل · لا يدّعي قياسات حية',
  loading: 'جارٍ فتح Jarvis…',
})
