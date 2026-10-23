import { useEffect, useId, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { usePack } from '../../i18n/pack'
import type { Locale } from '../../i18n'
import { useStore } from '../../app/store'
import { useReadOnly } from '../../shared/readOnly'
import { rmdApi } from './api'
import { EvidenceDetails, evidenceText } from './display'
import { messages } from './messages'
import { SourceInspector } from './SourcePanel'
import type { EvidenceText } from './types'
import './rmd.css'

interface Citation { source_id: string; clause_id?: string; source_name?: string; locator: unknown; revision?: string | number; sha256?: string }
interface Answer { text: string; source: 'deterministic' | 'model'; provider?: string; citations: Citation[]; limitations?: EvidenceText[] }
export interface RmdAssistantPanelProps { packId: string; analysisId?: string; onDismiss?: () => void }

export function RmdAssistantPanel({packId,analysisId,onDismiss}:RmdAssistantPanelProps) {
  const {t,locale,dir}=usePack(messages),{identity}=useStore(),readOnly=useReadOnly(),id=useId()
  const pending=useRef<AbortController|null>(null)
  const previousScope=useRef('')
  const [question,setQuestion]=useState(''),[answer,setAnswer]=useState<(Answer&{locale:Locale})|null>(null)
  const [busy,setBusy]=useState(false),[error,setError]=useState<string|null>(null),[source,setSource]=useState<string|null>(null)
  const [access,setAccess]=useState<'checking'|'allowed'|'denied'>('checking'),[attempt,setAttempt]=useState(0)
  const scope=`${identity?.principal.subject??'local'}:${packId}:${analysisId??''}`
  useEffect(()=>{
    const controller=new AbortController()
    pending.current?.abort();pending.current=null;setAnswer(null);setError(null);setBusy(false);setSource(null);setAccess('checking')
    if(previousScope.current!==scope){previousScope.current=scope;setQuestion('')}
    rmdApi.pack(packId,controller.signal).then(()=>{if(!controller.signal.aborted)setAccess('allowed')})
      .catch(reason=>{if(!controller.signal.aborted){setAccess('denied');setError(reason instanceof Error&&reason.message?reason.message:t('failed'))}})
    const recheck=()=>setAttempt(value=>value+1)
    window.addEventListener('focus',recheck)
    return()=>{controller.abort();pending.current?.abort();pending.current=null;window.removeEventListener('focus',recheck)}
  },[packId,scope,attempt,t])
  async function submit(event:FormEvent){
    event.preventDefault()
    if(!question.trim()||busy||access!=='allowed')return
    pending.current?.abort()
    const controller=new AbortController();pending.current=controller
    const answerLocale=locale
    setBusy(true);setError(null);setAnswer(null)
    try {
      const result=await rmdApi.assistant<Answer>(packId,question.trim(),analysisId,controller.signal)
      if(!controller.signal.aborted&&pending.current===controller)setAnswer({...result,citations:result.citations??[],locale:answerLocale})
    } catch(reason){if(!controller.signal.aborted&&pending.current===controller)setError(reason instanceof Error&&reason.message?reason.message:t('failed'))}
    finally{if(pending.current===controller){setBusy(false);pending.current=null}}
  }
  function cancel(){pending.current?.abort();pending.current=null;setBusy(false)}
  return <section className="rmd rmd-assistant rmd-card rmd-stack" aria-labelledby={`${id}-title`} dir={dir}>
    <header><h3 id={`${id}-title`}>{t('assistantTitle')}</h3><p className="rmd-muted">{t('assistantHelp')}</p><p className="rmd-source-id">{t('pack')}: <bdi>{packId}</bdi>{analysisId&&<> · {t('analysisId')}: <bdi>{analysisId}</bdi></>}</p></header>
    <form className="rmd-stack" onSubmit={submit} aria-busy={busy}>
      <label htmlFor={`${id}-question`}>{t('assistantQuestion')}<textarea id={`${id}-question`} value={question} onChange={event=>setQuestion(event.target.value)} placeholder={t('assistantPlaceholder')} maxLength={2000} required disabled={busy}/></label>
      <div className="rmd-actions"><button className="btn btn--primary" type="submit" disabled={busy||!question.trim()||access!=='allowed'}>{t('assistantAsk')}</button>{busy&&<button className="btn" type="button" onClick={cancel}>{t('assistantCancel')}</button>}{onDismiss&&<button className="btn" type="button" onClick={onDismiss}>{t('assistantDismiss')}</button>}</div>
    </form>
    {(busy||access==='checking')&&<p role="status">{t('assistantWaiting')}</p>}{error&&<div role="alert" className="rmd-error"><p>{error}</p>{access==='denied'&&<button className="btn" onClick={()=>setAttempt(value=>value+1)}>{t('retry')}</button>}</div>}
    {answer&&access==='allowed'&&<article className="rmd-stack"><p className="rmd-eyebrow">{answer.source==='model'?t('assistantModel'):t('assistantRules')}{answer.provider&&<> · <bdi>{answer.provider}</bdi></>}</p><div className="rmd-assistant__answer" lang={answer.locale} dir={answer.locale==='ar'?'rtl':'ltr'}>{answer.text}</div>
      {answer.citations.length>0&&<section><h4>{t('assistantCitations')}</h4><ul className="rmd-list">{answer.citations.map((citation,index)=><li key={`${citation.source_id}-${citation.clause_id??index}`}><button className="btn btn--ghost" onClick={()=>setSource(citation.source_id)}><bdi>{citation.source_name??citation.source_id}</bdi></button><EvidenceDetails value={citation.locator} empty={t('unknown')}/>{citation.revision&&<p>{t('revision')}: <bdi>{citation.revision}</bdi></p>}{citation.sha256&&<p className="rmd-source-id"><bdi>{citation.sha256}</bdi></p>}</li>)}</ul></section>}
      {!!answer.limitations?.length&&<section><h4>{t('limitations')}</h4><ul>{answer.limitations.map((item,index)=><li key={index} dir="auto">{evidenceText(item,locale)}</li>)}</ul></section>}
    </article>}
    {source&&<SourceInspector packId={packId} sourceId={source} readOnly={readOnly} onClose={()=>setSource(null)} onChanged={()=>undefined}/>}
  </section>
}
export default RmdAssistantPanel
