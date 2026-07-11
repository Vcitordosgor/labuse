import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { ErrorBoundary } from './components/ErrorBoundary'
import { is429 } from './lib/api'
import './styles/index.css'

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
      <QueryClientProvider client={qc}>
        <App />
      </QueryClientProvider>
    </ErrorBoundary>
  </React.StrictMode>,
)
