import { useRef, useState } from 'react'
import { api } from '../../shared/api'
import type { RunExecutive } from '../../shared/types'
import type { executiveMessages } from './executiveMessages'

type Message = keyof typeof executiveMessages.en

interface ExportJob {
  controller: AbortController
  scope: string
  popup: Window | null
  url?: string
  poll?: ReturnType<typeof setInterval>
  timeout?: ReturnType<typeof setTimeout>
  ready?: () => void
  printing?: boolean
  printed?: () => void
}

/** The Command Centre's export: a download, or a print preview that is
 * polled until the report document is loaded and the fonts are ready.
 * Extracted from the view (assessment U18) so the view holds the brief
 * and the hook holds the job; one job at a time, cancelled when the scope
 * changes or the view unmounts. */
export function useExecutiveExport(brief: RunExecutive | null, data: RunExecutive | null,
                                   currentScope: { current: string }) {
  const [exportFormat, setExportFormat] = useState<'html' | 'docx'>('html')
  const [exportBusy, setExportBusy] = useState(false)
  const [exportError, setExportError] = useState<Message | null>(null)
  const [exportStatus, setExportStatus] = useState<Message | null>(null)
  const exportRef = useRef<ExportJob | null>(null)
  const objectUrls = useRef(new Set<string>())

  function revoke(url: string) {
    if (objectUrls.current.delete(url)) URL.revokeObjectURL(url)
  }
  function disposeExport(job: ExportJob) {
    job.controller.abort()
    clearInterval(job.poll)
    clearTimeout(job.timeout)
    try {
      if (job.printed) job.popup?.removeEventListener('afterprint', job.printed)
      if (job.popup && !job.popup.closed) job.popup.close()
    } catch { /* A closed or externally navigated preview is no longer usable. */ }
    if (job.url) revoke(job.url)
    if (exportRef.current === job) exportRef.current = null
  }
  function isCurrent(job: ExportJob) {
    return exportRef.current === job && job.scope === currentScope.current && !job.controller.signal.aborted
  }
  function finishExport(job: ExportJob, error: Message | null, status: Message | null = null) {
    if (!isCurrent(job)) return
    disposeExport(job)
    setExportBusy(false)
    setExportError(error)
    setExportStatus(status)
  }
  function cancelExport() {
    if (exportRef.current) finishExport(exportRef.current, null, 'exec.exportCancelled')
  }
  async function exportReport(print: boolean) {
    if (!data || brief !== data || exportRef.current) return
    setExportError(null)
    setExportStatus(null)
    const stamp = brief.run.updated_at
    const snapshotId = brief.snapshot_id
    if (!stamp || !snapshotId) { setExportError('exec.exportStale'); return }
    let popup: Window | null = null
    if (print) {
      // Reserve the preview while this explicit user gesture is still active.
      try {
        popup = window.open('', '_blank')
        if (popup) popup.opener = null
      } catch { popup?.close(); popup = null }
      if (!popup) { setExportError('exec.popupBlocked'); return }
    }
    const job: ExportJob = { controller: new AbortController(), scope: currentScope.current, popup }
    exportRef.current = job
    setExportBusy(true)
    if (popup) job.poll = setInterval(() => {
      if (popup.closed) finishExport(job, null, 'exec.printClosed')
      else job.ready?.()
    }, 400)
    try {
      const result = await api.downloadExecutive(brief.run.id, brief.language, brief.scope.filters, stamp, snapshotId, print ? 'html' : exportFormat, job.controller.signal)
      if (!isCurrent(job)) return
      if (popup?.closed) { finishExport(job, null, 'exec.printClosed'); return }
      const url = URL.createObjectURL(result.blob)
      objectUrls.current.add(url)
      if (!popup) {
        const link = document.createElement('a')
        link.href = url
        link.download = result.name
        try { link.click() } catch (error) { revoke(url); throw error }
        // The browser may consume the blob after the click handler returns.
        setTimeout(() => revoke(url), 1_000)
        finishExport(job, null, 'exec.downloadReady')
        return
      }
      job.url = url
      const loaded = () => popup.location.href === url && popup.document.URL === url && popup.document.readyState === 'complete'
      // Navigation replaces the blank window's global and its load listeners.
      // Poll the actual report document, then enter the font/print path once.
      job.ready = async () => {
        try {
          if (job.printing || !isCurrent(job) || popup.closed || !loaded()) return
          job.printing = true
          await popup.document.fonts?.ready
          if (!isCurrent(job)) return
          if (popup.closed) { finishExport(job, null, 'exec.printClosed'); return }
          if (!loaded()) { finishExport(job, 'exec.printFailed'); return }
          clearTimeout(job.timeout)
          job.printed = () => finishExport(job, null, 'exec.printDone')
          popup.addEventListener('afterprint', job.printed, { once: true })
          popup.focus()
          setExportStatus('exec.printRequested')
          popup.print()
        } catch { finishExport(job, 'exec.printFailed') }
      }
      job.timeout = setTimeout(() => finishExport(job, 'exec.printFailed'), 30_000)
      popup.location.href = url
    } catch (error) {
      const stale = error instanceof Error && 'status' in error && error.status === 409
      finishExport(job, stale ? 'exec.exportStale' : 'exec.exportFailed')
    }
  }

  function reset() {
    setExportBusy(false)
    setExportError(null)
    setExportStatus(null)
  }
  function dispose() {
    if (exportRef.current) disposeExport(exportRef.current)
    for (const url of objectUrls.current) revoke(url)
  }
  return { exportFormat, setExportFormat, exportBusy, exportError, exportStatus, cancelExport, exportReport, reset, dispose }
}
