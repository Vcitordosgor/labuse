// IMPLANTATION-4 (suite v4) — HARNAIS DE CAPTURE de l'écran Étude (Docs, sans carte). Monte le VRAI
// EtudeEcran en overlay ; l'API (/moteurs/config, /modules/etude) est BOUCHONNÉE ici (Response réelles),
// zéro dépendance à la base. Témoin L'Étang-Salé AW 99/451/624/625, UA. Le plan masse dessiné reçoit un
// GeoJSON réaliste (34 places DESSINÉES = les 34 annoncées, verrou). Harnais de recette uniquement.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createRoot } from 'react-dom/client'
import '@fontsource/inter/400.css'
import '@fontsource/inter/500.css'
import '@fontsource/inter/600.css'
import './styles/index.css'
import { EtudeEcran } from './components/outils/EtudeEcran'
import { useApp } from './store/useApp'

// ── géométrie (mètres locaux → WGS84 autour de L'Étang-Salé) ─────────────────────────────────
const lat0 = -21.2605, lon0 = 55.2905
const P = (x: number, y: number): [number, number] =>
  [lon0 + x / (111320 * Math.cos((lat0 * Math.PI) / 180)), lat0 + y / 110540]
const rect = (x0: number, y0: number, x1: number, y1: number) =>
  ({ type: 'Polygon', coordinates: [[P(x0, y0), P(x1, y0), P(x1, y1), P(x0, y1), P(x0, y0)]] })
const line = (pts: [number, number][]) => ({ type: 'LineString', coordinates: pts.map(([x, y]) => P(x, y)) })
const feat = (kind: string, geometry: unknown) => ({ type: 'Feature', properties: { kind }, geometry })

function placesRow(y: number) {
  const out = []
  for (let i = 0; i < 17; i++) { const x = 5 + i * 2.5; out.push(feat('place', rect(x, y, x + 2.3, y + 5))) }
  return out
}
// une barre (scénario A) : voie au sud, accès, 2 rangs de 17 places + allée, bâtiment au nord.
const geojsonA = {
  type: 'FeatureCollection',
  features: [
    feat('assiette', rect(0, 0, 50, 35)),
    feat('parcelle', rect(0, 0, 25, 35)), feat('parcelle', rect(25, 0, 50, 35)),
    feat('zone', rect(4, 4, 46, 31)),
    feat('voie', line([[0, 0], [50, 0]])),
    feat('acces', rect(44, 0, 47, 5.5)),
    ...placesRow(5.5), ...placesRow(15.5),
    feat('allee', rect(5, 10.5, 47.5, 15.5)),
    feat('espace_libre', rect(6, 20.8, 44, 22.5)),
    feat('batiment_emprise', rect(6, 23, 44, 31)),
    feat('module', rect(6, 23, 44, 31)),
  ],
}
// deux barres (scénario B) : deux bâtiments plus courts.
const geojsonB = {
  type: 'FeatureCollection',
  features: [
    feat('assiette', rect(0, 0, 50, 35)),
    feat('parcelle', rect(0, 0, 25, 35)), feat('parcelle', rect(25, 0, 50, 35)),
    feat('zone', rect(4, 4, 46, 31)),
    feat('voie', line([[0, 0], [50, 0]])),
    feat('acces', rect(44, 0, 47, 5.5)),
    ...placesRow(5.5), feat('allee', rect(5, 10.5, 47.5, 15.5)),
    feat('batiment_emprise', rect(6, 17, 23, 31)), feat('batiment_emprise', rect(27, 17, 44, 31)),
  ],
}

const CONTROLES = [
  { nom: 'Emprise au sol ≤ 70 % (1 222 m²)', regle: '≤ 70 %', mesure: '1 155 m²', resultat: 'Réussi', citation: 'PLU UA · art. 9 · p.23', detail: null },
  { nom: 'Hauteur ≤ 12 m à l’égout', regle: '≤ 12 m', mesure: 'R+3', resultat: 'Réussi', citation: 'PLU UA · art. 10 · p.24', detail: null },
  { nom: 'Stationnement 34 / 34', regle: '≥ imposé', mesure: '34', resultat: 'Réussi', citation: 'PLU UA · art. 12 · p.25', detail: null },
  { nom: 'Distance entre constructions', regle: 'silence du règlement', mesure: '—', resultat: 'Non applicable', citation: null, detail: null },
  { nom: 'Locaux vélos · déchets', regle: 'non modélisé', mesure: '—', resultat: 'Non effectué', citation: null, detail: null },
]
const scn = (ref: string, forme: string, niveaux: number, statut: string,
  logements: number, places: number, sdp: number, geojson: unknown, par_type: Record<string, number>) => ({
  ref, forme, niveaux, niveaux_label: `R+${niveaux - 1}`, statut_etude: statut,
  resume: { logements, places, sdp_m2: sdp },
  controles_compte: { reussi: 3, echoue: 0, non_effectue: 1, non_applicable: 1 },
  programme: { par_type, shab_par_type_m2: {}, shab_estimee_m2: Math.round(sdp * 0.73), ratio_shab_sdp: 0.73,
    mixite_applicable: true, logements_aides_imposes: Math.round(logements * 0.2), sdp_aidee_imposee_m2: Math.round(sdp * 0.2) },
  distribution_niveaux: Array.from({ length: niveaux }, (_, n) => ({
    niveau: n, par_type: { T2: Math.round(par_type.T2 / niveaux), T3: Math.round((par_type.T3 ?? 0) / niveaux) }, sdp_m2: Math.round(sdp / niveaux) })),
  stationnement: { places, places_imposees: places, details_places: {}, m2_par_place: 12.5,
    surface_stationnement_m2: places * 12.5, note: { allee_unique: true, deux_cotes: true, raison: 'deux côtés de l’allée' },
    acces: { distance_angle_m: 12, note: 'visibilité à confirmer' } },
  surfaces_mesurees_m2: {}, emprise_sol_m2: 1155, pleine_terre_m2: 420,
  controles: CONTROLES, checks_geometriques: [], geojson,
})

const PAYLOAD = {
  moteur: { livrable: 'IMPLANTATION-2', version_conventions: 'implantation-conventions-1', etiquette: 'Estimé', crs_dessin: 'EPSG:2975', crs_carte: 'EPSG:4326' },
  entrees: { idus: ['97404000AW0099', '97404000AW0451', '97404000AW0624', '97404000AW0625'], commune: "L'Étang-Salé", insee: '97404', zone: 'UA', type_projet: 'collectif', objectif: 'equilibre', programme_mode: 'propose', stationnement: 'aerien', terrain: 'libere' },
  regles: { zone: 'UA', insee: '97404', lignes: [
    { nom: 'Recul sur voie', valeur: 4, unite: 'm', validee: true, article: 'UA 6', page_pdf: 22, citation: null },
    { nom: 'Emprise au sol', valeur: 70, unite: '%', validee: true, article: 'UA 9', page_pdf: 23, citation: null },
    { nom: 'Hauteur à l’égout', valeur: 12, unite: 'm', validee: true, article: 'UA 10', page_pdf: 24, citation: null },
    { nom: 'Espaces verts', valeur: 20, unite: '%', validee: true, article: 'UA 13', page_pdf: 26, citation: null },
  ] },
  terrain: { contenance_totale_m2: 1746, aire_dessin_m2: 1744, zone_implantation_m2: 1222, has_voie: true, note_limites: null, contraintes: {}, ppr_rouge_m2: 0, ppr_bleue_m2: 0, pente_lidar: null,
    parcelles: [99, 451, 624, 625].map((n) => ({ idu: `97404000AW0${n}`, numero: `${n}`, contenance_m2: 436, aire_dessin_m2: 435 })) },
  hypotheses: { profondeur_m: 13, coef_plancher_habitable: 0.8, surfaces: { T2: 50, T3: 65, T4: 80 }, largeur_coursive_m: 1.4, hauteur_etage_m: 3, place_m: [2.5, 5], allee_largeur_m: 5, etiquette: 'Estimé' },
  programme_saisi: null, statut_global: 'exploitable en pré-faisabilité', message: null,
  scenarios: [
    scn('A', 'barre', 4, 'exploitable en pré-faisabilité', 28, 34, 2020, geojsonA, { T2: 18, T3: 10 }),
    scn('B', 'deux_barres', 4, 'exploitable en pré-faisabilité', 26, 32, 1900, geojsonB, { T2: 16, T3: 10 }),
    scn('C', 'barre', 3, 'à compléter', 20, 24, 1500, geojsonA, { T2: 14, T3: 6 }),
  ],
}

// ── fetch bouchonné (Response réelles) ───────────────────────────────────────────────────────
const json = (body: unknown) => new Response(JSON.stringify(body), { status: 200, headers: { 'content-type': 'application/json' } })
const vraiFetch = window.fetch.bind(window)
window.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
  const u = typeof input === 'string' ? input : input instanceof URL ? input.href : (input as Request).url
  if (u.includes('/moteurs/config')) return json({ assemblage_max_ecran: 8 })
  if (u.includes('/modules/etude')) return json(PAYLOAD)
  if (u.startsWith('data:') || u.endsWith('.css') || u.endsWith('.woff2') || u.endsWith('.woff')) return vraiFetch(input, init)
  return json({})
}) as typeof fetch

const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
document.body.style.background = '#060A08'
createRoot(document.getElementById('root')!).render(
  <QueryClientProvider client={qc}><EtudeEcran /></QueryClientProvider>,
)
// ouvre l'overlay sur l'assiette témoin après le montage (comme la 9e carte Docs / la tuile fiche).
setTimeout(() => useApp.getState().ouvrirEtude(PAYLOAD.entrees.idus), 50)
