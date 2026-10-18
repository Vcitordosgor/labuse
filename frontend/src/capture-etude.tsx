// IMPLANTATION-4 — HARNAIS DE CAPTURE de l'écran Étude (Docs). Monte le VRAI EtudeEcran ; l'API est
// bouchonnée ici avec un PAYLOAD RÉEL pré-généré par le moteur (`frontend/public/capture/payload-*.json`,
// servi same-origin par Vite) → la PLANCHE affichée est celle du serveur, à l'identique du PDF. Choix de
// la commune par `?c=es|sa|sd`. Harnais de recette uniquement.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createRoot } from 'react-dom/client'
import '@fontsource/inter/400.css'
import '@fontsource/inter/500.css'
import '@fontsource/inter/600.css'
import './styles/index.css'
import { EtudeEcran } from './components/outils/EtudeEcran'
import { useApp } from './store/useApp'

const c = new URLSearchParams(location.search).get('c') || 'es'
const vraiFetch = window.fetch.bind(window)
const json = (body: unknown) => new Response(JSON.stringify(body), { status: 200, headers: { 'content-type': 'application/json' } })

vraiFetch(`${import.meta.env.BASE_URL}capture/payload-${c}.json`)
  .then((r) => r.json())
  .then((PAYLOAD) => {
    window.fetch = (async (input: RequestInfo | URL) => {
      const u = typeof input === 'string' ? input : input instanceof URL ? input.href : (input as Request).url
      if (u.includes('/moteurs/config')) return json({ assemblage_max_ecran: 8 })
      if (u.includes('/modules/etude')) return json(PAYLOAD)
      return json({})
    }) as typeof fetch

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    document.body.style.background = '#060A08'
    createRoot(document.getElementById('root')!).render(
      <QueryClientProvider client={qc}><EtudeEcran /></QueryClientProvider>,
    )
    setTimeout(() => useApp.getState().ouvrirEtude(PAYLOAD.entrees.idus as string[]), 50)
  })
