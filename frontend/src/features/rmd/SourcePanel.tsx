import { useEffect, useId, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { usePack } from '../../i18n/pack'
import { Dialog } from '../../shared/components/Dialog'
import { MAX_UPLOAD_BYTES } from '../../shared/api'
import { rmdApi, saveDownload } from './api'
import { EvidenceDetails, evidenceText, valueText } from './display'
import { messages, type RmdMessageKey } from './messages'
import { grains } from './types'
import type { ApplicabilityDecision, EvidenceSource, SheetMapping, SourceCell, SourceSheet, ValueState } from './types'

const fields = ['sr_id','wo_id','wo_status','event_date','location','category','symptom','assessment','recovery_action','suspected_cause','verified_root_cause','rca_evidence','source_reconciliation_label','comparison_source','due_date','outstanding_status'] as const
export function SourceApplicability({value}:{value?:ApplicabilityDecision}) {
  const {t}=usePack(messages)
  const key=value?.state==='confirmed_current'?'applicabilityConfirmed':value?.state==='superseded'?'applicabilitySuperseded':value?.state==='not_applicable'?'applicabilityNotApplicable':'applicabilityUnverified'
  return <p className="rmd-muted">{t(key)}</p>
}
function sheetsFor(source: EvidenceSource): SourceSheet[] { return source.sheets ?? source.metadata?.sheets ?? [] }
function startingMapping(source: EvidenceSource): SheetMapping[] {
  return source.mapping?.sheets?.map(sheet => ({ ...sheet, columns: { ...sheet.columns } })) ?? sheetsFor(source).map(sheet => ({
    name: sheet.name, role: sheet.suggested_role ?? 'other', header_row: sheet.header_row_proposed ?? sheet.header_row ?? sheet.proposed_header_row ?? 1, columns: {},
  }))
}

export function ImportSource({ packId, onImported, readOnly }: { packId: string; onImported: () => void; readOnly: boolean }) {
  const { t } = usePack(messages)
  const id = useId(), input = useRef<HTMLInputElement>(null), alive = useRef(true), lock = useRef(false), generation = useRef(0)
  const [file, setFile] = useState<File | null>(null)
  const [kind, setKind] = useState<'procedure' | 'workbook'>('workbook')
  const [busy, setBusy] = useState(false), [error, setError] = useState<string | null>(null), [notice, setNotice] = useState(false)
  useEffect(() => { alive.current = true;generation.current+=1;lock.current=false;setBusy(false);return () => { alive.current = false;generation.current+=1 } }, [])
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(null); setNotice(false)
    if (lock.current) return
    if (!file) { setError(t('fileRequired')); return }
    if (file.size > MAX_UPLOAD_BYTES) { setError(t('fileTooLarge')); return }
    const scope=generation.current
    lock.current = true; setBusy(true)
    try {
      await rmdApi.upload(packId, file, kind)
      if (!alive.current||scope!==generation.current) return
      setFile(null); if (input.current) input.current.value = ''
      setNotice(true); onImported()
    } catch (reason) { if (alive.current&&scope===generation.current) setError(reason instanceof Error && reason.message ? reason.message : t('failed')) }
    finally { if(scope===generation.current){lock.current = false; if (alive.current) setBusy(false)} }
  }
  return <details className="rmd-card rmd-import">
    <summary>{t('importSources')}</summary>
    <form className="rmd-stack" onSubmit={submit} aria-busy={busy}>
      <p className="rmd-muted">{t('fileHelp')}</p>
      <div className="rmd-form-row">
        <label htmlFor={`${id}-kind`}>{t('sourceKind')}<select id={`${id}-kind`} value={kind} disabled={busy || readOnly} onChange={event => { setKind(event.target.value as typeof kind); setFile(null); if (input.current) input.current.value = '' }}><option value="workbook">{t('workbook')}</option><option value="procedure">{t('procedure')}</option></select></label>
        <label htmlFor={`${id}-file`}>{t('sourceFile')}<input ref={input} id={`${id}-file`} type="file" accept={kind === 'workbook' ? '.xlsx,.xlsm' : '.doc,.docx'} onChange={event => { setFile(event.target.files?.[0] ?? null); setError(null) }} disabled={busy || readOnly} aria-describedby={`${id}-file-details`} /></label>
      </div>
      <p id={`${id}-file-details`} className="rmd-muted">{file ? <><bdi>{file.name}</bdi> · <bdi>{file.size.toLocaleString('en')}</bdi> {t('bytes')}</> : t('sourceFile')}</p>
      {error && <p className="rmd-error" role="alert">{error}</p>}
      {notice && <p role="status">{t('imported')}</p>}
      <button className="btn btn--primary" type="submit" disabled={busy || readOnly || !file}>{busy ? t('uploading') : t('upload')}</button>
    </form>
  </details>
}

export function SourceInspector({ packId, sourceId, readOnly, onClose, onChanged }: {
  packId: string; sourceId: string; readOnly: boolean; onClose: () => void; onChanged: () => void
}) {
  const { t, locale, formatNumber } = usePack(messages)
  const id = useId(), alive = useRef(true), lock = useRef(false), translate = useRef(t)
  const draftSource=useRef(''),draftRevision=useRef<number|undefined>(undefined),dirty=useRef(false)
  const generation=useRef(0)
  translate.current = t
  const [source, setSource] = useState<EvidenceSource | null>(null)
  const [authorised,setAuthorised]=useState(false)
  const [mapping, setMapping] = useState<SheetMapping[]>([])
  const [loading, setLoading] = useState(true), [attempt, setAttempt] = useState(0)
  const [error, setError] = useState<string | null>(null), [busy, setBusy] = useState(false), [notice, setNotice] = useState(false)
  useEffect(() => { alive.current = true;generation.current+=1;lock.current=false;setBusy(false);return () => { alive.current = false;generation.current+=1 } }, [])
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError(null);setAuthorised(false)
    rmdApi.source(packId, sourceId, controller.signal).then(result => { if (!controller.signal.aborted) {
      setSource(result);setAuthorised(true)
      if(draftSource.current!==result.id||!dirty.current){draftSource.current=result.id;draftRevision.current=result.revision;dirty.current=false;setMapping(startingMapping(result))}
      else if(draftRevision.current!==result.revision)setError(translate.current('mappingStale'))
    } })
      .catch(reason => { if (!controller.signal.aborted) setError(reason instanceof Error && reason.message ? reason.message : translate.current('failed')) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [packId, sourceId, attempt])
  async function save(event: FormEvent) {
    event.preventDefault(); if (lock.current) return
    const scope=generation.current
    lock.current = true; setBusy(true); setError(null); setNotice(false)
    try { const result = await rmdApi.map(packId, sourceId, mapping, draftRevision.current); if (alive.current&&scope===generation.current) { setSource(result); draftRevision.current=result.revision;dirty.current=false;setMapping(startingMapping(result));setNotice(true); onChanged() } }
    catch (reason) { if (alive.current&&scope===generation.current) setError(reason instanceof Error && reason.message ? reason.message : t('failed')) }
    finally { if(scope===generation.current){lock.current = false; if (alive.current) setBusy(false)} }
  }
  async function download() {
    if (!source || lock.current) return
    const scope=generation.current
    lock.current = true; setBusy(true); setError(null)
    try { const data = await rmdApi.original(packId, source); if (alive.current&&scope===generation.current) saveDownload(data) }
    catch (reason) { if (alive.current&&scope===generation.current) setError(reason instanceof Error && reason.message ? reason.message : t('failed')) }
    finally { if(scope===generation.current){lock.current = false; if (alive.current) setBusy(false)} }
  }
  const sheets = source ? sheetsFor(source) : []
  const document = source?.document ?? source?.metadata?.document
  const coverage = source?.coverage ?? source?.metadata?.coverage
  const warnings = source?.warnings ?? source?.metadata?.warnings ?? []
  return <Dialog title={authorised&&source?source.name:t('inspectSource')} onClose={onClose} wide initialFocus="panel">
    {loading && <p role="status">{t('loading')}</p>}
    {error && <div className="rmd-error" role="alert"><p>{error}</p><button className="btn" disabled={busy} onClick={() => {dirty.current=false;setAttempt(value => value + 1)}}>{source ? t('reloadMapping') : t('retry')}</button>{source&&<p>{t('reloadMappingHelp')}</p>}</div>}
    {source && authorised && <div className="rmd-stack">
      <p className="rmd-source-id"><strong>{t('sourceVersion')}</strong> <bdi>{source.sha256}</bdi></p>
      {source.kind==='procedure'&&<><SourceApplicability value={source.applicability}/><details><summary>{t('applicability')}</summary><EvidenceDetails value={source.applicability} empty={t('unknown')}/></details></>}
      {warnings.length > 0 && <div><h3>{t('warnings')}</h3><ul>{warnings.map((warning, index) => <li key={index} dir="auto">{evidenceText(warning, locale)}</li>)}</ul></div>}
      <details><summary>{t('sourceCoverage')}</summary><p>{t('coverageHelp')}</p><EvidenceDetails value={coverage} empty={t('unknown')} /></details>
      {document && <section><h3>{t('digest')}</h3><p><strong>{t('documentCode')}:</strong> <bdi>{source.document_code ?? document.document_code ?? document.code ?? t('unknown')}</bdi> · <strong>{t('revision')}:</strong> <bdi>{source.document_revision ?? document.revision ?? t('unknown')}</bdi></p><EvidenceDetails value={document.digest ?? document} empty={t('unknown')} /></section>}
      {sheets.length > 0 && <form className="rmd-stack" onSubmit={save} aria-busy={busy}>
        <h3>{t('mapping')}</h3><p>{t('mappingHelp')}</p>
        {mapping.map((draft, index) => {
          const sheet = sheets.find(item => item.name === draft.name)
          if (!sheet) return null
          const columns = sheet.columns ?? []
          function change(next: Partial<SheetMapping>) { dirty.current=true;setMapping(current => current.map((item, at) => at === index ? { ...item, ...next } : item)) }
          const row = sheet.rows?.find(item => (item.source_row ?? item.row) === draft.header_row)
          function label(letter: string) {
            const cell = row?.cells && !Array.isArray(row.cells) ? row.cells[letter] : undefined
            return valueText(cell?.value ?? cell?.raw_value, columns.find(item => item.letter === letter)?.label ?? letter)
          }
          return <fieldset key={draft.name} className="rmd-sheet"><legend dir="auto">{draft.name}</legend>
            {(sheet.hidden || (sheet.visibility && sheet.visibility !== 'visible')) && <p className="rmd-notice">{t('hiddenSheet')}</p>}
            <div className="rmd-form-row">
              <label htmlFor={`${id}-${index}-grain`}>{t('grain')}<select id={`${id}-${index}-grain`} disabled={readOnly || busy} value={draft.role} onChange={event => change({ role: event.target.value as SheetMapping['role'] })}>{grains.map(grain => <option key={grain} value={grain}>{t(grain)}</option>)}</select></label>
              <label htmlFor={`${id}-${index}-row`}>{t('headerRow')}<input id={`${id}-${index}-row`} min="1" max={sheet.source_row_count ?? 1_048_576} required type="number" disabled={readOnly || busy} value={draft.header_row} onChange={event => change({ header_row: Number(event.target.value) })} /></label>
              <label htmlFor={`${id}-${index}-date`}>{t('dateFormat')}<select id={`${id}-${index}-date`} disabled={readOnly||busy} value={draft.date_format??'ISO'} onChange={event=>change({date_format:event.target.value as SheetMapping['date_format']})}><option value="ISO">{t('dateISO')}</option><option value="DMY">{t('dateDMY')}</option><option value="MDY">{t('dateMDY')}</option></select></label>
            </div>
            <p className="rmd-muted">{t('dateFormatHelp')}</p>
            <p className="rmd-muted">{t('beyondFilter')} <bdi>{sheet.auto_filter_ref ?? sheet.auto_filter ?? ''}</bdi></p>
            {draft.role !== 'summary' && <div className="rmd-mapping-grid">{fields.map(field => <label key={field} htmlFor={`${id}-${index}-${field}`}>{t(field)}<select id={`${id}-${index}-${field}`} disabled={readOnly || busy} value={draft.columns[field] ?? ''} onChange={event => change({ columns: { ...draft.columns, [field]: event.target.value } })}><option value="">{t('ignoreField')}</option>{columns.map(column => <option key={column.letter} value={column.letter}>{column.letter} · {label(column.letter)}{column.hidden ? ` · ${t('hiddenColumn')}` : ''}</option>)}</select></label>)}</div>}
            {draft.role!=='summary'&&<ValueStateEditor mapping={draft} onChange={value_states=>change({value_states})} disabled={readOnly||busy}/>}
            <details><summary>{t('records')}</summary><div className="rmd-table" tabIndex={0} role="region" aria-label={`${t('sheet')} ${sheet.name}`}><table><thead><tr><th>{t('sourceRow')}</th>{columns.slice(0,12).map(column => <th key={column.letter} scope="col"><bdi>{column.letter}</bdi> · <span dir="auto">{label(column.letter)}</span>{column.hidden && <span className="rmd-muted"> · {t('hiddenColumn')}</span>}</th>)}</tr></thead><tbody>{sheet.rows?.slice(0,10).map((sourceRow, at) => <tr key={sourceRow.source_row ?? at}><th scope="row">{formatNumber(sourceRow.source_row ?? sourceRow.row ?? at + 1)}</th>{columns.slice(0,12).map(column => {
              const cell: SourceCell | undefined = sourceRow.cells && !Array.isArray(sourceRow.cells) ? sourceRow.cells[column.letter] : undefined
              return <td key={column.letter} dir="auto">{valueText(cell?.value ?? cell?.raw_value, t('unknown'))}{cell?.formula && <small className="rmd-formula"><bdi>{cell.formula}</bdi> · {valueText(cell.cached_value ?? cell.cached, t('notMeasured'))}</small>}</td>
            })}</tr>)}</tbody></table></div></details>
          </fieldset>
        })}
        {notice && <p role="status">{t('mapped')}</p>}
        <button className="btn btn--primary" type="submit" disabled={readOnly || busy || loading}>{busy ? t('saving') : t('saveMapping')}</button>
      </form>}
      <details><summary>{t('sourceDetails')}</summary><EvidenceDetails value={source.extraction} empty={t('unknown')} /></details>
      <div className="rmd-actions"><button className="btn" disabled={busy} onClick={download}>{t('original')}</button><button className="btn" onClick={onClose}>{t('close')}</button></div>
    </div>}
  </Dialog>
}

function ValueStateEditor({mapping,onChange,disabled}:{mapping:SheetMapping;onChange:(states:NonNullable<SheetMapping['value_states']>)=>void;disabled:boolean}){
  const {t}=usePack(messages),id=useId(),[field,setField]=useState<string>('sr_id'),[token,setToken]=useState(''),[meaning,setMeaning]=useState<ValueState>('unknown')
  const choices=['unknown','not_applicable','not_measured','unresolved_placeholder']as const
  const label=(state:ValueState)=>state==='not_applicable'?t('notApplicable'):state==='not_measured'?t('notMeasured'):state==='unresolved_placeholder'?t('placeholders'):state==='measured_zero'?t('measuredZero'):state==='recorded'?t('recorded'):state==='blank'?t('blank'):t('unknown')
  const rules=Object.entries(mapping.value_states??{}).flatMap(([name,values])=>Object.entries(values).map(([source,meaning])=>({name,source,meaning})))
  function add(){if(!token.length)return;onChange({...mapping.value_states,[field]:{...mapping.value_states?.[field],[token]:meaning}});setToken('')}
  function remove(name:string,source:string){const next={...mapping.value_states,[name]:{...mapping.value_states?.[name]}};delete next[name][source];if(!Object.keys(next[name]).length)delete next[name];onChange(next)}
  return <details><summary>{t('valueStates')}</summary><p className="rmd-muted">{t('valueStatesHelp')}</p><div className="rmd-form-row"><label htmlFor={`${id}-field`}>{t('field')}<select id={`${id}-field`} value={field} onChange={event=>setField(event.target.value)} disabled={disabled}>{fields.map(name=><option key={name} value={name}>{t(name)}</option>)}</select></label><label htmlFor={`${id}-token`}>{t('sourceValue')}<input id={`${id}-token`} value={token} onChange={event=>setToken(event.target.value)} maxLength={64} disabled={disabled}/></label><label htmlFor={`${id}-meaning`}>{t('recordedMeaning')}<select id={`${id}-meaning`} value={meaning} onChange={event=>setMeaning(event.target.value as ValueState)} disabled={disabled}>{choices.map(state=><option key={state} value={state}>{label(state)}</option>)}</select></label><button className="btn" type="button" onClick={add} disabled={disabled||!token.length}>{t('addRule')}</button></div>{rules.length>0&&<ul className="rmd-list">{rules.map(rule=><li key={`${rule.name}-${rule.source}`}><span>{fields.includes(rule.name as typeof fields[number])?t(rule.name as typeof fields[number]):rule.name} · <bdi>{rule.source}</bdi> → {label(rule.meaning)}</span> <button className="btn btn--ghost" type="button" disabled={disabled} onClick={()=>remove(rule.name,rule.source)} aria-label={`${t('removeRule')} · ${rule.name} · ${rule.source}`}>{t('removeRule')}</button></li>)}</ul>}</details>
}

export function sourceLabel(source: EvidenceSource): string { return source.document_code ?? source.document?.document_code ?? source.metadata?.document?.document_code ?? source.name }
export const fieldKeys = fields as readonly RmdMessageKey[]
