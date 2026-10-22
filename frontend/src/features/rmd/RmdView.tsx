import { useCallback, useEffect, useId, useRef, useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'
import { usePack } from '../../i18n/pack'
import { useStore } from '../../app/store'
import { ApiError } from '../../shared/api'
import { useReadOnly } from '../../shared/readOnly'
import { Dialog } from '../../shared/components/Dialog'
import { Icon } from '../../shared/components/Icon'
import { rmdApi, saveDownload } from './api'
import { EvidenceDetails, evidenceText } from './display'
import { EvidenceChartCard, RecordsDialog } from './EvidencePanel'
import type { EvidenceSelection } from './EvidencePanel'
import { ImportSource, SourceApplicability, SourceInspector } from './SourcePanel'
import { messages, type RmdMessageKey } from './messages'
import type { AnalysisFilters, Clause, EvidenceAnalysis, EvidencePack, EvidenceSource, ProposedAction, ProposedLink } from './types'
import '../dashboard/dashboard.css'
import './rmd.css'

type View = 'overview' | 'investigations' | 'knowledge' | 'quality'
const views: View[] = ['overview', 'investigations', 'knowledge', 'quality']

function useRequestKey() {
  const keys = useRef(new Map<string,string>())
  return (kind: string, body: unknown, completed = false) => {
    const signature = `${kind}:${JSON.stringify(body)}`
    if (!keys.current.has(signature)) keys.current.set(signature,crypto.randomUUID())
    const key = keys.current.get(signature)!
    if (completed) keys.current.delete(signature)
    return key
  }
}

function normalise(result: EvidenceAnalysis): EvidenceAnalysis {
  return { ...result, counts_by_grain: result.counts_by_grain ?? {}, kpis: result.kpis ?? [], charts: result.charts ?? [],
    priorities: result.priorities ?? [], conflicts: result.conflicts ?? [], proposed_links: result.proposed_links ?? [],
    completeness: result.completeness ?? [], readiness: result.readiness ?? [], limitations: result.limitations ?? [] }
}

export interface RmdViewProps { onExplain?: (packId: string, analysisId: string) => void; onOpenRun?: (runId: string) => void }

export function RmdView(props: RmdViewProps) {
  const { t, dir } = usePack(messages)
  const { identity } = useStore(), readOnly = useReadOnly()
  const [packs, setPacks] = useState<EvidencePack[]>([]), [selected, setSelected] = useState('')
  const [loading, setLoading] = useState(true), [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0), [creating, setCreating] = useState(false), [title, setTitle] = useState('')
  const id = useId(), key = useRequestKey(), createLock = useRef(false), identityRef = useRef(identity?.principal.subject), loadedIdentity = useRef(identity?.principal.subject)
  identityRef.current = identity?.principal.subject
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError(null)
    if (loadedIdentity.current !== identity?.principal.subject) {
      loadedIdentity.current = identity?.principal.subject; setPacks([]); setSelected(''); setTitle(''); setCreating(false)
    }
    rmdApi.packs(controller.signal).then(result => {
      if (controller.signal.aborted) return
      setPacks(result.packs ?? []); setSelected(current => result.packs.some(pack => pack.id === current) ? current : result.packs[0]?.id ?? '')
    }).catch(reason => { if (!controller.signal.aborted) setError(reason instanceof Error && reason.message ? reason.message : t('failed')) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [identity?.principal.subject, attempt, t])
  async function create(event: FormEvent) {
    event.preventDefault()
    if (createLock.current) return
    if (!title.trim()) { setError(t('nameRequired')); return }
    createLock.current = true; setCreating(true); setError(null)
    const actor = identity?.principal.subject
    try {
      const result = await rmdApi.create(title.trim(),key('create',title.trim()))
      key('create',title.trim(),true)
      if (actor !== identityRef.current) return
      setPacks(current => [...current.filter(pack=>pack.id!==result.id),result]); setSelected(result.id); setTitle('')
    } catch (reason) { if (actor === identityRef.current) setError(reason instanceof Error && reason.message ? reason.message : t('failed')) }
    finally { createLock.current = false; if (actor === identityRef.current) setCreating(false) }
  }
  return <section className="rmd view" aria-labelledby={`${id}-heading`} dir={dir}>
    <header className="rmd-heading"><div><p className="rmd-eyebrow">{t('privateEvidence')}</p><h2 id={`${id}-heading`}>{t('title')}</h2><p>{t('intro')}</p></div><span className="rmd-emblem"><Icon name="shield" size={28} /></span></header>
    <p className="rmd-muted">{t('noDemo')}</p>
    {loading && <p role="status">{t('loading')}</p>}
    {error && <div className="rmd-error" role="alert"><p>{error}</p><button className="btn" onClick={()=>setAttempt(value=>value+1)}>{t('retry')}</button></div>}
    {!loading && <div className="rmd-toolbar">
      {packs.length > 0 && <label htmlFor={`${id}-pack`}>{t('pack')}<select id={`${id}-pack`} value={selected} onChange={event=>setSelected(event.target.value)} disabled={creating}>{packs.map(pack=><option key={pack.id} value={pack.id}>{pack.title}</option>)}</select></label>}
      {!readOnly && <details className="rmd-create" open={!packs.length || undefined}><summary>{t('createPack')}</summary><form onSubmit={create} className="rmd-form-row" aria-busy={creating}><label htmlFor={`${id}-name`}>{t('packName')}<input id={`${id}-name`} value={title} onChange={event=>setTitle(event.target.value)} disabled={creating} maxLength={160} required /></label><button className="btn" type="submit" disabled={creating}>{t('create')}</button></form></details>}
    </div>}
    {!loading && !selected && <section className="rmd-empty"><h3>{t('emptyPacks')}</h3><p>{t('emptyPacksHelp')}</p></section>}
    {selected && <PackWorkspace key={`${identity?.principal.subject ?? 'local'}:${selected}`} packId={selected} readOnly={readOnly} {...props} />}
  </section>
}
export default RmdView

function PackWorkspace({ packId, readOnly, onExplain, onOpenRun }: RmdViewProps & { packId: string; readOnly: boolean }) {
  const { t, locale, formatDate } = usePack(messages)
  const id = useId(), alive = useRef(true), key = useRequestKey(), lock = useRef(false), generation = useRef(0)
  const [pack, setPack] = useState<EvidencePack | null>(null), [attempt, setAttempt] = useState(0)
  const [packAuthorised,setPackAuthorised]=useState(false)
  const [loading, setLoading] = useState(true), [error, setError] = useState<string | null>(null), [notice, setNotice] = useState<string | null>(null)
  const [analysisId, setAnalysisId] = useState(''), [analysis, setAnalysis] = useState<EvidenceAnalysis | null>(null), [analysisLoading, setAnalysisLoading] = useState(false)
  const [analysisAttempt, setAnalysisAttempt] = useState(0), [view, setView] = useState<View>('overview')
  const [filters, setFilters] = useState<AnalysisFilters>({}), [busy, setBusy] = useState(false)
  const [sourceId, setSourceId] = useState<string | null>(null), [evidence, setEvidence] = useState<EvidenceSelection | null>(null)
  const [actions, setActions] = useState<ProposedAction[]>([])
  const [actionsError, setActionsError] = useState<string | null>(null), [actionsLoading, setActionsLoading] = useState(false)
  const refresh = useCallback(()=>setAttempt(value=>value+1),[])
  useEffect(()=>{alive.current=true;generation.current+=1;lock.current=false;setBusy(false);return()=>{alive.current=false;generation.current+=1}},[])
  useEffect(()=>{
    const controller = new AbortController(); setLoading(true); setError(null);setPackAuthorised(false)
    rmdApi.pack(packId,controller.signal).then(result=>{
      if(controller.signal.aborted)return
      setPack(result);setPackAuthorised(true);setAnalysisId(current=>result.analyses?.some(item=>item.id===current)?current:result.analyses?.[0]?.id??'')
    }).catch(reason=>{if(!controller.signal.aborted)setError(reason instanceof Error&&reason.message?reason.message:t('failed'))})
      .finally(()=>{if(!controller.signal.aborted)setLoading(false)})
    setActionsLoading(true);setActionsError(null)
    rmdApi.actions(packId,controller.signal).then(result=>{if(!controller.signal.aborted)setActions(result.actions??[])})
      .catch(reason=>{if(!controller.signal.aborted)setActionsError(reason instanceof Error&&reason.message?reason.message:t('failed'))})
      .finally(()=>{if(!controller.signal.aborted)setActionsLoading(false)})
    return()=>controller.abort()
  },[packId,attempt,t])
  useEffect(()=>{
    const controller=new AbortController();setAnalysis(null)
    setEvidence(null)
    if(!analysisId){setAnalysisLoading(false);return()=>controller.abort()}
    setAnalysisLoading(true);setError(null)
    rmdApi.analysis(packId,analysisId,controller.signal).then(result=>{if(!controller.signal.aborted)setAnalysis(normalise(result))})
      .catch(reason=>{if(!controller.signal.aborted)setError(reason instanceof Error&&reason.message?reason.message:t('failed'))})
      .finally(()=>{if(!controller.signal.aborted)setAnalysisLoading(false)})
    return()=>controller.abort()
  },[packId,analysisId,analysisAttempt,t])
  async function mutate(operation:(isCurrent:()=>boolean)=>Promise<void>) {
    if(lock.current)return
    const scope=generation.current,current=()=>alive.current&&scope===generation.current
    lock.current=true;setBusy(true);setError(null);setNotice(null)
    try{await operation(current)}catch(reason){if(current())setError(reason instanceof ApiError&&reason.status===409?t('conflict'):reason instanceof ApiError&&reason.status===403?t('forbidden'):reason instanceof Error&&reason.message?reason.message:t('failed'))}
    finally{if(scope===generation.current){lock.current=false;if(alive.current)setBusy(false)}}
  }
  function calculate(event:FormEvent){event.preventDefault();void mutate(async current=>{
    const operation = { filters, sources: pack?.sources?.map(source=>({id:source.id,sha256:source.sha256,revision:source.revision})) }
    const result=await rmdApi.analyse(packId,filters,key('analyse',operation))
    key('analyse',operation,true)
    if(!current())return
    setAnalysis(normalise(result));setAnalysisId(result.id);refresh()
  })}
  function exportFile(format:'html'|'csv'){if(!analysis)return;void mutate(async current=>{const result=await rmdApi.export(packId,analysis.id,format);if(current())saveDownload(result)})}
  function reviewReport(){
    if(!analysis||!onOpenRun)return
    if(analysis.run_id){onOpenRun(analysis.run_id);return}
    void mutate(async current=>{
      const result=await rmdApi.reviewRun(packId,analysis.id,key('review-run',analysis.id))
      if(current()){setAnalysis(value=>value?{...value,run_id:result.run_id}:value);refresh();onOpenRun(result.run_id)}
    })
  }
  function propose(priority:string){if(!analysis)return;void mutate(async current=>{
    const result=await rmdApi.proposeAction(packId,analysis.id,priority,key('action',{analysis:analysis.id,priority}))
    if(current()){setActions(value=>[...value.filter(action=>action.id!==result.id),result]);setNotice(t('actionAdded'))}
  })}
  function reviewLink(link:ProposedLink,decision:'confirmed'|'rejected',note:string){void mutate(async current=>{
    await rmdApi.decideLink(packId,link.id,decision,note,link.revision??1)
    if(current()){setNotice(t('linkReviewed'));setAnalysisAttempt(value=>value+1)}
  })}
  function tabKeys(event:KeyboardEvent<HTMLButtonElement>,current:View){
    const direction=locale==='ar'?-1:1,at=views.indexOf(current)
    let next=at
    if(event.key==='ArrowRight')next=(at+direction+views.length)%views.length
    else if(event.key==='ArrowLeft')next=(at-direction+views.length)%views.length
    else if(event.key==='Home')next=0
    else if(event.key==='End')next=views.length-1
    else return
    event.preventDefault();setView(views[next]);document.getElementById(`${id}-tab-${views[next]}`)?.focus()
  }
  const writesBlocked=readOnly||pack?.permissions?.write===false
  return <div className="rmd-stack">
    {loading&&<p role="status">{t('loading')}</p>}
    {error&&<div role="alert" className="rmd-error"><p>{error}</p><button className="btn" onClick={()=>{refresh();setAnalysisAttempt(value=>value+1)}}>{t('retry')}</button></div>}
    {notice&&<p role="status" className="rmd-notice">{notice}</p>}
    {pack&&<div className="rmd-stack" hidden={!packAuthorised} style={!packAuthorised?{display:'none'}:undefined} inert={!packAuthorised}>
      <div className="rmd-context"><strong dir="auto">{pack.title}</strong><span>{t('pack')}: <bdi>{pack.id}</bdi></span><span>{t('sources')}: <bdi>{pack.sources?.length??0}</bdi></span><button className="btn btn--ghost" onClick={refresh} disabled={loading||busy}>{t('refresh')}</button></div>
      <div className="rmd-toolbar">
        <label htmlFor={`${id}-analysis`}>{t('selectedAnalysis')}<select id={`${id}-analysis`} value={analysisId} onChange={event=>setAnalysisId(event.target.value)} disabled={busy||analysisLoading}><option value="">{t('noAnalysis')}</option>{pack.analyses?.map(item=><option key={item.id} value={item.id}>{item.title??item.id} · {item.created_at||item.calculated_at?formatDate(item.created_at??item.calculated_at!):item.calculation_version}</option>)}</select></label>
      </div>
      <ImportSource packId={packId} onImported={refresh} readOnly={writesBlocked}/>
      <details className="rmd-card"><summary>{t('sources')} · {pack.sources?.length??0}</summary><SourceRegister sources={pack.sources??[]} onInspect={setSourceId}/></details>
      <form onSubmit={calculate} className="rmd-card rmd-filters" aria-describedby={`${id}-filter-help`}>
        <h3>{t('filters')}</h3><div className="rmd-form-row">
          <label htmlFor={`${id}-from`}>{t('from')}<input id={`${id}-from`} type="date" value={filters.from??''} onChange={event=>setFilters({...filters,from:event.target.value||undefined})}/></label>
          <label htmlFor={`${id}-to`}>{t('to')}<input id={`${id}-to`} type="date" value={filters.to??''} onChange={event=>setFilters({...filters,to:event.target.value||undefined})}/></label>
          <label htmlFor={`${id}-location`}>{t('locationFilter')}<input id={`${id}-location`} value={filters.location??''} onChange={event=>setFilters({...filters,location:event.target.value||undefined})}/></label>
          <label htmlFor={`${id}-category`}>{t('categoryFilter')}<input id={`${id}-category`} value={filters.category??''} onChange={event=>setFilters({...filters,category:event.target.value||undefined})}/></label>
        </div><p id={`${id}-filter-help`} className="rmd-muted">{t('filterHelp')}</p>
        <button id={`${id}-calculate`} className={`btn${analysis?'':' btn--primary'}`} type="submit" disabled={writesBlocked||busy||!pack.sources?.length}>{busy?t('calculating'):t('calculate')}</button>
      </form>
      {analysis&&<div className="rmd-context"><span>{t('analysisId')}: <bdi>{analysis.id}</bdi></span><span>{t('version')}: <bdi>{analysis.calculation_version}</bdi></span><span>{t('calculatedAt')}: <bdi>{analysis.calculated_at?formatDate(analysis.calculated_at):t('unknown')}</bdi></span></div>}
      <div className="rmd-tabs" role="tablist" aria-label={t('title')}>{views.map(item=><button key={item} id={`${id}-tab-${item}`} role="tab" aria-selected={view===item} aria-controls={`${id}-panel-${item}`} tabIndex={view===item?0:-1} onKeyDown={event=>tabKeys(event,item)} onClick={()=>setView(item)}>{t(item)}</button>)}</div>
      {analysisLoading&&<p role="status">{t('loading')}</p>}
      <div id={`${id}-panel-${view}`} role="tabpanel" aria-labelledby={`${id}-tab-${view}`} tabIndex={0} className="rmd-stack">
        {view==='knowledge'?<KnowledgePanel packId={packId} sources={pack.sources??[]} onInspectSource={setSourceId}/>:!analysis&&!analysisLoading?<section className="rmd-empty"><h3>{t('noAnalysis')}</h3><p>{t('noAnalysisHelp')}</p></section>:analysis&&<>
          <details className="rmd-card"><summary>{t('displayedScope')}</summary><EvidenceDetails value={{filters:analysis.filters,period:analysis.period,coverage:analysis.coverage,source_versions:analysis.source_versions}} empty={t('unknown')}/><p className="rmd-muted">{t('sourceChanged')}</p></details>
          {view==='overview'&&<>
            <div className="rmd-kpis">{analysis.kpis.map(kpi=><article className="rmd-card rmd-kpi" key={kpi.id}><h3 dir="auto">{evidenceText(kpi.title,locale)}</h3><strong className="rmd-number">{typeof kpi.value==='number'?new Intl.NumberFormat(locale==='ar'?'ar-u-nu-latn':'en').format(kpi.value):t('unavailable')}</strong><p dir="auto">{evidenceText(kpi.question,locale)}</p><button className="btn btn--ghost" onClick={()=>setEvidence({title:evidenceText(kpi.title,locale),query:{record_ids:kpi.evidence_record_ids},calculation:kpi})}>{t('evidence')}</button></article>)}</div>
            <p className="rmd-notice">{t('noUniqueIncidents')}</p>
            <h3>{t('priorities')}</h3>{!analysis.priorities.length&&<p>{t('noPriorities')}</p>}
            <div className="rmd-priorities">{analysis.priorities.map((priority,index)=><article className="rmd-card" key={priority.id}><p className="rmd-eyebrow">{index+1}</p><h4 dir="auto">{evidenceText(priority.finding,locale)}</h4><p dir="auto">{evidenceText(priority.management_implication,locale)}</p><details><summary>{t('proposedAction')}</summary><dl className="rmd-details"><div><dt>{t('proposedAction')}</dt><dd dir="auto">{evidenceText(priority.proposed_action,locale)}</dd></div><div><dt>{t('uncertainty')}</dt><dd dir="auto">{evidenceText(priority.uncertainty,locale)}</dd></div><div><dt>{t('suggestedOwner')}</dt><dd dir="auto">{evidenceText(priority.owner_role,locale)}</dd></div><div><dt>{t('dueBasis')}</dt><dd dir="auto">{evidenceText(priority.due_date_basis,locale)} · {priority.due_date??t('noDueDate')}</dd></div><div><dt>{t('closure')}</dt><dd dir="auto">{evidenceText(priority.closure_evidence,locale)}</dd></div></dl></details><div className="rmd-actions"><button className="btn" onClick={()=>setEvidence({title:evidenceText(priority.finding,locale),query:{record_ids:priority.evidence.record_ids}})}>{t('evidence')}</button><button className="btn" onClick={()=>propose(priority.id)} disabled={writesBlocked||busy}>{t('proposeAction')}</button></div></article>)}</div>
            <ActionRegister actions={actions.filter(action=>action.analysis_id===analysis.id)} error={actionsError} loading={actionsLoading} onRetry={refresh}/>
          </>}
          {view==='investigations'&&<Investigations analysis={analysis} onEvidence={setEvidence} onReview={reviewLink} disabled={writesBlocked||busy}/>}
          {view==='quality'&&<Quality analysis={analysis} onEvidence={setEvidence} sources={pack.sources??[]} onInspectSource={setSourceId}/>}
          <section className="rmd-card"><h3>{t('limitations')}</h3>{analysis.limitations.length>0?<ul>{analysis.limitations.map((limitation,index)=><li dir="auto" key={index}>{evidenceText(limitation,locale)}</li>)}</ul>:<p>{t('unknown')}</p>}</section>
        </>}
      </div>
      {analysis&&<footer className="rmd-card"><div className="rmd-actions">{onOpenRun&&<button className="btn btn--primary" disabled={busy||(!analysis.run_id&&writesBlocked)} onClick={reviewReport}>{t('reviewReport')}</button>}<button className="btn" disabled={busy} onClick={()=>exportFile('html')}>{t('exportBrief')}</button><button className="btn" disabled={busy} onClick={()=>exportFile('csv')}>{t('exportActions')}</button>{onExplain&&<button className="btn" onClick={()=>onExplain(packId,analysis.id)}>{t('explain')}</button>}</div><p className="rmd-muted">{t('exportHelp')}</p></footer>}
      <p className="rmd-muted">{t('allReadsPrivate')}</p>
    </div>}
    {sourceId&&<SourceInspector key={sourceId} packId={packId} sourceId={sourceId} readOnly={writesBlocked} onClose={()=>setSourceId(null)} onChanged={refresh}/>}
    {evidence&&analysis&&<RecordsDialog packId={packId} analysisId={analysis.id} selection={evidence} onClose={()=>setEvidence(null)}/>}
  </div>
}

function SourceRegister({sources,onInspect}:{sources:EvidenceSource[];onInspect:(id:string)=>void}){
  const {t}=usePack(messages)
  return sources.length?<div className="rmd-source-list">{sources.map(source=><article key={source.id} className="rmd-source"><div><h4><bdi>{source.name}</bdi></h4><p>{t(source.kind)} · <bdi>{source.sha256?.slice(0,16)}</bdi></p>{source.kind==='procedure'&&<p>{t('documentCode')}: <bdi>{source.document_code??t('unknown')}</bdi> · {t('revision')}: <bdi>{source.document_revision??t('unknown')}</bdi></p>}{source.kind==='procedure'&&<SourceApplicability value={source.applicability}/>}</div><button className="btn" onClick={()=>onInspect(source.id)}>{source.kind==='workbook'?t('mapColumns'):t('inspectSource')}</button></article>)}</div>:<p>{t('noSources')}</p>
}

function ActionRegister({actions,error,loading,onRetry}:{actions:ProposedAction[];error:string|null;loading:boolean;onRetry:()=>void}){
  const {t,locale}=usePack(messages)
  return <section className="rmd-card"><h3>{t('actionRegister')}</h3>{loading&&<p role="status">{t('loading')}</p>}{error&&<div className="rmd-error" role="alert"><p>{error}</p><button className="btn" onClick={onRetry}>{t('retry')}</button></div>}{actions.length?<div className="rmd-table" role="region" aria-label={t('actionRegister')} tabIndex={0}><table><thead><tr><th scope="col">{t('proposedAction')}</th><th scope="col">{t('suggestedOwner')}</th><th scope="col">{t('dueBasis')}</th><th scope="col">{t('reviewState')}</th></tr></thead><tbody>{actions.map(action=><tr key={action.id}><th scope="row" dir="auto">{evidenceText(action.proposed_action??action.title,locale)}</th><td dir="auto">{evidenceText(action.owner_role,locale)||t('unknown')}</td><td dir="auto">{evidenceText(action.due_date_basis,locale)} · {action.due_date??t('noDueDate')}</td><td>{action.state&&action.state in messages.en?t(action.state as RmdMessageKey):action.state??t('proposed')}</td></tr>)}</tbody></table></div>:!loading&&!error&&<p>{t('noActions')}</p>}</section>
}

function Investigations({analysis,onEvidence,onReview,disabled}:{analysis:EvidenceAnalysis;onEvidence:(selection:EvidenceSelection)=>void;onReview:(link:ProposedLink,decision:'confirmed'|'rejected',note:string)=>void;disabled:boolean}){
  const {t,locale,formatNumber}=usePack(messages)
  const reconciliation=analysis.reconciliation
  return <>
    <p className="rmd-notice">{t('noUniqueIncidents')}</p>
    {reconciliation&&<section className="rmd-card"><h3>{t('calculatedMatches')}</h3><p>{t('labelsHelp')}</p><div className="rmd-two-col">{([{title:t('sourceLabels'),rows:reconciliation.source_labels.map(item=>({...item,label:item.label}))},{title:t('calculatedMatches'),rows:reconciliation.calculated_outcomes.map(item=>({...item,label:item.code}))}]).map(group=><div key={group.title}><h4>{group.title}</h4><div className="rmd-table" tabIndex={0} role="region" aria-label={group.title}><table><thead><tr><th scope="col">{t('recorded')}</th><th scope="col">{t('value')}</th><th scope="col">{t('evidence')}</th></tr></thead><tbody>{group.rows.map((row,index)=><tr key={`${row.label}-${index}`}><th scope="row" dir="auto">{row.label||t('unknown')}</th><td>{formatNumber(row.count)}</td><td><button className="btn btn--ghost" onClick={()=>onEvidence({title:`${group.title} · ${row.label}`,query:{record_ids:row.record_ids}})}>{t('evidence')}</button></td></tr>)}</tbody></table></div></div>)}</div><details><summary>{t('comparisonScope')}</summary><EvidenceDetails value={reconciliation.comparison_scope} empty={t('unknown')}/></details></section>}
    {analysis.status_distributions&&<details className="rmd-card"><summary>{t('wo_status')}</summary><EvidenceDetails value={analysis.status_distributions} empty={t('unknown')}/><p>{t('completenessHelp')}</p></details>}
    <div className="rmd-chart-grid">{analysis.charts.map(chart=><EvidenceChartCard key={chart.id} chart={chart} onEvidence={onEvidence}/>)}</div>
    <section className="rmd-card"><h3>{t('conflicts')}</h3>{analysis.conflicts.length?<div className="rmd-source-list">{analysis.conflicts.map(conflict=><article key={conflict.id} className="rmd-source"><div><h4><bdi>{conflict.sr_id??conflict.id}</bdi></h4><p dir="auto">{evidenceText(conflict.interpretation,locale)}</p><p>{t('unresolved')} · <span dir="auto">{conflict.values.map(item=>String(item.value??t('unknown'))).join(' / ')}</span></p></div><button className="btn" onClick={()=>onEvidence({title:t('conflicts'),query:{record_ids:conflict.record_ids},explanation:conflict.interpretation})}>{t('evidence')}</button></article>)}</div>:<p>{t('noConflicts')}</p>}</section>
    <section className="rmd-card"><h3>{t('candidateLinks')}</h3><p>{t('candidateHelp')}</p>{analysis.proposed_links.length?analysis.proposed_links.map(link=><LinkReview key={link.id} link={link} onReview={onReview} disabled={disabled} onEvidence={onEvidence}/>):<p>{t('noCandidates')}</p>}</section>
    <section className="rmd-card"><h3>{t('recurrence')}</h3>{analysis.recurrence?.length?<div className="rmd-source-list">{analysis.recurrence.map(item=><article className="rmd-source" key={item.id}><div><h4 dir="auto">{item.symptom_label} · {item.location}</h4><p><bdi>{formatNumber(item.count)}</bdi> {t('sourceRecords')}</p><p dir="auto">{evidenceText(item.interpretation,locale)}</p></div><button className="btn" onClick={()=>onEvidence({title:t('recurrence'),query:{record_ids:item.record_ids},explanation:item.interpretation})}>{t('evidence')}</button></article>)}</div>:<p>{t('noRecords')}</p>}</section>
    <details className="rmd-card"><summary>{t('records')}</summary><EvidenceDetails value={analysis.relationships} empty={t('unknown')}/></details>
  </>
}

function LinkReview({link,onReview,disabled,onEvidence}:{link:ProposedLink;onReview:(link:ProposedLink,decision:'confirmed'|'rejected',note:string)=>void;disabled:boolean;onEvidence:(selection:EvidenceSelection)=>void}){
  const {t,locale}=usePack(messages),id=useId(),[note,setNote]=useState('')
  const state=link.state in messages.en?t(link.state as RmdMessageKey):link.state
  return <article className="rmd-link"><h4 dir="auto">{evidenceText(link.reason,locale)}</h4><p><bdi>{link.left_record_id}</bdi> ↔ <bdi>{link.right_record_id}</bdi> · {state}</p><p>{link.method in messages.en?t(link.method as RmdMessageKey):link.method}</p><button className="btn" onClick={()=>onEvidence({title:t('candidateLinks'),query:{record_ids:[link.left_record_id,link.right_record_id]},explanation:link.reason})}>{t('evidence')}</button><details><summary>{t('evidence')}</summary><EvidenceDetails value={link.evidence} empty={t('unknown')}/></details>{link.state==='proposed'&&<div className="rmd-stack"><label htmlFor={id}>{t('reviewNote')}<textarea id={id} value={note} onChange={event=>setNote(event.target.value)} disabled={disabled} maxLength={2000}/></label><div className="rmd-actions"><button className="btn" disabled={disabled||!note.trim()} onClick={()=>onReview(link,'confirmed',note.trim())}>{t('confirmLink')}</button><button className="btn" disabled={disabled||!note.trim()} onClick={()=>onReview(link,'rejected',note.trim())}>{t('rejectLink')}</button></div></div>}</article>
}

function Quality({analysis,onEvidence,sources,onInspectSource}:{analysis:EvidenceAnalysis;onEvidence:(selection:EvidenceSelection)=>void;sources:EvidenceSource[];onInspectSource:(id:string)=>void}){
  const {t,locale,formatNumber}=usePack(messages)
  return <>
    {analysis.age_and_due_date_review&&<AgeReview key={analysis.id} review={analysis.age_and_due_date_review} onEvidence={onEvidence}/>}
    <section className="rmd-card"><h3>{t('completeness')}</h3><p>{t('completenessHelp')}</p><div className="rmd-table" role="region" tabIndex={0} aria-label={t('completeness')}><table><thead><tr><th scope="col">{t('grain')}</th><th scope="col">{t('field')}</th>{(['recorded','missing','unknownCount','notApplicableCount','notMeasuredCount','placeholders']as const).map(key=><th key={key} scope="col">{t(key)}</th>)}<th scope="col">{t('evidence')}</th></tr></thead><tbody>{analysis.completeness.map((row,index)=><tr key={`${row.grain}-${row.field}-${index}`}><td>{row.grain in messages.en?t(row.grain as RmdMessageKey):row.grain}</td><th scope="row">{row.field in messages.en?t(row.field as RmdMessageKey):row.field}</th>{[row.recorded,row.missing,row.unknown,row.not_applicable,row.not_measured,row.unresolved_placeholders].map((value,at)=><td key={at}>{typeof value==='number'?formatNumber(value):t('unknown')}</td>)}<td><button className="btn btn--ghost" onClick={()=>onEvidence({title:`${t('completeness')} · ${row.field}`,query:{record_ids:row.record_ids_missing}})}>{t('evidence')}</button></td></tr>)}</tbody></table></div></section>
    <section className="rmd-card"><h3>{t('sourceCoverage')}</h3><p>{t('coverageHelp')}</p><SourceRegister sources={sources} onInspect={onInspectSource}/></section>
    <section><h3>{t('readiness')}</h3><p>{t('readinessHelp')}</p><div className="rmd-two-col">{analysis.readiness.map(measure=><article key={measure.id} className="rmd-card"><p className="rmd-eyebrow">{t('unavailable')}</p><h4 dir="auto">{evidenceText(measure.label,locale)}</h4><p dir="auto">{evidenceText(measure.reason,locale)}</p><h5>{t('missingInputs')}</h5><ul>{measure.missing_inputs.map((item,index)=><li key={index} dir="auto">{evidenceText(item,locale)}</li>)}</ul><details><summary>{t('validationNeeded')}</summary><ul>{measure.needed_validation.map((item,index)=><li key={index} dir="auto">{evidenceText(item,locale)}</li>)}</ul></details></article>)}</div></section>
  </>
}

function AgeReview({review,onEvidence}:{review:NonNullable<EvidenceAnalysis['age_and_due_date_review']>;onEvidence:(selection:EvidenceSelection)=>void}){
  const {t,formatNumber}=usePack(messages),[offset,setOffset]=useState(0)
  const limit=25
  return <section className="rmd-card"><h3>{t('ageReview')}</h3><p>{t('ageHelp')}</p><p className="rmd-muted">{t('asOf')}: <bdi>{review.as_of}</bdi></p><dl className="rmd-details">{(['overdue','not_overdue','unassessable']as const).map(state=><div key={state}><dt>{t(state==='not_overdue'?'notOverdue':state)}</dt><dd><bdi>{formatNumber(review[state])}</bdi><button className="btn btn--ghost" onClick={()=>onEvidence({title:t('ageReview'),query:{record_ids:review.records.filter(row=>state==='unassessable'?row.overdue===null:state==='overdue'?row.overdue===true:row.overdue===false).map(row=>row.record_id)}})}>{t('evidence')}</button></dd></div>)}</dl><details><summary>{t('records')}</summary><div className="rmd-table" role="region" tabIndex={0} aria-label={t('ageReview')}><table><thead><tr><th scope="col">{t('recordId')}</th><th scope="col">{t('ageDays')}</th><th scope="col">{t('due_date')}</th><th scope="col">{t('reviewState')}</th><th scope="col">{t('evidence')}</th></tr></thead><tbody>{review.records.slice(offset,offset+limit).map(row=><tr key={row.record_id}><th scope="row"><bdi>{row.record_id}</bdi></th><td>{row.age_since_event_days===null?t('unknown'):formatNumber(row.age_since_event_days)}</td><td><bdi>{row.due_date??t('noDueDate')}</bdi></td><td>{row.overdue===null?t('unassessable'):row.overdue?t('overdue'):t('notOverdue')}</td><td><button className="btn btn--ghost" onClick={()=>onEvidence({title:t('ageReview'),query:{record_ids:[row.record_id]}})}>{t('evidence')}</button></td></tr>)}</tbody></table></div><div className="rmd-actions"><button className="btn" disabled={!offset} onClick={()=>setOffset(value=>Math.max(0,value-limit))}>{t('previous')}</button><span>{t('pageRange',{from:review.records.length?offset+1:0,to:Math.min(offset+limit,review.records.length),total:review.records.length})}</span><button className="btn" disabled={offset+limit>=review.records.length} onClick={()=>setOffset(value=>value+limit)}>{t('next')}</button></div></details></section>
}

function KnowledgePanel({packId,sources,onInspectSource}:{packId:string;sources:EvidenceSource[];onInspectSource:(id:string)=>void}){
  const {t}=usePack(messages),id=useId()
  const [query,setQuery]=useState(''),[source,setSource]=useState(''),[request,setRequest]=useState<{q:string;source:string;nonce:number}|null>(null)
  const [hits,setHits]=useState<Clause[]>([]),[loading,setLoading]=useState(false),[error,setError]=useState<string|null>(null),[selected,setSelected]=useState<Clause|null>(null)
  useEffect(()=>{
    if(!request)return
    const controller=new AbortController();setLoading(true);setError(null);setHits([])
    rmdApi.knowledge(packId,request.q,request.source,controller.signal).then(result=>{if(!controller.signal.aborted)setHits(result.hits??[])})
      .catch(reason=>{if(!controller.signal.aborted)setError(reason instanceof Error&&reason.message?reason.message:t('failed'))})
      .finally(()=>{if(!controller.signal.aborted)setLoading(false)})
    return()=>controller.abort()
  },[packId,request,t])
  function search(event:FormEvent){event.preventDefault();setRequest(current=>({q:query.trim(),source,nonce:(current?.nonce??0)+1}))}
  return <>
    <section className="rmd-card"><h3>{t('knowledge')}</h3><p className="rmd-notice">{t('authorityBoundary')}</p><SourceRegister sources={sources.filter(item=>item.kind==='procedure')} onInspect={onInspectSource}/></section>
    <section className="rmd-card"><form className="rmd-form-row" onSubmit={search}><label htmlFor={`${id}-query`}>{t('knowledgeSearch')}<input id={`${id}-query`} placeholder={t('searchPlaceholder')} value={query} onChange={event=>setQuery(event.target.value)} maxLength={500}/></label><label htmlFor={`${id}-source`}>{t('source')}<select id={`${id}-source`} value={source} onChange={event=>setSource(event.target.value)}><option value="">{t('allDocuments')}</option>{sources.filter(item=>item.kind==='procedure').map(item=><option key={item.id} value={item.id}>{item.name}</option>)}</select></label><button className="btn btn--primary" type="submit" disabled={loading}>{t('search')}</button></form></section>
    {loading&&<p role="status">{t('loading')}</p>}{error&&<p role="alert" className="rmd-error">{error}</p>}
    {request&&!loading&&!error&&!hits.length&&<p>{t('noClauses')}</p>}
    <div className="rmd-source-list">{hits.map((hit,index)=><article className="rmd-card" key={`${hit.id}-${index}`}><h4 dir="auto">{hit.heading??hit.source_name??hit.document_code??t('clause')}</h4><p dir="auto" className="rmd-excerpt">{hit.text}</p><p className="rmd-source-id"><bdi>{hit.document_code??hit.source_name}</bdi> · <span dir="auto">{typeof hit.locator==='string'?hit.locator:t('locator')}</span></p><button className="btn" onClick={()=>setSelected(hit)}>{t('evidence')}</button></article>)}</div>
    {selected&&<Dialog title={selected.heading??t('clause')} onClose={()=>setSelected(null)} wide initialFocus="panel"><div className="rmd-stack"><p>{t('clauseHelp')}</p><p><strong>{t('source')}:</strong> <bdi>{selected.source_name??selected.document_code??selected.source_id}</bdi> · <strong>{t('revision')}:</strong> <bdi>{selected.document_revision??selected.revision??t('unknown')}</bdi></p><EvidenceDetails value={selected.locator} empty={t('unknown')}/><div className="rmd-clause" lang={selected.language} dir="auto">{selected.text}</div><SourceApplicability value={selected.applicability}/><EvidenceDetails value={selected.applicability} empty={t('unknown')}/><button className="btn" onClick={()=>setSelected(null)}>{t('close')}</button></div></Dialog>}
  </>
}
