import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { ErrorBoundary } from './components/ErrorBoundary'
import { is429, SOURCE } from './lib/api'
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

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      {SOURCE
        ? (
          <QueryClientProvider client={qc}>
            <App />
          </QueryClientProvider>
        )
        : <RunNonConfigure />}
    </ErrorBoundary>
  </React.StrictMode>,
)
