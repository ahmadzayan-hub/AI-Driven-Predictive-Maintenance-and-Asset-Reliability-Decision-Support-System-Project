import { formatNumberIn, interpolate, type Locale } from '../../i18n'
import { jarvisMessages } from '../../i18n/jarvis'
import type { JarvisAnswer } from './JarvisWorkspace'

/** Keep analytical units and uncertainty audible; never rewrite displayed evidence. */
export function jarvisSpeech(answer: JarvisAnswer | null, locale: Locale): string {
  if (!answer?.result) return answer?.text ?? ''
  const result = answer.result
  const messages = jarvisMessages[locale]
  const units: Record<string, string> = {
    percent: '%', hours: messages.hours, years: messages.years, count: messages.count,
    ratio: messages.times, money: result.currency ?? messages.currencyUnknown,
  }
  const scope = interpolate(messages.speechScope, { records: result.records, total: result.total_records })
  return [scope, ...result.measures.map(m => {
    const value = m.value === null ? messages.noValue : `${formatNumberIn(locale, m.value, { maximumFractionDigits: 2 })} ${units[m.scale ?? ''] ?? messages.unitUnknown}`
    const reason = m.reason ?? (m.value === null ? messages.undefinedReason : '')
    const coverage = m.records === undefined || m.records_unmeasured === undefined ? messages.coverageUnknown
      : interpolate(messages.speechCoverage, { measured: m.records, unmeasured: m.records_unmeasured })
    return `${m.title}: ${value}. ${reason} ${coverage}`
  })].join(' ')
}
