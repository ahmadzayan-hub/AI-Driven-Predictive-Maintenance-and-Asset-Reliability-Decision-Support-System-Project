import { useState, type ReactNode } from 'react'
import { usePack } from '../../i18n/pack'
import { jarvisMessages } from '../../i18n/jarvis'
import './jarvis.css'

export type CoreState = 'ready' | 'listening' | 'processing' | 'speaking' | 'unavailable' | 'requesting' | 'transcribing' | 'preparing'
/** State animation, never an invented audio waveform or model activity signal. */
export function JarvisCore({ state, children, muted = true, onToggleAudio }: { state: CoreState; children?: ReactNode; muted?: boolean; onToggleAudio?: () => void }) {
  const { t } = usePack(jarvisMessages)
  const [still, setStill] = useState(false)
  const orb = <>
      <svg viewBox="0 0 240 240"><circle className="jarvis-core__gold" cx="120" cy="120" r="108" /><circle cx="120" cy="120" r="88" />
        <circle className="jarvis-core__arc" cx="120" cy="120" r="99" /><circle className="jarvis-core__pulse" cx="120" cy="120" r="69" />
        <path className="jarvis-core__mic" d="M105 101v20a15 15 0 0 0 30 0v-20a15 15 0 0 0-30 0Zm-9 18a24 24 0 0 0 48 0m-24 24v14m-12 0h24" />
        {/* Speaking: the orb takes a human head's outline. A state cue, never a face of anyone. */}
        <path className="jarvis-core__head" d="M100 170v-16c-14-8-22-22-22-40 0-28 20-48 46-48 24 0 42 18 42 42 0 6-1 10-3 14l10 16c2 3 0 5-3 5h-7v12c0 6-4 9-10 9h-12v6m9-66h1" /></svg>
      <span>JARVIS</span>
    </>
  return <section className="jarvis-core" data-state={state} data-still={still} aria-label={t('voiceStage')}>
    <div className="jarvis-core__top"><span>{t('voiceStage')}</span><button type="button" aria-pressed={still} onClick={() => setStill(!still)}>{t('reduceMotion')}</button></div>
    {onToggleAudio ? <><button type="button" className="jarvis-core__orb" aria-label={t(muted ? 'unmute' : 'muted')} aria-pressed={!muted} onClick={onToggleAudio}>{orb}</button><p>{t(muted ? 'unmute' : 'muted')}</p></>
      : <div className="jarvis-core__orb" aria-hidden="true">{orb}</div>}
    <p className="jarvis-core__state" aria-live="polite">{t(state)}</p>
    <p className="jarvis-core__caption">{t('stateAnimation')}</p>
    <div className="jarvis-core__controls">{children}</div>
  </section>
}
