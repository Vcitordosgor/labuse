// HARNAIS PARCOURS-CLIENT-1 — config vite dev SINGLE-ORIGIN (port 8795).
// ⚠ À COPIER DANS frontend/ avant de lancer (les plugins ne se résolvent que depuis frontend/) :
//     cp scripts/vite.parcours.config.mjs ../../../frontend/vite.parcours.config.mjs
//     (cd frontend && LABUSE_API_DEV=http://127.0.0.1:5995 node_modules/.bin/vite --config vite.parcours.config.mjs)
// N'est PAS une correction produit : sert à jouer l'UX réelle quand le build prod (Rolldown, chunk
// vendor) rend une page blanche sous le chromium disponible (voir RAPPORT, BLOQUANT-1). Le dev sert le
// SPA non-minifié et PROXIFIE toutes les routes serveur + API vers l'API FastAPI (5995) → même origine.
import { readFileSync } from 'node:fs'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const SERVED_RUN = readFileSync(new URL('../config/served_run.txt', import.meta.url), 'utf-8')
  .split('\n').map((l) => l.trim()).find((l) => l && !l.startsWith('#')) ?? ''

const API = process.env.LABUSE_API_DEV ?? 'http://127.0.0.1:5995'

const PROXY = [
  '/login', '/logout', '/login/2fa', '/invitation', '/reset', '/reset-demande',
  '/cgv', '/mentions-legales', '/confidentialite', '/onboarding', '/stripe', '/guide',
  '/flash', '/flash-retour.js', '/parcours.js', '/favicon.ico', '/readyz', '/healthz',
  '/map', '/parcels', '/stats', '/sources', '/filters', '/filtre', '/discover', '/health',
  '/coverage', '/assemblage', '/compare', '/communes', '/v2', '/scoring', '/projets', '/ia',
  '/crm', '/pipeline', '/modules', '/watch', '/share', '/dossier', '/faisabilite', '/charge',
  '/bilan', '/signalement', '/pre-dossier', '/proprietaires', '/moteurs', '/moi', '/events',
  '/adresses', '/zonage', '/accueil', '/traducteur-plu', '/courrier', '/dossier-banquier',
  '/anti-fiche', '/servitudes-invisibles', '/comparateur-communes', '/carnet-secteur',
  '/renouvellement', '/scoreur-adresse', '/verif-procedure', '/plu-annuaire', '/alertes',
  '/outils', '/radar', '/usage', '/retours', '/admin', '/argumentaire', '/lettre-zonage',
  '/pipeline-rarete', '/ortho', '/shortlist', '/audit', '/feedback', '/protection',
  '/apporteur', '/financier', '/sante', '/api', '/resume',
]

export default defineConfig({
  base: '/',
  plugins: [react()],
  define: { 'import.meta.env.VITE_RUN_LABEL': JSON.stringify(SERVED_RUN) },
  server: {
    port: 8795,
    host: '127.0.0.1',
    strictPort: true,
    proxy: Object.fromEntries(PROXY.map((p) => [p, { target: API, changeOrigin: true }])),
  },
})
