import { readFileSync } from 'node:fs'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// M31 (arbitrage Vic) : le run servi a UN SEUL point de vérité versionné, config/served_run.txt.
// Le bundle le LIT ici au build (1ʳᵉ ligne non commentée) et l'injecte en VITE_RUN_LABEL → api.ts
// SOURCE. Plus de littéral de run divergent dans le front ni de dépendance à une var d'env de build.
const SERVED_RUN = readFileSync(new URL('../config/served_run.txt', import.meta.url), 'utf-8')
  .split('\n').map((l) => l.trim()).find((l) => l && !l.startsWith('#')) ?? ''

// API FastAPI (labuse api) proxifiée en dev. En prod, FastAPI sert dist/ à la même origine.
const API = 'http://127.0.0.1:8000'
// F6 (M12) : le proxy dev doit couvrir TOUTES les routes métier — sinon /projets (chercher-plus,
// ajouter, kanban…) et /ia, /crm, /pipeline, /modules… tombent en 404 en `npm run dev` et « rien
// ne se passe » au clic. En prod FastAPI sert dist/ à la même origine (aucun proxy), donc sans effet.
const apiPaths = ['/map', '/parcels', '/stats', '/sources', '/filters', '/discover',
  '/health', '/coverage', '/assemblage', '/compare', '/mutation', '/communes',
  '/projets', '/ia', '/crm', '/pipeline', '/modules', '/watch', '/share', '/dossier',
  '/faisabilite', '/charge', '/signalement', '/guide',
  '/api']   // M26-B : /api/copilote (runs + SSE)

export default defineConfig({
  base: '/socle/', // servi par FastAPI sous /socle (cf. app.py). Dev vite = racine.
  plugins: [react()],
  // M31 : injecte le run servi versionné dans le bundle (api.ts lit import.meta.env.VITE_RUN_LABEL).
  define: { 'import.meta.env.VITE_RUN_LABEL': JSON.stringify(SERVED_RUN) },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks: {
          maplibre: ['maplibre-gl'],
          vendor: ['react', 'react-dom', '@tanstack/react-query', 'zustand'],
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: Object.fromEntries(apiPaths.map((p) => [p, { target: API, changeOrigin: true }])),
  },
})
