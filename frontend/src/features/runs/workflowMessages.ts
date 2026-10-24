import { definePack } from '../../i18n/pack'

export const workflowMessages = definePack({
  'workflow.draftWork': 'Draft maintenance work using this analysis source',
  'workflow.datasetsLoading': 'Loading stored datasets…',
  'workflow.datasetsFailed': 'Stored datasets could not be refreshed. Any choices shown are from the last successful load; your selection and question are unchanged.',
  'workflow.retryDatasets': 'Retry loading datasets',
  'workflow.runsLoading': 'Loading previous runs…',
  'workflow.runsFailed': 'Previous runs could not be refreshed. Any runs shown are from the last successful load. Retry to check for updates.',
  'workflow.retryRuns': 'Retry loading previous runs',
  'workflow.runsEmpty': 'No previous runs were returned for this workspace.',
  'workflow.openReport': 'Next: open the exact report below before confirming that you have read it.',
  'workflow.confirmRead': 'Next: confirm that you have read this exact report. Opening it alone does not approve publication.',
  'workflow.readyReview': 'Ready for your decision. Nothing is published until you choose Approve and publish and the server confirms it.',
}, {
  'workflow.draftWork': 'إنشاء مسودة صيانة من مصدر هذا التحليل',
  'workflow.datasetsLoading': 'جارٍ تحميل مجموعات البيانات المحفوظة…',
  'workflow.datasetsFailed': 'تعذّر تحديث مجموعات البيانات المحفوظة. الخيارات المعروضة، إن وجدت، من آخر تحميل ناجح؛ لم يتغير اختيارك أو سؤالك.',
  'workflow.retryDatasets': 'إعادة محاولة تحميل البيانات',
  'workflow.runsLoading': 'جارٍ تحميل التحليلات السابقة…',
  'workflow.runsFailed': 'تعذّر تحديث التحليلات السابقة. التحليلات المعروضة، إن وجدت، من آخر تحميل ناجح. أعد المحاولة للتحقق من التحديثات.',
  'workflow.retryRuns': 'إعادة محاولة تحميل التحليلات السابقة',
  'workflow.runsEmpty': 'لم تُرجع الخدمة تحليلات سابقة لمساحة العمل هذه.',
  'workflow.openReport': 'التالي: افتح التقرير المحدد أدناه قبل تأكيد قراءته.',
  'workflow.confirmRead': 'التالي: أكّد أنك قرأت هذا التقرير المحدد. فتحه وحده لا يعني الموافقة على النشر.',
  'workflow.readyReview': 'جاهز لقرارك. لا يُنشر شيء حتى تختار «الموافقة والنشر» ويؤكّد الخادم ذلك.',
})
