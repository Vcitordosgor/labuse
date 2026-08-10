import { useQuery } from '@tanstack/react-query'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useRef, useState } from 'react'
import { getCommunes, getFiche, getMapLayer, getParcelsGeojson, getRenouvGeojson, getTilesMeta, parcelAt } from '../../lib/api'
import { ALL_TIER_META, CINQUANTE_PAS_COLOR, EQUIP_META, ZONE_FAM_META, ZONE_FAM_ORDER } from '../../lib/status'
import { TOKENS } from '../../lib/tokens'
import { fmtArea, fmtDistance, haversine, pathLength, polygonArea, roughCentroid, type LngLat } from '../../lib/geo'
import { useApp, type Filters, type MapTool } from '../../store/useApp'
import { BASEMAP_SOURCES } from './basemaps'
import { Legend } from './Legend'
import { MapToolbar } from './MapToolbar'
import { Loading } from '../Loading'

// ── Fonds de plan : registre PARTAGÉ (carte principale + comparateur swipe). Voir ./basemaps.

const STYLE: maplibregl.StyleSpecification = {
  version: 8,
  // M6.1 : hôte glyphs CORRIGÉ — l'ancien (basemaps.cartocdn.com/gl/<style>/…) répond 404
  // sans en-têtes CORS : AUCUN calque symbol ne rendait (étiquettes de zone, pastilles #rang
  // M5.1). Le bon endpoint vient du style.json Carto ; vérifié 200 + Access-Control-Allow-Origin.
  glyphs: 'https://tiles.basemaps.cartocdn.com/fonts/{fontstack}/{range}.pbf',
  sources: {},
  layers: [{ id: 'bg', type: 'background', paint: { 'background-color': '#060A08' } }],
}

// Correctif M5 (verdict effectif) : la couleur EST le verdict sur la carte — étage 0 prime
// (écartée quasi invisible, inchangé), puis tier v2 quand un run existe (palette TIER_V2_META,
// cf. lib/status.ts). M48 (F4) : le repli `status` (matrice v1 morte) est RETIRÉ — le MVT ne bake
// plus matrice_statut et le GeoJSON l'avait déjà supprimé (M37) ; sans tier v2 → défaut neutre.
// `etage0` est bool en GeoJSON et int (0/1) en MVT → to-number.
const LEGACY_COLOR = '#39463F'
const LEGACY_OPACITY = 0.03
const ETAGE0: maplibregl.ExpressionSpecification = ['>=', ['to-number', ['coalesce', ['get', 'etage0'], 0]], 1]
const TIER_V2: maplibregl.ExpressionSpecification = ['coalesce', ['get', 'tier_v2'], '']
// M-Q P2-72 — la palette de remplissage DÉRIVE de lib/status.ts (ALL_TIER_META = 5 tiers v2 + 6
// déclassements), plus de littéraux recopiés qui divergeaient. Deux effets réparés : (1) une
// retouche de palette dans status.ts suit désormais sur la carte ; (2) les 6 tiers de déclassement
// — dans le filtre par défaut « tout montrer » (M30) — sont peints en TERRE (TIER_DECLASSE_META
// #8C7468) au lieu de tomber sur le gris de fond (invisibles alors que la liste les colore).
// Le patron est celui de ZONE_FAM_COLOR ci-dessous.
// Seule exception GRAVÉE : le tier v2 'ecartee' suit la DOCTRINE du verdict d'en-tête (écartée =
// braise #E8695A, cf. verdictMeta) et partage la teinte d'exclusion de l'étage 0 — pas le gris de
// TIER_V2_META.ecartee. De toute façon quasi éteint (opacité 0.04), color secondaire.
const ECARTEE_COLOR = '#E8695A'
const STATUS_COLOR: maplibregl.ExpressionSpecification = [
  'case', ETAGE0, ECARTEE_COLOR,
  ['match', TIER_V2,
    ...Object.entries(ALL_TIER_META).flatMap(([k, m]) => [k, k === 'ecartee' ? ECARTEE_COLOR : m.color]),
    LEGACY_COLOR],
] as unknown as maplibregl.ExpressionSpecification
// Opacité PAR DÉFAUT (carte non filtrée) : les tiers servables ressortent, les autres restent
// atténués — inchangé. Les déclassements héritent de l'opacité d'écartée (0.04, quasi éteints par
// défaut) ; ils deviennent PLEINEMENT visibles dès qu'on les FILTRE (l'effet plus bas force alors
// fill-opacity à 0,72). Table dérivée d'ALL_TIER_META : aucun tier ne peut retomber muet.
const TIER_OPACITY: Record<string, number> = {
  brulante: 0.95, chaude: 0.9, reserve_fonciere: 0.55, a_creuser: 0.45, ecartee: 0.04,
}
const DECLASSE_OPACITY = 0.04
const STATUS_OPACITY: maplibregl.ExpressionSpecification = [
  'case', ETAGE0, 0.04,
  ['match', TIER_V2,
    ...Object.keys(ALL_TIER_META).flatMap((k) => [k, TIER_OPACITY[k] ?? DECLASSE_OPACITY]),
    LEGACY_OPACITY],
] as unknown as maplibregl.ExpressionSpecification
// liseré des promues : pipeline v2 (brûlante/chaude, hors étage 0). M48 (F4) : la branche de repli
// `status` (matrice morte) est retirée — le liseré suit le tier v2 servi.
const PROMUES_FILTER: maplibregl.FilterSpecification = [
  'all', ['in', TIER_V2, ['literal', ['brulante', 'chaude']]], ['!', ETAGE0],
] as unknown as maplibregl.FilterSpecification

// M6.1 item 1 — couche « Zonage PLU (parcelles) » : le REMPLISSAGE passe en couleur par
// famille (palette ZONE_FAM_META, distincte du verdict v2). Hors zonage GPU (zone_fam
// null) : trame neutre quasi éteinte — on ne peint pas ce qu'on ne sait pas.
const ZONE_FAM_COLOR: maplibregl.ExpressionSpecification = [
  'match', ['coalesce', ['get', 'zone_fam'], ''],
  ...ZONE_FAM_ORDER.flatMap((f) => [f as string, ZONE_FAM_META[f].color]),
  '#39463F',
] as unknown as maplibregl.ExpressionSpecification
const ZONE_FAM_OPACITY: maplibregl.ExpressionSpecification = [
  'case', ['==', ['coalesce', ['get', 'zone_fam'], ''], ''], 0.06, 0.55,
]

// tier v2 EFFECTIF en expression MapLibre (même règle que effectiveTier côté lib) :
// étage 0 → 'ecartee', sinon tier_v2 (les tuiles/geojson d'avant run v2 → chaîne vide)
const EFFECTIVE_TIER: maplibregl.ExpressionSpecification = ['case', ETAGE0, 'ecartee', TIER_V2]

function toExpr(f: Filters): maplibregl.FilterSpecification {
  const c: maplibregl.ExpressionSpecification[] = []
  if (f.tiers.length) c.push(['in', EFFECTIVE_TIER, ['literal', f.tiers]])
  if (f.scoreMin != null) c.push(['>=', ['coalesce', ['get', 'q_score'], 0], f.scoreMin])
  if (f.surfaceMin != null) c.push(['>=', ['coalesce', ['get', 'surface_m2'], 0], f.surfaceMin])
  if (f.surfaceMax != null) c.push(['<=', ['coalesce', ['get', 'surface_m2'], 0], f.surfaceMax])
  if (f.sdpMin != null) c.push(['>=', ['coalesce', ['get', 'sdp_residuelle_m2'], -1], f.sdpMin])
  if (f.evenement) c.push(['==', ['get', 'evenement'], 'rouge'])
  if (f.veille) c.push(['==', ['coalesce', ['get', 'veille'], false], true])
  if (f.horsCopro) c.push(['!=', ['coalesce', ['get', 'copro_v2'], false], true])
  if (f.flags.length) c.push(['any', ...f.flags.map((fl) => ['in', fl, ['get', 'flags']] as maplibregl.ExpressionSpecification)])
  if (f.communes.length) c.push(['in', ['get', 'commune'], ['literal', f.communes]])
  return ['all', ...c] as maplibregl.FilterSpecification
}

const SP_BOUNDS: [number, number, number, number] = [55.21, -21.14, 55.35, -20.97]
const ILE_BOUNDS: [number, number, number, number] = [55.20, -21.42, 55.87, -20.85]
const EMPTY_FC = { type: 'FeatureCollection', features: [] } as const

// Item 11 (UX V1) : padding de fitBounds BORNÉ au canvas — 40 px fixes déclenchaient
// « Map cannot fit within canvas » au boot 375 (le panneau ne laissait presque rien à la
// carte). Jamais plus d'un dixième de la plus petite dimension, plancher 8 px.
const fitPadding = (w: number, h: number) => Math.max(8, Math.min(40, Math.floor(Math.min(w, h) / 10)))

const OVERLAYS = {
  zonage: {
    paint: {
      'fill-color': ['case',
        ['in', ['slice', ['upcase', ['coalesce', ['get', 'subtype'], '']], 0, 1], ['literal', ['U']]],
        '#5CE6A1', '#8a6b3f'] as unknown as maplibregl.ExpressionSpecification,
      'fill-opacity': 0.10,
    },
  },
  ppr: { paint: { 'fill-color': '#E8695A', 'fill-opacity': 0.14 } },
  // P10 (dernière passe) : Parc national en MARRON/terre (#8B5A2B) — distinct du menthe des
  // statuts et du vert-clair d'avant qui « envahissait ». Lisible sur ortho ET fond sombre.
  parc: { paint: { 'fill-color': '#8B5A2B', 'fill-opacity': 0.22 } },
  // M55-A-bis : l'ancien bleu pâle (#8FB4F0 @ 0.16) se noyait dans le Carto sombre ET collidait
  // avec l'icône police (#8FB4F0) et la bande bleue déjà prise (AU #4C7DF0, réserve #6FA8DC,
  // 50 pas #4CC3E8). Chartreuse/lime = le seul creux franc de la palette (or ~45°, verts ~148°),
  // tranche fort sur fond sombre, hors du violet RÉSERVÉ aux résultats de recherche.
  anru: { paint: { 'fill-color': '#C6E82E', 'fill-opacity': 0.30 } },
} as const
const PARC_LINE = '#7A4A1E'   // liseré marron foncé — borne nette du Parc

//: ÉQUIPEMENTS (contexte promotrice, affichage seul) — 7 catégories, pictogramme + pastille.
// Point 13 : un SYMBOLE parlant par type d'équipement. La META est partagée (lib/status.ts) :
// même source pour la légende (Legend.tsx) et le rendu carte. Émoji rendu via canvas → addImage
// (aucune lib ; repli = la pastille colorée + la légende si l'OS n'a pas la police émoji).
const EQUIP_CATS = EQUIP_META.map((e) => e.key)
// M55-A item 4 : libellé CLIENT d'une catégorie d'équipement (« École », « Commerce »…) —
// la même source que la légende (EQUIP_META), pour ne jamais exposer la clé technique au clic.
const EQUIP_LABEL: Record<string, string> = Object.fromEntries(EQUIP_META.map((e) => [e.key, e.label]))

// M55-A item 4 : centroïde (approx) de la parcelle SÉLECTIONNÉE, si elle est rendue à l'écran —
// pour afficher « à ~N m de la parcelle sélectionnée » dans la bulle d'un équipement. Renvoie
// null hors sélection / hors champ : la bulle tombe alors proprement sur nom + catégorie seuls.
function selectedParcelCentroid(m: maplibregl.Map): LngLat | null {
  const sel = useApp.getState().selectedIdu
  if (!sel) return null
  const lids = ['parcels-fill', 'ile-fill'].filter((l) => m.getLayer(l))
  if (!lids.length) return null
  const feats = m.queryRenderedFeatures({ layers: lids, filter: ['==', ['get', 'idu'], sel] as never })
  return feats[0] ? roughCentroid(feats[0].geometry) : null
}

function makeEquipIcons(m: maplibregl.Map) {
  const S = 46
  for (const { key, emoji, color } of EQUIP_META) {
    if (m.hasImage(`equip-${key}`)) continue
    const cv = document.createElement('canvas')
    cv.width = cv.height = S
    const ctx = cv.getContext('2d')
    if (!ctx) continue
    ctx.beginPath(); ctx.arc(S / 2, S / 2, S / 2 - 3, 0, Math.PI * 2)
    ctx.fillStyle = color; ctx.globalAlpha = 0.95; ctx.fill()
    ctx.globalAlpha = 1; ctx.lineWidth = 2; ctx.strokeStyle = '#06130C'; ctx.stroke()
    ctx.font = `${Math.round(S * 0.5)}px "Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",system-ui`
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
    ctx.fillText(emoji, S / 2, S / 2 + 1)
    m.addImage(`equip-${key}`, ctx.getImageData(0, 0, S, S), { pixelRatio: 2 })
  }
}

// M6.1 item 2 : une géométrie de la collection touche-t-elle la bbox de la commune ?
// Test sommet-dans-bbox, suffisant pour le toast « commune sans littoral » (les bandes des
// 50 pas sont étroites et longent le rivage — pas besoin d'intersection géométrique fine).
function fcTouchesBbox(fc: { features: { geometry: unknown }[] },
                       bbox: (number | null)[]): boolean {
  const [minX, minY, maxX, maxY] = bbox as number[]
  const touch = (c: unknown): boolean => Array.isArray(c) && (
    typeof c[0] === 'number'
      ? c[0] >= minX && c[0] <= maxX && (c[1] as number) >= minY && (c[1] as number) <= maxY
      : (c as unknown[]).some(touch))
  return fc.features.some((f) => touch((f.geometry as { coordinates?: unknown })?.coordinates))
}

/** Machine à mesurer : points cliqués + rendu geojson + lecture (distance/surface/alti/zone). */
interface Measure {
  pts: LngLat[]
  alti: { pt: LngLat; z: number } | null
}

export function MapView() {
  const ref = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map | null>(null)
  const ready = useRef(false)
  const [mapReady, setMapReady] = useState(false) // state : re-déclenche les effets APRÈS le load (remontage CRM→cartes)
  const { selectedIdu, select, filters, layers, basemap, orthoYear, terrain3d, tool, setTool, zone, setZone, moduleMap, flyTo, setFlyTo, commune, verdict, iaRestitution, module } = useApp()
  const ile = commune == null
  const toolRef = useRef<MapTool | null>(null)
  toolRef.current = tool
  const [measure, setMeasure] = useState<Measure>({ pts: [], alti: null })
  const measureRef = useRef(measure)
  measureRef.current = measure
  const labelMarker = useRef<maplibregl.Marker | null>(null)
  const [tilesLoading, setTilesLoading] = useState(false)   // P5 : chargement des tuiles

  // z<10 : les marqueurs communes règnent (bandeau contextuel + labels du fond retirés — C3)
  const [lowZoom, setLowZoom] = useState(false)
  useEffect(() => {
    const m = map.current
    if (!m || !ready.current) return
    const h = () => setLowZoom(m.getZoom() < 10)
    h()
    m.on('zoom', h)
    return () => { m.off('zoom', h) }
  }, [mapReady])

  const geo = useQuery({ queryKey: ['geojson', commune], queryFn: getParcelsGeojson, enabled: !ile })
  const zonage = useQuery({ queryKey: ['layer', 'zonage', commune], queryFn: () => getMapLayer('plu_gpu_zone'), enabled: layers.zonage && !ile })
  const ppr = useQuery({ queryKey: ['layer', 'ppr', commune], queryFn: () => getMapLayer('ppr'), enabled: layers.ppr && !ile })
  // (mode île : zonage/PPR passent par les tuiles MVT overlays — sources posées à l'init)
  // R6 : parc (8 Mo simplifiés, opt-in), ANRU (10 Ko) et équipements (2,3 Mo) servis ÎLE
  const parc = useQuery({ queryKey: ['layer', 'parc', commune], queryFn: () => getMapLayer('parc_national'), enabled: layers.parc })
  const anru = useQuery({ queryKey: ['layer', 'anru', commune], queryFn: () => getMapLayer('anru'), enabled: layers.anru })
  // M55-E : la couche équipements COMPLÈTE (limit 20000 = plafond endpoint ; 15 214 en base,
  // 271 Ko gzippé) — le défaut 6000 tronquait 61 % des marqueurs en mode île (centre de
  // Saint-Denis vide, Hauts couverts : l'ordre des lignes décidait des survivants).
  const equip = useQuery({ queryKey: ['layer', 'equip', commune], queryFn: () => getMapLayer('amenite', 20_000), enabled: layers.equipements })
  // M6.1 item 2 : 50 pas géométriques (163 polygones île, commune NULL → servis partout)
  const cinquantePas = useQuery({ queryKey: ['layer', 'cinquante_pas'], queryFn: () => getMapLayer('cinquante_pas'), enabled: layers.cinquante_pas })
  // M-RENOUV : segment Renouvellement (occupées, potentiel) — OFF par défaut, top rangs servis
  const renouv = useQuery({ queryKey: ['layer', 'renouv', commune], queryFn: getRenouvGeojson, enabled: layers.renouv })
  // M6.1 item 1 : les tuiles île portent-elles zone_fam ? (sinon repli honnête au prochain build)
  const tilesMeta = useQuery({ queryKey: ['tiles-meta'], queryFn: getTilesMeta, staleTime: 60_000, retry: false })
  const communes = useQuery({ queryKey: ['communes'], queryFn: getCommunes })
  // le remplissage zonage n'est appliqué que si la source ACTIVE porte zone_fam :
  // geojson commune = toujours (jointure live) ; tuiles île = au prochain build-mvt
  // M12 C5 : DEUX portes vers cette recoloration — « Zonage PLU (par parcelle) » (avec étiquette
  // au zoom + popup au clic) ET la nouvelle « Colorisation par type de zonage » (lecture
  // d'ensemble, sans clic). L'une OU l'autre allume le remplissage par famille.
  // M55-A (fusion A) : une seule couche parcellaire (`zonage_parcelle`) — elle colore d'emblée
  // toutes les parcelles par famille ET porte l'étiquette (zoom) + le popup (clic).
  const zonageColor = layers.zonage_parcelle
  const zonageFill = zonageColor && (!ile || tilesMeta.data?.zonage_parcelle === true)

  // ───────────────────────── init ─────────────────────────
  useEffect(() => {
    if (!ref.current || map.current) return
    const m = new maplibregl.Map({
      container: ref.current,
      style: STYLE,
      // île par défaut ; une commune restaurée par l'URL cadre directement chez elle (Saint-Paul
      // connu statiquement, les autres via fitBounds dès que /communes répond)
      bounds: useApp.getState().commune == null ? ILE_BOUNDS
        : useApp.getState().commune === 'Saint-Paul' ? SP_BOUNDS : ILE_BOUNDS,
      fitBoundsOptions: { padding: fitPadding(ref.current.clientWidth, ref.current.clientHeight) },
      attributionControl: false,
      maxPitch: 70,
    })
    map.current = m
    // tuiles hors-emprise (océan) : l'IGN répond 400 → bruit inévitable, avalé ici pour que la
    // console ne montre que les VRAIES erreurs (règle d'inspection : zéro ligne rouge parasite)
    m.on('error', (e) => {
      const msg = String((e as { error?: Error }).error?.message ?? '')
      if (/AJAXError|40[04]/.test(msg)) return
      console.error(e.error ?? e)
    })
    m.on('load', () => {
      // fonds de plan (tous chargés, visibilité pilotée)
      for (const [id, src] of Object.entries(BASEMAP_SOURCES)) {
        m.addSource(id, { type: 'raster', tiles: src.tiles, tileSize: 256, attribution: src.attribution, ...(src.maxzoom ? { maxzoom: src.maxzoom } : {}) })
        m.addLayer({ id, type: 'raster', source: id, layout: { visibility: id === 'bm-carto' ? 'visible' : 'none' },
          paint: { 'raster-opacity': id === 'bm-carto' ? 0.55 : 1 } })
      }
      // MNT (relief 3D) — terrarium AWS (libre)
      m.addSource('dem', { type: 'raster-dem', encoding: 'terrarium', tileSize: 256, maxzoom: 13,
        tiles: ['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'] })

      m.addSource('parcels', { type: 'geojson', data: EMPTY_FC as never, promoteId: 'idu' })
      for (const k of Object.keys(OVERLAYS)) m.addSource(`ov-${k}`, { type: 'geojson', data: EMPTY_FC as never })
      for (const [k, o] of Object.entries(OVERLAYS)) {
        m.addLayer({ id: `ov-${k}`, type: 'fill', source: `ov-${k}`, layout: { visibility: 'none' }, paint: o.paint as never })
      }
      // P10 : liseré marron du Parc national (borne nette)
      m.addLayer({ id: 'ov-parc-line', type: 'line', source: 'ov-parc', layout: { visibility: 'none' },
        paint: { 'line-color': PARC_LINE, 'line-width': 1.2, 'line-opacity': 0.7 } })
      // M6.1 item 2 : 50 pas géométriques — remplissage léger + CONTOUR CÔTIER tireté
      // (style distinct : bande littorale, pas une couche de zonage pleine)
      m.addSource('ov-50pas', { type: 'geojson', data: EMPTY_FC as never })
      m.addLayer({ id: 'ov-50pas', type: 'fill', source: 'ov-50pas', layout: { visibility: 'none' },
        paint: { 'fill-color': CINQUANTE_PAS_COLOR, 'fill-opacity': 0.16 } })
      m.addLayer({ id: 'ov-50pas-line', type: 'line', source: 'ov-50pas', layout: { visibility: 'none' },
        paint: { 'line-color': CINQUANTE_PAS_COLOR, 'line-width': 1.6, 'line-dasharray': [2, 1.4], 'line-opacity': 0.9 } })
      // M-RENOUV : segment Renouvellement — CUIVRE (token dédié), remplissage + contour fin.
      // Parcelles OCCUPÉES à potentiel : style volontairement distinct des tiers (ni vert ni violet).
      m.addSource('ov-renouv', { type: 'geojson', data: EMPTY_FC as never })
      m.addLayer({ id: 'ov-renouv', type: 'fill', source: 'ov-renouv', layout: { visibility: 'none' },
        paint: { 'fill-color': TOKENS.renouv, 'fill-opacity': 0.38 } })
      m.addLayer({ id: 'ov-renouv-line', type: 'line', source: 'ov-renouv', layout: { visibility: 'none' },
        paint: { 'line-color': TOKENS.renouv, 'line-width': 1.1, 'line-opacity': 0.85 } })
      // P11 : limites communales OFFICIELLES (geo.api.gouv 974) — ligne verte de la charte
      m.addSource('communes-bounds', { type: 'geojson', data: `${(import.meta as unknown as { env: { BASE_URL: string } }).env.BASE_URL}communes974.geojson` })
      m.addLayer({ id: 'communes-bounds', type: 'line', source: 'communes-bounds', layout: { visibility: 'none' },
        paint: { 'line-color': '#5CE6A1', 'line-width': ['interpolate', ['linear'], ['zoom'], 8, 1.1, 13, 1.8],
                 'line-opacity': 0.55 } })
      m.addLayer({ id: 'parcels-fill', type: 'fill', source: 'parcels', paint: { 'fill-color': STATUS_COLOR, 'fill-opacity': STATUS_OPACITY } })
      // contours : promues (statut) OU toutes (couche « limites parcelles »)
      m.addLayer({ id: 'parcels-limites', type: 'line', source: 'parcels', layout: { visibility: 'none' },
        paint: { 'line-color': '#8FA69A', 'line-width': 0.3, 'line-opacity': 0.4 } })
      m.addLayer({ id: 'parcels-line', type: 'line', source: 'parcels', filter: PROMUES_FILTER, paint: { 'line-color': STATUS_COLOR, 'line-width': 0.6, 'line-opacity': 0.9 } })
      m.addLayer({ id: 'parcels-sel', type: 'line', source: 'parcels', filter: ['==', ['get', 'idu'], ''], paint: { 'line-color': '#ECF5EF', 'line-width': 2 } })
      // M5.1 — badge carte : liseré braise sur les BRÛLANTES v2 (hors étage 0), et pastille
      // « #rang » sur les opportunités v2 au zoom rapproché (mode commune). Le badge « V nn »
      // v1.3 a disparu : un seul monde visible, le v2.
      m.addLayer({
        id: 'parcels-brulantes', type: 'line', source: 'parcels',
        filter: ['all', ['==', TIER_V2, 'brulante'], ['!', ETAGE0]] as never,
        paint: { 'line-color': '#FF6B35', 'line-width': 1.8, 'line-opacity': 0.95 },
      })
      m.addLayer({
        id: 'parcels-v-badge', type: 'symbol', source: 'parcels', minzoom: 15,
        filter: ['all', ['in', TIER_V2, ['literal', ['brulante', 'chaude']]], ['!', ETAGE0],
                 ['!=', ['coalesce', ['get', 'rang_v2'], -1], -1]] as never,
        layout: {
          'text-field': ['concat', '#', ['to-string', ['get', 'rang_v2']]] as never,
          'text-size': 10, 'text-anchor': 'top', 'text-offset': [0, 0.8], 'text-optional': true,
        },
        paint: { 'text-color': ['case', ['==', TIER_V2, 'brulante'], '#FF8A50', '#E8B44C'] as never,
                 'text-halo-color': '#06130C', 'text-halo-width': 1.2 },
      })
      // M6.1 item 1 : étiquette de la zone PLU PRÉCISE (zone_lib) au zoom ≥ 16 — mode commune
      m.addLayer({
        id: 'parcels-zone-label', type: 'symbol', source: 'parcels', minzoom: 16,
        layout: { visibility: 'none', 'text-field': ['coalesce', ['get', 'zone_lib'], ''] as never,
          'text-size': 11, 'text-optional': true },
        paint: { 'text-color': '#ECF5EF', 'text-halo-color': '#06130C', 'text-halo-width': 1.3 },
      })

      // R6 : overlays zonage/PPR en tuiles MVT pour le mode ÎLE (29 Mo / 88 Mo en GeoJSON)
      m.addSource('ovmvt-zonage', { type: 'vector', minzoom: 8, maxzoom: 15,
        tiles: [`${window.location.origin}/map/tiles/ov/plu_gpu_zone/{z}/{x}/{y}.pbf`] })
      m.addSource('ovmvt-ppr', { type: 'vector', minzoom: 8, maxzoom: 15,
        tiles: [`${window.location.origin}/map/tiles/ov/ppr/{z}/{x}/{y}.pbf`] })
      m.addLayer({ id: 'ovmvt-zonage', type: 'fill', source: 'ovmvt-zonage', 'source-layer': 'plu_gpu_zone',
        layout: { visibility: 'none' }, paint: OVERLAYS.zonage.paint as never })
      m.addLayer({ id: 'ovmvt-ppr', type: 'fill', source: 'ovmvt-ppr', 'source-layer': 'ppr',
        layout: { visibility: 'none' }, paint: OVERLAYS.ppr.paint as never })

      // ── mode ÎLE : calques jumeaux sur tuiles MVT (431k parcelles — le GeoJSON ne tient pas) ──
      m.addSource('parcels-ile', { type: 'vector', minzoom: 9, maxzoom: 15,
        tiles: [`${window.location.origin}/map/tiles/{z}/{x}/{y}.pbf`] })
      const SL = { source: 'parcels-ile', 'source-layer': 'parcels' } as const
      m.addLayer({ id: 'ile-fill', type: 'fill', ...SL, layout: { visibility: 'none' },
        paint: { 'fill-color': STATUS_COLOR, 'fill-opacity': STATUS_OPACITY } })
      m.addLayer({ id: 'ile-limites', type: 'line', ...SL, layout: { visibility: 'none' },
        paint: { 'line-color': '#8FA69A', 'line-width': 0.3, 'line-opacity': 0.4 } })
      m.addLayer({ id: 'ile-line', type: 'line', ...SL, layout: { visibility: 'none' },
        filter: PROMUES_FILTER, paint: { 'line-color': STATUS_COLOR, 'line-width': 0.6, 'line-opacity': 0.9 } })
      m.addLayer({ id: 'ile-sel', type: 'line', ...SL, layout: { visibility: 'none' },
        filter: ['==', ['get', 'idu'], ''], paint: { 'line-color': '#ECF5EF', 'line-width': 2 } })
      // M15 A1 : couche de PICKING de l'outil Assemblage — contours de TOUTES les parcelles,
      // violet et bien visibles, uniquement quand l'outil est actif (sinon la carte outils est
      // quasi vide et on ne voit pas quoi cliquer). Aucun impact hors assemblage.
      m.addLayer({ id: 'ile-pick', type: 'line', ...SL, layout: { visibility: 'none' },
        paint: { 'line-color': '#B497F0', 'line-width': 0.8, 'line-opacity': 0.85 } })
      // M6.1 : étiquette zone PLU en mode île — ne rend que si les tuiles portent zone_lib
      // (prochain build-mvt) ; d'ici là text-field vide = aucun rendu, rien ne casse
      m.addLayer({
        id: 'ile-zone-label', type: 'symbol', ...SL, minzoom: 16,
        layout: { visibility: 'none', 'text-field': ['coalesce', ['get', 'zone_lib'], ''] as never,
          'text-size': 11, 'text-optional': true },
        paint: { 'text-color': '#ECF5EF', 'text-halo-color': '#06130C', 'text-halo-width': 1.3 },
      })

      // mesure (ligne + polygone + points + étiquette)
      m.addSource('measure', { type: 'geojson', data: EMPTY_FC as never })
      m.addLayer({ id: 'measure-fill', type: 'fill', source: 'measure', filter: ['==', ['geometry-type'], 'Polygon'], paint: { 'fill-color': '#5CE6A1', 'fill-opacity': 0.12 } })
      m.addLayer({ id: 'measure-line', type: 'line', source: 'measure', filter: ['in', ['geometry-type'], ['literal', ['LineString', 'Polygon']]], paint: { 'line-color': '#5CE6A1', 'line-width': 2, 'line-dasharray': [2, 1.5] } })
      m.addLayer({ id: 'measure-pts', type: 'circle', source: 'measure', filter: ['==', ['geometry-type'], 'Point'], paint: { 'circle-radius': 3.5, 'circle-color': '#5CE6A1', 'circle-stroke-color': '#06130C', 'circle-stroke-width': 1.5 } })

      // calques MODULE (violet) : surlignage de parcelles + géométries propres (lots, permis)
      m.addSource('module-extra', { type: 'geojson', data: EMPTY_FC as never })
      m.addLayer({ id: 'module-hl', type: 'line', source: 'parcels', filter: ['==', ['get', 'idu'], ''],
        paint: { 'line-color': '#B497F0', 'line-width': 1.6, 'line-opacity': 0.95 } })
      m.addLayer({ id: 'ile-hl', type: 'line', source: 'parcels-ile', 'source-layer': 'parcels',
        layout: { visibility: 'none' }, filter: ['==', ['get', 'idu'], ''],
        paint: { 'line-color': '#B497F0', 'line-width': 1.6, 'line-opacity': 0.95 } })
      m.addLayer({ id: 'module-lot', type: 'line', source: 'module-extra',
        filter: ['==', ['get', 'kind'], 'lot'],
        paint: { 'line-color': '#B497F0', 'line-width': 1.8, 'line-dasharray': [2, 1.6] } })
      m.addLayer({ id: 'module-pts', type: 'circle', source: 'module-extra',
        filter: ['==', ['get', 'kind'], 'permis'],
        paint: { 'circle-radius': 4, 'circle-color': '#B497F0', 'circle-opacity': 0.85,
                 'circle-stroke-color': '#120d1d', 'circle-stroke-width': 1.2 } })

      // équipements (points OSM, affichage seul) — cercles colorés, plancher z13 (pas
      // d'icônes par milliers à l'écran), clic = nom de l'équipement
      makeEquipIcons(m)
      m.addSource('ov-equip', { type: 'geojson', data: EMPTY_FC as never })
      // M12 C3 — les pastilles d'équipement GROSSISSENT quand on zoome (elles rétrécissaient) :
      // l'ancienne rampe 12→0,32 / 17→0,60 s'aplatissait vite et PLAFONNAIT à z17 ; au zoom
      // rapproché (z18-20, l'échelle de travail sur une parcelle) elles restaient figées à 0,60
      // pendant que tout le reste de la carte grossissait → effet de rétrécissement relatif.
      // Rampe croissante et CONTINUE jusqu'à z20 : plus on approche, plus la pastille est lisible.
      // M14 B2 (QA-63, reprise M13-D3/QA-49) : icônes ×1,5 — rampe M12 (0,30/0,55/0,85/1,3)
      // multipliée par 1,5 → 0,45/0,825/1,275/1,95. Aucune autre taille ne l'écrase (seule
      // définition d'icon-size pour ov-equip ; le bitmap addImage garde son pixelRatio).
      m.addLayer({ id: 'ov-equip', type: 'symbol', source: 'ov-equip', minzoom: 12,
        layout: { visibility: 'none',
                  'icon-image': ['concat', 'equip-', ['get', 'subtype']] as never,
                  'icon-size': ['interpolate', ['linear'], ['zoom'],
                    12, 0.45, 15, 0.825, 17, 1.275, 20, 1.95] as never,
                  'icon-allow-overlap': true } })
      // M55-A item 4 : les équipements RÉAGISSENT au clic — bulle sobre (nom + catégorie CLIENT,
      // et distance à la parcelle sélectionnée si pertinent). `preventDefault()` empêche le clic
      // d'ouvrir AUSSI la fiche de la parcelle sous l'icône (les handlers parcels-fill / clic
      // universel testent `defaultPrevented`) — sinon le geste « paraissait » sans effet propre.
      m.on('click', 'ov-equip', (e) => {
        const ev = e as maplibregl.MapLayerMouseEvent
        const f = ev.features?.[0]
        if (!f) return
        ev.preventDefault()
        const sub = String(f.properties?.subtype ?? '')
        const cat = EQUIP_LABEL[sub] ?? sub
        const nom = f.properties?.name && f.properties.name !== 'null' ? String(f.properties.name) : '(sans nom OSM)'
        const c = selectedParcelCentroid(m)
        const dist = c ? `<div style="color:#5CE6A1;font-size:10px;margin-top:2px">à ~${fmtDistance(haversine([ev.lngLat.lng, ev.lngLat.lat], c))} de la parcelle sélectionnée</div>` : ''
        new maplibregl.Popup({ closeButton: false, className: 'labuse-popup' })
          .setLngLat(ev.lngLat)
          .setHTML(`<div style="background:#0F1A14;border:1px solid #2E6B4F;color:#ECF5EF;font:12px Inter,sans-serif;padding:6px 10px;border-radius:8px">${nom}<div style="color:#8FA69A;font-size:10px">${cat}</div>${dist}</div>`)
          .addTo(m)
      })
      m.on('mouseenter', 'ov-equip', () => { if (!toolRef.current) m.getCanvas().style.cursor = 'pointer' })
      m.on('mouseleave', 'ov-equip', () => { m.getCanvas().style.cursor = toolRef.current ? 'crosshair' : '' })

      // zone dessinée persistante (filtre les résultats)
      m.addSource('zone', { type: 'geojson', data: EMPTY_FC as never })
      m.addLayer({ id: 'zone-fill', type: 'fill', source: 'zone', paint: { 'fill-color': '#5CE6A1', 'fill-opacity': 0.06 } })
      m.addLayer({ id: 'zone-line', type: 'line', source: 'zone', paint: { 'line-color': '#5CE6A1', 'line-width': 1.6, 'line-dasharray': [3, 2] } })

      for (const layerId of ['parcels-fill', 'ile-fill']) {
        m.on('click', layerId, (e) => {
          if (toolRef.current) return // un outil actif consomme le clic
          if ((e as maplibregl.MapLayerMouseEvent).defaultPrevented) return // M55-A : clic équipement déjà traité
          const f = (e as maplibregl.MapLayerMouseEvent).features?.[0]
          if (!f) return
          // G1 (M12) : une feature sans `idu` (clic hors-parcelle, tuile en cours de chargement,
          // trame promues-only) ne doit JAMAIS ouvrir une fiche « undefined » qui échoue en faux
          // « serveur injoignable ». On abandonne silencieusement — le clic universel plus bas
          // (parcelAt) prendra le relais si un point→parcelle est résoluble.
          const rawIdu = f.properties?.idu
          if (rawIdu == null || rawIdu === '' || rawIdu === 'undefined') return
          const idu = String(rawIdu)
          const st = useApp.getState()
          if (st.module === 'assemblage') {              // M16 : le clic compose l'assiette
            st.setMsel(st.msel.includes(idu) ? st.msel.filter((x) => x !== idu) : [...st.msel, idu])
            return
          }
          // M6.1 : couche zonage active → la zone PLU précise s'affiche AUSSI au clic
          // (popup éphémère, même gabarit que les équipements) — la fiche s'ouvre normalement
          if (st.layers.zonage_parcelle) {
            const lib = f.properties?.zone_lib && f.properties.zone_lib !== 'null' ? String(f.properties.zone_lib) : null
            const fam = f.properties?.zone_fam ? String(f.properties.zone_fam) : null
            if (lib || fam) {
              new maplibregl.Popup({ closeButton: false, className: 'labuse-popup' })
                .setLngLat((e as maplibregl.MapLayerMouseEvent).lngLat)
                .setHTML(`<div style="background:#0F1A14;border:1px solid #2E6B4F;color:#ECF5EF;font:12px Inter,sans-serif;padding:6px 10px;border-radius:8px">Zone ${lib ?? fam}<div style="color:#8FA69A;font-size:10px">zonage PLU (GPU)${fam && lib ? ` · famille ${fam}` : ''}</div></div>`)
                .addTo(m)
            }
          }
          select(idu)
        })
        m.on('mouseenter', layerId, () => { if (!toolRef.current) m.getCanvas().style.cursor = 'pointer' })
        m.on('mouseleave', layerId, () => { m.getCanvas().style.cursor = toolRef.current ? 'crosshair' : '' })
      }
      // C7 (décision Vic) : CLIC UNIVERSEL — si aucune feature parcelle vectorielle sous le
      // curseur (trame raster/limites, zoom promues-only…), le serveur résout point→parcelle.
      m.on('click', (e) => {
        if (toolRef.current) return
        if (e.defaultPrevented) return // M55-A : un équipement a capté ce clic (bulle affichée)
        const hits = m.queryRenderedFeatures(e.point, { layers: ['parcels-fill', 'ile-fill'].filter((l) => !!m.getLayer(l)) })
        if (hits.length > 0) return   // le handler de calque a déjà ouvert la fiche
        parcelAt(e.lngLat.lng, e.lngLat.lat).then((r) => {
          if (r.idu) select(r.idu)
        }).catch(() => undefined)
      })

      // P5 (dernière passe) : indicateur de chargement des TUILES (île MVT + fonds) — la carte
      // ne semble jamais figée pendant le fetch. `idle` = tout rendu, plus rien en attente.
      m.on('dataloading', () => setTilesLoading(true))
      m.on('idle', () => setTilesLoading(false))

      ready.current = true
      setMapReady(true)
      ;(window as unknown as Record<string, unknown>).__labuse_map = m // hook QA (ping sémantique)
      m.fire('labuse:ready' as never)
    })
    return () => { m.remove(); map.current = null; ready.current = false }
  }, [select])

  // ───────────────────────── données ─────────────────────────
  useEffect(() => {
    const m = map.current
    if (m && ready.current && geo.data) (m.getSource('parcels') as maplibregl.GeoJSONSource | undefined)?.setData(geo.data as never)
  }, [geo.data, geo.dataUpdatedAt, mapReady])

  useEffect(() => {
    const m = map.current
    if (!m || !ready.current) return
    const pairs: [string, typeof zonage][] = [['zonage', zonage], ['ppr', ppr], ['parc', parc], ['anru', anru]]
    for (const [k, qy] of pairs) if (qy.data) (m.getSource(`ov-${k}`) as maplibregl.GeoJSONSource | undefined)?.setData(qy.data as never)
    if (equip.data) {
      const feats = equip.data.features.filter((f) => EQUIP_CATS.includes((f.properties as { subtype?: string }).subtype as never))
      ;(m.getSource('ov-equip') as maplibregl.GeoJSONSource | undefined)?.setData({ type: 'FeatureCollection', features: feats } as never)
      // M55-E : plafond endpoint (20 000) ATTEINT → la couche est tronquée, on le DIT (règle
      // no-silent-caps — un marqueur manquant sans avertissement est un mensonge visuel).
      if (layers.equipements && equip.data.features.length >= 20_000) {
        useApp.getState().setToast('Équipements : plus de 20 000 objets — l\u2019affichage est tronqué au plafond du serveur.')
      }
    }
    // M6 2a (§1.6, anomalie A3) : couche activée mais VIDE sur le périmètre → le dire,
    // jamais un silence (l'utilisateur ne sait pas si la couche est vide ou cassée).
    if (layers.anru && anru.data && anru.data.features.length === 0) {
      useApp.getState().setToast(
        commune ? `Aucun périmètre ANRU (NPNRU) sur ${commune} — 6 communes en portent un.`
                : 'Aucun périmètre ANRU (NPNRU) sur ce cadrage.')
    }
    // M6.1 item 2 : 50 pas — servis île entière (commune NULL en base) ; en mode commune,
    // même pattern honnête que l'ANRU : commune SANS littoral → toast, jamais un silence.
    // M-RENOUV : calque Renouvellement — si le serveur tronque (top rangs), le DIRE (toast),
    // jamais un « tout » silencieux (règle no-silent-caps).
    if (renouv.data) {
      ;(m.getSource('ov-renouv') as maplibregl.GeoJSONSource | undefined)?.setData(renouv.data as never)
      if (layers.renouv && renouv.data.total > renouv.data.servis) {
        useApp.getState().setToast(
          `Renouvellement : ${renouv.data.servis.toLocaleString('fr-FR')} parcelles affichées sur ` +
          `${renouv.data.total.toLocaleString('fr-FR')} (meilleurs rangs)${commune ? ` — ${commune}` : ' — île entière'}.`)
      }
    }
    if (cinquantePas.data) {
      ;(m.getSource('ov-50pas') as maplibregl.GeoJSONSource | undefined)?.setData(cinquantePas.data as never)
      if (layers.cinquante_pas && commune) {
        const bbox = communes.data?.find((c) => c.commune === commune)?.bbox
        if (bbox && bbox[0] != null && !fcTouchesBbox(cinquantePas.data, bbox)) {
          useApp.getState().setToast(
            `Aucune bande des 50 pas géométriques sur ${commune} — commune sans littoral.`)
        }
      }
    }
  }, [zonage.data, ppr.data, parc.data, anru.data, equip.data, cinquantePas.data, renouv.data, layers.cinquante_pas, layers.renouv, commune, communes.data, mapReady])

  // M6.1 item 1 (repli île) : la couche zonage est demandée mais les tuiles servies ne portent
  // pas encore zone_fam → le dire franchement (elle arrivera au prochain `labuse build-mvt`).
  useEffect(() => {
    if (ile && layers.zonage_parcelle && tilesMeta.data && !tilesMeta.data.zonage_parcelle) {
      useApp.getState().setToast(
        'Colorisation par zonage en mode île : disponible au prochain build de tuiles — choisissez une commune pour l’utiliser dès maintenant.')
    }
  }, [ile, layers.zonage_parcelle, tilesMeta.data])

  // M55-A (fusion A) : Saint-Philippe n'a PAS de PLU numérisé (0 zone GPU, 9/4162 parcelles calées) —
  // c'est une commune au RNU. Quand une couche de zonage est active chez elle, le dire franchement
  // plutôt qu'afficher un fond vide muet (même règle « no-silent » que l'ANRU / les 50 pas).
  useEffect(() => {
    if (commune === 'Saint-Philippe' && (layers.zonage_parcelle || layers.zonage)) {
      useApp.getState().setToast('Saint-Philippe : commune au RNU — pas de zonage PLU.')
    }
  }, [commune, layers.zonage_parcelle, layers.zonage])

  // M55-B point 6 : les équipements ne se peignent qu'à partir du zoom 12 (sinon 15 000 icônes
  // illisibles). Couche active mais vue trop large → le DIRE (« zoomez »), jamais un silence.
  useEffect(() => {
    const m = map.current
    if (!m || !ready.current || !layers.equipements) return
    if (m.getZoom() < 12) {
      useApp.getState().setToast('Zoomez pour afficher les équipements (visibles au niveau « rue », dès le zoom d’une commune).')
    }
  }, [layers.equipements, mapReady])

  // ───────────────────────── fond de plan + relief ─────────────────────────
  useEffect(() => {
    const m = map.current
    if (!m || !ready.current) return
    const active = basemap === 'dark' ? 'bm-carto'
      : basemap === 'plan' ? 'bm-plan'
      : orthoYear === '2000' ? 'bm-ortho-2000' : orthoYear === '1950' ? 'bm-ortho-1950' : 'bm-ortho-now'
    for (const id of Object.keys(BASEMAP_SOURCES)) {
      if (m.getLayer(id)) m.setLayoutProperty(id, 'visibility', id === active ? 'visible' : 'none')
    }
    // sur ortho/plan (fonds clairs ou photo), les écartées quasi invisibles gênent moins que le voile sombre
    // M6.1 : couche zonage parcelle active → NE PAS écraser son opacité dédiée
    if (m.getLayer('parcels-fill') && !zonageFill) {
      m.setPaintProperty('parcels-fill', 'fill-opacity', filters.tiers.length === 0 ? STATUS_OPACITY : 0.72)
      m.setPaintProperty('ile-fill', 'fill-opacity', filters.tiers.length === 0 ? STATUS_OPACITY : 0.72)
    }
  }, [basemap, orthoYear, filters.tiers, mapReady, ile, lowZoom, zonageFill])

  useEffect(() => {
    const m = map.current
    if (!m || !ready.current) return
    if (terrain3d) {
      m.setTerrain({ source: 'dem', exaggeration: 1.35 })
      if (m.getPitch() < 20) m.easeTo({ pitch: 55, duration: 800 })
    } else {
      m.setTerrain(null)
      m.easeTo({ pitch: 0, duration: 600 })
    }
  }, [terrain3d])

  // ───────────────────────── couches / filtres / mode ─────────────────────────
  useEffect(() => {
    const m = map.current
    if (!m || !ready.current || !m.getLayer('parcels-fill')) return
    const vis = (on: boolean) => (on ? 'visible' : 'none')
    // deux jeux de calques (GeoJSON commune / MVT île) — un seul visible à la fois
    m.setLayoutProperty('parcels-fill', 'visibility', vis(layers.parcelles && !ile))
    m.setLayoutProperty('parcels-line', 'visibility', vis(layers.parcelles && !ile))
    m.setLayoutProperty('parcels-limites', 'visibility', vis(layers.limites && !ile))
    m.setLayoutProperty('ile-fill', 'visibility', vis(layers.parcelles && ile))
    m.setLayoutProperty('ile-line', 'visibility', vis(layers.parcelles && ile))
    m.setLayoutProperty('ile-limites', 'visibility', vis(layers.limites && ile))
    m.setLayoutProperty('ile-sel', 'visibility', vis(ile))
    m.setLayoutProperty('ile-hl', 'visibility', vis(ile))
    // M15 A1 : couche de picking Assemblage — contours violets visibles seulement quand l'outil est actif
    m.setLayoutProperty('ile-pick', 'visibility', vis(module === 'assemblage' && ile))
    m.setLayoutProperty('ov-zonage', 'visibility', vis(layers.zonage && !ile))
    m.setLayoutProperty('ov-ppr', 'visibility', vis(layers.ppr && !ile))
    m.setLayoutProperty('ovmvt-zonage', 'visibility', vis(layers.zonage && ile))
    m.setLayoutProperty('ovmvt-ppr', 'visibility', vis(layers.ppr && ile))
    m.setLayoutProperty('ov-parc', 'visibility', vis(layers.parc))
    m.setLayoutProperty('ov-parc-line', 'visibility', vis(layers.parc))
    m.setLayoutProperty('ov-anru', 'visibility', vis(layers.anru))
    // M6.1 item 2 : 50 pas géométriques (remplissage + contour tireté) — servis île entière
    m.setLayoutProperty('ov-50pas', 'visibility', vis(layers.cinquante_pas))
    m.setLayoutProperty('ov-50pas-line', 'visibility', vis(layers.cinquante_pas))
    // M-RENOUV : segment Renouvellement (cuivre) — OFF par défaut
    m.setLayoutProperty('ov-renouv', 'visibility', vis(layers.renouv))
    m.setLayoutProperty('ov-renouv-line', 'visibility', vis(layers.renouv))
    // M6.1 item 1 : étiquette de zone PRÉCISE (zone_lib, z ≥ 16) — suit la couche zonage
    m.setLayoutProperty('parcels-zone-label', 'visibility', vis(layers.zonage_parcelle && !ile))
    m.setLayoutProperty('ile-zone-label', 'visibility', vis(layers.zonage_parcelle && ile))
    m.setLayoutProperty('ov-equip', 'visibility', vis(layers.equipements))
    m.setLayoutProperty('communes-bounds', 'visibility', vis(layers.communes))   // P11
    const expr = toExpr(filters)
    for (const fill of ['parcels-fill', 'ile-fill']) {
      m.setFilter(fill, expr)
      // M6.1 item 1 : la couche « Zonage PLU (parcelles) » PRIME sur le verdict — le
      // remplissage devient la famille de zone (palette dédiée), verdict rallumé au toggle off.
      // `zonageFill` déjà conditionné : geojson commune toujours, tuiles île si zone_fam servie.
      if (zonageFill) {
        m.setPaintProperty(fill, 'fill-color', ZONE_FAM_COLOR)
        m.setPaintProperty(fill, 'fill-opacity', ZONE_FAM_OPACITY)
      } else if (!verdict) {
        // R1 : VERDICT ÉTEINT = trame cadastrale NEUTRE (le langage promoteur), aucune couleur
        m.setPaintProperty(fill, 'fill-color', '#22302A')
        m.setPaintProperty(fill, 'fill-opacity', 0.28)
      } else {
        m.setPaintProperty(fill, 'fill-color', STATUS_COLOR)
        m.setPaintProperty(fill, 'fill-opacity', filters.tiers.length === 0 ? STATUS_OPACITY : 0.72)
      }
    }
    // liseré des promues : uniquement verdict allumé
    m.setLayoutProperty('parcels-line', 'visibility', vis(layers.parcelles && !ile && verdict))
    m.setLayoutProperty('ile-line', 'visibility', vis(layers.parcelles && ile && verdict))
    m.setFilter('parcels-line', ['all', PROMUES_FILTER, expr] as maplibregl.FilterSpecification)
    m.setFilter('ile-line', ['all', PROMUES_FILTER, expr] as maplibregl.FilterSpecification)
    // M5.1 : badges carte v2 (liseré brûlantes v2 + pastille #rang) — verdict allumé, mode commune
    for (const id of ['parcels-brulantes', 'parcels-v-badge']) {
      if (m.getLayer(id)) m.setLayoutProperty(id, 'visibility', vis(!ile && verdict))
    }
  }, [filters, layers, geo.dataUpdatedAt, mapReady, ile, verdict, zonageFill, module])

  // P3 (dernière passe) — RÉSULTATS DE RECHERCHE EN VIOLET : quand une recherche/projet est
  // active (restitution posée), les parcelles-résultats (promues filtrées) reçoivent un CONTOUR
  // VIOLET épais — le remplissage de STATUT est conservé (on voit résultat ET qualité). Sans
  // recherche, le liseré reste couleur de statut (menthe/vert). Distinction immédiate.
  useEffect(() => {
    const m = map.current
    if (!m || !ready.current) return
    const active = !!iaRestitution
    for (const id of ['parcels-line', 'ile-line']) {
      if (!m.getLayer(id)) continue
      m.setPaintProperty(id, 'line-color', active ? '#B497F0' : STATUS_COLOR)
      m.setPaintProperty(id, 'line-width', active ? 2 : 0.6)
      m.setPaintProperty(id, 'line-opacity', active ? 1 : 0.9)
    }
  }, [iaRestitution, mapReady, ile, verdict, filters])

  // ── VAGUE 0 (île) : sous z10 les tuiles parcellaires ne servent rien — l'île raconte où
  // sont les cibles via UN marqueur par commune (nom + chaudes, dimensionné/coloré), cliquable
  // → bascule le sélecteur (fitBounds existant). Marqueurs DOM (pas de dépendance glyphes).
  const aggMarkers = useRef<maplibregl.Marker[]>([])
  useEffect(() => {
    const m = map.current
    if (!m || !ready.current) return
    aggMarkers.current.forEach((mk) => mk.remove())
    aggMarkers.current = []
    if (!ile || !communes.data) return
    const updateVis = () => {
      const show = m.getZoom() < 10
      aggMarkers.current.forEach((mk) => { mk.getElement().style.display = show ? '' : 'none' })
    }
    // anti-chevauchement (côte Nord dense) : décalages pixels manuels, consignés
    const OFFSETS: Record<string, [number, number]> = {
      'Saint-Denis': [-14, -10], 'Sainte-Marie': [16, 8], 'Sainte-Suzanne': [26, -6],
      'Le Port': [-18, -4], 'La Possession': [10, 12],
    }
    for (const c of communes.data) {
      if (!c.bbox || c.bbox[0] == null) continue
      const hot = verdict && c.chaudes > 0   // R1 : sans verdict, les marqueurs restent NEUTRES
      const el = document.createElement('button')
      el.setAttribute('data-commune-marker', c.commune)
      // P8 (dernière passe) : le marqueur mène à la FICHE COMMUNE (contexte), plus « N chaudes »
      // en évidence ; le nombre de chaudes reste en INFO secondaire (survol).
      // M36 Lot A : depuis M35 `c.chaudes` = TIERS du run servi (brûlantes + chaudes) — l'ancienne
      // étiquette « (matrice Q×A) » était devenue FAUSSE. L'échelle thermique est la bonne (R3).
      el.title = verdict && c.chaudes > 0
        ? `${c.commune} — ${c.chaudes} parcelles brûlantes ou chaudes au classement servi · ouvrir la fiche commune`
        : `${c.commune} · ouvrir la fiche commune`
      const name = c.commune.replace(/^(Les|Le|La|L')\s?/, '')
      // A2 (post-revue) : le libellé renvoie à la FICHE COMMUNE (plus de compteur de chaudes visible)
      el.innerHTML = `<span>${name}</span><span style="opacity:.6;font-size:.82em"> · Fiche commune</span>`
      const size = Math.min(13, 10 + (verdict ? Math.log10(Math.max(1, c.chaudes)) * 2 : 0))
      el.style.cssText = `cursor:pointer;white-space:nowrap;border-radius:9999px;padding:2px 9px;` +
        `display:inline-flex;align-items:center;gap:4px;` +
        `font:600 ${size}px Inter,sans-serif;border:1px solid ${hot ? '#2E6B4F' : '#26302B'};` +
        `background:${hot ? 'rgba(9,26,18,.92)' : 'rgba(10,14,12,.85)'};color:${hot ? '#5CE6A1' : '#8FA69A'};` +
        (hot ? 'box-shadow:0 0 10px rgba(92,230,161,.25);' : '')
      // M55-C point 4 (décision Vic 10/08, remplace le comportement « fiche seule ») : cliquer le
      // nom de commune = TROIS effets en un — ouvrir la fiche, caler le périmètre sur la commune
      // (liste/compteurs/filtres suivent) ET recadrer la carte (l'effet de fit sur `commune` s'en
      // charge). `focusCommune` fait les trois d'un coup.
      el.onclick = (e) => { e.stopPropagation(); useApp.getState().focusCommune(c.commune) }
      aggMarkers.current.push(new maplibregl.Marker({ element: el, offset: OFFSETS[c.commune] ?? [0, 0] })
        .setLngLat([(c.bbox[0] + c.bbox[2]) / 2, (c.bbox[1] + c.bbox[3]) / 2]).addTo(m))
    }
    updateVis()
    m.on('zoom', updateVis)
    return () => { m.off('zoom', updateVis); aggMarkers.current.forEach((mk) => mk.remove()); aggMarkers.current = [] }
  }, [ile, communes.data, mapReady, verdict])

  // changement de commune → recadrage sur son emprise (bbox servie par /communes)
  useEffect(() => {
    const m = map.current
    if (!m || !ready.current) return
    const pad = fitPadding(m.getContainer().clientWidth, m.getContainer().clientHeight)
    if (ile) { m.fitBounds(ILE_BOUNDS, { padding: pad, duration: 900 }); return }
    const info = communes.data?.find((c) => c.commune === commune)
    if (info?.bbox) m.fitBounds(info.bbox as [number, number, number, number], { padding: pad, duration: 900 })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [commune, communes.data, mapReady])

  useEffect(() => {
    const m = map.current
    if (!m || !ready.current || !m.getLayer('parcels-sel')) return
    m.setFilter('parcels-sel', ['==', ['get', 'idu'], selectedIdu ?? ''])
    m.setFilter('ile-sel', ['==', ['get', 'idu'], selectedIdu ?? ''])
    // PING SYSTÉMATIQUE : toute sélection (liste, module, CRM, notification) recentre + pulse 2 s
    if (!selectedIdu) return
    const feat = geo.data?.features.find((f) => (f.properties as { idu?: string }).idu === selectedIdu)
    let cancelled = false
    const centroidReady = (c: [number, number] | null) => {
      if (!c || cancelled) return
      m.flyTo({ center: c, zoom: Math.max(m.getZoom(), 16), duration: 800 })
    }
    if (feat) centroidReady(roughCentroid(feat.geometry))
    else {
      // mode île (ou parcelle hors du GeoJSON chargé) : le centroïde vient de la fiche API.
      // CONTRAT (Vic, 07/07) : un clic dans la liste = je VOIS la parcelle pulser, où qu'elle
      // soit — le champ est `coords` [lon, lat] (le fallback lat/lon muet était le bug).
      getFiche(selectedIdu).then((f) => {
        const c = (f as unknown as { coords?: [number, number] }).coords
        if (Array.isArray(c) && c.length === 2) centroidReady([c[0], c[1]])
      }).catch(() => undefined)
    }
    const pingId = geo.data && feat ? 'parcels-ping' : 'ile-ping'
    if (!m.getLayer(pingId)) {
      m.addLayer(pingId === 'parcels-ping'
        ? { id: 'parcels-ping', type: 'line', source: 'parcels',
            filter: ['==', ['get', 'idu'], ''], paint: { 'line-color': '#ECF5EF', 'line-width': 6, 'line-opacity': 0.9, 'line-blur': 3 } }
        : { id: 'ile-ping', type: 'line', source: 'parcels-ile', 'source-layer': 'parcels',
            filter: ['==', ['get', 'idu'], ''], paint: { 'line-color': '#ECF5EF', 'line-width': 6, 'line-opacity': 0.9, 'line-blur': 3 } })
    }
    m.setFilter(pingId, ['==', ['get', 'idu'], selectedIdu])
    let t0: number | null = null
    let raf = 0
    const pulse = (ts: number) => {
      if (t0 == null) t0 = ts
      const dt = (ts - t0) / 1000
      // 3 s : en mode île le vol (800 ms) + le chargement des tuiles à destination doivent
      // laisser un pulse VISIBLE à l'arrivée
      if (dt > 3 || !m.getLayer(pingId)) {
        if (m.getLayer(pingId)) m.setPaintProperty(pingId, 'line-opacity', 0)
        return
      }
      m.setPaintProperty(pingId, 'line-opacity', 0.45 + 0.45 * Math.abs(Math.sin(dt * Math.PI * 2)))
      m.setPaintProperty(pingId, 'line-width', 5 + 4 * Math.abs(Math.sin(dt * Math.PI * 2)))
      raf = requestAnimationFrame(pulse)
    }
    raf = requestAnimationFrame(pulse)
    return () => { cancelAnimationFrame(raf); cancelled = true }
  }, [selectedIdu, geo.data, mapReady])

  // module actif → surlignage + géométries propres (les DEUX jeux de calques)
  useEffect(() => {
    const m = map.current
    if (!m || !ready.current || !m.getLayer('module-hl')) return
    const f = moduleMap.idus.length
      ? (['in', ['get', 'idu'], ['literal', moduleMap.idus.slice(0, 4000)]] as never)
      : (['==', ['get', 'idu'], ''] as never)
    m.setFilter('module-hl', f)
    if (m.getLayer('ile-hl')) m.setFilter('ile-hl', f)
    ;(m.getSource('module-extra') as maplibregl.GeoJSONSource | undefined)?.setData((moduleMap.extra ?? EMPTY_FC) as never)
  }, [moduleMap, mapReady])

  // flyTo demandé (fiche → « 1950 », modules…)
  useEffect(() => {
    if (!flyTo || !map.current) return
    map.current.flyTo({ center: flyTo.center, zoom: flyTo.zoom, duration: 900 })
    setFlyTo(null)
  }, [flyTo, setFlyTo])

  // zone dessinée → tracé persistant sur la carte (le filtre des résultats vit dans la liste)
  useEffect(() => {
    const m = map.current
    if (!m || !ready.current) return
    const data = zone
      ? { type: 'FeatureCollection', features: [{ type: 'Feature', geometry: { type: 'Polygon', coordinates: [[...zone, zone[0]]] }, properties: {} }] }
      : EMPTY_FC
    ;(m.getSource('zone') as maplibregl.GeoJSONSource | undefined)?.setData(data as never)
  }, [zone, mapReady])

  // ───────────────────────── outils de mesure ─────────────────────────
  // rendu du geojson de mesure
  useEffect(() => {
    const m = map.current
    if (!m || !ready.current) return
    const feats: object[] = measure.pts.map((p) => ({ type: 'Feature', geometry: { type: 'Point', coordinates: p }, properties: {} }))
    if (measure.pts.length >= 2) {
      const t = toolRef.current
      if ((t === 'surface' || t === 'zone') && measure.pts.length >= 3) {
        feats.push({ type: 'Feature', geometry: { type: 'Polygon', coordinates: [[...measure.pts, measure.pts[0]]] },
          properties: { label: t === 'surface' ? fmtArea(polygonArea(measure.pts)) : '' } })
      } else {
        feats.push({ type: 'Feature', geometry: { type: 'LineString', coordinates: measure.pts },
          properties: { label: t === 'distance' ? fmtDistance(pathLength(measure.pts)) : '' } })
      }
    }
    if (measure.alti) {
      feats.push({ type: 'Feature', geometry: { type: 'Point', coordinates: measure.alti.pt },
        properties: { label: `${measure.alti.z.toFixed(0)} m` } })
    }
    ;(m.getSource('measure') as maplibregl.GeoJSONSource | undefined)?.setData({ type: 'FeatureCollection', features: feats } as never)

    // étiquette de mesure = marker HTML (pas de glyphes carte → pas de dépendance CORS)
    const t = toolRef.current
    const text = t === 'distance' && measure.pts.length >= 2 ? fmtDistance(pathLength(measure.pts))
      : t === 'surface' && measure.pts.length >= 3 ? fmtArea(polygonArea(measure.pts))
      : measure.alti ? `${measure.alti.z.toFixed(0)} m` : null
    const at = measure.alti?.pt ?? measure.pts[measure.pts.length - 1]
    labelMarker.current?.remove()
    labelMarker.current = null
    if (text && at) {
      const el = document.createElement('div')
      el.textContent = text
      el.style.cssText = 'background:#0F1A14;border:1px solid #5CE6A1;color:#5CE6A1;font:600 11px "JetBrains Mono",monospace;padding:2px 7px;border-radius:9999px;transform:translateY(-14px);white-space:nowrap'
      labelMarker.current = new maplibregl.Marker({ element: el, anchor: 'bottom' }).setLngLat(at).addTo(m)
    }
  }, [measure])

  // interactions outil (clic / double-clic / Échap)
  useEffect(() => {
    const m = map.current
    if (!m || !ready.current) return
    m.getCanvas().style.cursor = tool ? 'crosshair' : ''
    if (tool) m.doubleClickZoom.disable()
    else m.doubleClickZoom.enable()
    if (!tool) return

    const onClick = async (e: maplibregl.MapMouseEvent) => {
      const p: LngLat = [e.lngLat.lng, e.lngLat.lat]
      if (tool === 'alti') {
        try {
          const r = await fetch(`https://data.geopf.fr/altimetrie/1.0/calcul/alti/rest/elevation.json?lon=${p[0]}&lat=${p[1]}&resource=ign_rge_alti_wld`)
          const d = await r.json()
          const z = d?.elevations?.[0]?.z
          if (typeof z === 'number') setMeasure((s) => ({ ...s, alti: { pt: p, z } }))
        } catch { /* réseau : silencieux, le point reste sans étiquette */ }
        return
      }
      setMeasure((s) => ({ ...s, pts: [...s.pts, p] }))
    }
    const onDbl = (e: maplibregl.MapMouseEvent) => {
      e.preventDefault()
      const pts = measureRef.current.pts
      if (tool === 'zone' && pts.length >= 3) {
        setZone(pts)
        setTool(null)
        setMeasure({ pts: [], alti: null })
      }
      // distance/surface : le double-clic fige la mesure (l'outil reste actif pour recommencer)
      if (tool === 'distance' || tool === 'surface') setMeasure((s) => ({ ...s, pts: s.pts }))
    }
    const onKey = (ev: KeyboardEvent) => {
      if (ev.key === 'Escape') { setMeasure({ pts: [], alti: null }); setTool(null) }
    }
    m.on('click', onClick)
    m.on('dblclick', onDbl)
    window.addEventListener('keydown', onKey)
    return () => { m.off('click', onClick); m.off('dblclick', onDbl); window.removeEventListener('keydown', onKey) }
  }, [tool, setTool, setZone])

  // changer d'outil = repartir propre
  useEffect(() => {
    setMeasure({ pts: [], alti: null })
    if (!tool) { labelMarker.current?.remove(); labelMarker.current = null }
  }, [tool])

  const readout = tool === 'distance' && measure.pts.length >= 2 ? fmtDistance(pathLength(measure.pts))
    : tool === 'surface' && measure.pts.length >= 3 ? fmtArea(polygonArea(measure.pts))
    : tool === 'alti' && measure.alti ? `${measure.alti.z.toFixed(1)} m NGR`
    : null

  return (
    <div className="relative min-w-0 flex-1">
      {/* h-full w-full EN PLUS de `absolute inset-0` : maplibre-gl.css pose `.maplibregl-map{position:
          relative}` (même spécificité que Tailwind `.absolute`) et, depuis le lazy-load M-V, cette CSS
          se charge APRÈS le bundle app → elle gagne → le conteneur repasse en `relative`, `inset-0` ne
          l'étire plus, ses enfants sont absolus → hauteur 0 → carte clippée (noir). Les dimensions
          explicites survivent quel que soit le `position` gagnant. Cf. RAPPORT_M_W_CARTE_NOIRE.md. */}
      <div ref={ref} className="absolute inset-0 h-full w-full" />
      <div className="absolute left-4 top-4 flex flex-col gap-2">
        {(['+', '−'] as const).map((s) => (
          <button key={s} onClick={() => map.current?.[s === '+' ? 'zoomIn' : 'zoomOut']()}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-line-2 bg-surface-2 text-txt shadow-elev-1 transition-colors duration-quick hover:text-txt-hi"
            title={s === '+' ? 'Zoomer' : 'Dézoomer'}>
            {s}
          </button>
        ))}
      </div>
      <MapToolbar />
      {/* M12 C6/C7 : UN SEUL panneau de légendes (verdict replié + zonage + 50 pas +
          équipements), cohabitant sans se recouvrir. La légende « Équipements » a quitté son
          bloc flottant (qui masquait le verdict) pour rejoindre ce panneau. */}
      <Legend />
      {/* B1/P5 : chargement carte DISCRET (données GeoJSON + tuiles MVT) — jamais figé */}
      {(geo.isFetching || tilesLoading) && (
        <div className="pointer-events-none absolute left-1/2 top-4 -translate-x-1/2 rounded-full border border-mint/30 bg-surface-2 px-4 py-2 shadow-elev-2">
          <Loading big label={geo.isFetching ? 'Chargement des parcelles' : 'Chargement de la carte'} />
        </div>
      )}
      {/* P3 : rappel de ce que signifie le violet pendant une recherche active */}
      {iaRestitution && (
        <div className="pointer-events-none absolute right-4 top-4 flex items-center gap-1.5 rounded-full border border-violet/40 bg-surface-2/95 px-3 py-1 text-[11px] text-violet shadow-elev-2">
          <span className="h-2 w-2 rounded-full ring-2 ring-violet" style={{ background: 'transparent' }} />
          contour violet = résultats de votre recherche
        </div>
      )}
      {tool && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full border border-mint bg-surface-2 px-4 py-1.5 text-xs text-mint shadow-elev-2">
          {readout ?? (tool === 'alti' ? 'Cliquez un point pour lire l’altitude'
            : tool === 'zone' ? 'Dessinez la zone — double-clic pour fermer et filtrer'
            : 'Cliquez pour mesurer — Échap pour quitter')}
        </div>
      )}
      {!tool && (
        <div className="pointer-events-none absolute bottom-4 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full border border-line-2 bg-surface-2 px-4 py-1.5 text-xs text-txt-mut shadow-elev-1">
          {ile && lowZoom ? 'Zoomez ou cliquez une commune pour voir ses parcelles' : 'Cliquez une parcelle pour ouvrir sa fiche'}
        </div>
      )}
      <div className="absolute bottom-2 right-3 font-sans text-[11px] text-st-none">
        {basemap === 'dark' ? '© OSM · CARTO' : '© IGN Géoplateforme'}
      </div>
    </div>
  )
}
