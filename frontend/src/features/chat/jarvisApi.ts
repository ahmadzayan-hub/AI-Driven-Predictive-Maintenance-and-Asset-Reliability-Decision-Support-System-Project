import { request } from '../../shared/api'
import type { DataContext } from '../../shared/types'
import type { JarvisAnswer } from './JarvisWorkspace'

// Load this feature's transport with Jarvis, outside the first-paint shell.
export const jarvisApi = {
  query: (id: string, text: string, context: DataContext, language: 'en' | 'ar', signal: AbortSignal) =>
    request<JarvisAnswer>(`/api/sessions/${encodeURIComponent(id)}/data-query`, {
      method: 'POST', body: JSON.stringify({ text, language, scope: {
        run_id: context.run_id, dataset_id: context.dataset_id, source_sha256: context.source_sha256,
        analysis_revision: context.analysis_revision, filters: context.filters,
      } }), signal,
    }),
}
