import './layout.css'
import { useEffect, useRef, useState } from 'react'
import { api, ApiError } from '../../shared/api'
import type { GroupKey, LayoutResult, LayoutSection, QueryAnswer, RecordsPage, RunExecutive, TableFilter } from '../../shared/types'
import { useI18n } from '../../i18n'
import { usePack } from '../../i18n/pack'
import { layoutMessages } from '../../i18n/layout'
import { Bars, Line } from './charts'
import { useAnswer } from './DashboardView'
import { isPicked, pick, type DashState, type Roles } from './state'
import { useJarvisPrompt } from './jarvisPrompt'
import { addVersion, readHistory, restore, sectionsOf, togglePin, writeHistory, type LayoutHistory } from './layoutHistory'

const label = (key: GroupKey) => key === null ? '' : Array.isArray(key) ? `${key[0]} – ${key[1]}` : String(key)

/** The manager's three questions, answered from the run's own findings and
 *  evidence (the executive brief): what is happening, what is expected, and
 *  the proposed decision with its evidence and the way to decide on it. */
function Brief({ runId, filters, result, onOpenRun }: {
  runId: string; filters: TableFilter[]; result: LayoutResult; onOpenRun: () => void
}) {
  const { t, formatNumber } = usePack(layoutMessages)
  const { locale } = useI18n()
  const [open, setOpen] = useState(false)
  const brief = useAnswer<RunExecutive>(`brief:${runId}:${locale}:${JSON.stringify(filters)}`, () => api.runExecutive(runId, locale, filters))
  const caps = result.capabilities
  const decision = brief.data?.advisory?.decisions?.[0]
  const priority = brief.data?.priorities?.[0]
  const chosen = decision ? { title: decision.title, detail: decision.action, refs: decision.evidence_refs }
    : priority ? { title: priority.title, detail: priority.detail, refs: priority.evidence_refs } : null
  const evidence = (brief.data?.evidence ?? []).filter((e) => chosen?.refs.includes(e.id))
  const expected = caps.predictive_risk?.available ? t('riskReady')
    : caps.forecast?.reason?.[locale] ?? t('unavailable')
  if (brief.error) return <p role="alert" className="card__meta">{t('error')}</p>
  if (!brief.data) return <p className="card__meta">{t('loading')}</p>
  return <dl className="layout__brief">
    <div><dt>{t('happening')}</dt><dd dir="auto">{brief.data.headline}</dd></div>
    <div><dt>{t('expected')}</dt><dd dir="auto">{expected}</dd></div>
    <div className="layout__decision"><dt>{t('decide')}</dt><dd>
      {chosen ? <><strong dir="auto">{chosen.title}</strong><p dir="auto">{chosen.detail}</p>
        <span className="layout__badge">{t('proposed')}</span>
        <div className="layout__actions">
          <button type="button" className="btn btn--ghost" aria-expanded={open} onClick={() => setOpen(!open)}>{t('evidence')}</button>
          <button type="button" className="btn btn--primary" onClick={onOpenRun}>{t('review')}</button>
        </div>
        {open ? <ul className="layout__evidence">{evidence.length ? evidence.map((e) => <li key={e.id}>
          <span dir="auto">{e.label}</span>: <bdi>{e.value === null ? t('noValue') : formatNumber(e.value)}</bdi>
          <small dir="auto"> · {e.method}</small></li>) : <li>{t('noValue')}</li>}</ul> : null}
      </> : <span>{t('noDecision')}</span>}
    </dd></div>
  </dl>
}

/** The selected priority, opened up: what drives it under the same filters,
 *  the records behind it, and questions Jarvis can answer for this selection. */
function Focus({ runId, name, drivers, measures, filters, maintenance, onClear }: {
  runId: string; name: string; drivers?: string; measures: LayoutSection['binding']['measures']; filters: TableFilter[]
  maintenance: boolean; onClear: () => void
}) {
  const { t, formatNumber } = usePack(layoutMessages)
  const { locale } = useI18n()
  const ask = useJarvisPrompt()
  const spec = drivers ? { group_by: [drivers], measures, filters, sort: { by: measures[0]?.agg === 'count' ? 'count' : `${measures[0]?.agg}:${measures[0]?.column}`, desc: true }, limit: 5 } : null
  const split = useAnswer<QueryAnswer>(spec ? `focus:${runId}:${locale}:${JSON.stringify(spec)}` : null, () => api.queryTable(runId, spec!, locale))
  const rows = useAnswer<RecordsPage>(`focus-r:${runId}:${locale}:${JSON.stringify(filters)}`, () => api.tableRecords(runId, { filters, limit: 5 }, locale))
  return <section className="layout__focus" aria-label={t('selected', { name })}>
    <header className="layout__head"><h5 dir="auto">{t('selected', { name })}</h5>
      <button type="button" className="btn btn--ghost" onClick={onClear}>{t('clear')}</button></header>
    {drivers && split.data ? <><h6>{t('drivers')} · <bdi>{drivers}</bdi></h6>
      <Bars items={split.data.groups.map((g) => ({ label: label(g.keys[0] ?? null), value: g.values[0] }))} label={t('drivers')} /></> : null}
    {rows.data ? <><h6>{t('sample')}</h6><div className="layout__scroll"><table className="table">
      <thead><tr>{rows.data.columns.slice(0, 6).map((c) => <th key={c} scope="col">{c}</th>)}</tr></thead>
      <tbody>{rows.data.rows.map((r, i) => <tr key={i}>{r.slice(0, 6).map((v, j) => <td key={j} dir="auto">{v ?? ''}</td>)}</tr>)}</tbody>
    </table></div><p className="card__meta">{t('rows', { n: formatNumber(rows.data.total) })}</p></> : null}
    {maintenance && ask ? <div className="layout__actions"><span className="card__meta">{t('jarvisScope')}</span>
      <button type="button" className="btn btn--ghost" onClick={() => ask(t('askCost'))}>{t('askCost')}</button>
      <button type="button" className="btn btn--ghost" onClick={() => ask(t('askFailures'))}>{t('askFailures')}</button></div>
      : <p className="card__meta">{t('jarvisOnly')}</p>}
  </section>
}

/** One planned section. Its numbers come from the query engine under the
 *  dashboard's shared filters, so a pick anywhere narrows every section and
 *  Jarvis, whose scope is the same filter list. */
function Section({ runId, section, filters, state, roles, setState, pinned, onPin, result, onOpenRun }: {
  runId: string; section: LayoutSection; filters: TableFilter[]; state: DashState; roles: Roles
  setState: (next: DashState) => void; pinned: boolean; onPin: () => void; result: LayoutResult; onOpenRun: () => void
}) {
  const { t, formatNumber } = usePack(layoutMessages)
  const { locale } = useI18n()
  const b = section.binding
  // A priority list is the selector: it keeps its own choices visible.
  const own = section.component === 'priorities' && typeof b.group_by?.[0] === 'string' ? b.group_by[0] : undefined
  const scoped = [...(b.filters ?? []), ...filters.filter((f) => f.column !== own)]
  const isTable = section.component === 'table'
  const spec = section.component === 'gap' || section.component === 'brief' ? null : isTable ? { filters: scoped, limit: Math.min(b.limit ?? 20, 50) }
    : { group_by: b.group_by, measures: b.measures, sort: b.sort, limit: b.limit ?? 100, filters: scoped }
  const answer = useAnswer<QueryAnswer | RecordsPage>(spec ? `ly:${runId}:${locale}:${section.id}:${JSON.stringify(spec)}` : null,
    (): Promise<QueryAnswer | RecordsPage> => isTable ? api.tableRecords(runId, spec!, locale) : api.queryTable(runId, spec as never, locale))
  const title = section.title[locale]
  const column = typeof b.group_by?.[0] === 'string' ? b.group_by[0] as string : null
  let body: React.ReactNode = <p className="card__meta">{t('loading')}</p>
  if (section.component === 'brief') body = <Brief runId={runId} filters={filters} result={result} onOpenRun={onOpenRun} />
  else if (section.component === 'gap') body = <p className="layout__gap"><strong>{t('unavailable')}</strong> · {section.reason?.[locale]}</p>
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
    } else if (section.component === 'priorities' && column) {
      const held = state.filters[column]?.[0]
      body = <><ol className="layout__priorities">{groups.slice(0, 3).map((g, i) => {
        const name = label(g.keys[0] ?? null)
        return <li key={name}><button type="button" aria-pressed={held === name} onClick={() => setState(pick(state, column, name, roles.date))}>
          <span className="layout__rank">{i + 1}</span><span dir="auto">{name}</span>
          <strong><bdi>{g.values[0] === null ? t('noValue') : formatNumber(g.values[0])}</bdi></strong></button></li>
      })}</ol>
      {held ? <Focus runId={runId} name={held} drivers={b.drivers} measures={b.measures} filters={filters}
        maintenance={result.domain?.name === 'maintenance'} onClear={() => setState(pick(state, column, held, roles.date))} /> : null}</>
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
export function DesignedPage({ runId, roles, state, filters, setState, onOpenRun }: {
  runId: string; roles: Roles; state: DashState; filters: TableFilter[]; setState: (next: DashState) => void; onOpenRun?: () => void
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
        result={shown!.result} onOpenRun={onOpenRun ?? (() => undefined)}
        onPin={() => save(togglePin(history, section.id))} />) : <p className="card__meta">{t('designing')}</p>}
    </div>
  </div>
}
