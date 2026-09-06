// CIRCUIT-P (lot 6.1) — point d'entrée du harness de recette : monte la vraie <CircuitSection/>.
// L'API (/admin/circuit…) est interceptée par Playwright avec des fixtures RÉELLES ; ce fichier ne
// connaît ni la base ni les fixtures. Il n'est utilisé qu'en recette (jamais dans l'app).
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createRoot } from 'react-dom/client'

import { CircuitSection } from './components/admin/circuit/Circuit'

const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
createRoot(document.getElementById('root')!).render(
  <QueryClientProvider client={qc}>
    <div style={{ padding: '18px 24px 120px', background: '#0f1512', minHeight: '100vh' }}>
      <CircuitSection />
    </div>
  </QueryClientProvider>,
)
