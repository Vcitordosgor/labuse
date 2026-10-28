import { readFileSync } from 'node:fs'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// M31 (arbitrage Vic) : le run servi a UN SEUL point de vérité versionné, config/served_run.txt.
// Le bundle le LIT ici au build (1ʳᵉ ligne non commentée) et l'injecte en VITE_RUN_LABEL → api.ts
// SOURCE. Plus de littéral de run divergent dans le front ni de dépendance à une var d'env de build.
const SERVED_RUN = readFileSync(new URL('../config/served_run.txt', import.meta.url), 'utf-8')
  .split('\n').map((l) => l.trim()).find((l) => l && !l.startsWith('#')) ?? ''

// API FastAPI (labuse api) proxifiée en dev. En prod, FastAPI sert dist/ à la même origine.
const API = process.env.LABUSE_API_DEV ?? 'http://127.0.0.1:8000'
// F6 (M12) : le proxy dev doit couvrir TOUTES les routes métier — sinon /projets (chercher-plus,
// ajouter, kanban…) et /ia, /crm, /pipeline, /modules… tombent en 404 en `npm run dev` et « rien
// ne se passe » au clic. En prod FastAPI sert dist/ à la même origine (aucun proxy), donc sans effet.
// M36 Lot A : '/v2' MANQUAIT — en dev, useV2Actif() (fetch /v2/modele) échouait toujours →
// la légende retombait sur le repli « matrice » alors que le run servi existe. Le dev raconte
// désormais la même chose que la prod (FastAPI même origine). '/mutation' retiré (M35 Lot E).
const apiPaths = ['/map', '/parcels', '/stats', '/sources', '/filters', '/filtre', '/discover',
  '/health', '/coverage', '/assemblage', '/compare', '/communes', '/v2', '/scoring',
  '/projets', '/ia', '/crm', '/pipeline', '/modules', '/watch', '/share', '/dossier',
  '/faisabilite', '/charge', '/bilan', '/signalement', '/guide',
  // M70 décision 11 (bug 11) : '/pre-dossier' MANQUAIT au proxy dev → le lien /pre-dossier/{idu}.zip
  // sortait de la base '/socle/' et Vite renvoyait « did you mean /socle/pre-dossier… ». Même
  // famille que '/bilan' (M58). En prod (FastAPI même origine) le lien fonctionnait déjà.
  '/pre-dossier',
  // '/bilan' (M58-P1) : la calculette de charge foncière charge /bilan/calculette-defaults —
  // MANQUAIT au proxy dev → 404 rouge en `npm run dev` (la calculette tombait sur son état
  // d'erreur Q5). Prod OK (même origine, FastAPI sert dist/). Comblé pour un dev honnête.
  // KELFONCIER-FIX-1 (Lot B) : '/proprietaires' (facettes + autocomplétion PM) MANQUAIT au proxy dev
  // → la section « Propriétaire » remontée 404-ait en `npm run dev` (endpoint pourtant vivant). En prod
  // (même origine, FastAPI) l'appel fonctionnait déjà ; comblé pour un dev honnête (même patron que /bilan).
  '/proprietaires',
  '/moteurs',   // M-U : outil Marché (+ baromètre/simulplu/zan) — JSON proxifié en dev
  '/moi', '/events',   // compte (menu VL) + cloche de notifs — MANQUAIENT → 404 rouges en `npm run dev`
                       // (les seules erreurs console rouges ; sans effet sur la carte, régression NI de M-W
                       //  ni de la carte — présentes aussi en vite 5, comblées ici pour un dev honnête)
  '/adresses',  // M55-B point 1 : autocomplétion de l'omnibox (/adresses/autocomplete) — MANQUAIT
                // → 404 en dev, la barre de recherche ne suggérait RIEN (silencieusement). Prod OK
                //   (FastAPI même origine), mais le dev doit être honnête.
  '/zonage',    // M99-B : sélecteur de zones (/zonage/zones) — MANQUAIT → menu VIDE en dev
                // (même famille que /bilan M58 et /pre-dossier M70). Prod OK (même origine).
  '/accueil',   // M55-D stage 9 : /accueil/chiffres (page d'accueil qui prouve)
  // M55-L point 13 (audit traducteur) : /traducteur-plu MANQUAIT → 404 en dev, d'où le message
  // « Traduction indisponible — réessayer » (le fetch relatif tombait sur vite, pas sur FastAPI ;
  //  l'endpoint répond 200 à :8000). Même famille que /moi,/events,/adresses. Prod OK (même origine).
  // /courrier et /dossier-banquier comblés au passage (mêmes 404 dev : module Courrier, tuile Financier).
  '/traducteur-plu', '/courrier', '/dossier-banquier',
  // M55-N point 1 (diagnostic) : /anti-fiche MANQUAIT → 404 en dev = « Motifs momentanément
  // indisponibles » sur le tiroir « Pourquoi pas ? ». L'endpoint répond 200 à :8000 (motifs réels
  // sur declasse_* ET ecartee) ; ce n'est PAS une donnée absente mais un proxy dev manquant. Prod OK
  // (même origine FastAPI). ⚠ TRAIN 8 : si la prod passe par Caddy, ces mêmes préfixes doivent y être
  // routés vers l'API (cf. RAPPORT_M55N — liste exhaustive des routes hors-`/parcels`).
  '/anti-fiche',
  // M82 : SEPT routes d'OUTILS manquaient au proxy dev → 404 en `npm run dev`, d'où les états
  // « indisponible » / « non calculé » que la recette a pris pour des outils morts. La donnée et les
  // routes sont SAINES (audit M82, SQL vérifié) ; c'était un trou de proxy dev, même famille que /bilan
  // (M58) et /anti-fiche (M55-N). Prod OK (même origine FastAPI). ⚠ TRAIN 8 Caddy : à router aussi.
  '/servitudes-invisibles', '/comparateur-communes', '/carnet-secteur', '/renouvellement',
  '/scoreur-adresse', '/verif-procedure', '/plu-annuaire',
  // GB-003 : '/alertes' (Veille › Secteurs — GET /alertes, POST /alertes/refresh, /alertes/ack)
  // MANQUAIT → 404 en `npm run dev` (la feed « Nouveautés » restait muette). Backend OK, prod OK.
  '/alertes',
  // RETOURS-1 R5 (Vic) : '/outils' MANQUAIT → /outils/taxe-amenagement/config tombait sur vite en
  // dev → « Barème indisponible — réessayez plus tard » alors que l'endpoint répond 200 à :8000.
  // MÊME famille que /bilan (M58), /anti-fiche (M55-N), M82. Prod OK (FastAPI même origine).
  // ⚠ TRAIN 8 Caddy : à router aussi si la prod passe par Caddy.
  '/outils',
  // RETOURS-1 R9 (Vic) : '/radar' MANQUAIT → tout le Radar client (biens, fiche, Marché) 404 en
  // dev → onglet Marché bloqué sur « Chargement… » (le front avalait l'erreur — corrigé aussi).
  '/radar',
  // DASHBOARD-V1 — capteurs (usage/retours) + Tour de contrôle admin
  '/usage', '/retours', '/admin',
  // EXPORTS-1 (6.3, audit D5) : routes backend qui MANQUAIENT encore au proxy dev — même famille
  // que /bilan (M58) / /pre-dossier (M70). /argumentaire était le cas de départ de l'audit
  // (l'export répondait 200 à :8000 mais 404 en dev). ⚠ TRAIN 8 Caddy : à router aussi.
  '/argumentaire', '/lettre-zonage', '/pipeline-rarete', '/ortho', '/shortlist',
  '/audit', '/feedback', '/readyz', '/protection',
  // RECETTE-1 R1/R2/R3 : les TROIS documents servis par le builder EXPORTS-2 (routes racine
  // `/resume/{idu}.pdf`, `/apporteur/{idu}.pdf`, `/financier/{idu}.pdf` + `/financier/{idu}/
  // questionnaire`) MANQUAIENT au proxy dev → en `npm run dev` le lien PDF sortait de la base
  // '/socle/' (« public base URL of /socle/ ») et le questionnaire tombait sur vite (« Impossible
  // de charger le questionnaire »). MÊME famille que /dossier, /pre-dossier (M70), /argumentaire.
  // Prod OK (FastAPI même origine). ⚠ TRAIN 8 Caddy : à router aussi.
  '/apporteur', '/financier',   // RECETTE-3 (T2) : '/resume' retiré (document Résumé supprimé)
  // COHERENCE-FIX-1 (lot A) : /sante/fraicheur (page Données — état des caches) — même famille
  // de trous de proxy dev que /outils, /bilan… Prod OK (même origine).
  '/sante',
  // DOCS-FIX-1 (P1, bloquant dev) : les 3 documents DOCS-1 servis par le builder exports
  // (`/gabarit/{idu}.pdf`, `/comparatif.pdf`, `/etude-zone.pdf`) ET la bibliothèque « Mes
  // documents » (`/documents`, GET/POST/DELETE + /rafraichir) MANQUAIENT au proxy dev → en
  // `npm run dev` le lien PDF sortait de la base '/socle/' (404 / page d'erreur Vite) et la
  // bibliothèque restait vide. MÊME famille de trous que /dossier, /financier, /apporteur
  // (RECETTE-1), /pre-dossier (M70). Prod OK (FastAPI même origine). Le garde-fou
  // tests/test_proxy_dev_couvre_routes_api.py échoue désormais si une route d'API reste hors
  // de cette liste — pour qu'une 4ᵉ occurrence ne revienne pas. ⚠ TRAIN 8 Caddy : routées aussi.
  '/gabarit', '/comparatif', '/etude-zone', '/documents',
  // ANNONCE-3 : le document « Analyse d'annonce » (miroir de l'outil Analyser une annonce) — entrée
  // adresse `/analyse-annonce/{idu}.pdf` ET entrée lien `/analyse-annonce.pdf?url=…`. Même famille de
  // trous de proxy dev que /gabarit·/comparatif·/etude-zone ; prod OK (FastAPI même origine).
  '/analyse-annonce',
  // DOCS-FIX-1 (P1, garde-fou) : trois routes d'API que le FRONT appelle en JSON (`j<…>`) mais qui
  // MANQUAIENT encore au proxy dev — révélées par test_proxy_dev_couvre_routes_api.py :
  //   • '/config'      → main.tsx au démarrage (fetchServedRun = /config/run = runs.current())
  //   • '/partners'    → getProfiles / promoteursActifs (/partners/profiles, /partners/promoteurs-actifs)
  //   • '/vocabulaire' → getPaliersDA / getScoringFraction (/vocabulaire/paliers, /scoring-fraction)
  // Même famille de trous dev que /bilan (M58). Prod OK (FastAPI même origine). ⚠ TRAIN 8 Caddy.
  '/config', '/partners', '/vocabulaire',
  '/api']   // M26-B : /api/copilote (runs + SSE)

export default defineConfig({
  base: '/socle/', // servi par FastAPI sous /socle (cf. app.py). Dev vite = racine.
  plugins: [react()],
  // M31 : injecte le run servi versionné dans le bundle (api.ts lit import.meta.env.VITE_RUN_LABEL).
  define: { 'import.meta.env.VITE_RUN_LABEL': JSON.stringify(SERVED_RUN) },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    // PARCOURS-FIX-1 (Lot 1.1, reprise de MAPLIBRE-1 9cc198cb) — CAUSE DE LA PAGE BLANCHE EN PROD :
    // le groupe de chunk manuel `vendor` regroupait React (module CommonJS) dans un chunk séparé ;
    // sous Rolldown (vite 8), le helper d'interop CJS `__commonJSMin` n'était PAS co-localisé avec ce
    // chunk → `TypeError: t is not a function` / `__commonJSMin is not a function` à l'init du vendor →
    // React ne montait jamais → écran blanc (le dev, non chunké, n'était pas touché). On SUPPRIME le
    // groupe `vendor` (React reste dans l'entrée, avec son helper). On GARDE le groupe `maplibre` :
    // maplibre-gl est ESM (pas de helper CJS → aucun risque) et doit rester dans son PROPRE chunk
    // asynchrone, hors du graphe initial (sinon Rolldown le hisse dans l'entrée). maplibre 4 conservé
    // (rien d'autre de la branche maplibre-1). Vérifié : build OK, page prod rendue (plus de page blanche).
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            { name: 'maplibre', test: /[\\/]node_modules[\\/]maplibre-gl[\\/]/ },
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
