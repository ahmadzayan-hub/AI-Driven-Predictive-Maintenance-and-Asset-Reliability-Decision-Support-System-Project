import { lazy, StrictMode, Suspense } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './app/App'
import { StoreProvider } from './app/store'
import { ViewBoundary, ViewLoading } from './app/lazyViews'
import { initializeInstall } from './app/installStore'
import { applyLocale, currentLocale } from './i18n'
// Design system v2 (ADR 0023): the faces are bundled with the app, Latin
// subsets only, so they are cached offline and never fetched from a third
// party. Arabic text uses the system stack set in tokens.css.
import '@fontsource/fira-sans/latin-400.css'
import '@fontsource/fira-sans/latin-500.css'
import '@fontsource/fira-sans/latin-600.css'
import '@fontsource/fira-code/latin-400.css'
import '@fontsource/fira-code/latin-500.css'
import './shared/styles/tokens.css'
import './shared/styles/base.css'
import './shared/styles/app.css'
import './shared/styles/workspace.css'
// Approved Miyaar shell overrides load after the retained base styles.
import './features/chat/miyaar.css'

applyLocale(currentLocale(), false)
// A self-contained design surface: fictional fixtures only, no StoreProvider,
// authenticated API calls, model calls or publishing actions (ADR 0037).
const isDesignPreview = new URLSearchParams(window.location.search).get('design') === 'maintenance'
const MaintenancePreview = lazy(() => import('./features/maintenance/MaintenancePreview').then((module) => ({ default: module.MaintenancePreview })))
if (!isDesignPreview) initializeInstall()
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {isDesignPreview ? <ViewBoundary><Suspense fallback={<ViewLoading />}><MaintenancePreview /></Suspense></ViewBoundary> : <StoreProvider>
      <App />
    </StoreProvider>}
  </StrictMode>,
)

// Installable PWA: register the service worker in production builds only,
// so development and tests always see live code.
if (!isDesignPreview && import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {
      /* offline caching is progressive enhancement — the app works without it */
    })
  })
}

