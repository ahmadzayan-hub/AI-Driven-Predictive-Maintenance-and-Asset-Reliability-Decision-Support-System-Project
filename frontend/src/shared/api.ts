import { translate } from '../i18n'
import type { AuthConfig, ColumnMapping, DatasetDetail, DatasetSummary, ExportPayload, IdentityInfo, JoinPreview, JoinSpec, KpiPolicy, MappingProblem, Pipelines, QueryAnswer, QuerySpec, RecordsPage, RecordsSpec, RunDetail, RunExecutive, RunKpis, RunSummary, SessionState, TableField, TableFilter, TranscriptEntry, UploadResult, Usage } from './types'

export const API_BASE = import.meta.env.VITE_API_BASE ?? ''
const REQUEST_TIMEOUT_MS = 10_000
// Run reads/controls may wait behind a serialized stage. Local narration is
// bounded to 60 seconds; allow its response and commit to reach the browser.
const RUN_REQUEST_TIMEOUT_MS = 90_000
// A 4 MB file on a slow connection, then read on the server.
const UPLOAD_TIMEOUT_MS = 60_000

/** The most one upload can be (server/datasets.py, ADR 0024). Checked
 *  here only to save a wasted transfer; the server decides. */
export const MAX_UPLOAD_BYTES = 4_000_000
export const UPLOAD_ACCEPT = '.csv,.tsv,.tab,.txt,.xlsx,.xlsm,.json,.jsonl,.ndjson'

export class ApiError extends Error {
  status: number
  offline: boolean
  /** Field-level reasons, when the server gives them (a refused mapping). */
  problems: MappingProblem[]

  constructor(message: string, status = 0, offline = false, problems: MappingProblem[] = []) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.offline = offline
    this.problems = problems
  }
}

/** The server's `detail`: a sentence, or a summary with field errors. */
function readDetail(body: unknown): { message: string | null; problems: MappingProblem[] } {
  if (!body || typeof body !== 'object' || !('detail' in body)) return { message: null, problems: [] }
  const detail = (body as { detail: unknown }).detail
  if (typeof detail === 'string') return { message: detail, problems: [] }
  if (detail && typeof detail === 'object' && 'message' in detail) {
    const { message, errors } = detail as { message: unknown; errors?: unknown }
    return {
      message: typeof message === 'string' ? message : null,
      problems: Array.isArray(errors) ? (errors as MappingProblem[]) : [],
    }
  }
  return { message: null, problems: [] }
}

export const TOKEN_KEY = 'aos-token'
export const AUTH_EXPIRED_EVENT = 'aos-auth-expired'

/** A delayed refusal for an old credential must not log out a new identity. */
function notifyUnauthorized(status: number, sentHeaders: Record<string, string>) {
  if (status === 401 && sentHeaders.Authorization && sentHeaders.Authorization === authHeaders().Authorization) {
    window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT))
  }
}

export function storeToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* private mode — the token lives for this page only */
  }
}

export function hasToken(): boolean {
  try {
    return Boolean(localStorage.getItem(TOKEN_KEY))
  } catch {
    return false
  }
}

/** Bearer token for hosted deployments that enable managed auth. In
 *  local mode none exists and the header is simply omitted. */
export function authHeaders(): Record<string, string> {
  try {
    const token = localStorage.getItem(TOKEN_KEY)
    return token ? { Authorization: `Bearer ${token}` } : {}
  } catch {
    return {}
  }
}

export async function request<T>(
  path: string,
  init: RequestInit = {},
  timeoutMs = REQUEST_TIMEOUT_MS,
): Promise<T> {
  const controller = new AbortController()
  const cancel = () => controller.abort()
  if (init.signal?.aborted) cancel()
  else init.signal?.addEventListener('abort', cancel, { once: true })
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  let response: Response
  const { headers, ...rest } = init
  const sentHeaders = { 'Content-Type': 'application/json', ...authHeaders(), ...(headers as Record<string, string> | undefined) }
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...rest,
      // A caller's headers add to these; the token is never dropped.
      headers: sentHeaders,
      signal: controller.signal,
    })
  } catch (error) {
    const timedOut = error instanceof DOMException && error.name === 'AbortError'
    // Transport failures are the one class of message this client
    // writes itself; everything else is the server's `detail`.
    throw new ApiError(
      timedOut ? translate('api.timeout') : translate('api.unreachable'),
      0,
      !timedOut,
    )
  } finally {
    clearTimeout(timer)
    init.signal?.removeEventListener('abort', cancel)
  }

  let body: unknown = null
  try {
    body = await response.json()
  } catch {
    body = null
  }

  if (!response.ok) {
    notifyUnauthorized(response.status, sentHeaders)
    const { message, problems } = readDetail(body)
    throw new ApiError(
      message ?? translate('api.failed', { status: response.status }),
      response.status,
      false,
      problems,
    )
  }
  return body as T
}

export interface OperationResult {
  reply_text: string
  state: SessionState
}

export interface MessageResult {
  reply: TranscriptEntry
  state: SessionState
}

export interface VoiceStatus {
  enabled: boolean
  available: boolean
  provider: 'faster-whisper'
  model: string | null
  max_seconds: number
  max_bytes: number
}

export interface VoiceTranscript {
  text: string
  language: 'en' | 'ar'
  provider: 'faster-whisper'
}

/** The file name a download was given, from Content-Disposition. */
function attachmentName(header: string | null, fallback: string): string {
  const match = header?.match(/filename="([^"]+)"/)
  return match ? match[1] : fallback
}

export const api = {
  kpiPolicy: (id: string, language: 'en' | 'ar', signal?: AbortSignal) =>
    request<KpiPolicy>(`/api/runs/${encodeURIComponent(id)}/kpi-policy?language=${language}`, { signal }),
  saveKpiPolicy: (id: string, policy: KpiPolicy, language: 'en' | 'ar', signal?: AbortSignal) =>
    request<KpiPolicy>(`/api/runs/${encodeURIComponent(id)}/kpi-policy?language=${language}`, {
      method: 'PUT', signal, body: JSON.stringify({ expected_revision: policy.revision, rules: policy.rules }),
    }),
  voiceStatus: () => request<VoiceStatus>('/api/voice/status'),
  transcribeSession: (id: string, audio: Blob, language: 'en' | 'ar', signal: AbortSignal) =>
    request<VoiceTranscript>(
      `/api/sessions/${encodeURIComponent(id)}/transcriptions?language=${language}`,
      { method: 'POST', body: audio, headers: { 'Content-Type': audio.type || 'application/octet-stream' }, signal },
      90_000,
    ),
  health: () => request<{ status: string; agent_name: string; version: string }>('/api/health'),
  authConfig: () => request<AuthConfig>('/api/auth/config'),
  identity: () => request<IdentityInfo>('/api/identity'),
  /** `language` seeds the agent's own reply language so the welcome
   *  message and command descriptions arrive in the reader's language
   *  from the first response, with no second request to correct them. */
  createSession: (language?: string) =>
    request<SessionState>('/api/sessions', {
      method: 'POST',
      body: JSON.stringify({ language: language ?? null }),
    }),
  getSession: (id: string) => request<SessionState>(`/api/sessions/${id}`),
  endSession: (id: string) => request<SessionState>(`/api/sessions/${id}`, { method: 'DELETE' }),
  // Leave transport headroom around the server's bounded 60-second local inference.
  sendMessage: (id: string, text: string) =>
    request<MessageResult>(`/api/sessions/${id}/messages`, {
      method: 'POST',
      body: JSON.stringify({ text }),
    }, 90_000),
  clearHistory: (id: string) =>
    request<OperationResult>(`/api/sessions/${id}/history`, { method: 'DELETE' }),
  setPreference: (id: string, key: string, value: string) =>
    request<OperationResult>(`/api/sessions/${id}/preferences`, {
      method: 'PUT',
      body: JSON.stringify({ key, value }),
    }),
  addMemory: (id: string, information: string, category?: string) =>
    request<OperationResult>(`/api/sessions/${id}/memory`, {
      method: 'POST',
      body: JSON.stringify({ information, category: category ?? null }),
    }),
  updateMemory: (id: string, key: string, information: string, category?: string) =>
    request<OperationResult>(`/api/sessions/${id}/memory/${encodeURIComponent(key)}`, {
      method: 'PUT',
      body: JSON.stringify({ information, category: category ?? null }),
    }),
  deleteMemory: (id: string, key: string) =>
    request<OperationResult>(`/api/sessions/${id}/memory/${encodeURIComponent(key)}`, {
      method: 'DELETE',
    }),
  exportData: (id: string) => request<ExportPayload>(`/api/sessions/${id}/export`),
  clearMemory: (id: string) =>
    request<OperationResult>(`/api/sessions/${id}/memory`, { method: 'DELETE' }),
  /** `datasetId` analyses a dataset already stored for this owner, so a
   *  file is never sent twice; it takes the place of `datasetText`. */
  createRun: (
    goal: string,
    datasetText?: string,
    datasetName?: string,
    profile?: string,
    language: 'en' | 'ar' = 'en',
    datasetId?: string,
    /** Other stored datasets joined onto this one, and a breakdown from
     *  the merged table (ADR 0030). The server checks the merge first. */
    merge?: { joins: JoinSpec[]; breakdown?: string | null },
  ) =>
    request<RunDetail>(
      '/api/runs',
      {
        method: 'POST',
        body: JSON.stringify({
          goal,
          dataset_text: datasetId ? null : (datasetText ?? null),
          dataset_name: datasetId ? null : (datasetName ?? null),
          dataset_id: datasetId ?? null,
          profile: profile || null,
          language,
          joins: merge?.joins.length ? merge.joins : null,
          breakdown: merge?.joins.length ? (merge.breakdown || null) : null,
        }),
      },
      merge?.joins.length ? UPLOAD_TIMEOUT_MS : REQUEST_TIMEOUT_MS,
    ),
  /** The merge a run with these joins would make, refused with every
   *  problem by field when it cannot be made (ADR 0030). */
  previewJoins: (datasetId: string, joins: JoinSpec[], breakdown: string | null, language: 'en' | 'ar' = 'en') =>
    request<JoinPreview>(
      `/api/joins/preview?language=${language}`,
      { method: 'POST', body: JSON.stringify({ dataset_id: datasetId, joins, breakdown: breakdown || null }) },
      UPLOAD_TIMEOUT_MS,
    ),
  listDatasets: () => request<{ datasets: DatasetSummary[] }>('/api/datasets'),
  /** The file itself is the request body: CSV, TSV, Excel, JSON or JSON
   *  Lines. The server reads it, stores it once and answers in `language`. */
  uploadDataset: (file: File, language: 'en' | 'ar' = 'en', sheet?: string) =>
    request<UploadResult>(
      `/api/datasets?name=${encodeURIComponent(file.name)}&language=${language}${sheet ? `&sheet=${encodeURIComponent(sheet)}` : ''}`,
      {
        method: 'POST',
        body: file,
        headers: { 'Content-Type': file.type || 'application/octet-stream' },
      },
      UPLOAD_TIMEOUT_MS,
    ),
  /** Preview, column profile, saved mapping and a suggestion (ADR 0025). */
  getDataset: (id: string, language: 'en' | 'ar' = 'en') =>
    request<DatasetDetail>(`/api/datasets/${encodeURIComponent(id)}?language=${language}`, {}, UPLOAD_TIMEOUT_MS),
  /** Checked against every row; a refusal carries `problems` by field. */
  saveMapping: (id: string, mapping: ColumnMapping, language: 'en' | 'ar' = 'en') =>
    request<DatasetDetail>(
      `/api/datasets/${encodeURIComponent(id)}/mapping?language=${language}`,
      {
        method: 'PUT',
        body: JSON.stringify({
          roles: mapping.roles,
          measure: mapping.measure,
          dimension: mapping.dimension,
          date_order: mapping.date_order,
          grain: mapping.grain,
          currency: mapping.currency ?? null,
        }),
      },
      UPLOAD_TIMEOUT_MS,
    ),
  /** Back to automatic detection for runs from now on. */
  clearMapping: (id: string, language: 'en' | 'ar' = 'en') =>
    request<DatasetDetail>(
      `/api/datasets/${encodeURIComponent(id)}/mapping?language=${language}`,
      { method: 'DELETE' },
      UPLOAD_TIMEOUT_MS,
    ),
  pipelines: () => request<Pipelines>('/api/pipelines'),
  listRuns: (state?: string) => request<{ runs: RunSummary[] }>(state ? `/api/runs?state=${encodeURIComponent(state)}` : '/api/runs'),
  usage: () => request<Usage>('/api/usage'),
  getRun: (id: string) => request<RunDetail>(`/api/runs/${id}`, {}, RUN_REQUEST_TIMEOUT_MS),
  /** The maintenance KPI register computed on a run's cleaned table
   *  (ADR 0049). 409 until the run has finished cleaning. */
  runKpis: (id: string, language: 'en' | 'ar' = 'en') =>
    request<RunKpis>(`/api/runs/${id}/kpis?language=${language}`),
  /** Read-only, evidence-linked brief over the same filters as the dashboard. */
  runExecutive: (id: string, language: 'en' | 'ar' = 'en', filters: TableFilter[] = [], signal?: AbortSignal) =>
    request<RunExecutive>(
      `/api/runs/${encodeURIComponent(id)}/executive?${new URLSearchParams({ language, filters: JSON.stringify(filters) })}`,
      { signal }, UPLOAD_TIMEOUT_MS,
    ),
  /** Business files are rendered from owned server evidence. The version guard
   * prevents silently exporting a different snapshot from the prepared brief. */
  downloadExecutive: async (id: string, language: 'en' | 'ar', filters: TableFilter[], expectedUpdatedAt: string, expectedSnapshotId: string,
    format: 'html' | 'docx' = 'html', signal?: AbortSignal) => {
    const controller = new AbortController()
    const cancel = () => controller.abort()
    if (signal?.aborted) cancel()
    else signal?.addEventListener('abort', cancel, { once: true })
    const timer = setTimeout(cancel, UPLOAD_TIMEOUT_MS)
    const sentHeaders = authHeaders()
    try {
      const params = new URLSearchParams({ language, format, filters: JSON.stringify(filters), expected_updated_at: expectedUpdatedAt, expected_snapshot_id: expectedSnapshotId })
      const response = await fetch(`${API_BASE}/api/runs/${encodeURIComponent(id)}/executive/export?${params}`, {
        headers: sentHeaders, signal: controller.signal,
      })
      if (!response.ok) {
        notifyUnauthorized(response.status, sentHeaders)
        let message: string | null = null
        try { message = readDetail(await response.json()).message } catch { /* use the status below */ }
        throw new ApiError(message ?? translate('api.failed', { status: response.status }), response.status)
      }
      const expectedType = format === 'html' ? 'text/html' : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
      if (response.headers.get('content-type')?.split(';')[0].trim() !== expectedType) {
        throw new ApiError(translate('api.failed', { status: response.status }), response.status)
      }
      const blob = await response.blob()
      const fallback = `miyaar-executive-${id.replace(/[^a-zA-Z0-9_-]/g, '_')}-${language}.${format}`
      return { blob, name: attachmentName(response.headers.get('content-disposition'), fallback) }
    } catch (error) {
      if (error instanceof ApiError) throw error
      const aborted = error instanceof DOMException && error.name === 'AbortError'
      throw new ApiError(translate(aborted ? 'api.timeout' : 'api.unreachable'), 0, !aborted)
    } finally {
      clearTimeout(timer)
      signal?.removeEventListener('abort', cancel)
    }
  },
  advanceRun: (id: string) => request<RunDetail>(`/api/runs/${id}/advance`, { method: 'POST' }, RUN_REQUEST_TIMEOUT_MS),
  pauseRun: (id: string) => request<RunDetail>(`/api/runs/${id}/pause`, { method: 'POST' }, RUN_REQUEST_TIMEOUT_MS),
  resumeRun: (id: string) => request<RunDetail>(`/api/runs/${id}/resume`, { method: 'POST' }, RUN_REQUEST_TIMEOUT_MS),
  cancelRun: (id: string) => request<RunDetail>(`/api/runs/${id}/cancel`, { method: 'POST' }, RUN_REQUEST_TIMEOUT_MS),
  /** A run's cleaned table (ADR 0031): fields, totals by group, rows. */
  tableFields: (id: string, language: 'en' | 'ar' = 'en') =>
    request<{ fields: TableField[]; records: number }>(
      `/api/runs/${encodeURIComponent(id)}/fields?language=${language}`, {}, UPLOAD_TIMEOUT_MS),
  queryTable: (id: string, spec: QuerySpec, language: 'en' | 'ar' = 'en') =>
    request<QueryAnswer>(
      `/api/runs/${encodeURIComponent(id)}/query?language=${language}`,
      { method: 'POST', body: JSON.stringify(spec) },
      UPLOAD_TIMEOUT_MS,
    ),
  tableRecords: (id: string, spec: RecordsSpec, language: 'en' | 'ar' = 'en') =>
    request<RecordsPage>(
      `/api/runs/${encodeURIComponent(id)}/records?language=${language}`,
      { method: 'POST', body: JSON.stringify(spec) },
      UPLOAD_TIMEOUT_MS,
    ),
  /** The cleaned table as a CSV file. Fetched with the token, which a
   *  plain link could not send, then handed to the browser to save. */
  downloadTable: async (id: string, language: 'en' | 'ar' = 'en') => {
    let response: Response
    const sentHeaders = authHeaders()
    try {
      response = await fetch(`${API_BASE}/api/runs/${encodeURIComponent(id)}/data.csv?language=${language}`, {
        headers: sentHeaders,
      })
    } catch {
      throw new ApiError(translate('api.unreachable'), 0, true)
    }
    if (!response.ok) {
      notifyUnauthorized(response.status, sentHeaders)
      let message: string | null = null
      try {
        message = readDetail(await response.json()).message
      } catch {
        message = null
      }
      throw new ApiError(message ?? translate('api.failed', { status: response.status }), response.status)
    }
    return {
      blob: await response.blob(),
      name: attachmentName(response.headers.get('content-disposition'), `run-${id}-cleaned.csv`),
    }
  },
  decideApproval: (id: string, approvalId: string, decision: 'approve' | 'reject') =>
    request<RunDetail>(`/api/runs/${id}/approvals/${approvalId}`, {
      method: 'POST',
      body: JSON.stringify({ decision }),
    }, RUN_REQUEST_TIMEOUT_MS),
}
