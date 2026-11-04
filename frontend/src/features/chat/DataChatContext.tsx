import { useEffect, useRef, useState } from 'react'
import { api } from '../../shared/api'
import { useReadOnly } from '../../shared/readOnly'
import type { DataContext, DataContextChoices, SessionState } from '../../shared/types'
import { describeFilters } from './describeFilters'

export function DataChatContext({ session, disabled, onSelected, onPending, want }: { session: SessionState; disabled: boolean; onSelected?: (context: DataContext | null) => void; onPending?: (pending: boolean) => void; want?: string }) {
  const labels = session.data_chat_labels
  const readOnly = useReadOnly()
  disabled = disabled || readOnly
  const [selected, setSelected] = useState(session.data_context ?? null)
  const [expanded, setExpanded] = useState(false)
  const [choices, setChoices] = useState<DataContextChoices['choices'] | null>(null)
  const [runId, setRunId] = useState('')
  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState(false)
  const generation = useRef(0)
  useEffect(() => { setSelected(session.data_context ?? null) }, [session.data_context])
  useEffect(() => () => { generation.current += 1 }, [])
  // A report handed over by another screen is selected once, through the same
  // permission-bound call as a manual choice; the server still decides access.
  // The hand-over is the whole report the brief was calculated on, so an
  // earlier binding of the same report with filters is replaced, not kept.
  const wanted = useRef<string | null>(null)
  const bound = session.data_context
  const whole = bound?.run_id === want && !(bound?.filters?.length)
  useEffect(() => {
    if (!want || disabled || wanted.current === want || whole) return
    wanted.current = want
    void update(want)
  }, [want, disabled, whole])

  async function update(select?: string | null) {
    const request = ++generation.current
    setBusy(true); setFailed(false); onPending?.(true)
    try {
      if (select === undefined) {
        const answer = await api.dataContext(session.session_id)
        if (request !== generation.current) return
        setChoices(answer.choices); setSelected(answer.selected); setRunId(''); onSelected?.(answer.selected)
      } else {
        const answer = await api.selectDataContext(session.session_id, select)
        if (request !== generation.current) return
        setSelected(answer.data_context ?? null); onSelected?.(answer.data_context ?? null)
      }
    } catch { if (request === generation.current) setFailed(true) }
    finally { if (request === generation.current) { setBusy(false); onPending?.(false) } }
  }

  if (!labels) return null
  return <details className="tool-cards" open={expanded} onToggle={event => setExpanded(event.currentTarget.open)}>
    <summary>{labels.title}: <bdi>{selected?.dataset_name ?? labels.none}</bdi></summary>
    <p>{labels.help}</p>
    {selected ? <div><p><bdi>{selected.run_id}</bdi> · {labels.scope}: {selected.records} / {selected.total_records}</p>
      <p>{labels.filters}: <bdi>{describeFilters(selected.filters) || '-'}</bdi></p></div> : null}
    <button type="button" className="btn btn--ghost" disabled={disabled || busy} onClick={() => void update()}>{labels.load}</button>
    {choices ? <><p>{labels.limit}</p><label>{labels.choose}<select value={runId} disabled={disabled || busy}
      onChange={event => setRunId(event.target.value)}><option value="">{labels.none}</option>
      {choices.map(choice => <option key={choice.run_id} value={choice.run_id}>{choice.dataset_name} · {choice.run_id}</option>)}</select></label>
      {!choices.length ? <p>{labels.empty}</p> : null}
      <button type="button" className="btn btn--ghost" disabled={disabled || busy || !runId} onClick={() => void update(runId)}>{labels.use}</button></> : null}
    {selected ? <button type="button" className="btn btn--ghost" disabled={disabled || busy} onClick={() => void update(null)}>{labels.clear}</button> : null}
    {busy ? <p role="status">{labels.busy}</p> : null}
    {failed ? <p role="alert">{labels.error}</p> : null}
  </details>
}
