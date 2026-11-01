import { useEffect, useRef, useState } from 'react'
import { api } from '../../shared/api'
import { useReadOnly } from '../../shared/readOnly'
import type { DataContextChoices, SessionState } from '../../shared/types'

export function DataChatContext({ session, disabled }: { session: SessionState; disabled: boolean }) {
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

  async function update(select?: string | null) {
    const request = ++generation.current
    setBusy(true); setFailed(false)
    try {
      if (select === undefined) {
        const answer = await api.dataContext(session.session_id)
        if (request !== generation.current) return
        setChoices(answer.choices); setSelected(answer.selected); setRunId('')
      } else {
        const answer = await api.selectDataContext(session.session_id, select)
        if (request !== generation.current) return
        setSelected(answer.data_context ?? null)
      }
    } catch { if (request === generation.current) setFailed(true) }
    finally { if (request === generation.current) setBusy(false) }
  }

  if (!labels) return null
  return <details className="tool-cards" open={expanded} onToggle={event => setExpanded(event.currentTarget.open)}>
    <summary>{labels.title}: <bdi>{selected?.dataset_name ?? labels.none}</bdi></summary>
    <p>{labels.help}</p>
    {selected ? <div><p><bdi>{selected.run_id}</bdi> · {labels.scope}: {selected.records} / {selected.total_records}</p>
      <p>{labels.filters}: <bdi>{JSON.stringify(selected.filters)}</bdi></p></div> : null}
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
