import './layout.css'
import { useEffect, useRef, useState } from 'react'
import { api, ApiError } from '../../shared/api'
import type { GroupKey, LayoutSection, QueryAnswer, RecordsPage, TableFilter } from '../../shared/types'
import { useI18n } from '../../i18n'
import { usePack } from '../../i18n/pack'
import { layoutMessages } from '../../i18n/layout'
import { Bars, Line } from './charts'
import { useAnswer } from './DashboardView'
import { isPicked, pick, type DashState, type Roles } from './state'
import { addVersion, readHistory, restore, sectionsOf, togglePin, writeHistory, type LayoutHistory } from './layoutHistory'

const label = (key: GroupKey) => key === null ? '' : Array.isArray(key) ? `${key[0]} – ${key[1]}` : String(key)

/** One planned section. Its numbers come from the query engine under the
 *  dashboard's shared filters, so a pick anywhere narrows every section and
 *  Jarvis, whose scope is the same filter list. */
function Section({ runId, section, filters, state, roles, setState, pinned, onPin }: {
  runId: string; section: LayoutSection; filters: TableFilter[]; state: DashState; roles: Roles
  setState: (next: DashState) => void; pinned: boolean; onPin: () => void
}) {
  const { t, formatNumber } = usePack(layoutMessages)
  const { locale } = useI18n()
  const b = section.binding
  const scoped = [...(b.filters ?? []), ...filters]
  const isTable = section.component === 'table'
  const spec = section.component === 'gap' ? null : isTable ? { filters: scoped, limit: Math.min(b.limit ?? 20, 50) }
    : { group_by: b.group_by, measures: b.measures, sort: b.sort, limit: b.limit ?? 100, filters: scoped }
  const answer = useAnswer<QueryAnswer | RecordsPage>(spec ? `ly:${runId}:${locale}:${section.id}:${JSON.stringify(spec)}` : null,
    (): Promise<QueryAnswer | RecordsPage> => isTable ? api.tableRecords(runId, spec!, locale) : api.queryTable(runId, spec as never, locale))
  const title = section.title[locale]
  const column = typeof b.group_by?.[0] === 'string' ? b.group_by[0] as string : null
  let body: React.ReactNode = <p className="card__meta">{t('loading')}</p>
  if (section.component === 'gap') body = <p className="layout__gap"><strong>{t('unavailable')}</strong> · {section.reason?.[locale]}</p>
  else if (answer.error) body = <p role="alert" className="card__meta">{t('error')}</p>
  else if (answer.data && 'columns' in answer.data) {
    const page = answer.data, keep = (b.columns ?? page.columns).map((c) => page.columns.indexOf(c)).filter((i) => i >= 0)
    body = <div className="layout__scroll"><table className="table"><thead><tr>{keep.map((i) => <th key={i} scope="col">{page.columns[i]}</th>)}</tr></thead>
      <tbody>{page.rows.map((row, r) => <tr key={r}>{keep.map((i) => <td key={i} dir="auto">{row[i] ?? ''}</td>)}</tr>)}</tbody></table></div>
  } else if (answer.data && 'groups' in answer.data) {
    const groups = answer.data.groups
    const points = groups.map((g) => ({ label: label(g.keys[0] ?? null), value: g.values[0] }))
    const pickable = column && section.interactions.includes('filter')
      ? { onPick: (value: string) => setState(pick(state, column, value, roles.date)), picked: (value: string) => isPicked(state, column, value, roles.date) }
      : {}
    if (section.component === 'kpi') {
      const value = groups[0]?.values[0]
      body = <p className="layout__kpi"><bdi>{value === null || value === undefined ? t('noValue') : formatNumber(value)}</bdi>
        <small>{t('rows', { n: formatNumber(answer.data.matched_records) })}</small></p>
    } else if (section.component === 'trend') body = <Line points={points} label={title} {...pickable} />
    else body = <Bars items={points} label={title} {...(section.component === 'distribution' ? {} : pickable)} />
  }
  return <section className={`card layout__section layout__section--${section.span}`} aria-label={title}>
    <header className="layout__head"><h4 dir="auto">{title}</h4>
      <button type="button" className="btn btn--ghost layout__pin" aria-pressed={pinned} onClick={onPin}>{pinned ? t('pinned') : t('pin')}</button></header>
    <p className="card__meta" dir="auto">{section.purpose[locale]}</p>
    {body}
  </section>
}

/** A layout designed for this run's data: planned on the server, validated
 *  and grounded there, rendered here only from registered components. */
export function DesignedPage({ runId, roles, state, filters, setState }: {
  runId: string; roles: Roles; state: DashState; filters: TableFilter[]; setState: (next: DashState) => void
}) {
  const { t, formatDate } = usePack(layoutMessages)
  const { locale } = useI18n()
  const [history, setHistory] = useState<LayoutHistory | null>(() => readHistory(runId))
  const [objective, setObjective] = useState('')
  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState(false)
  const generation = useRef(0)

  function save(next: LayoutHistory) { setHistory(next); writeHistory(runId, next) }
  async function design(goal: string) {
    const token = ++generation.current
    setBusy(true); setFailed(false)
    try {
      const result = await api.planLayout(runId, goal, locale)
      // A newer request, or another run, wins: a late answer is dropped.
      if (generation.current === token) save(addVersion(readHistory(runId), result, new Date().toISOString()))
    } catch (error) {
      if (generation.current === token) setFailed(error instanceof ApiError || error instanceof Error)
    } finally { if (generation.current === token) setBusy(false) }
  }
  useEffect(() => {
    const stored = readHistory(runId)
    setHistory(stored)
    // A refresh keeps the layout; only a first visit designs one.
    if (!stored) void design('')
    return () => { generation.current++ }
  }, [runId]) // eslint-disable-line react-hooks/exhaustive-deps

  const shown = history?.versions[history.current]
  return <div className="layout">
    <div className="layout__bar">
      <form className="layout__ask" onSubmit={(event) => { event.preventDefault(); void design(objective) }}>
        <label><span className="visually-hidden">{t('objective')}</span>
          <input value={objective} maxLength={300} placeholder={t('objective')} onChange={(e) => setObjective(e.target.value)} /></label>
        <button type="submit" className="btn btn--primary" disabled={busy}>{busy ? t('designing') : t('redesign')}</button>
      </form>
      {shown ? <span className="layout__source" role="status">{shown.result.source === 'model'
        ? t('model', { name: shown.result.provider ?? '' }) : t('rules')}</span> : null}
    </div>
    {failed ? <p role="alert" className="statusline statusline--error">{t('failed')}</p> : null}
    {history && history.versions.length > 1 ? <details className="layout__history"><summary>{t('earlier')}</summary><ol>
      {history.versions.map((v, i) => <li key={v.at}><button type="button" className="evidence-link" aria-current={i === history.current ? 'true' : undefined}
        onClick={() => save(restore(history, i))}>{t('version', { n: String(i + 1), time: formatDate(v.at) })}</button></li>)}
    </ol></details> : null}
    {shown?.result.notes.length ? <details className="layout__history"><summary>{t('why')}</summary>
      <ul>{shown.result.notes.map((note) => <li key={note.en}>{note[locale]}</li>)}</ul></details> : null}
    <div className="layout__grid">
      {history ? sectionsOf(history).map((section) => <Section key={section.id} runId={runId} section={section} filters={filters}
        state={state} roles={roles} setState={setState} pinned={history.pinned.includes(section.id)}
        onPin={() => save(togglePin(history, section.id))} />) : <p className="card__meta">{t('designing')}</p>}
    </div>
  </div>
}
