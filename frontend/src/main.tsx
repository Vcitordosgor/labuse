import { useApp } from './store/useApp'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import ReactDOM from 'react-dom/client'
import { LogoIntro, useOuvertureUneFois } from './components/LogoIntro'
import { Chargement } from './components/Loading'
import { ErrorBoundary } from './components/ErrorBoundary'
import { EcranOrdinateur } from './components/EcranOrdinateur'
import { bureau } from './chargerBureau'
import { installFocusModality } from './lib/focusModality'
import { _setServedRun, fetchServedRun, is429, SOURCE } from './lib/api'
// CORRECTIFS-1 C7 — polices AUTO-HÉBERGÉES (@fontsource, bundlées par Vite) : plus aucun appel à
// Google Fonts (ni au runtime, ni au build). Poids = ceux chargés auparavant.
import '@fontsource/inter/400.css'
import '@fontsource/inter/500.css'
import '@fontsource/inter/600.css'
import '@fontsource/space-grotesk/500.css'
import '@fontsource/space-grotesk/700.css'
import '@fontsource/jetbrains-mono/400.css'
import '@fontsource/jetbrains-mono/500.css'
import '@fontsource/jetbrains-mono/600.css'
import './styles/index.css'

// M-Q P2-70 — GARDE DE DÉMARRAGE : le run servi (SOURCE) est injecté au build depuis
// config/served_run.txt (vite.config.ts → VITE_RUN_LABEL). S'il est VIDE, l'injection a échoué :
// booter quand même servirait un run indéterminé (toutes les requêtes portent `source=`), listes
// vides sans explication. On refuse de démarrer et on le DIT franchement — mieux vaut un écran
// « run non configuré » qu'un mauvais run silencieux.
function RunNonConfigure() {
  return (
    <div data-run-non-configure role="alert" style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: '#060A08', color: '#ECF5EF', font: '14px/1.6 Inter, system-ui, sans-serif',
      padding: 24, textAlign: 'center',
    }}>
      <div style={{ maxWidth: 440 }}>
        <p style={{ color: '#E8695A', fontWeight: 700, fontSize: 15, marginBottom: 8 }}>
          ▲ Run non configuré
        </p>
        <p style={{ color: '#8FA69A' }}>
          Le run servi (<code>VITE_RUN_LABEL</code>) n'a pas été injecté dans ce build. L'application
          ne peut pas démarrer sans lui — elle servirait un classement indéterminé.
        </p>
        <p style={{ color: '#5f7568', marginTop: 12, fontSize: 12 }}>
          Reconstruire le front après avoir renseigné <code>config/served_run.txt</code>
          {' '}(<code>npm run build</code>).
        </p>
      </div>
    </div>
  )
}

const qc = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false,
      // 429 : re-tenter tout de suite ne fait que remplir la fenêtre de rate-limit —
      // le retry différé (~1 min) est géré par l'UI (RateLimit429 dans la fiche).
      retry: (failureCount, error) => !is429(error) && failureCount < 1,
    },
  },
})

const root = ReactDOM.createRoot(document.getElementById('root')!)
const runPret = fetchServedRun()
  .then((r) => _setServedRun(r?.run))
  .catch(() => { /* Le run du bundle sert de repli. */ })

const entreeAdmin = new URLSearchParams(window.location.hash.slice(1)).get('admin') === '1'

function Bureau({ children }: { children: React.ReactNode }) {
  const [montre, fini] = useOuvertureUneFois()
  const admin = useApp((s) => s.view === 'admin')
  return <>
    {montre && !entreeAdmin && !admin && <LogoIntro onFini={fini} />}
    {children}
  </>
}

installFocusModality()
if (!bureau) {
  void runPret.then(() => {
    root.render(
      <React.StrictMode><EcranOrdinateur /></React.StrictMode>,
    )
  })
} else {
  function rendreBureau(contenu: React.ReactNode) {
    root.render(
      <React.StrictMode>
        <ErrorBoundary>
          <QueryClientProvider client={qc}><Bureau>{contenu}</Bureau></QueryClientProvider>
        </ErrorBoundary>
      </React.StrictMode>,
    )
  }
  rendreBureau(<Chargement variant="bloc" label="Chargement de l’application" />)
  void Promise.all([bureau, runPret]).then(([{ default: App }]) => {
    rendreBureau(SOURCE ? <App /> : <RunNonConfigure />)
  }).catch(() => {
    rendreBureau(<p role="alert">Impossible de charger l’application. Rechargez la page pour réessayer.</p>)
  })
}
