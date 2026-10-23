import type { RunDetail } from '../../shared/types'
import { summarizeRunEvidence } from './evidence'

/** Build a draft from a *server-owned* validated run. Does not certify model accuracy. */
export function motionFromRun(run: RunDetail) {
  const validation = summarizeRunEvidence(run)
  const headline = run.reports?.find((report) => report.headline?.trim())?.headline
  if (validation.status !== 'passed' || !run.report?.id || !headline) {
    throw new Error('A completed run with independent evidence checks and a report is required')
  }
  if (headline.length > 480 || run.goal.length > 480) {
    throw new Error('This run needs a shorter human-reviewed motion narrative')
  }
  const evidence = [{
    source_id: run.id, revision: 'v' + run.report.version,
    locator: 'report:' + run.report.id,
    data_status: 'RECORDED_IN_REGISTER' as const,
  }]
  return {
    schema: 'motion-evidence-v1', language: run.report_language,
    format: 'wide', classification: 'INTERNAL', duration: 15,
    source_context: {
      run_id: run.id, dataset_name: run.dataset_name,
      report_id: run.report.id, version: run.report.version,
      validation: 'RUN_LEVEL_CHECKS_PASSED',
      warning: 'A passing run validator is not evidence of real-world model accuracy',
    },
    approval: { state: 'DRAFT', issued: false },
    scenes: [
      { kind: 'hook', text: run.goal, evidence },
      { kind: 'evidence', text: headline, evidence },
      { kind: 'action', text: run.report_language === 'ar'
          ? 'النتائج والتوصيات تحتاج مراجعة بشرية قبل النشر.'
          : 'Review calculations and recommendations before publication.', evidence },
    ],
  }
}

export function downloadMotionRun(manifest: object) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(manifest, null, 2)], {
    type: 'application/json',
  }))
  try {
    const a = document.createElement('a')
    a.href = url
    a.download = 'asset-reliability-motion-draft.json'
    a.click()
  } finally {
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
}
