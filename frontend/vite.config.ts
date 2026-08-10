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
// M36 Lot A : '/v2' MANQUAIT — en dev, useV2Actif() (fetch /v2/modele) échouait toujours →
// la légende retombait sur le repli « matrice » alors que le run servi existe. Le dev raconte
// désormais la même chose que la prod (FastAPI même origine). '/mutation' retiré (M35 Lot E).
const apiPaths = ['/map', '/parcels', '/stats', '/sources', '/filters', '/discover',
  '/health', '/coverage', '/assemblage', '/compare', '/communes', '/v2',
  '/projets', '/ia', '/crm', '/pipeline', '/modules', '/watch', '/share', '/dossier',
  '/faisabilite', '/charge', '/signalement', '/guide',
  '/moteurs',   // M-U : outil Marché (+ baromètre/simulplu/zan) — JSON proxifié en dev
  '/moi', '/events',   // compte (menu VL) + cloche de notifs — MANQUAIENT → 404 rouges en `npm run dev`
                       // (les seules erreurs console rouges ; sans effet sur la carte, régression NI de M-W
                       //  ni de la carte — présentes aussi en vite 5, comblées ici pour un dev honnête)
  '/adresses',  // M55-B point 1 : autocomplétion de l'omnibox (/adresses/autocomplete) — MANQUAIT
                // → 404 en dev, la barre de recherche ne suggérait RIEN (silencieusement). Prod OK
                //   (FastAPI même origine), mais le dev doit être honnête.
  '/api']   // M26-B : /api/copilote (runs + SSE)

export default defineConfig({
  base: '/socle/', // servi par FastAPI sous /socle (cf. app.py). Dev vite = racine.
  plugins: [react()],
  // M31 : injecte le run servi versionné dans le bundle (api.ts lit import.meta.env.VITE_RUN_LABEL).
  define: { 'import.meta.env.VITE_RUN_LABEL': JSON.stringify(SERVED_RUN) },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    // M-W (vite 8, Rolldown) : `rollupOptions` → `rolldownOptions`, et l'ancien `manualChunks`
    // OBJET (retiré sous Rolldown) → `output.codeSplitting.groups` (test par chemin ; `advancedChunks`
    // est lui-même déprécié → on prend le nom courant `codeSplitting`). Découpage IDENTIQUE :
    // maplibre-gl dans son chunk (isolé + différé par le lazy-load M-V), react/react-dom/react-query/
    // zustand dans `vendor`. Vérifié après build : chunks maplibre/vendor présents, maplibre HORS du
    // graphe initial (index.html), pas d'explosion de bundle, aucun avertissement.
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            { name: 'maplibre', test: /[\\/]node_modules[\\/]maplibre-gl[\\/]/ },
            { name: 'vendor', test: /[\\/]node_modules[\\/](react|react-dom|scheduler|@tanstack[\\/]react-query|zustand)[\\/]/ },
          ],
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: Object.fromEntries(apiPaths.map((p) => [p, { target: API, changeOrigin: true }])),
  },
})
