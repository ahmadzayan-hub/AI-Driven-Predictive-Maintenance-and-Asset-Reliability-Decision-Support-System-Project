import { useEffect, useId, useState } from 'react'
import { usePack } from '../../i18n/pack'
import { Dialog } from '../../shared/components/Dialog'
import { Bars, Figure, Line } from '../dashboard/charts'
import { rmdApi } from './api'
import { EvidenceDetails, evidenceText, valueText } from './display'
import { messages, type RmdMessageKey } from './messages'
import type { CalculationDetails, EvidenceChart, EvidencePage, EvidenceQuery, EvidenceText } from './types'

export interface EvidenceSelection { title: string; query: EvidenceQuery; calculation?: CalculationDetails; explanation?: EvidenceText }

export function RecordsDialog({ packId, analysisId, selection, onClose }: { packId: string; analysisId: string; selection: EvidenceSelection; onClose: () => void }) {
  const { t, locale, formatNumber } = usePack(messages)
  const [page, setPage] = useState<EvidencePage | null>(null)
  const [offset, setOffset] = useState(0), [attempt, setAttempt] = useState(0)
  const [loading, setLoading] = useState(true), [error, setError] = useState<string | null>(null)
  const key = JSON.stringify(selection.query), id = useId(), limit = 25
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError(null); setPage(null)
    const query: EvidenceQuery = JSON.parse(key)
    rmdApi.records(packId, analysisId, { ...query, offset, limit }, controller.signal).then(result => { if (!controller.signal.aborted) setPage(result) })
      .catch(reason => { if (!controller.signal.aborted) setError(reason instanceof Error && reason.message ? reason.message : t('failed')) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [packId, analysisId, key, offset, attempt, t])
  const calc = selection.calculation
  const columns = ['sr_id', 'wo_id', 'wo_status', 'event_date', 'location'] as const
  return <Dialog title={selection.title} onClose={onClose} wide initialFocus="panel">
    <div className="rmd-stack">
      <p>{t('recordsHelp')}</p>
      {selection.explanation && <p dir="auto">{evidenceText(selection.explanation, locale)}</p>}
      {calc && <details><summary>{t('calculations')}</summary><dl className="rmd-details">
        <div><dt>{t('formulas')}</dt><dd dir="auto">{calc.formula??t('unknown')}</dd></div>
        <div><dt>{t('population')}</dt><dd dir="auto">{calc.population?.grain??t('unknown')} · <bdi>{calc.population?formatNumber(calc.population.records):t('unknown')}</bdi></dd></div>
        <div><dt>{t('unit')}</dt><dd>{calc.unit==='records'?t('sourceRecords'):calc.unit??t('unknown')}</dd></div>
        <div><dt>{t('numerator')}</dt><dd>{calc.numerator === null || calc.numerator === undefined ? t('notApplicable') : formatNumber(calc.numerator)}</dd></div>
        <div><dt>{t('denominator')}</dt><dd>{calc.denominator === null || calc.denominator === undefined ? t('notApplicable') : formatNumber(calc.denominator)}</dd></div>
        <div><dt>{t('missingPolicy')}</dt><dd dir="auto">{evidenceText(calc.missing_policy, locale) || t('unknown')}</dd></div>
        <div><dt>{t('exclusions')}</dt><dd><EvidenceDetails value={calc.exclusions} empty={t('unknown')} /></dd></div>
        <div><dt>{t('displayedScope')}</dt><dd><EvidenceDetails value={{period:calc.period,coverage:calc.coverage}} empty={t('unknown')} /></dd></div>
        <div><dt>{t('sourceVersions')}</dt><dd><EvidenceDetails value={calc.source_versions} empty={t('unknown')} /></dd></div>
        <div><dt>{t('version')}</dt><dd><bdi>{calc.calculation_version}</bdi></dd></div>
      </dl></details>}
      {loading && <p role="status">{t('loading')}</p>}
      {error && <div className="rmd-error" role="alert"><p>{error}</p><button className="btn" onClick={() => setAttempt(value => value + 1)}>{t('retry')}</button></div>}
      {page && (page.records.length ? <>
        <div className="rmd-table" role="region" tabIndex={0} aria-labelledby={`${id}-table`}><table>
          <caption id={`${id}-table`}>{t('records')}</caption>
          <thead><tr><th scope="col">{t('sourceRow')}</th>{columns.map(field => <th key={field} scope="col">{t(field)}</th>)}<th scope="col">{t('fields')}</th></tr></thead>
          <tbody>{page.records.map(record => <tr key={record.id}>
            <th scope="row"><bdi>{record.sheet}</bdi> · <bdi>{formatNumber(record.source_row)}</bdi><small className="rmd-formula"><bdi>{record.id}</bdi></small></th>
            {columns.map(field => <td key={field} dir="auto"><bdi>{valueText(record.fields[field], t('unknown'))}</bdi></td>)}
            <td><details><summary>{t('fields')}</summary><dl className="rmd-details">{Object.entries(record.fields).map(([field,value]) => <div key={field}><dt dir="auto">{field in messages.en ? t(field as RmdMessageKey) : field.replaceAll('_',' ')}</dt><dd dir="auto">{valueText(value,t('unknown'))}</dd></div>)}</dl><p><strong>{t('source')}:</strong> <bdi>{record.source_id}</bdi></p><p className="rmd-source-id"><bdi>{record.source_sha}</bdi></p></details></td>
          </tr>)}</tbody>
        </table></div>
        <div className="rmd-actions"><button className="btn" disabled={loading || offset === 0} onClick={() => setOffset(value => Math.max(0,value-limit))}>{t('previous')}</button><span role="status">{t('pageRange',{from:offset+1,to:Math.min(offset+limit,page.total),total:page.total})}</span><button className="btn" disabled={loading || offset+page.records.length>=page.total} onClick={() => setOffset(value=>value+limit)}>{t('next')}</button></div>
      </> : <p>{t('noRecords')}</p>)}
      <button className="btn" onClick={onClose}>{t('close')}</button>
    </div>
  </Dialog>
}

export function EvidenceChartCard({ chart, onEvidence }: { chart: EvidenceChart; onEvidence: (selection: EvidenceSelection) => void }) {
  const { t, locale, formatNumber } = usePack(messages)
  const title = evidenceText(chart.title,locale), items = chart.table.map(row => ({ label: row.label, value: row.value }))
  const month = (label: string) => /^\d{4}-\d{2}$/.test(label) ? Number(label.slice(0,4))*12+Number(label.slice(5,7)) : null
  const observed = items.flatMap<{label:string;value:number|null}>((item,index) => {
    const current=month(item.label),previous=index?month(items[index-1].label):null
    return current!==null&&previous!==null&&current-previous>1 ? [{label:t('notMeasured'),value:null},item] : [item]
  })
  const share = (value: number | null | undefined) => typeof value==='number' ? `${formatNumber(value*100,{maximumFractionDigits:1})}%` : t('unavailable')
  return <section className="rmd-card rmd-chart">
    <Figure title={title} chart={chart.kind === 'line' ? <Line points={observed} label={title} /> : <Bars items={items} label={title} />} table={<table>
      <caption>{t('chartTable')}</caption><thead><tr><th scope="col">{t('bucket')}</th><th scope="col">{t('value')}</th>{chart.kind==='bar'&&<><th scope="col">{t('share')}</th><th scope="col">{t('cumulativeShare')}</th></>}<th scope="col">{t('evidence')}</th></tr></thead>
      <tbody>{chart.table.map((row,index)=><tr key={`${row.label}-${index}`}><th scope="row" dir="auto">{row.label || t('unknown')}</th><td>{formatNumber(row.value)}</td>{chart.kind==='bar'&&<><td><bdi>{share(row.share)}</bdi></td><td><bdi>{share(row.cumulative_share)}</bdi></td></>}<td><button className="btn btn--ghost" onClick={()=>onEvidence({title:`${title} · ${row.label}`,query:{record_ids:row.record_ids},explanation:chart.question,calculation:chart})}>{t('evidence')}</button></td></tr>)}</tbody>
    </table>} />
    <p className="rmd-muted">{t('denominator')}: <bdi>{formatNumber(chart.denominator)}</bdi> · {t('omitted')}: <bdi>{formatNumber(chart.missing_records)}</bdi></p>
    {chart.kind==='line'&&<p className="rmd-muted">{t('observedMonths')}</p>}
    <button className="btn" onClick={()=>onEvidence({title,query:{record_ids:chart.table.flatMap(row=>row.record_ids)},explanation:chart.question,calculation:chart})}>{t('evidence')}</button>
  </section>
}
