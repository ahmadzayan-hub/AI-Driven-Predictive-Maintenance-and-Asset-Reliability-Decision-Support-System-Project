import type { ReactNode } from 'react'
import type { Locale } from '../../i18n'
import type { EvidenceText, EvidenceValue } from './types'

export function evidenceText(value: EvidenceText | undefined | null, locale: Locale): string {
  if (typeof value === 'string') return value
  return value?.[locale] ?? value?.en ?? value?.ar ?? ''
}

export function valueText(value: EvidenceValue | undefined, missing: string): string {
  return value === undefined || value === null || value === '' ? missing : String(value)
}

/** Source metadata is quoted text. Unknown fields remain inspectable without
 * injecting markup or implying a client-side interpretation. */
export function EvidenceDetails({ value, empty, depth = 0 }: { value: unknown; empty: string; depth?: number }): ReactNode {
  if (value === null || value === undefined || value === '') return <span className="rmd-muted">{empty}</span>
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return <span dir="auto">{String(value)}</span>
  if (depth > 5) return <pre className="rmd-pre" dir="auto">{JSON.stringify(value, null, 2)}</pre>
  if (Array.isArray(value)) return value.length ? <ul className="rmd-list">{value.map((item, index) => <li key={index}><EvidenceDetails value={item} empty={empty} depth={depth + 1} /></li>)}</ul> : <span className="rmd-muted">{empty}</span>
  if (typeof value === 'object') return <dl className="rmd-details">{Object.entries(value).map(([key, item]) => <div key={key}><dt dir="auto">{key.replaceAll('_', ' ')}</dt><dd><EvidenceDetails value={item} empty={empty} depth={depth + 1} /></dd></div>)}</dl>
  return <span className="rmd-muted">{empty}</span>
}
