import { useCallback, useSyncExternalStore } from 'react'

export type Tab = 'overview' | 'datasets' | 'chat' | 'runs' | 'approvals' | 'memory' | 'preferences' | 'activity'
export interface Route { tab: Tab; runId?: string }
const TABS = new Set<Tab>(['overview', 'datasets', 'chat', 'runs', 'approvals', 'memory', 'preferences', 'activity'])

export function parseRoute(hash: string): Route {
  const [name, rawId] = hash.replace(/^#\/?/, '').split('/')
  const tab = name === 'assistant' || name === 'workspace' ? 'chat' : name
  if (!TABS.has(tab as Tab)) return { tab: 'chat' }
  if (tab === 'runs' && rawId && /^[a-zA-Z0-9_-]{1,100}$/.test(rawId)) return { tab, runId: rawId }
  return { tab: tab as Tab }
}

export function routeHash(route: Route): string {
  return `#/${route.tab === 'chat' ? 'assistant' : route.tab}${route.tab === 'runs' && route.runId ? `/${encodeURIComponent(route.runId)}` : ''}`
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
