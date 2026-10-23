import { useCallback, useSyncExternalStore } from 'react'

export type Tab = 'operations' | 'overview' | 'assets' | 'datasets' | 'rmd' | 'chat' | 'runs' | 'dashboard' | 'approvals' | 'memory' | 'preferences' | 'activity'
/** Where the reader is. A dashboard address also carries its page and
 *  every choice made on it (ADR 0032), so a filtered page survives a
 *  reload and can be shared. An address that names no view, or one that
 *  does not exist, lands on the Command Centre: a returning manager
 *  opens on the decision, and the assistant stays one tap away. */
export interface Route { tab: Tab; runId?: string; page?: string; query?: string; source?: 'upload'; profile?: 'maintenance' | 'models' }
const TABS = new Set<Tab>(['operations', 'overview', 'assets', 'datasets', 'rmd', 'chat', 'runs', 'dashboard', 'approvals', 'memory', 'preferences', 'activity'])
const ID = /^[a-zA-Z0-9_-]{1,100}$/
const PAGE = /^[a-z]{1,20}$/

export function parseRoute(hash: string): Route {
  const raw = hash.replace(/^#\/?/, '')
  const mark = raw.indexOf('?')
  const path = mark === -1 ? raw : raw.slice(0, mark)
  const query = mark === -1 ? '' : raw.slice(mark + 1)
  const [name, rawId, rawPage] = path.split('/')
  const tab = name === 'assistant' || name === 'workspace' ? 'chat' : name
  if (!TABS.has(tab as Tab)) return { tab: 'overview' }
  if ((tab === 'runs' || tab === 'operations') && rawId && ID.test(rawId)) return { tab, runId: rawId }
  if (tab === 'runs' && !rawId && new URLSearchParams(query).get('source') === 'upload') {
    const profile = new URLSearchParams(query).get('profile')
    return { tab, source: 'upload', ...(profile === 'maintenance' || profile === 'models' ? { profile } : {}) }
  }
  if (tab === 'dashboard') {
    const route: Route = { tab }
    if (rawId && ID.test(rawId)) {
      route.runId = rawId
      if (rawPage && PAGE.test(rawPage)) route.page = rawPage
      if (query) route.query = query
    }
    return route
  }
  return { tab: tab as Tab }
}

export function routeHash(route: Route): string {
  if (route.tab === 'dashboard') {
    if (!route.runId) return '#/dashboard'
    return `#/dashboard/${encodeURIComponent(route.runId)}${route.page ? `/${route.page}` : ''}${route.query ? `?${route.query}` : ''}`
  }
  return `#/${route.tab === 'chat' ? 'assistant' : route.tab}${(route.tab === 'runs' || route.tab === 'operations') && route.runId ? `/${encodeURIComponent(route.runId)}` : route.tab === 'runs' && route.source === 'upload' ? `?source=upload${route.profile ? `&profile=${route.profile}` : ''}` : ''}`
}

function subscribe(listener: () => void) {
  window.addEventListener('hashchange', listener)
  return () => window.removeEventListener('hashchange', listener)
}

export function useHashRoute(): [Route, (route: Route) => void] {
  const hash = useSyncExternalStore(subscribe, () => window.location.hash, () => '')
  const navigate = useCallback((route: Route) => {
    const next = routeHash(route)
    if (window.location.hash !== next) window.location.hash = next
  }, [])
  return [parseRoute(hash), navigate]
}
