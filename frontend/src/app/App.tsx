import { ReadOnlyContext } from '../shared/readOnly'
import { Activity, Suspense, useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { MiyaarMark } from '../shared/components/MiyaarMark'
import { ChatView } from '../features/chat/ChatView'
import type { ComposerHandle } from '../features/chat/Composer'
import type { RunPreset } from '../features/runs/RunsView'
import { useI18n } from '../i18n'
import type { MessageKey } from '../i18n'
import { ConfirmDialog } from '../shared/components/ConfirmDialog'
import { Icon } from '../shared/components/Icon'
import type { IconName } from '../shared/components/Icon'
import { StatusBadge } from '../shared/components/StatusBadge'
import { languageLabel, toneLabel } from '../shared/labels'
import type { CommandInfo } from '../shared/types'
import {
  ActivityView,
  AssetIntelligenceView,
  ApprovalsView,
  CommandPalette,
  DatasetsView,
  HelpDialog,
  MemoryView,
  Onboarding,
  OperationsView,
  RmdView,
  RmdAssistantPanel,
  OverviewView,
  PreferencesView,
  prefetchWhenIdle,
  RunsView,
  DashboardView,
  SignIn,
  ViewBoundary,
  ViewLoading,
} from './lazyViews'
import { useStore } from './store'
import { useTheme } from './useTheme'

import { runStore } from '../features/runs/runStore'
import { useHashRoute } from './routing'
import type { Route, Tab } from './routing'

// The command shortcut as this platform writes it (assessment U17): the
// Command key on Apple hardware, Control elsewhere.
const MODIFIER_KEY = typeof navigator !== 'undefined' && /Mac|iPhone|iPad|iPod/.test(navigator.platform) ? '⌘' : 'Ctrl'

interface NavItem {
  id: Tab
  label: MessageKey
  icon: IconName
}

// Three primary work areas retain every existing route under native disclosures.
// The assistant and workspace tools remain available without replacing views.
const NAV_GROUPS: Array<{ id: string; label: MessageKey; items: NavItem[] }> = [
  {
    id: 'decide', label: 'nav.decision',
    items: [
      { id: 'overview', label: 'nav.overview', icon: 'dashboard' },
      { id: 'assets', label: 'nav.assets', icon: 'activity' },
      { id: 'rmd', label: 'nav.rmd', icon: 'search' },
    ],
  },
  {
    id: 'prepare', label: 'nav.dataAnalysis',
    items: [
      { id: 'datasets', label: 'nav.datasets', icon: 'database' },
      { id: 'runs', label: 'nav.runs', icon: 'sparkle' },
    ],
  },
  { id: 'report', label: 'nav.reportsOutputs', items: [
    { id: 'dashboard', label: 'nav.dashboard', icon: 'chart' },
    { id: 'approvals', label: 'nav.approvals', icon: 'shield' },
  ] },
  {
    id: 'assist', label: 'nav.tools',
    items: [
      { id: 'operations', label: 'nav.operations', icon: 'check' },
      { id: 'chat', label: 'nav.workspace', icon: 'chat' },
      { id: 'memory', label: 'nav.memory', icon: 'memory' },
      { id: 'activity', label: 'nav.activity', icon: 'clock' },
      { id: 'preferences', label: 'nav.preferences', icon: 'settings' },
    ],
  },
]

// Views the view-only demo leaves out: those that live on a chat session,
// which the demo does not have, and Administration.
const NEEDS_SESSION: ReadonlySet<Tab> = new Set<Tab>(['chat', 'memory', 'preferences', 'operations', 'rmd'])
const DEMO_GROUPS = NAV_GROUPS.map((group) => ({ ...group, items: group.items.filter((item) => !NEEDS_SESSION.has(item.id)) }))

// The phone bar opens the three work areas; More exposes every preserved route.
const BAR_ITEMS = NAV_GROUPS.slice(0, 3).map((group) => ({ ...group.items[0], short: group.label }))

const ONBOARDING_KEY = 'aos-onboarded'

export function App() {
  const store = useStore()
  const { t, locale } = useI18n()
  const { isDark, toggleTheme } = useTheme()
  // The session opens on the Command Centre: a returning manager lands on
  // the decision, and a newcomer sees the onboarding dialog first and then
  // the same view. The assistant is one tap away. An explicit address
  // still opens the view it names.
  const [route, navigate] = useHashRoute()
  const tab = route.tab
  const [visited, setVisited] = useState<Tab[]>(['overview'])
  useEffect(() => { setVisited((previous) => previous.includes(tab) ? previous : [...previous, tab]) }, [tab])
  // Which run the Runs view opens, and what its form starts with. Only one
  // of the two is set at a time, so the view never has to choose.
  const [runTarget, setRunTarget] = useState<{ id: string; nonce: number } | null>(null)
  const [runPreset, setRunPreset] = useState<RunPreset | null>(null)
  const runNonce = useRef(0)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [helpOpen, setHelpOpen] = useState(false)
  const [confirming, setConfirming] = useState<'history' | 'end' | null>(null)
  const [confirmBusy, setConfirmBusy] = useState(false)
  const [showOnboarding, setShowOnboarding] = useState(() => {
    try {
      return localStorage.getItem(ONBOARDING_KEY) !== '1'
    } catch {
      return false
    }
  })
  const composerRef = useRef<ComposerHandle | null>(null)
  const [pendingCommand, setPendingCommand] = useState<string | null>(null)
  const [evidenceContext, setEvidenceContext] = useState<{ packId: string; analysisId: string } | null>(null)
  const currentRunId = tab === 'runs' ? route.runId ?? null : runTarget?.id ?? null
  // The dashboard keeps its address while another view is open, so going
  // back to it returns to the same page and filters (ADR 0032).
  const lastDashboard = useRef<Route>({ tab: 'dashboard' })
  if (tab === 'dashboard') lastDashboard.current = route
  const dashboardRoute = lastDashboard.current

  useLayoutEffect(() => {
    runStore.reset()
    setEvidenceContext(null)
  }, [store.session?.session_id, store.identity?.principal.subject, store.identity?.principal.role])

  const demo = store.demo
  // The demo opens on the Overview and never shows a view that needs a session.
  useEffect(() => { if (demo && NEEDS_SESSION.has(tab)) navigate({ tab: 'overview' }) }, [demo, tab, navigate])

  useEffect(() => {
    if (tab === 'chat' && pendingCommand) { composerRef.current?.insert(pendingCommand); setPendingCommand(null) }
  }, [tab, pendingCommand])

  useEffect(() => {
    if (tab === 'runs' && route.runId) setRunTarget((previous) => previous?.id === route.runId ? previous : { id: route.runId!, nonce: ++runNonce.current })
  }, [tab, route.runId])

  const selectRun = useCallback((id: string | null) => {
    setRunTarget(id ? { id, nonce: ++runNonce.current } : null)
    if (tab === 'runs') navigate({ tab: 'runs', runId: id ?? undefined })
  }, [tab, navigate])

  // "Analyse the sales data" in the chat starts a run; the person
  // should see it, not be told to go and find it.
  useEffect(() => {
    if (!store.openRun) return
    setRunPreset(null)
    setRunTarget(store.openRun)
    navigate({ tab: 'runs', runId: store.openRun.id })
  }, [store.openRun, navigate])

  /** Move to a view from the navigation: a plain visit, with no preset. */
  function go(next: Tab) {
    setRunPreset(null)
    if (next === 'dashboard') navigate(lastDashboard.current)
    else navigate({ tab: next, runId: next === 'runs' ? runTarget?.id : undefined })
    setDrawerOpen(false)
  }

  function openDashboard(id: string) {
    navigate({ tab: 'dashboard', runId: id })
  }

  function openRun(id: string) {
    runNonce.current += 1
    setRunPreset(null)
    setRunTarget({ id, nonce: runNonce.current })
    navigate({ tab: 'runs', runId: id })
  }

  function startAnalysis(preset: RunPreset | null) {
    runNonce.current += 1
    setRunTarget(null)
    setRunPreset(preset)
    navigate({ tab: 'runs' })
  }

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setPaletteOpen((open) => !open)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  // Drawer modal semantics: Escape closes, focus moves in on open and
  // returns to the menu button on close.
  const drawerRef = useRef<HTMLDivElement | null>(null)
  const menuButtonRef = useRef<HTMLButtonElement | null>(null)
  // The drawer opens from the header's menu button or the bar's "More";
  // focus goes back to whichever opened it.
  const drawerOpenerRef = useRef<HTMLButtonElement | null>(null)
  useEffect(() => {
    if (!drawerOpen) return
    const first = drawerRef.current?.querySelector<HTMLElement>('button')
    first?.focus()
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setDrawerOpen(false)
      if (event.key === 'Tab') {
        const items = drawerRef.current?.querySelectorAll<HTMLElement>('button:not([disabled]), a[href]')
        if (!items?.length) return
        const first = items[0], last = items[items.length - 1]
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      ;(drawerOpenerRef.current ?? menuButtonRef.current)?.focus()
    }
  }, [drawerOpen])

  function openDrawer(opener: HTMLButtonElement) {
    drawerOpenerRef.current = opener
    setDrawerOpen(true)
  }

  // The other views' chunks follow in idle time once the session is up,
  // so the first paint waits only for the shell and the chat (ADR 0028).
  const hasSession = store.session !== null
  useEffect(() => (hasSession ? prefetchWhenIdle() : undefined), [hasSession])

  const dismissOnboarding = useCallback(() => {
    setShowOnboarding(false)
    try {
      localStorage.setItem(ONBOARDING_KEY, '1')
    } catch {
      /* localStorage unavailable — the dialog simply reappears next visit */
    }
  }, [])

  function pickCommand(command: CommandInfo) {
    setPaletteOpen(false)
    setEvidenceContext(null)
    go('chat')
    const hasArguments = command.usage.trim() !== command.command
    setPendingCommand(hasArguments ? `${command.command} ` : command.command)
  }

  async function confirmAction() {
    setConfirmBusy(true)
    if (confirming === 'history') {
      await store.clearHistory()
    } else if (confirming === 'end') {
      await store.endSession()
    }
    setConfirmBusy(false)
    setConfirming(null)
  }

  const { session, bootError, status } = store
  const otherLocale = locale === 'en' ? 'ar' : 'en'

  // One control a reader can always find: the other language's name, in
  // that language. Marked with its own `lang` so a screen reader
  // pronounces it correctly rather than in the interface language.
  const languageButton = (
    <button
      type="button"
      className="langbtn"
      aria-label={t('language.switch')}
      onClick={() => {
        void store.setLanguage(otherLocale)
        setDrawerOpen(false)
      }}
    >
      <Icon name="globe" size={16} />
      <span lang={otherLocale}>{t('language.other')}</span>
    </button>
  )

  // Hosted deployments gate everything behind the identity provider.
  const accessPending = store.authConfig?.mode === 'jwt' && Boolean(store.identity) && !store.identity?.principal.permissions.includes('write')
  if ((store.needsSignIn || accessPending) && store.authConfig) {
    return (
      <ViewBoundary>
        <Suspense fallback={<ViewLoading />}>
          <SignIn
            config={store.authConfig}
            onSignedIn={store.signIn}
            accessPending={accessPending}
            onSignOut={store.signOut}
          />
        </Suspense>
      </ViewBoundary>
    )
  }

  if (!session) {
    return (
      <div className="shell">
        <header className="shell__header">
          <div className="brand">
            <span className="brand__mark" aria-hidden="true"><img src="/artwork/asset-reliability-mark.svg" alt="" width={32} height={32} /></span>
            <span className="brand__name" title={t('brand.fullName')}>{t('brand.name')}</span>
          </div>
          <div className="header__spacer" style={{ flex: 1 }} />
          {languageButton}
        </header>
        {bootError ? (
          <div className="empty" style={{ margin: 'auto' }}>
            <div className="empty__icon">
              <Icon name="alert" size={32} />
            </div>
            <p>{bootError}</p>
            <p style={{ marginTop: 'var(--space-4)' }}>
              <button type="button" className="btn btn--primary" onClick={() => void store.start()}>
                <Icon name="refresh" size={16} />
                {t('boot.tryAgain')}
              </button>
            </p>
          </div>
        ) : (
          <div className="boot" role="status" aria-label={t('boot.startingAria')}><span className="visually-hidden">{t('boot.startingAria')}</span>
            <div className="skeleton skeleton--orb" />
            <div className="skeleton skeleton--title" />
            <div className="skeleton skeleton--line" />
            <div className="skeleton skeleton--line skeleton--short" />
            <p className="boot__text">{t('boot.starting')}</p>
          </div>
        )}
      </div>
    )
  }

  const memoryCount = Object.keys(session.memory).length
  const rawName = session.preferences.user_name
  const userName = typeof rawName === 'string' && rawName.trim() ? rawName.trim() : null

  function pane(id: Tab, content: ReactNode) {
    if (demo && NEEDS_SESSION.has(id)) return null
    if (tab !== id && !visited.includes(id)) return null
    return <Activity key={id} mode={tab === id ? 'visible' : 'hidden'}><ViewBoundary><Suspense fallback={<ViewLoading />}>{content}</Suspense></ViewBoundary></Activity>
  }

  const sidebar = (
    <div className="sidebar">
      {demo ? null : <button type="button" className="miyaar-sidebar" onClick={() => go('chat')}>
        <MiyaarMark /><span><strong>{t('assistant.name')}</strong><small>{t('miyaar.workspace')}</small></span>
      </button>}
      <nav className="sidebar__nav" aria-label={t('nav.main')}>
        {(demo ? DEMO_GROUPS : NAV_GROUPS).map((group) => (
          <details key={group.id} className="sidebar__group" data-group={group.id} open={group.items.some((item) => item.id === tab)}><summary>{t(group.label)}</summary>
            {group.items.map((item) => (
              <button
                key={item.id}
                type="button"
                className="navbtn"
                aria-current={tab === item.id ? 'page' : undefined}
                onClick={() => go(item.id)}
              >
                <Icon name={item.icon} size={18} />
                {t(item.label)}
                {item.id === 'memory' && memoryCount > 0 ? (
                  <span className="navbtn__badge">{memoryCount}</span>
                ) : null}
              </button>
            ))}
          </details>
        ))}
      </nav>
      <div className="sidebar__footer">
        <button type="button" className="btn btn--subtle miyaar-mobile-help"
          onClick={() => { setDrawerOpen(false); setHelpOpen(true) }}>
          <Icon name="help" size={16} />{t('help.aria')}
        </button>
        {demo ? null : <>
        <button
          type="button"
          className="btn btn--ghost"
          onClick={() => {
            void store.start()
            go('chat')
          }}
        >
          <Icon name="plus" size={16} />
          {t('session.new')}
        </button>
        <button
          type="button"
          className="btn btn--subtle"
          onClick={() => {
            setConfirming('end')
            setDrawerOpen(false)
          }}
          disabled={session.ended}
        >
          <Icon name="power" size={16} />
          {t('session.end')}
        </button>
        </>}
        <div className="sidebar__identity">
          <span className="sidebar__avatar" aria-hidden="true">
            {(store.identity?.principal.email || userName || 'A').charAt(0).toUpperCase()}
          </span>
          <span className="sidebar__who">
            <span dir="auto">{demo ? t('demo.visitor') : store.identity?.principal.email || userName || t('session.roleLocal')}</span>
            <span className="sidebar__meta">
              {session.version ? `v${session.version} · ` : ''}{store.identity?.principal.role ?? t('session.roleLocal')}
            </span>
          </span>
          {store.identity && !demo ? (
            <button
              type="button"
              className="iconbtn"
              aria-label={t('session.signOut')}
              title={t('session.signOut')}
              onClick={() => {
                store.signOut()
                setDrawerOpen(false)
              }}
            >
              <Icon name="power" size={16} />
            </button>
          ) : null}
        </div>
      </div>
    </div>
  )

  return (
    <div className="shell">
      <a className="skiplink" href={tab === 'chat' && !evidenceContext ? '#composer-input' : '#workspace-main'} onClick={(event) => {
        event.preventDefault()
        document.getElementById(tab === 'chat' && !evidenceContext ? 'composer-input' : 'workspace-main')?.focus()
      }}>
        {t(tab === 'chat' && !evidenceContext ? 'shell.skip' : 'shell.skipMain')}
      </a>
      <header className="shell__header" inert={drawerOpen}>
        <button
          type="button"
          ref={menuButtonRef}
          className="iconbtn menubtn"
          aria-label={t('nav.open')}
          aria-expanded={drawerOpen}
          onClick={(event) => openDrawer(event.currentTarget)}
        >
          <Icon name="menu" />
        </button>
        <div className="brand">
          <span className="brand__mark" aria-hidden="true"><img src="/artwork/asset-reliability-mark.svg" alt="" width={32} height={32} /></span>
          <h1 className="brand__name" title={t('assistant.tagline')}>{t('assistant.name')}</h1>
          <span className="brand__descriptor">{t('assistant.tagline')}</span>
        </div>
        <div className="header__search">
          <button
            type="button"
            className="searchbtn"
            onClick={() => setPaletteOpen(true)}
            aria-label={t('search.aria')}
          >
            <Icon name="search" size={16} />
            <span className="searchbtn__text">{t('search.button')}</span>
            <kbd>{MODIFIER_KEY} K</kbd>
          </button>
        </div>
        <div className="header__spacer" />
        <div className="header__actions">
          {languageButton}
          <button
            type="button"
            className="iconbtn"
            aria-label={isDark ? t('theme.toLight') : t('theme.toDark')}
            data-control="theme"
            onClick={toggleTheme}
          >
            <Icon name={isDark ? 'sun' : 'moon'} />
          </button>
          <button
            type="button"
            className="iconbtn"
            aria-label={t('help.aria')}
            data-control="help"
            onClick={() => setHelpOpen(true)}
          >
            <Icon name="help" />
          </button>
        </div>
      </header>
      <div className={`shell__mode${!demo && status === 'ready' && tab !== 'chat' ? ' visually-hidden' : ''}`} inert={drawerOpen}>{demo ? <strong title={t('demo.note')}>{t('demo.badge')}</strong> : <StatusBadge status={status} />}</div>

      <div className="shell__body">
        {sidebar}

        {drawerOpen ? (
          <>
            <button
              type="button"
              className="scrim"
              aria-label={t('nav.close')}
              onClick={() => setDrawerOpen(false)}
            />
            <div
              className="drawer"
              role="dialog"
              aria-modal="true"
              aria-label={t('nav.drawer')}
              ref={drawerRef}
            >
              {sidebar}
            </div>
          </>
        ) : null}

        <main className="main" id="workspace-main" inert={drawerOpen} tabIndex={-1} key={`${session.session_id}:${store.identity?.principal.subject ?? 'local'}:${store.identity?.principal.role ?? 'local'}`}>
          <ReadOnlyContext.Provider value={demo}>
          {pane('operations', <OperationsView key={route.tab === 'operations' ? route.runId ?? 'manual' : 'manual'} sourceRunId={route.tab === 'operations' ? route.runId : undefined} onClearSource={() => navigate({ tab: 'operations' })} onOpenRun={openRun} />)}
          {pane('rmd', <RmdView onOpenRun={openRun} onExplain={(packId, analysisId) => {
            setEvidenceContext({ packId, analysisId }); navigate({ tab: 'chat' })
          }} />)}
          {pane('overview', (
            <OverviewView onOpenRun={openRun} onStart={startAnalysis} onAddDataset={() => go('datasets')} canStart={!demo} onApprovals={() => go('approvals')}
              onOpenDashboard={(id) => (id ? openDashboard(id) : go('dashboard'))} onSeeAll={() => go('runs')} />
          ))}
          {pane('assets', (
            <AssetIntelligenceView onOpenRun={openRun}
              onUpload={demo ? undefined : () => go('datasets')} />
          ))}
          {pane('datasets', (
            <DatasetsView
              onAnalyse={(dataset) =>
                startAnalysis({ kind: 'stored', id: dataset.id, name: dataset.name })
              }
            />
          ))}
          {pane('chat', (
            evidenceContext ? <RmdAssistantPanel
              key={evidenceContext.packId + ':' + evidenceContext.analysisId}
              packId={evidenceContext.packId} analysisId={evidenceContext.analysisId}
              onDismiss={() => setEvidenceContext(null)} /> :
            <ChatView
              key={session.session_id}
              session={session}
              sending={store.sending}
              failedText={store.failedText}
              pendingText={store.pendingText}
              requestError={store.requestError}
              connectionStatus={status}
              onAction={(action) => {
                // The assistant's upload suggestion reaches the Datasets flow too (U15).
                if (action === 'analyse' || action === 'report') go('datasets')
                else if (action === 'approvals') go('approvals')
                else go('assets')
              }}
              offline={status === 'offline'}
              userName={userName}
              onSend={store.send}
              onRetry={() => void store.retryFailed()}
              onDismissFailed={store.dismissFailed}
              composerRef={composerRef}
              onOpenRun={openRun}
            />
          ))}
          {pane('runs', (
            <RunsView
              draftScope={session.session_id}
              key={currentRunId ?? `form-${runNonce.current}-${route.source ?? ''}-${route.profile ?? ''}`}
              onRunSelected={selectRun}
              openRunId={currentRunId}
              openNonce={runTarget?.nonce ?? 0}
              preset={route.source === 'upload' && !route.runId ? { kind: 'upload', profile: route.profile } : runPreset}
              onOpenDashboard={openDashboard}
              onDraftWork={(id) => navigate({ tab: 'operations', runId: id })}
            />
          ))}
          {pane('dashboard', (
            <DashboardView
              runId={dashboardRoute.runId ?? null}
              page={dashboardRoute.page ?? null}
              query={dashboardRoute.query ?? ''}
              onNavigate={navigate}
              onOpenRun={openRun}
            />
          ))}
          {pane('memory', (
            <MemoryView
              entries={session.memory_entries}
              disabled={session.ended}
              onAdd={store.addMemory}
              onUpdate={store.updateMemory}
              onDelete={store.deleteMemory}
              onClearAll={store.clearMemory}
              onExport={store.exportData}
              onClearHistory={() => setConfirming('history')}
            />
          ))}
          {pane('preferences', (
            <PreferencesView
              preferences={session.preferences}
              disabled={session.ended}
              locale={locale}
              onSet={store.setPreference}
              onSetLanguage={store.setLanguage}
            />
          ))}
          {pane('activity', (
            <ActivityView
              events={store.events}
              session={session}
              status={status}
              lastSyncedAt={store.lastSyncedAt}
            />
          ))}
        {pane('approvals', <ApprovalsView onOpenRun={openRun} />)}
          </ReadOnlyContext.Provider>
        </main>

        {tab === 'chat' && !demo && !evidenceContext ? (
          <aside className="rail" aria-label={t('rail.aria')}>
            <div className="rail__section">
              <MiyaarMark large />
              <h2 className="rail__title">{t('miyaar.context')}</h2>
              <dl>
                <div className="rail__row">
                  <dt>{t('rail.agent')}</dt>
                  <dd dir="auto">{t('assistant.name')}</dd>
                </div>
                <div className="rail__row">
                  <dt>{t('rail.messages')}</dt>
                  <dd>{session.transcript.length}</dd>
                </div>
                <div className="rail__row">
                  <dt>{t('rail.memoryEntries')}</dt>
                  <dd>{memoryCount}</dd>
                </div>
                <div className="rail__row">
                  <dt>{t('rail.tone')}</dt>
                  <dd>{toneLabel(t, String(session.preferences.tone ?? 'friendly'))}</dd>
                </div>
                <div className="rail__row">
                  <dt>{t('rail.language')}</dt>
                  <dd>{languageLabel(t, session.preferences.language ?? 'English')}</dd>
                </div>
              </dl>
            </div>
            <div className="rail__section">
              <h2 className="rail__title">{t('rail.recent')}</h2>
              {store.events.length === 0 ? (
                <p className="rail__event">{t('rail.none')}</p>
              ) : (
                store.events.slice(0, 6).map((event) => (
                  <p key={event.id} className="rail__event">
                    <span className={`dot dot--${event.kind}`} aria-hidden="true" />
                    {t(event.code, event.vars)}
                  </p>
                ))
              )}
            </div>
          </aside>
        ) : null}
      </div>

      <nav className="tabbar" aria-label={t('nav.primary')}>
        {BAR_ITEMS.map((item) => (
          <button
            key={item.id}
            type="button"
            className="tabbar__btn"
            aria-current={tab === item.id ? 'page' : undefined}
            onClick={() => go(item.id)}
          >
            <Icon name={item.icon} size={20} />
            <span>{t(item.short ?? item.label)}</span>
          </button>
        ))}
        <button
          type="button"
          className={`tabbar__btn ${BAR_ITEMS.some((item) => item.id === tab) ? '' : 'tabbar__btn--holding'}`}
          aria-haspopup="dialog"
          aria-expanded={drawerOpen}
          onClick={(event) => openDrawer(event.currentTarget)}
        >
          <Icon name="more" size={20} />
          <span>{t('nav.more')}</span>
        </button>
      </nav>

      {/* Each dialog appears when its chunk arrives, with nothing to hold its
          place; one that fails to load leaves the page as it was. */}
      {paletteOpen ? (
        <ViewBoundary fallback={null}>
          <Suspense fallback={null}>
            <CommandPalette
              commands={session.commands}
              onPick={pickCommand}
              onClose={() => setPaletteOpen(false)}
            />
          </Suspense>
        </ViewBoundary>
      ) : null}
      {helpOpen ? (
        <ViewBoundary fallback={null}>
          <Suspense fallback={null}>
            <HelpDialog commands={session.commands} onClose={() => setHelpOpen(false)} />
          </Suspense>
        </ViewBoundary>
      ) : null}
      {showOnboarding && !demo ? (
        <ViewBoundary fallback={null}>
          <Suspense fallback={null}>
            <Onboarding onDismiss={dismissOnboarding} />
          </Suspense>
        </ViewBoundary>
      ) : null}
      {confirming ? (
        <ConfirmDialog
          title={confirming === 'history' ? t('confirm.history.title') : t('confirm.end.title')}
          message={
            confirming === 'history' ? t('confirm.history.message') : t('confirm.end.message')
          }
          confirmLabel={
            confirming === 'history' ? t('confirm.history.confirm') : t('confirm.end.confirm')
          }
          busy={confirmBusy}
          onCancel={() => setConfirming(null)}
          onConfirm={() => void confirmAction()}
        />
      ) : null}
    </div>
  )
}
