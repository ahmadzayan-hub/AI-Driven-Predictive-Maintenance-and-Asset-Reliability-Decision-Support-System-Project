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
        {/* Speaking: an abstract waveform replaces the microphone. A state cue, never a face or an audio level. */}
        <path className="jarvis-core__wave" d="M78 120h10l6-14 8 30 8-44 8 56 8-40 8 26 8-18 6 4h12" /></svg>
      <span>MIYAAR</span>
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
