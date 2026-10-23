import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { usePack } from '../../i18n/pack'
import { api } from '../../shared/api'
import { Dialog } from '../../shared/components/Dialog'
import type { RunSummary } from '../../shared/types'
import { messages } from './messages'
import { Field } from './OperationsView'
import type { Mutate } from './OperationsView'
import { operationsApi } from './operationsApi'
import { priorities } from './RegistryPanel'
import type { Completion, OperationsOverview, OrderChange, OrderStatus, Priority, WorkOrder } from './types'

interface Props { data: OperationsOverview; busy: boolean; mutate: Mutate; onOpenRun: (id: string) => void }

export function WorkOrdersPanel({ data, busy, mutate, onOpenRun }: Props) {
  const { t } = usePack(messages)
  const [filter, setFilter] = useState<OrderStatus | ''>('')
  const [selected, setSelected] = useState('')
  const orders = data.work_orders.filter((order) => !filter || order.status === filter)
  const order = data.work_orders.find((item) => item.id === selected)
  return <section aria-label={t('orders')}>
    {data.permissions.write && <details className="operations__card operations__draft"><summary>{t('newDraft')}</summary><DraftForm data={data} busy={busy} mutate={mutate} onCreated={setSelected} /></details>}
    <Field label={t('status')}><select value={filter} onChange={(event) => setFilter(event.target.value as OrderStatus | '')}><option value="">{t('all')}</option>{(['draft', 'authorized', 'in_progress', 'completed', 'cancelled'] as const).map((status) => <option key={status} value={status}>{t(status)}</option>)}</select></Field>
    <div className="operations__workgrid">
      <div className="operations__queue">
        {!orders.length && <p>{t('noOrders')}</p>}
        {orders.map((item) => <button type="button" key={item.id} className="operations__order" aria-pressed={selected === item.id} onClick={() => setSelected(item.id)}>
          <span className={`operations__status operations__status--${item.status}`}>{t(item.status)}</span>
          <strong dir="auto">{item.title}</strong><span dir="auto">{data.assets.find((asset) => asset.id === item.asset_id)?.name}</span>
          <span>{t('priority')}: {t(item.priority)}</span>
          {item.due_date && <span>{t('due')}: <bdi>{item.due_date}</bdi></span>}
        </button>)}
      </div>
      {order ? <OrderDetails key={order.id} order={order} data={data} busy={busy} mutate={mutate} onOpenRun={onOpenRun} /> : <div className="operations__card"><p>{t('selectOrder')}</p></div>}
    </div>
  </section>
}

function DraftForm({ data, busy, mutate, onCreated }: Omit<Props, 'onOpenRun'> & { onCreated: (id: string) => void }) {
  const { t } = usePack(messages)
  const [assetId, setAssetId] = useState(''), [title, setTitle] = useState(''), [rationale, setRationale] = useState('')
  const [runId, setRunId] = useState(''), [column, setColumn] = useState('Asset_ID')
  const [priority, setPriority] = useState<Priority>('medium'), [assignee, setAssignee] = useState(''), [due, setDue] = useState('')
  const [runs, setRuns] = useState<RunSummary[]>([])
  useEffect(() => {
    let alive = true
    api.listRuns().then((result) => { if (alive) setRuns(result.runs.filter((run) => ['awaiting_approval', 'completed'].includes(run.state))) }).catch(() => {})
    return () => { alive = false }
  }, [])
  async function create(event: FormEvent) {
    event.preventDefault()
    const asset = data.assets.find((item) => item.id === assetId)
    if (!asset) return
    const body = { asset_id: assetId, title: title.trim(), rationale: rationale.trim(), run_id: runId.trim(), asset_column: column.trim(), source_asset_id: asset.external_id, priority, assignee, due_date: due }
    const success = await mutate('draft', body, async (key) => {
      const result = await operationsApi.createOrder(data.organization.id, body, key)
      onCreated(result.id)
    })
    if (success) { setTitle(''); setRationale('') }
  }
  return <form onSubmit={(event) => void create(event)}><fieldset disabled={busy || !data.assets.length}>
    {!data.assets.length && <p>{t('noAssets')}</p>}
    <Field label={t('asset')}><select value={assetId} onChange={(event) => setAssetId(event.target.value)} required><option value="">{t('choose')}</option>{data.assets.map((asset) => <option value={asset.id} key={asset.id}>{asset.name} · {asset.external_id}</option>)}</select></Field>
    <Field label={t('titleField')}><input required maxLength={200} value={title} onChange={(event) => setTitle(event.target.value)} /></Field>
    <Field label={t('rationale')}><textarea required maxLength={2000} rows={3} value={rationale} onChange={(event) => setRationale(event.target.value)} /></Field>
    <p id="operations-evidence-help">{t('evidenceHelp')}</p>
    <div className="operations__forms">
      <Field label={t('run')}><input required value={runId} onChange={(event) => setRunId(event.target.value)} list="operations-runs" maxLength={64} dir="ltr" aria-describedby="operations-evidence-help" /></Field>
      <datalist id="operations-runs">{runs.map((run) => <option key={run.id} value={run.id}>{run.goal}</option>)}</datalist>
      <Field label={t('column')}><input required maxLength={200} value={column} onChange={(event) => setColumn(event.target.value)} dir="auto" /></Field>
    </div>
    <AssignmentFields data={data} priority={priority} setPriority={setPriority} assignee={assignee} setAssignee={setAssignee} due={due} setDue={setDue} />
    <button className="btn btn--primary">{t('createDraft')}</button>
  </fieldset></form>
}

function AssignmentFields({ data, priority, setPriority, assignee, setAssignee, due, setDue }: {
  data: OperationsOverview; priority: Priority; setPriority: (value: Priority) => void;
  assignee: string; setAssignee: (value: string) => void; due: string; setDue: (value: string) => void;
}) {
  const { t } = usePack(messages)
  return <div className="operations__forms">
    <Field label={t('priority')}><select value={priority} onChange={(event) => setPriority(event.target.value as Priority)}>{priorities.map((value) => <option value={value} key={value}>{t(value)}</option>)}</select></Field>
    <Field label={t('assignee')}><select required value={assignee} onChange={(event) => setAssignee(event.target.value)}><option value="">{t('choose')}</option>{data.members.filter((member) => member.role !== 'viewer').map((member) => <option key={member.subject} value={member.subject}>{member.subject}</option>)}</select></Field>
    <Field label={t('due')}><input type="date" required value={due} onChange={(event) => setDue(event.target.value)} /></Field>
  </div>
}

function OrderDetails({ order, data, busy, mutate, onOpenRun }: Props & { order: WorkOrder }) {
  const { t, formatDate, formatTime } = usePack(messages)
  const [priority, setPriority] = useState(order.priority), [assignee, setAssignee] = useState(order.assignee ?? ''), [due, setDue] = useState(order.due_date ?? '')
  const [confirm, setConfirm] = useState<'authorized' | 'cancelled' | null>(null)
  const [outcome, setOutcome] = useState(''), [notes, setNotes] = useState(''), [labor, setLabor] = useState('0')
  const [parts, setParts] = useState<Array<{ id: number; part: string; quantity: string }>>([])
  const [nextPart, setNextPart] = useState(1)
  const asset = data.assets.find((item) => item.id === order.asset_id)
  const editable = !['completed', 'cancelled'].includes(order.status) && data.permissions.write
  const canProgress = data.permissions.write && (data.organization.role !== 'technician' || order.assignee === data.principal_subject)
  const scheduleChanged = priority !== order.priority || assignee !== (order.assignee ?? '') || due !== (order.due_date ?? '')
  async function change(values: Omit<OrderChange, 'expected_version'>) {
    const body = { ...values, expected_version: order.version }
    return mutate(`order-${order.id}`, body, (key) => operationsApi.updateOrder(data.organization.id, order.id, body, key))
  }
  async function finish(event: FormEvent) {
    event.preventDefault()
    const completion: Completion = { outcome: outcome.trim(), notes: notes.trim(), labor_hours: Number(labor), parts: parts.map((part) => ({ part: part.part.trim(), quantity: Number(part.quantity) })) }
    await change({ status: 'completed', completion })
  }
  return <section className="operations__card operations__detail" aria-label={t('details')}>
    <header><span className={`operations__status operations__status--${order.status}`}>{t(order.status)}</span><span className="operations__version">{t('version', { n: order.version })}</span><h3 dir="auto">{order.title}</h3><p dir="auto">{asset?.name} · {asset?.external_id}</p></header>
    <p dir="auto">{order.rationale}</p>
    <details><summary>{t('evidence')}</summary><dl className="operations__evidence">
      <div><dt>{t('run')}</dt><dd><bdi>{order.evidence.run_id}</bdi></dd></div>
      <div><dt>{t('column')}</dt><dd dir="auto">{order.evidence.asset_column}</dd></div>
      <div><dt>{t('assetId')}</dt><dd dir="auto">{order.evidence.source_asset_id}</dd></div>
    </dl><p>{t('records', { n: order.evidence.matching_records })}</p><button type="button" className="btn btn--ghost" onClick={() => onOpenRun(order.evidence.run_id)}>{t('openRun')}</button></details>
    {editable && order.status !== 'in_progress' && data.organization.role !== 'technician' && <form onSubmit={(event) => { event.preventDefault(); void change({ priority, assignee, due_date: due }) }}><fieldset disabled={busy}>
      {order.status === 'authorized' && <p>{t('reschedule')}</p>}
      <AssignmentFields data={data} priority={priority} setPriority={setPriority} assignee={assignee} setAssignee={setAssignee} due={due} setDue={setDue} />
      <button className="btn btn--ghost">{t('saveAssignment')}</button>
    </fieldset></form>}
    <div className="operations__actions">
      {scheduleChanged && <p>{t('saveFirst')}</p>}
      {order.status === 'draft' && data.permissions.authorize && <button className="btn btn--primary" disabled={busy || scheduleChanged} onClick={() => setConfirm('authorized')}>{t('authorize')}</button>}
      {order.status === 'authorized' && canProgress && <button className="btn btn--primary" disabled={busy || scheduleChanged} onClick={() => void change({ status: 'in_progress' })}>{t('start')}</button>}
      {editable && data.permissions.authorize && <button className="btn btn--ghost" disabled={busy} onClick={() => setConfirm('cancelled')}>{t('cancelOrder')}</button>}
    </div>
    {order.status === 'in_progress' && canProgress && <form onSubmit={(event) => void finish(event)}><h3>{t('completion')}</h3><p id="operations-outcome-help">{t('outcomeHelp')}</p><fieldset disabled={busy}>
      <Field label={t('outcome')}><input required maxLength={120} value={outcome} onChange={(event) => setOutcome(event.target.value)} aria-describedby="operations-outcome-help" /></Field>
      <Field label={t('notes')}><textarea required rows={3} maxLength={2000} value={notes} onChange={(event) => setNotes(event.target.value)} /></Field>
      <Field label={t('labor')}><input type="number" min="0" max="10000" step="any" required value={labor} onChange={(event) => setLabor(event.target.value)} /></Field>
      <h4>{t('parts')}</h4>
      {parts.map((part, index) => <div className="operations__parts" key={part.id}>
        <Field label={`${t('part')} ${index + 1}`}><input value={part.part} maxLength={160} required onChange={(event) => setParts((items) => items.map((item) => item.id === part.id ? { ...item, part: event.target.value } : item))} /></Field>
        <Field label={`${t('quantity')} ${index + 1}`}><input type="number" min="0.001" step="any" max="1000000" required value={part.quantity} onChange={(event) => setParts((items) => items.map((item) => item.id === part.id ? { ...item, quantity: event.target.value } : item))} /></Field>
        <button type="button" className="btn btn--ghost" aria-label={t('removePart', { n: index + 1 })} onClick={() => setParts((items) => items.filter((item) => item.id !== part.id))}>×</button>
      </div>)}
      <button type="button" className="btn btn--ghost" disabled={parts.length >= 100} onClick={() => { setParts((items) => [...items, { id: nextPart, part: '', quantity: '1' }]); setNextPart((value) => value + 1) }}>{t('addPart')}</button>
      <button className="btn btn--primary">{t('complete')}</button>
    </fieldset></form>}
    {order.status === 'completed' && <section><h3>{t('completion')}</h3><p dir="auto">{order.completion.outcome}</p><p dir="auto">{order.completion.notes}</p><p>{t('labor')}: {order.completion.labor_hours}</p><ul>{order.completion.parts?.map((part, index) => <li key={index} dir="auto">{part.part} × {part.quantity}</li>)}</ul></section>}
    <details><summary>{t('audit')}</summary><ol className="operations__audit">{order.audit.map((entry) => <li key={entry.id}>
      <strong>{['draft', 'created', 'updated', 'authorized', 'in_progress', 'completed', 'cancelled', 'assigned'].includes(entry.action.replace(/^work_/, '')) ? t(entry.action.replace(/^work_/, '') as 'created') : t('historyEntry')}</strong>
      <span dir="auto">{entry.actor}</span><span>{t('version', { n: entry.version })}</span><time dateTime={entry.created_at}>{formatDate(entry.created_at)} {formatTime(entry.created_at)}</time>
    </li>)}</ol></details>
    {confirm && <Dialog title={t(confirm === 'authorized' ? 'authorizationTitle' : 'cancelTitle')} labelledById="operations-confirm-title" onClose={() => { if (!busy) setConfirm(null) }}>
      <p className="dialog__body">{t(confirm === 'authorized' ? 'authorizationHelp' : 'cancelHelp')}</p><p className="dialog__body" dir="auto">{order.title} · {asset?.name}</p>
      <p className="dialog__body">{t('assignee')}: <bdi>{order.assignee}</bdi> · {t('due')}: <bdi>{order.due_date}</bdi> · {t('priority')}: {t(order.priority)}</p>
      <div className="dialog__actions"><button className="btn btn--ghost" disabled={busy} onClick={() => setConfirm(null)}>{t('cancel')}</button><button className={`btn ${confirm === 'authorized' ? 'btn--primary' : 'btn--danger'}`} disabled={busy} onClick={async () => { if (await change({ status: confirm })) setConfirm(null) }}>{t(confirm === 'authorized' ? 'authorize' : 'cancelOrder')}</button></div>
    </Dialog>}
  </section>
}
