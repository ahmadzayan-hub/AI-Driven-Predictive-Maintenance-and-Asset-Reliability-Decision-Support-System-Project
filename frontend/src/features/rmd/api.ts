import { API_BASE, AUTH_EXPIRED_EVENT, ApiError, authHeaders, request } from '../../shared/api'
import { currentLocale } from '../../i18n'
import type { AnalysisFilters, Clause, EvidenceAnalysis, EvidencePack, EvidencePage, EvidenceQuery, EvidenceSource, ProposedAction, SheetMapping } from './types'

const base = '/api/rmd/packs'
const packPath = (id: string) => `${base}/${encodeURIComponent(id)}`
const localized = (url: string) => `${url}${url.includes('?') ? '&' : '?'}language=${currentLocale()}`
const read = <T>(url: string, signal?: AbortSignal) => request<T>(localized(url), { signal }, 90_000)
const write = <T>(url: string, body: object, method = 'POST') => request<T>(localized(url), { method, body: JSON.stringify(body) }, 90_000)

/** Downloads preserve the same credential boundary as JSON reads. No API URL
 * is exposed as an unauthenticated anchor or cached as a public asset. */
async function download(url: string, fallback: string) {
  const headers = authHeaders()
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 90_000)
  try {
    const response = await fetch(`${API_BASE}${localized(url)}`, { headers, signal: controller.signal, cache: 'no-store' })
    if (!response.ok) {
      if (response.status === 401 && headers.Authorization && headers.Authorization === authHeaders().Authorization) window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT))
      let message = ''
      try { const body = await response.json(); if (typeof body.detail === 'string') message = body.detail } catch { /* use a translated caller fallback */ }
      throw new ApiError(message, response.status)
    }
    const disposition=response.headers.get('content-disposition')??''
    let name=disposition.match(/filename="([^"/\\]+)"/)?.[1]??fallback
    const encoded=disposition.match(/filename\*\s*=\s*UTF-8'[^']*'([^;]+)/i)?.[1]
    if(encoded){try{name=decodeURIComponent(encoded.trim().replace(/^"|"$/g,''))}catch{/* retain the safe fallback */}}
    name=name.replace(/[\u0000-\u001f/\\]/g,'_')||fallback
    return { blob: await response.blob(), name }
  } finally { clearTimeout(timer) }
}

export const rmdApi = {
  packs: (signal?: AbortSignal) => read<{ packs: EvidencePack[] }>(base, signal),
  pack: (id: string, signal?: AbortSignal) => read<EvidencePack>(packPath(id), signal),
  create: (title: string, key: string) => write<EvidencePack>(base, { title, idempotency_key: key }),
  source: (pack: string, source: string, signal?: AbortSignal) => read<EvidenceSource>(`${packPath(pack)}/sources/${encodeURIComponent(source)}`, signal),
  upload: (pack: string, file: File, kind: 'procedure' | 'workbook') => request<EvidenceSource>(localized(`${packPath(pack)}/sources?${new URLSearchParams({kind,filename:file.name})}`), {
    method: 'POST', body: file, headers: { 'Content-Type': 'application/octet-stream' },
  }, 120_000),
  map: (pack: string, source: string, sheets: SheetMapping[], revision?: number) => write<EvidenceSource>(`${packPath(pack)}/sources/${encodeURIComponent(source)}/mapping`, { sheets: sheets.map(sheet=>({...sheet,columns:Object.fromEntries(Object.entries(sheet.columns).filter(([,column])=>column!==''))})), expected_revision: revision }, 'PUT'),
  analyse: (pack: string, filters: AnalysisFilters, key: string) => write<EvidenceAnalysis>(`${packPath(pack)}/analyses`, { filters, idempotency_key: key }),
  reviewRun: (pack: string, analysis: string, key: string) => write<{ run_id: string }>(`${packPath(pack)}/analyses/${encodeURIComponent(analysis)}/review-run`, { idempotency_key: key }),
  analysis: (pack: string, id: string, signal?: AbortSignal) => read<EvidenceAnalysis>(`${packPath(pack)}/analyses/${encodeURIComponent(id)}`, signal),
  records: (pack: string, id: string, query: EvidenceQuery, signal?: AbortSignal) => request<EvidencePage>(localized(`${packPath(pack)}/analyses/${encodeURIComponent(id)}/records/query`), {
    method: 'POST', body: JSON.stringify(query), signal,
  }, 90_000),
  knowledge: (pack: string, q: string, source = '', signal?: AbortSignal) => read<{ hits: Clause[]; total?: number }>(`${packPath(pack)}/knowledge?${new URLSearchParams(source?{q,source_id:source}:{q})}`, signal),
  assistant: <T>(pack: string, question: string, analysis: string | undefined, signal: AbortSignal) => request<T>(localized(`${packPath(pack)}/assistant`), {
    method: 'POST', body: JSON.stringify({ question, analysis_id: analysis, language: currentLocale() }), signal,
  }, 90_000),
  decideLink: (pack: string, id: string, decision: 'confirmed' | 'rejected', note: string, revision = 1) => write<unknown>(`${packPath(pack)}/links/${encodeURIComponent(id)}`, { decision, note, expected_revision: revision }, 'PATCH'),
  actions: (pack: string, signal?: AbortSignal) => read<{ actions: ProposedAction[] }>(`${packPath(pack)}/actions`, signal),
  proposeAction: (pack: string, analysis: string, priority: string, key: string) => write<ProposedAction>(`${packPath(pack)}/actions`, { analysis_id: analysis, priority_id: priority, idempotency_key: key }),
  original: (pack: string, source: EvidenceSource) => download(`${packPath(pack)}/sources/${encodeURIComponent(source.id)}/download`, source.name),
  export: (pack: string, analysis: string, format: 'html' | 'csv') => download(`${packPath(pack)}/analyses/${encodeURIComponent(analysis)}/export?format=${format}`, `rmd-evidence.${format}`),
}

export function saveDownload({ blob, name }: { blob: Blob; name: string }) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url; anchor.download = name; anchor.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
