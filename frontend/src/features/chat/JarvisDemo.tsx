import { useState } from 'react'
import { api } from '../../shared/api'
import type { SessionState } from '../../shared/types'
import { applyLocale } from '../../i18n'
import { usePack } from '../../i18n/pack'
import { jarvisMessages } from '../../i18n/jarvis'
import { JarvisWorkspace } from './JarvisWorkspace'

export default function JarvisDemo() {
  const { t, locale } = usePack(jarvisMessages)
  const [session, setSession] = useState<SessionState | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(false)
  async function open() {
    if (busy) return
    setBusy(true); setError(false)
    try {
      // Only the isolated synthetic launcher exposes this marker. A production
      // server cannot be silently labelled as a synthetic demonstration.
      const marker = await fetch('/api/jarvis-demo', { cache: 'no-store' })
      if (!marker.ok || (await marker.json()).synthetic !== true) throw new Error('Not a demo server')
      setSession(await api.createSession(locale))
    } catch { setError(true) }
    finally { setBusy(false) }
  }
  return <main className="jarvis-demo"><header><strong>{t('demo')}</strong>
    <button className="btn btn--ghost" disabled={busy} onClick={() => { setSession(null); applyLocale(locale === 'en' ? 'ar' : 'en') }}>{locale === 'en' ? 'العربية' : 'English'}</button></header>
    {session ? <JarvisWorkspace session={session} /> : <section className="jarvis"><h1>{t('title')}</h1><p>{t('boundary')}</p>
      <button className="btn btn--primary" disabled={busy} onClick={() => void open()}>{t('boot')}</button>{error && <p role="alert">{t('bootError')}</p>}</section>}
  </main>
}
