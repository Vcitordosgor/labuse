import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// API FastAPI (labuse api) proxifiée en dev. En prod, FastAPI sert dist/ à la même origine.
const API = 'http://127.0.0.1:8000'
// F6 (M12) : le proxy dev doit couvrir TOUTES les routes métier — sinon /projets (chercher-plus,
// ajouter, kanban…) et /ia, /crm, /pipeline, /modules… tombent en 404 en `npm run dev` et « rien
// ne se passe » au clic. En prod FastAPI sert dist/ à la même origine (aucun proxy), donc sans effet.
const apiPaths = ['/map', '/parcels', '/stats', '/sources', '/filters', '/discover',
  '/health', '/coverage', '/assemblage', '/compare', '/mutation', '/communes',
  '/projets', '/ia', '/crm', '/pipeline', '/modules', '/watch', '/share', '/dossier',
  '/faisabilite', '/charge', '/signalement', '/guide']

export default defineConfig({
  base: '/socle/', // servi par FastAPI sous /socle (cf. app.py). Dev vite = racine.
  plugins: [react()],
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
