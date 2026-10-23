import '../../shared/styles/session.css'
import { useEffect, useRef, useState } from 'react'
import { useI18n } from '../../i18n'
import { Icon } from '../../shared/components/Icon'
import type { AuthConfig } from '../../shared/types'
import { authMessages } from '../../i18n/authMessages'
import { accessToken, CALLBACK_PATH, callbackAllowed, emailLink, exchangeCallback, oauthUrl, providerRequest, settings } from './managedAuth'
import type { ProviderSettings } from './managedAuth'

interface SignInProps {
  config: AuthConfig
  onSignedIn: (token: string) => void | Promise<void>
  accessPending?: boolean
  onSignOut?: () => void
}

/** Passwords go only to the managed provider. Callback codes are S256-bound
 * to a locally initiated attempt; the API still verifies identity and roles. */
export function SignIn({ config, onSignedIn, accessPending = false, onSignOut }: SignInProps) {
  const { t, locale, setLocale } = useI18n()
  const words = authMessages(locale)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const working = useRef(false)
  const callbackStarted = useRef(false)
  const alive = useRef(true)
  const [available, setAvailable] = useState<ProviderSettings | null>(null)
  const [checking, setChecking] = useState(false)
  const [checkFailed, setCheckFailed] = useState(false)
  const [retry, setRetry] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState(false)
  const canUseProvider = config.flows.includes('password')
  const canRedirect = callbackAllowed(config)
  const otherLocale = locale === 'en' ? 'ar' : 'en'

  function failure(caught: unknown) {
    const key = caught instanceof Error ? caught.message : 'provider'
    return key in words ? words[key as keyof typeof words] : key
  }

  async function run(action: () => Promise<void>) {
    if (working.current) return
    working.current = true
    setBusy(true); setError(null); setNotice(false)
    try { await action() }
    catch (caught) { if (alive.current) setError(failure(caught)) }
    finally { working.current = false; if (alive.current) setBusy(false) }
  }

  useEffect(() => {
    alive.current = true
    return () => { alive.current = false }
  }, [])

  useEffect(() => {
    if (!canUseProvider || accessPending) return
    const controller = new AbortController()
    setChecking(true); setCheckFailed(false)
    void settings(config, controller.signal).then((value) => { if (!controller.signal.aborted) setAvailable(value) }).catch(() => {
      if (!controller.signal.aborted) { setAvailable(null); setCheckFailed(true) }
    }).finally(() => { if (!controller.signal.aborted) setChecking(false) })
    return () => controller.abort()
  }, [config, canUseProvider, accessPending, retry])

  useEffect(() => {
    if (window.location.pathname !== CALLBACK_PATH || callbackStarted.current) return
    callbackStarted.current = true
    void run(async () => {
      const token = await exchangeCallback(config)
      if (alive.current) await onSignedIn(token)
    })
    // A callback is consumed once, not on render/translation changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function signInWithPassword(event: React.FormEvent) {
    event.preventDefault()
    void run(async () => {
      const payload = await providerRequest(config, '/token?grant_type=password', { email: email.trim(), password })
      if (alive.current) { setPassword(''); await onSignedIn(accessToken(payload)) }
    })
  }

  function sendLink(createUser: boolean) {
    if (!email.trim()) { setError(t('signin.enterEmail')); return }
    if (!available?.external.email || (createUser && available.disable_signup)) return
    void run(async () => { await emailLink(config, email.trim(), createUser); if (alive.current) setNotice(true) })
  }

  function social(name: 'google' | 'apple') {
    if (available?.external[name] !== true) return
    void run(async () => { const url = await oauthUrl(config, name); if (alive.current) window.location.assign(url) })
  }

  return (
    <main className="signin" aria-label={t('signin.aria')}>
      <div className="signin__card">
        <div className="signin__top">
          <span className="brand__mark signin__mark" aria-hidden="true">A</span>
          <button type="button" className="langbtn" aria-label={t('language.switch')} onClick={() => setLocale(otherLocale)}>
            <Icon name="globe" size={16} /><span lang={otherLocale}>{t('language.other')}</span>
          </button>
        </div>
        <h1 className="signin__title">{accessPending ? words.pendingTitle : t('signin.title')}</h1>
        <p className="signin__desc">{accessPending ? words.pending : t('signin.desc')}</p>
        {accessPending ? <button type="button" className="btn" onClick={onSignOut}>{words.signout}</button> : canUseProvider ? <>
          <form onSubmit={signInWithPassword}>
            <div className="field">
              <label className="field__label" htmlFor="signin-email">{t('signin.email')}</label>
              <input id="signin-email" className="field__input" type="email" dir="ltr" autoComplete="email" value={email}
                onChange={(event) => setEmail(event.target.value)} disabled={busy} required />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="signin-password">{t('signin.password')}</label>
              <input id="signin-password" className="field__input" type="password" dir="ltr" autoComplete="current-password"
                value={password} onChange={(event) => setPassword(event.target.value)} disabled={busy} />
            </div>
            <div className="signin__actions">
              <button type="submit" className="btn btn--primary" disabled={busy || !email.trim()}>
                {busy ? <span className="spinner" aria-hidden="true" /> : null}{t('signin.submit')}
              </button>
              {canRedirect && available?.external.email === true ? <>
                <button type="button" className="btn btn--ghost" disabled={busy || !email.trim()} onClick={() => sendLink(false)}>{words.link}</button>
                {!available.disable_signup ? <button type="button" className="btn btn--ghost" disabled={busy || !email.trim()} onClick={() => sendLink(true)}>{words.signup}</button> : null}
              </> : null}
            </div>
          </form>
          {checking ? <p role="status">{words.loading}</p> : checkFailed ? <p role="status">{words.settingsFailed} <button className="btn btn--ghost" type="button" onClick={() => setRetry((v) => v + 1)} disabled={busy}>{words.retry}</button></p> : null}
          {canRedirect ? <>
            <p className="signin__desc">{words.linkHelp}</p>
            <div className="signin__actions">
              {(['google', 'apple'] as const).filter((name) => available?.external[name] === true).map((name) =>
                <button key={name} type="button" className="btn" disabled={busy} onClick={() => social(name)}>{words[name]}</button>)}
            </div>
            {available && !available.external.google && !available.external.apple ? <p>{words.socialUnavailable}</p> : null}
          </> : <p>{words.activation}</p>}
        </> : <p className="signin__warning" role="status"><Icon name="alert" size={16} />{t('signin.noProvider')}</p>}
        <p className={`statusline ${error ? 'statusline--error' : notice ? 'statusline--success' : ''}`} role="status" aria-live="polite" dir="auto">
          {error ?? (notice ? words.sent : '')}
        </p>
      </div>
    </main>
  )
}
