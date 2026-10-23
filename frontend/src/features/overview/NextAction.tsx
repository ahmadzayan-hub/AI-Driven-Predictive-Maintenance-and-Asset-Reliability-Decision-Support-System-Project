import { definePack, usePack } from '../../i18n/pack'
import type { RunSummary } from '../../shared/types'
import { stateLabel } from '../../shared/labels'
import { recentRuns, waitingForApproval } from './summary'

export const journeyMessages = definePack({
  journey: 'Your next step',
  upload: 'Prepare your data',
  quality: 'Check quality',
  analyse: 'Run analysis',
  review: 'Review report',
  start: 'Start with your maintenance data',
  startHelp: 'Upload a dataset, check its columns and quality, then choose an analysis.',
  ready: 'Report available · awaiting your review',
  readyHelp: 'Analysis progress is not approval. Read the report and its evidence before deciding.',
  active: 'Your analysis is in progress',
  activeHelp: 'Open the run for recorded stages and any action needed. Progress is not a quality score.',
  stopped: 'This analysis needs attention',
  stoppedHelp: 'Inspect the recorded result and limitations before retrying or using its findings.',
  view: 'Open analysis',
  reviewAction: 'Review this report',
  uploadAction: 'Upload data',
  demo: 'Explore the sample report',
  demoHelp: 'Fictional data, not your assets.',
  steps: 'Workflow steps',
  counts: 'Workspace totals',
  basis: 'Count basis',
  countBasis: 'Workspace count from {source}; source as-of unavailable. Owner unassigned; no performance target.',
  evidence: 'Analysis checks and optional exports',
  tools: 'Other workflows',
}, {
  journey: 'خطوتك التالية',
  upload: 'تجهيز البيانات',
  quality: 'فحص الجودة',
  analyse: 'تشغيل التحليل',
  review: 'مراجعة التقرير',
  start: 'ابدأ ببيانات الصيانة',
  startHelp: 'ارفع مجموعة بيانات، وراجع أعمدتها وجودتها، ثم اختر التحليل.',
  ready: 'التقرير متاح · بانتظار مراجعتك',
  readyHelp: 'اكتمال مراحل التحليل لا يعني الاعتماد. اقرأ التقرير وأدلته قبل اتخاذ القرار.',
  active: 'تحليلك قيد التنفيذ',
  activeHelp: 'افتح التحليل لمتابعة المراحل المسجلة وأي إجراء مطلوب. التقدم ليس درجة للجودة.',
  stopped: 'هذا التحليل يحتاج إلى متابعة',
  stoppedHelp: 'راجع النتيجة المسجلة وحدودها قبل إعادة المحاولة أو استخدام النتائج.',
  view: 'فتح التحليل',
  reviewAction: 'مراجعة هذا التقرير',
  uploadAction: 'رفع البيانات',
  demo: 'استعرض التقرير التجريبي',
  demoHelp: 'بيانات افتراضية، وليست بيانات أصولك.',
  steps: 'خطوات العمل',
  counts: 'إجماليات مساحة العمل',
  basis: 'تفسير العدد',
  countBasis: 'عدد من مساحة العمل، المصدر {source}؛ تاريخ المصدر غير متاح. المسؤول غير محدد؛ لا يوجد هدف أداء.',
  evidence: 'فحوص التحليل والتصدير الاختياري',
  tools: 'مسارات عمل أخرى',
})

/** An existing run, never an invented workflow or a claim about model readiness. */
export function nextActionRun(runs: RunSummary[]): RunSummary | undefined {
  return waitingForApproval(runs)[0]
    ?? recentRuns(runs, runs.length).find((run) => ['running', 'queued'].includes(run.state))
    ?? recentRuns(runs, runs.length).find((run) => ['failed', 'partially_completed'].includes(run.state))
}

export function NextAction({ runs, canStart, onUpload, onOpenRun }: {
  runs: RunSummary[]
  canStart: boolean
  onUpload: () => void
  onOpenRun: (id: string) => void
}) {
  const { t } = usePack(journeyMessages)
  const run = canStart ? nextActionRun(runs) : recentRuns(runs)[0]
  const waiting = run?.state === 'awaiting_approval'
  const active = run?.state === 'running' || run?.state === 'queued'
  const heading = !canStart ? 'demo' : waiting ? 'ready' : active ? 'active' : run ? 'stopped' : 'start'
  const step = run ? (active ? 2 : 3) : 0
  return <section className="next-action" aria-labelledby="next-action-title">
    <p className="next-action__eyebrow">{t('journey')}</p>
    <h3 id="next-action-title">{t(heading)}</h3>
    <p>{t(`${heading}Help`)}</p>
    {run ? <p className="next-action__source"><span dir="auto">{run.dataset_name}</span> · {stateLabel(t, run.state)}</p> : null}
    {run || canStart ? <button className="btn btn--primary" type="button" onClick={() => run ? onOpenRun(run.id) : onUpload()}>
      {t(run ? (waiting && canStart ? 'reviewAction' : 'view') : 'uploadAction')}
    </button> : null}
    <details className="next-action__help"><summary>{t('steps')}</summary>
    <ol className="next-action__steps" aria-label={t('journey')}>
      {(['upload', 'quality', 'analyse', 'review'] as const).map((label, index) => <li key={label} aria-current={index === step ? 'step' : undefined}><span aria-hidden="true">{index + 1}</span>{t(label)}</li>)}
    </ol></details>
  </section>
}
