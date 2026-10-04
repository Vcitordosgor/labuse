// MAPLIBRE-1 Lot B — chargement du worker maplibre 6 sous Vite.
//
// maplibre 6 est distribué en ESM pur et charge son worker (`maplibre-gl-worker.mjs`) par URL. Sous un
// bundler comme Vite, `import.meta.url` ne résout PAS le worker à l'intérieur du graphe de modules : il
// faut déclarer son URL explicitement (doc officielle de migration v5→v6). `?worker&url` fait passer le
// worker par le pipeline *worker* de Vite (chunk autonome, dépendances incluses) et renvoie son URL.
//
// C'est LA correction des deux pannes de la tentative précédente :
//   - en dev (`npm run dev`), « maplibre-gl-worker.mjs introuvable » (le pré-bundling Vite ne le trouvait pas) ;
//   - dans le build servi par l'API (`/socle/`), PAGE NOIRE (le worker n'était pas émis → aucune tuile rendue).
// `optimizeDeps.exclude` seul ne règle NI l'un NI l'autre ; `setWorkerUrl` les règle tous les deux.
import * as maplibregl from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'

let fait = false
/** À appeler une fois, AVANT toute création de `maplibregl.Map`. Idempotent. */
export function reglerWorkerMaplibre(): void {
  if (fait) return
  maplibregl.setWorkerUrl(workerUrl)
  // MAPLIBRE-1 (perf, retour Vic) — CAUSE DE LA LENTEUR, mesurée sur Chrome GPU matériel (ANGLE Metal, M1),
  // même parcours v4 puis v6, molette + glisser réels :
  //   v4           : 0 % de frames lentes, 0 ms de blocage fil principal  → FLUIDE 60 fps
  //   v6 (défaut)  : 23 % de frames lentes, p95 184 ms, 2500 ms de blocage → SACCADÉ
  //   v6 + ce fix  : 1,8 % de frames lentes, p95 17,6 ms, 107 ms de blocage → FLUIDE (≈ v4)
  // v4 ET v6 tournent à UN SEUL worker par défaut (getWorkerCount()=1 mesuré pour les deux ; maplibre met
  // workerCount=1 hors Safari). Mais le pipeline de tuiles de v6 est plus lourd : un worker unique ne suit
  // plus pendant l'interaction (décodage sérialisé → le fil principal attend → saccade), là où celui de v4
  // suffisait. On donne donc à v6 le parallélisme de décodage qu'il lui faut. setWorkerCount DOIT être
  // appelé avant la 1ʳᵉ carte (pool de workers créé paresseusement au 1ᵉʳ Map).
  const hc = (typeof navigator !== 'undefined' && navigator.hardwareConcurrency) || 8
  maplibregl.setWorkerCount(Math.max(Math.floor(hc / 2), 2))   // M1 (8 cœurs) → 4 workers
  // diagnostic (sans effet produit, utile au débogage) : accès à maplibre-gl pour introspecter la config.
  ;(window as unknown as Record<string, unknown>).__mlgl = maplibregl
  fait = true
}
