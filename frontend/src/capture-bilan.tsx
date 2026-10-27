// DOCS-COHERENCE-1 (G7) — HARNAIS DE CAPTURE de l'écran Bilan (Docs). Monte le VRAI BilanEcran ;
// les appels /bilan/{idu}/modele et /bilan/{idu}/calcul passent par le proxy Vite vers l'API locale
// (aucun bouchon, aucune auth : ces deux routes sont publiques). `?idu=` choisit la parcelle.
// Harnais de recette uniquement — « Enregistrer » n'est jamais cliqué.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createRoot } from 'react-dom/client'
import '@fontsource/inter/400.css'
import '@fontsource/inter/500.css'
import '@fontsource/inter/600.css'
import './styles/index.css'
import { BilanEcran } from './components/fiche/BilanEcran'

const idu = new URLSearchParams(location.search).get('idu') || '97415000BY0083'
const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
document.body.style.background = '#060A08'
createRoot(document.getElementById('root')!).render(
  <QueryClientProvider client={qc}>
    <BilanEcran idu={idu} onClose={() => { /* capture : pas de fermeture */ }} />
  </QueryClientProvider>,
)
