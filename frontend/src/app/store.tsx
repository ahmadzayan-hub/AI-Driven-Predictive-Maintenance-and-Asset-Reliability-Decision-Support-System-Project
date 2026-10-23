import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import {
  applyLocale,
  currentLocale,
  localeFromPreference,
  preferenceFor,
  storedLocale,
  translate,
  translatePlural,
} from '../i18n'
import type { Locale, MessageKey, Vars } from '../i18n'
import { api, ApiError, AUTH_EXPIRED_EVENT, hasToken, storeToken } from '../shared/api'
import type {
  ActivityEvent,
  ActivityKind,
  AuthConfig,
  ConnectionStatus,
  IdentityInfo,
  SessionState,
} from '../shared/types'

export interface OperationOutcome {
  ok: boolean
  message: string
}

interface Store {
  authConfig: AuthConfig | null
  /** The public view-only demo: no sign-in, no chat, nothing writable. */
  demo: boolean
  needsSignIn: boolean
  identity: IdentityInfo | null
  signIn: (token: string) => Promise<void>
  signOut: () => void
  session: SessionState | null
  bootError: string | null
  status: ConnectionStatus
  sending: boolean
  failedText: string | null
  pendingText: string | null
  requestError: string | null
  events: ActivityEvent[]
  lastSyncedAt: string | null
  /** A run the assistant just started from the chat; the shell opens it. */
  openRun: { id: string; nonce: number } | null
  start: () => Promise<void>
  send: (text: string) => Promise<boolean>
  retryFailed: () => Promise<void>
  dismissFailed: () => void
  clearHistory: () => Promise<OperationOutcome>
  setPreference: (key: string, value: string) => Promise<OperationOutcome>
  /** Interface language and the agent's reply language, changed together. */
  setLanguage: (locale: Locale) => Promise<OperationOutcome>
  addMemory: (information: string, category?: string) => Promise<OperationOutcome>
  updateMemory: (key: string, information: string, category?: string) => Promise<OperationOutcome>
  deleteMemory: (key: string) => Promise<OperationOutcome>
  clearMemory: () => Promise<OperationOutcome>
  exportData: () => Promise<OperationOutcome>
  endSession: () => Promise<OperationOutcome>
}

const StoreContext = createContext<Store | null>(null)

const SESSION_KEY = 'aos-session'

function readStoredSessionId(): string | null {
  try {
    return localStorage.getItem(SESSION_KEY)
  } catch {
    return null
  }
}

function storeSessionId(id: string) {
  try {
    localStorage.setItem(SESSION_KEY, id)
  } catch {
    /* private mode — the session simply won't survive a refresh */
  }
}

export function useStore(): Store {
  const store = useContext(StoreContext)
  if (!store) throw new Error('useStore must be used inside <StoreProvider>')
  return store
}

let eventId = 0

export function StoreProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<SessionState | null>(null)
  const [bootError, setBootError] = useState<string | null>(null)
  const [events, setEvents] = useState<ActivityEvent[]>([])
  const [sending, setSending] = useState(false)
  const [failedText, setFailedText] = useState<string | null>(null)
  const [pendingText, setPendingText] = useState<string | null>(null)
  const [requestError, setRequestError] = useState<string | null>(null)
  const sessionGeneration = useRef(0)
  const sendInFlight = useRef(false)
  const [offline, setOffline] = useState(!navigator.onLine)
  const [lastError, setLastError] = useState(false)
  const [lastSyncedAt, setLastSyncedAt] = useState<string | null>(null)
  const [authConfig, setAuthConfig] = useState<AuthConfig | null>(null)
  const [identity, setIdentity] = useState<IdentityInfo | null>(null)
  const [needsSignIn, setNeedsSignIn] = useState(false)
  const [demo, setDemo] = useState(false)
  const demoRef = useRef(false)
  const pendingCount = useRef(0)
  const [pending, setPending] = useState(0)
  const [openRun, setOpenRun] = useState<{ id: string; nonce: number } | null>(null)

  const pushEvent = useCallback(
    (code: MessageKey, kind: ActivityKind, detail?: string, vars?: Vars) => {
      eventId += 1
      const event: ActivityEvent = {
        id: eventId,
        code,
        vars,
        kind,
        detail,
        time: new Date().toISOString(),
      }
      setEvents((current) => [event, ...current].slice(0, 100))
    },
    [],
  )

  const beginWork = useCallback(() => {
    pendingCount.current += 1
    setPending(pendingCount.current)
  }, [])

  const endWork = useCallback(() => {
    pendingCount.current = Math.max(0, pendingCount.current - 1)
    setPending(pendingCount.current)
  }, [])

  useEffect(() => {
    function goOnline() {
      setOffline(false)
      pushEvent('event.connection.restored', 'success')
    }
    function goOffline() {
      setOffline(true)
      pushEvent('event.connection.lost', 'error')
    }
    window.addEventListener('online', goOnline)
    window.addEventListener('offline', goOffline)
    return () => {
      window.removeEventListener('online', goOnline)
      window.removeEventListener('offline', goOffline)
    }
  }, [pushEvent])

  // A 401 anywhere means the token is missing, expired, or revoked:
  // drop it and return the user to the sign-in screen.
  const handleUnauthorized = useCallback(() => {
    sessionGeneration.current += 1
    sendInFlight.current = false
    setSending(false)
    setPendingText(null)
    setFailedText(null)
    setRequestError(null)
    storeToken(null)
    setIdentity(null)
    setSession(null)
    setNeedsSignIn(true)
  }, [])

  useEffect(() => {
    window.addEventListener(AUTH_EXPIRED_EVENT, handleUnauthorized)
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, handleUnauthorized)
  }, [handleUnauthorized])

  const start = useCallback(async () => {
    // A session is a write; the view-only demo never asks for one.
    if (demoRef.current) return
    const generation = ++sessionGeneration.current
    sendInFlight.current = false
    setSending(false)
    setPendingText(null)
    setRequestError(null)
    beginWork()
    setBootError(null)
    try {
      // The agent phrases its own replies from the session's language
      // preference; seeding it from the interface language means the
      // welcome message is already in the right language.
      const state = await api.createSession(preferenceFor(currentLocale()))
      if (generation !== sessionGeneration.current) return
      setSession(state)
      storeSessionId(state.session_id)
      setFailedText(null)
      setLastError(false)
      setOffline(false)
      setLastSyncedAt(new Date().toISOString())
      pushEvent('event.session.started', 'success', translate('assistant.name'))
    } catch (error) {
      if (generation !== sessionGeneration.current) return
      if (error instanceof ApiError && error.status === 401) {
        handleUnauthorized()
        return
      }
      const message = error instanceof ApiError ? error.message : translate('outcome.startFailed')
      setBootError(message)
      pushEvent('event.session.startFailed', 'error', message)
    } finally {
      endWork()
    }
  }, [beginWork, endWork, pushEvent, handleUnauthorized])

  /** A restored session may have been created in another language, or
   *  on another device. The browser's explicit choice wins and the agent
   *  is told; with no explicit choice, the session's language is applied
   *  to the interface without being recorded as a choice. */
  const reconcileLanguage = useCallback((state: SessionState) => {
    const chosen = storedLocale()
    const sessionLocale = localeFromPreference(state.preferences.language)
    if (chosen === null) {
      if (sessionLocale !== currentLocale()) applyLocale(sessionLocale, false)
      return
    }
    if (chosen !== sessionLocale && !state.ended) {
      api
        .setPreference(state.session_id, 'language', preferenceFor(chosen))
        .then((result) => setSession(result.state))
        .catch(() => {
          /* the next preference change carries the language with it */
        })
    }
  }, [])

  // On page load, restore the previous session when the server still has
  // it and it hasn't ended; otherwise fall back to a fresh session.
  const bootstrap = useCallback(async () => {
    // Ask the server whether this deployment requires an account before
    // touching any protected endpoint.
    try {
      const config = await api.authConfig()
      setAuthConfig(config)
      if (config.mode === 'demo') {
        // Everyone is the same read-only visitor, so there is nothing to sign
        // in to and no session to open: a closed local one stands in for it.
        demoRef.current = true
        setDemo(true)
        try { setIdentity(await api.identity()) } catch { /* the views still read */ }
        setSession({ session_id: 'demo', agent_name: '', version: '', welcome: '', ended: true,
          created_at: '', transcript: [], preferences: {}, memory: {}, memory_entries: [],
          history: [], memory_persisted: false, commands: [] })
        setOffline(false)
        return
      }
      if (config.mode === 'jwt') {
        if (window.location.pathname === '/auth/callback' || !hasToken()) {
          setNeedsSignIn(true)
          return
        }
        try {
          const verified = await api.identity()
          if (verified.mode !== 'jwt' || verified.principal.provider !== 'jwt') throw new Error(translate('signin.failed'))
          setIdentity(verified)
          if (!verified.principal.permissions.includes('write')) return
        } catch (error) {
          if (error instanceof ApiError && error.status === 401) {
            handleUnauthorized()
            return
          }
          setBootError(error instanceof Error ? error.message : translate('signin.failed'))
          return
        }
      }
    } catch {
      // An unreachable config endpoint is handled by the session boot
      // below, which surfaces a retryable error state.
    }

    const storedId = readStoredSessionId()
    if (storedId) {
      beginWork()
      try {
        const state = await api.getSession(storedId)
        if (!state.ended) {
          setSession(state)
          setOffline(false)
          setLastSyncedAt(new Date().toISOString())
          pushEvent(
            'event.session.restored',
            'success',
            translatePlural('session.restoredMessages', state.transcript.length),
          )
          reconcileLanguage(state)
          return
        }
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          handleUnauthorized()
          return
        }
        // Offline or server error: surface it instead of silently
        // replacing the session. A 404 just means the session expired.
        if (error instanceof ApiError && (error.status === 0 || error.status >= 500)) {
          setBootError(error.message)
          pushEvent('event.session.restoreFailed', 'error', error.message)
          return
        }
      } finally {
        endWork()
      }
    }
    await start()
  }, [beginWork, endWork, pushEvent, start, handleUnauthorized, reconcileLanguage])

  const signIn = useCallback(
    async (token: string) => {
      const generation = ++sessionGeneration.current
      storeToken(token)
      setBootError(null)
      let verified: IdentityInfo
      try {
        verified = await api.identity()
        if (verified.mode !== "jwt" || verified.principal.provider !== "jwt") throw new Error(translate("signin.failed"))
      } catch (error) {
        if (generation === sessionGeneration.current) handleUnauthorized()
        throw error
      }
      if (generation !== sessionGeneration.current) throw new Error(translate('signin.failed'))
      setIdentity(verified)
      setSession(null)
      try { localStorage.removeItem(SESSION_KEY) } catch { /* storage is optional */ }
      setNeedsSignIn(false)
      if (verified.principal.permissions.includes('write')) await start()
    },
    [handleUnauthorized, start],
  )

  const signOut = useCallback(() => {
    try {
      localStorage.removeItem('aos-session')
    } catch {
      /* nothing stored */
    }
    handleUnauthorized()
    pushEvent('event.signedOut', 'info')
  }, [handleUnauthorized, pushEvent])

  const startedOnce = useRef(false)
  useEffect(() => {
    // Guard against React StrictMode double-invoking the mount effect in
    // development, which would otherwise open two sessions.
    if (startedOnce.current) return
    startedOnce.current = true
    void bootstrap()
    // bootstrap() is stable; run once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const send = useCallback(
    async (text: string) => {
      if (!session || session.ended || sendInFlight.current) return false
      const generation = sessionGeneration.current
      sendInFlight.current = true
      setPendingText(text)
      setRequestError(null)
      setSending(true)
      setFailedText(null)
      beginWork()
      try {
        const result = await api.sendMessage(session.session_id, text)
        if (generation !== sessionGeneration.current) return false
        if (!result?.reply?.text?.trim() || result.state?.session_id !== session.session_id) throw new Error('Invalid conversation response')
        setSession(result.state)
        setLastError(false)
        // Any confirmed server response proves connectivity — never stay
        // stuck in offline mode after a successful request.
        setOffline(false)
        setLastSyncedAt(new Date().toISOString())
        pushEvent(
          'event.request.completed',
          'info',
          text.length > 60 ? `${text.slice(0, 60)}…` : text,
        )
        if (result.state.ended) pushEvent('event.session.ended', 'info')
        const runId = result.reply.result?.run_id
        const startedRun = result.reply.action === 'start_run' || result.reply.action === 'runtime'
        if (startedRun && typeof runId === 'string') {
          setOpenRun({ id: runId, nonce: Date.now() })
        }
        return true
      } catch (error) {
        if (generation !== sessionGeneration.current) return false
        if (error instanceof ApiError && error.status === 401) { handleUnauthorized(); return false }
        const message = error instanceof ApiError ? error.message : translate('outcome.requestFailed')
        setRequestError(message)
        setFailedText(text)
        setLastError(true)
        if (error instanceof ApiError && error.offline) setOffline(true)
        pushEvent('event.request.failed', 'error', message)
        return false
      } finally {
        if (generation === sessionGeneration.current) {
          sendInFlight.current = false
          setPendingText(null)
          setSending(false)
        }
        endWork()
      }
    },
    [session, beginWork, endWork, pushEvent, handleUnauthorized],
  )

  const retryFailed = useCallback(async () => {
    const text = failedText
    if (!text) return
    setFailedText(null)
    await send(text)
  }, [failedText, send])

  const dismissFailed = useCallback(() => { setFailedText(null); setRequestError(null) }, [])

  const runOperation = useCallback(
    async (
      operation: (sessionId: string) => Promise<{ reply_text: string; state: SessionState }>,
      code: MessageKey,
    ): Promise<OperationOutcome> => {
      if (!session) return { ok: false, message: translate('outcome.noSession') }
      const generation = sessionGeneration.current
      beginWork()
      try {
        const result = await operation(session.session_id)
        if (generation !== sessionGeneration.current) return { ok: false, message: '' }
        setSession(result.state)
        setLastError(false)
        setOffline(false)
        setLastSyncedAt(new Date().toISOString())
        pushEvent(code, 'success', result.reply_text)
        return { ok: true, message: result.reply_text }
      } catch (error) {
        const message = error instanceof ApiError ? error.message : translate('outcome.requestFailed')
        if (error instanceof ApiError && error.offline) setOffline(true)
        setLastError(true)
        pushEvent(`${code}.failed` as MessageKey, 'error', message)
        return { ok: false, message }
      } finally {
        endWork()
      }
    },
    [session, beginWork, endWork, pushEvent],
  )

  const clearHistory = useCallback(
    () => runOperation((id) => api.clearHistory(id), 'event.history.cleared'),
    [runOperation],
  )
  const setPreference = useCallback(
    (key: string, value: string) =>
      runOperation((id) => api.setPreference(id, key, value), 'event.preference.changed'),
    [runOperation],
  )
  const setLanguage = useCallback(
    async (locale: Locale): Promise<OperationOutcome> => {
      // The interface switches at once; the agent is told so its next
      // reply matches. With no live session there is nothing to tell.
      applyLocale(locale)
      if (!session || session.ended) return { ok: true, message: '' }
      return runOperation(
        (id) => api.setPreference(id, 'language', preferenceFor(locale)),
        'event.preference.changed',
      )
    },
    [session, runOperation],
  )
  const addMemory = useCallback(
    (information: string, category?: string) =>
      runOperation((id) => api.addMemory(id, information, category), 'event.memory.saved'),
    [runOperation],
  )
  const updateMemory = useCallback(
    (key: string, information: string, category?: string) =>
      runOperation(
        (id) => api.updateMemory(id, key, information, category),
        'event.memory.updated',
      ),
    [runOperation],
  )
  const deleteMemory = useCallback(
    (key: string) => runOperation((id) => api.deleteMemory(id, key), 'event.memory.removed'),
    [runOperation],
  )
  const clearMemory = useCallback(
    () => runOperation((id) => api.clearMemory(id), 'event.memory.cleared'),
    [runOperation],
  )

  const exportData = useCallback(async (): Promise<OperationOutcome> => {
    if (!session) return { ok: false, message: translate('outcome.noSession') }
    beginWork()
    try {
      const payload = await api.exportData(session.session_id)
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'agentic-os-export.json'
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
      setLastSyncedAt(new Date().toISOString())
      pushEvent('event.export.done', 'success', 'agentic-os-export.json')
      return { ok: true, message: translate('outcome.exported') }
    } catch (error) {
      const message = error instanceof ApiError ? error.message : translate('outcome.exportFailed')
      pushEvent('event.export.failed', 'error', message)
      return { ok: false, message }
    } finally {
      endWork()
    }
  }, [session, beginWork, endWork, pushEvent])

  const endSession = useCallback(async (): Promise<OperationOutcome> => {
    if (!session) return { ok: false, message: translate('outcome.noSession') }
    const generation = sessionGeneration.current
    beginWork()
    try {
      const state = await api.endSession(session.session_id)
      if (generation !== sessionGeneration.current) return { ok: false, message: '' }
      sessionGeneration.current += 1
      sendInFlight.current = false
      setSending(false)
      setPendingText(null)
      setFailedText(null)
      setRequestError(null)
      setSession(state)
      pushEvent('event.session.ended', 'info')
      return { ok: true, message: translate('outcome.sessionEnded') }
    } catch (error) {
      const message = error instanceof ApiError ? error.message : translate('outcome.requestFailed')
      pushEvent('event.session.endFailed', 'error', message)
      return { ok: false, message }
    } finally {
      endWork()
    }
  }, [session, beginWork, endWork, pushEvent])

  const status: ConnectionStatus = offline
    ? 'offline'
    : session?.ended && !demo
      ? 'ended'
      : pending > 0
        ? 'working'
        : lastError
          ? 'error'
          : 'ready'

  const value = useMemo<Store>(
    () => ({
      authConfig,
      demo,
      needsSignIn,
      identity,
      signIn,
      signOut,
      session,
      bootError,
      status,
      sending,
      failedText,
      pendingText,
      requestError,
      events,
      lastSyncedAt,
      openRun,
      start,
      send,
      retryFailed,
      dismissFailed,
      clearHistory,
      setPreference,
      setLanguage,
      addMemory,
      updateMemory,
      deleteMemory,
      clearMemory,
      exportData,
      endSession,
    }),
    [
      authConfig,
      demo,
      needsSignIn,
      identity,
      signIn,
      signOut,
      session,
      bootError,
      status,
      sending,
      failedText,
      pendingText,
      requestError,
      events,
      lastSyncedAt,
      openRun,
      start,
      send,
      retryFailed,
      dismissFailed,
      clearHistory,
      setPreference,
      setLanguage,
      addMemory,
      updateMemory,
      deleteMemory,
      clearMemory,
      exportData,
      endSession,
    ],
  )

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>
}

