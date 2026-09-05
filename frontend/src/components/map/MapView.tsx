import { useQuery } from '@tanstack/react-query'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useRef, useState } from 'react'
import { getCommunes, getFiche, getFiltreIdus, getMapLayer, getParcelsGeojson, getRenouvGeojson, getTilesMeta, parcelAt } from '../../lib/api'
import { ALL_TIER_META, BPE_DOM, EQUIP_META, ZONE_FAM_META, ZONE_FAM_ORDER } from '../../lib/status'
import { MAP_THEME, type MapTokens } from '../../lib/mapTheme'
import { TOKENS } from '../../lib/tokens'
import { fmtArea, fmtDistance, haversine, pathLength, polygonArea, roughCentroid, type LngLat } from '../../lib/geo'
import { communePastille } from '../../lib/communes'
import { useApp, type Filters, type MapTool } from '../../store/useApp'
import { BASEMAP_SOURCES, activeBasemapKey } from './basemaps'
import { Legend } from './Legend'
import { VefaDetail } from './VefaDetail'
import { MapToolbar } from './MapToolbar'
import { Loading } from '../Loading'

// ── Fonds de plan : registre PARTAGÉ (carte principale + comparateur swipe). Voir ./basemaps.

const STYLE: maplibregl.StyleSpecification = {
  version: 8,
  // FOND-SOMBRE : glyphs EMBARQUÉS (public/fonts/Open Sans Regular, 256 ranges pbf) — l'hôte Carto
  // (M6.1) exige désormais une clé. Même police que servie avant (Open Sans Regular), zéro réseau.
  // Les couches symbol posent text-font: ['Open Sans Regular'] explicitement (le défaut MapLibre
  // demanderait la pile composite « Open Sans Regular,Arial Unicode MS Regular », dossier inexistant).
  glyphs: `${window.location.origin}${(import.meta as unknown as { env: { BASE_URL: string } }).env.BASE_URL}fonts/{fontstack}/{range}.pbf`,
  sources: {},
  // canvas au niveau MER du Sombre (#181918 MESURÉ, cf. SOMBRE_MER) : pas de flash noir au boot.
  layers: [{ id: 'bg', type: 'background', paint: { 'background-color': '#181918' } }],
}

// Correctif M5 (verdict effectif) : la couleur EST le verdict sur la carte — étage 0 prime
// (écartée quasi invisible, inchangé), puis tier v2 quand un run existe (palette TIER_V2_META,
// cf. lib/status.ts). M48 (F4) : le repli `status` (matrice v1 morte) est RETIRÉ — le MVT ne bake
// plus matrice_statut et le GeoJSON l'avait déjà supprimé (M37) ; sans tier v2 → défaut neutre.
// `etage0` est bool en GeoJSON et int (0/1) en MVT → to-number.
// RETOURS-5 T3 — carrosserie SOMBRE commune des popups carte (opérations, concurrents) : jamais de fond
// blanc illisible. Fond quasi opaque, bord --card-line, ombre portée pour détacher de la carte.
const POPUP_BOX_CSS = 'font:12px system-ui;color:#e9edeb;min-width:220px;max-width:280px;background:rgba(14,18,16,.97);border:1px solid #232a26;border-radius:11px;padding:13px;box-shadow:0 12px 32px rgba(0,0,0,.55)'
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
// RETOURS-11 R5 (04/09) — sur fond PHOTO (ortho/plan), l'aplat parcellaire (verdict/zonage) noie
// l'île entière au zoom large. `photoFade` fond n'importe quelle opacité cible AU ZOOM sur photo
// (0 sous ~12, cible atteinte vers 16) ; hors photo (Sombre/Clair = témoins) la valeur passe telle
// quelle → aucun changement de rendu. Le multiplicateur d'un aplat par le zoom n'existe pas en
// style MapLibre : on ré-échelonne la cible dans une interpolation de zoom.
const photoFade = (target: number, photo: boolean): number | maplibregl.ExpressionSpecification =>
  !photo ? target
    : (['interpolate', ['linear'], ['zoom'], 12, 0, 14, target * 0.55, 16, target] as unknown as maplibregl.ExpressionSpecification)
// M105-B — contour des tiers PAR THÈME : en Clair, les liserés brûlante/chaude s'assombrissent
// (mêmes teintes, ≥ 3:1 sur la terre claire — tokens lib/mapTheme) ; en Sombre, l'expression
// historique verbatim. Un seul propriétaire du paint : l'effet « résultats en violet » plus bas.
const statusLineExpr = (clair: boolean): maplibregl.ExpressionSpecification => !clair ? STATUS_COLOR : [
  'case', ETAGE0, ECARTEE_COLOR,
  ['match', TIER_V2,
    ...Object.entries(ALL_TIER_META).flatMap(([k, mt]) => [k,
      k === 'brulante' ? MAP_THEME.clair.contourBrulante
        : k === 'chaude' ? MAP_THEME.clair.contourChaude
          : k === 'ecartee' ? ECARTEE_COLOR : mt.color]),
    LEGACY_COLOR],
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
  // M129-B : q_score (matrice) mort — plus de filtre carte scoreMin.
  if (f.surfaceMin != null) c.push(['>=', ['coalesce', ['get', 'surface_m2'], 0], f.surfaceMin])
  if (f.surfaceMax != null) c.push(['<=', ['coalesce', ['get', 'surface_m2'], 0], f.surfaceMax])
  if (f.sdpMin != null) c.push(['>=', ['coalesce', ['get', 'sdp_residuelle_m2'], -1], f.sdpMin])
  if (f.evenement) c.push(['==', ['get', 'evenement'], 'rouge'])
  if (f.veille) c.push(['==', ['coalesce', ['get', 'veille'], false], true])
  if (f.horsCopro) c.push(['!=', ['coalesce', ['get', 'copro_v2'], false], true])
  // FIX-CARTE T2 : le filtre `flags` NE s'exprime plus sur la tuile (`flags` retiré des tuiles,
  // propriété texte la plus lourde) — il passe par le repli serveur getFiltreIdus (voir
  // hasCriteresHorsTuiles) qui peint les IDU exacts. La liste/fiche portent déjà les flags.
  if (f.communes.length) c.push(['in', ['get', 'commune'], ['literal', f.communes]])
  return ['all', ...c] as maplibregl.FilterSpecification
}

// M55-G suite (point 1) — les critères que `toExpr` NE PEUT PAS exprimer (absents des
// propriétés des tuiles : signaux de vie, état du sol, constructibilité, propriété,
// économie…). Constat mesuré : avec un de ces critères actif, la carte peignait TOUT ce qui
// passait le sous-ensemble « client » (liste = 1 parcelle, commune entière colorée). Quand
// l'un d'eux est actif, la carte demande au serveur les IDU du résultat exact (getFiltreIdus)
// et restreint la palette à eux — le reste en trame neutre.
function hasCriteresHorsTuiles(f: Filters): boolean {
  return !!(f.flags.length   // FIX-CARTE T2 : flags retiré des tuiles → résolu côté serveur (IDU exacts)
    || f.signaux.length || f.etatSol.length || f.constructibilite.length
    || f.zonagePlu.length || f.zonePlu.length || f.capaciteMin != null || f.sdpMax != null
    || f.proprietaireType.length || f.etatSociete.length || f.copro.length
    || f.npnru || f.adresseAbsente || f.personneMorale || f.sousDensite
    || f.multMin != null || f.rangMax != null || f.renouvellement
    || f.budgetMax != null || f.chargeMin != null || f.chargeMax != null
    || f.prixMarcheMin != null || f.prixMarcheMax != null || f.marcheFiable
    || f.caMin != null || f.modeBRentable)
}

const SP_BOUNDS: [number, number, number, number] = [55.21, -21.14, 55.35, -20.97]
// M83 A1 — REPLI de tout premier frame seulement (avant que /communes ait chargé). Le cadrage réel de
// l'île est CALCULÉ sur l'emprise des données (union des bbox `ST_Extent` par commune, cf. ileBounds) —
// si la couverture évolue, le cadrage suit. Jamais figé sur ces coordonnées à l'affichage.
const ILE_BOUNDS: [number, number, number, number] = [55.20, -21.42, 55.87, -20.85]
// FIX-CARTE B1 — limite de navigation : ILE_BOUNDS + ~0,2° de marge (on garde de l'air autour de
// l'île sans pouvoir dériver vers l'océan/le monde, où les parcelles renvoient 204 et le fond est vide).
const REUNION_MAXBOUNDS: [number, number, number, number] = [55.00, -21.62, 56.07, -20.65]
const EMPTY_FC = { type: 'FeatureCollection', features: [] } as const

// M83 A1 — emprise réelle de l'île = union des bbox de communes servies par /communes (ST_Extent du
// parcellaire). Repli sur ILE_BOUNDS tant que la donnée n'est pas là (1er frame).
function ileBounds(communes: { bbox?: number[] }[] | undefined): [number, number, number, number] {
  let x1 = Infinity, y1 = Infinity, x2 = -Infinity, y2 = -Infinity
  for (const c of communes ?? []) {
    if (!c.bbox || c.bbox.length < 4) continue
    x1 = Math.min(x1, c.bbox[0]); y1 = Math.min(y1, c.bbox[1])
    x2 = Math.max(x2, c.bbox[2]); y2 = Math.max(y2, c.bbox[3])
  }
  return Number.isFinite(x1) ? [x1, y1, x2, y2] : ILE_BOUNDS
}

// Item 11 (UX V1) : padding de fitBounds BORNÉ au canvas — 40 px fixes déclenchaient
// « Map cannot fit within canvas » au boot 375 (le panneau ne laissait presque rien à la
// carte). Jamais plus d'un dixième de la plus petite dimension, plancher 8 px.
const fitPadding = (w: number, h: number) => Math.max(8, Math.min(40, Math.floor(Math.min(w, h) / 10)))

// M105-B — les couleurs/opacités de zonage, PPR, ANRU et 50 pas vivent dans lib/mapTheme
// (un jeu de tokens PAR THÈME) : ici la colonne `sombre` (création des couches),
// `applyClairMode` pose la colonne du thème courant au même format. Un seul endroit.
const zonageFillExpr = (t: MapTokens) => ['case',
  ['in', ['slice', ['upcase', ['coalesce', ['get', 'subtype'], '']], 0, 1], ['literal', ['U']]],
  t.zonageU, t.zonageAutre] as unknown as maplibregl.ExpressionSpecification
// M137-Y — couleur ZFANG/FRR PAR ÉTAT (data-driven sur le subtype), comme zonageFillExpr.
const dispoColorExpr = (t: MapTokens, kind: 'zfang' | 'frr') => (kind === 'zfang'
  ? ['match', ['get', 'subtype'], 'renforce', t.zfangRenforce, t.zfangStandard]
  : ['match', ['get', 'subtype'], 'totalite', t.frrTotalite, t.frrPartie]) as unknown as maplibregl.ExpressionSpecification
// M137-Y — assombrit une teinte (hachure = shade plus foncé de l'aplat → visible sur toute couleur).
const darken = (hex: string, f: number): string => {
  const n = parseInt(hex.slice(1), 16)
  const r = Math.round(((n >> 16) & 255) * f), g = Math.round(((n >> 8) & 255) * f), b = Math.round((n & 255) * f)
  return `#${((1 << 24) | (r << 16) | (g << 8) | b).toString(16).slice(1)}`
}
const T_SOMBRE = MAP_THEME.sombre
// SECTEUR-2b (U1) — choropleth du prix du neuf VEFA : rampe séquentielle DISTINCTE (jaune → orange →
// magenta), tranchée franchement sur le fond sombre VERT, hors du vert des statuts. Communes sous le
// seuil (subtype 'sous_seuil') : gris muet + HACHURE grise (couche -trame dédiée), jamais vides.
const VEFA_RAMP: Record<string, string> = {
  moins_4000: '#FDE047', '4000_4500': '#FB923C', '4500_5000': '#EA6D2A',
  '5000_5500': '#D6337A', '5500_plus': '#A21CAF', sous_seuil: '#3B4046',
}
const vefaColorExpr = ['match', ['get', 'subtype'],
  'moins_4000', VEFA_RAMP.moins_4000, '4000_4500', VEFA_RAMP['4000_4500'],
  '4500_5000', VEFA_RAMP['4500_5000'], '5000_5500', VEFA_RAMP['5000_5500'],
  '5500_plus', VEFA_RAMP['5500_plus'], 'sous_seuil', VEFA_RAMP.sous_seuil,
  '#3B4046'] as unknown as maplibregl.ExpressionSpecification
// opacité : aplat lisible pour les tranches peintes, plus discret pour le gris sous-seuil (la hachure porte).
const vefaOpacityExpr = ['match', ['get', 'subtype'], 'sous_seuil', 0.28, 0.55] as unknown as maplibregl.ExpressionSpecification
const OVERLAYS = {
  // SECTEUR-2b (U1) — prix du neuf VEFA (aplat commune) : teinte par tranche + gris pour sous_seuil.
  vefa_neuf: { paint: { 'fill-color': vefaColorExpr, 'fill-outline-color': '#0b0f14', 'fill-opacity': vefaOpacityExpr } },
  zonage: { paint: { 'fill-color': zonageFillExpr(T_SOMBRE), 'fill-opacity': T_SOMBRE.zonageOpacity } },
  // P10 (dernière passe) : Parc national en MARRON/terre (#8B5A2B) — distinct du menthe des
  // statuts et du vert-clair d'avant qui « envahissait ». Lisible sur ortho ET fond sombre.
  // Hors mapTheme : 1,34:1 mesuré sur la terre claire (AUDIT_M105B) — conforme dans les deux thèmes.
  parc: { paint: { 'fill-color': '#8B5A2B', 'fill-opacity': 0.22 } },
  ppr: { paint: { 'fill-color': T_SOMBRE.ppr, 'fill-opacity': T_SOMBRE.pprOpacity } },
  // M137-U — ZNIEFF (contrainte patrimoine naturel) : aplat vert olive, distinct du Parc (marron) et du PPR (rouge).
  znieff: { paint: { 'fill-color': T_SOMBRE.znieff, 'fill-opacity': T_SOMBRE.znieffOpacity, 'fill-outline-color': T_SOMBRE.znieff } },
  // M55-A-bis : chartreuse/lime = le seul creux franc de la palette (or ~45°, verts ~148°),
  // tranche fort sur fond sombre, hors du violet RÉSERVÉ aux résultats de recherche.
  anru: { paint: { 'fill-color': T_SOMBRE.anru, 'fill-opacity': T_SOMBRE.anruOpacity } },
  // M134 — couche « Dispositifs ». Contour = teinte pleine (fill-outline-color, ≥3:1). ZFANG/FRR :
  // l'intensité du régime (renforcé/totalité) se lit à l'OPACITÉ via un `match` sur le subtype
  // (même teinte identitaire, doctrine M105-B) — comme `zonage` porte déjà une expression data-driven.
  qpv: { paint: { 'fill-color': T_SOMBRE.qpv, 'fill-opacity': T_SOMBRE.qpvOpacity, 'fill-outline-color': T_SOMBRE.qpv } },
  tva_primo: { paint: { 'fill-color': T_SOMBRE.tvaPrimo, 'fill-opacity': T_SOMBRE.tvaPrimoOpacity, 'fill-outline-color': T_SOMBRE.tvaPrimo } },
  // M137-X — ZFANG/FRR : APLAT plein pour l'état de base ; l'AUTRE état (ZFANG renforcée / FRR en
  // partie) est marqué par des HACHURES (couche `-trame` dédiée) — texture catégorielle, plus le
  // dégradé d'opacité ambigu d'avant. Une seule opacité d'aplat par dispositif.
  zfang: { paint: { 'fill-color': dispoColorExpr(T_SOMBRE, 'zfang'), 'fill-outline-color': dispoColorExpr(T_SOMBRE, 'zfang'), 'fill-opacity': T_SOMBRE.dispoFillOpacity } },
  frr: { paint: { 'fill-color': dispoColorExpr(T_SOMBRE, 'frr'), 'fill-outline-color': dispoColorExpr(T_SOMBRE, 'frr'), 'fill-opacity': T_SOMBRE.dispoFillOpacity } },
} as const
const PARC_LINE = '#7A4A1E'   // liseré marron foncé — borne nette du Parc

// ═══ FOND-SOMBRE — le Sombre n'a PLUS de raster (CARTO clé requise → retiré, décision Vic) ═══
// Le rendu Sombre est reproduit aux teintes EFFECTIVEMENT MESURÉES à l'écran avant retrait
// (qa/fond-sombre, captures avant) : le raster dark_nolabels à raster-opacity 0,55 sur le canvas
// #060A08 rendait mer = (24,25,24) et terre nue = (8,10,9). Aucune couleur nouvelle : ce sont les
// valeurs que l'utilisateur voyait déjà. La TERRE est portée par la masse dissoute `ile-mass`
// (même mécanisme que le Clair), la MER par le canvas `bg`. Aucun raster de remplacement, aucun
// ombrage (le relief en volume = mode 3D).
const SOMBRE_MER = '#181918'    // mer Sombre MESURÉE (blend raster CARTO 0,55 sur #060A08)
const SOMBRE_TERRE = '#080A09'  // terre Sombre MESURÉE (idem)

// ═══ M65 P8 — MODE CLAIR = INVERSION FIGURE/FOND (redéfinit le Clair M64) ═══
// La MER (fond hors terre = `bg`) reste le canvas historique #060A08 (le Clair ne touche PAS
// au fond de carte). Ce qui change, c'est la TERRE :
//  · masse terrestre (île dissoute) = GRIS #C9C4B8 (couche `ile-mass`) → la terre sans parcelle
//    (cirques, forêt, volcan) est grise ; la mer, non couverte, reste le `bg` noir ;
//  · parcelles = BLANC CASSÉ #F4F2EC (jamais blanc pur : les traits fins de 0,5 px doivent tenir) —
//    posé dans l'effet palette (branche neutre), qui a `basemap` en deps ;
//  · trait de côte = vert de marque #4ADE80 2,2 px (couche `ile-cote`, contour dissous seulement) ;
//  · limites parcelles #B9B3A6 0,5 px · limites communes #2E7D52 1,6 px (≈3× les parcelles).
// Bascules M64 CONSERVÉES (elles se posent maintenant sur de la terre claire) : traits achromatiques
// (sélection/pulse/étiquette de zone) → valeur sombre. Pastilles de commune : INCHANGÉES (revert de
// l'adaptation « pastille claire » M64, cf. leur effet) — un seul token diffère entre les modes.
const SOMBRE_BG = '#060A08'   // canvas historique — mer du mode Clair (et sous les rasters Plan/Ortho).
// largeur des limites communes en Sombre (interpolée par zoom) — restaurée hors Clair.
const COMMUNES_W_SOMBRE = ['interpolate', ['linear'], ['zoom'], 8, 1.1, 13, 1.8]
function applyClairMode(m: maplibregl.Map, basemap: string) {
  const clair = basemap === 'clair'
  const sombre = basemap === 'dark'
  // RETOURS-11 C4 — fonds PHOTO/CLAIR (Plan IGN, Ortho IGN, tous millésimes) : les traits fins et
  // les aplats sombres se noient sur la tuile claire/photographique. On applique un variant de style
  // « lisibilité fond clair » en surcouche, PILOTÉ ICI (seul propriétaire du paint basemap-dépendant),
  // sans DUPLIQUER de couche. Clair et Sombre (témoins) ne passent JAMAIS par ce bloc.
  const photo = basemap === 'plan' || basemap === 'ortho'
  const set = (id: string, prop: string, val: unknown) => { if (m.getLayer(id)) m.setPaintProperty(id, prop as never, val as never) }
  const vis = (id: string, on: boolean) => { if (m.getLayer(id)) m.setLayoutProperty(id, 'visibility', on ? 'visible' : 'none') }
  // FOND-SOMBRE : la mer du Sombre = teinte mesurée du rendu raster d'avant ; Clair garde le noir.
  set('bg', 'background-color', sombre ? SOMBRE_MER : SOMBRE_BG)
  // TERRE : masse île dissoute — grise en Clair, terre mesurée en Sombre ; CACHÉE sous Plan/Ortho
  // (dans la pile elle est AU-DESSUS des rasters de fond, elle les recouvrirait).
  vis('ile-mass', clair || sombre)
  set('ile-mass', 'fill-color', clair ? '#C9C4B8' : SOMBRE_TERRE)
  vis('ile-cote', clair)
  // traits achromatiques (#ECF5EF) invisibles sur terre claire → foncés en Clair (bascule M64).
  const selLine = clair ? '#14181A' : '#ECF5EF'
  for (const id of ['parcels-sel', 'ile-sel', 'parcels-ping', 'ile-ping']) set(id, 'line-color', selLine)
  // RETOURS-11 C4 — text-halo-width réappliqué à sa valeur de création (1.3) hors fond photo, pour
  // que le retour en Clair/Sombre efface l'épaississement du variant photo (témoins intacts).
  for (const id of ['parcels-zone-label', 'ile-zone-label']) { set(id, 'text-color', clair ? '#14181A' : '#ECF5EF'); set(id, 'text-halo-color', clair ? '#FFFFFF' : '#06130C'); set(id, 'text-halo-width', 1.3) }
  // M105 P4.1 — limites parcelles NOIRES en vue claire (le beige #B9B3A6 se noyait sur la
  // terre claire) ; la vue sombre ne bouge pas. Deux traitements selon le fond, assumés.
  for (const id of ['parcels-limites', 'ile-limites']) {
    set(id, 'line-color', clair ? '#000000' : '#8FA69A')
    set(id, 'line-width', clair ? 0.5 : 0.3)
    set(id, 'line-opacity', 0.4)   // RETOURS-11 C4 — valeur de création restaurée (le variant photo la monte à 0,9)
  }
  // limites communes : vert foncé #2E7D52 / 1,6 px (≈3× parcelles) sur terre claire — elles ne se
  // noient plus dans le cadastre ; sinon menthe + interpolation sombre d'origine.
  set('communes-bounds', 'line-color', clair ? '#2E7D52' : '#5CE6A1')
  set('communes-bounds', 'line-width', clair ? 1.6 : COMMUNES_W_SOMBRE)
  set('communes-bounds', 'line-opacity', 0.55)   // RETOURS-11 C4 — création restaurée (variant photo la monte à 0,95)
  // M105-B — les couches d'INFORMATION consomment le jeu de tokens du thème (lib/mapTheme,
  // un jeu par thème, un seul endroit) : zonage, PPR, ANRU (+trame), 50 pas, liseré brûlantes.
  // Le contour des tiers (parcels-line/ile-line) a son propriétaire unique : l'effet violet.
  const t = MAP_THEME[clair ? 'clair' : 'sombre']
  // MESURÉ SUR CAPTURES (P3) : en Clair les parcelles sont OPAQUES (#F4F2EC @1) — l'ordre de
  // création les peignait AU-DESSUS des couches d'information : l'aplat de zonage ne rendait
  // que sur la masse non parcellisée, et les limites communes étaient recouvertes. En Clair,
  // les remplissages parcellaires DESCENDENT sous le bloc d'information (les limites noires,
  // sélections et étiquettes restent au-dessus) ; en Sombre, l'ordre d'origine est RESTAURÉ —
  // la vue sombre ne bouge pas.
  const mv = (id: string, before: string) => { if (m.getLayer(id) && m.getLayer(before)) m.moveLayer(id, before) }
  if (clair) {
    for (const id of ['parcels-base', 'parcels-fill', 'ile-base', 'ile-fill']) mv(id, 'ov-zonage')
  } else {
    for (const id of ['parcels-base', 'parcels-fill']) mv(id, 'parcels-limites')
    for (const id of ['ile-base', 'ile-fill']) mv(id, 'ile-limites')
  }
  for (const id of ['ov-zonage', 'ovmvt-zonage']) { set(id, 'fill-color', zonageFillExpr(t)); set(id, 'fill-opacity', t.zonageOpacity) }
  for (const id of ['ov-zonage-line', 'ovmvt-zonage-line']) { set(id, 'line-color', zonageFillExpr(t)); set(id, 'line-width', t.zonageContourW) }
  for (const id of ['ov-ppr', 'ovmvt-ppr']) { set(id, 'fill-color', t.ppr); set(id, 'fill-opacity', t.pprOpacity) }
  for (const id of ['ov-ppr-line', 'ovmvt-ppr-line']) { set(id, 'line-color', t.ppr); set(id, 'line-width', t.pprContourW) }
  set('ov-anru', 'fill-color', t.anru); set('ov-anru', 'fill-opacity', t.anruOpacity)
  set('ov-anru-trame', 'fill-opacity', t.anruTrameOpacity)
  // M134 — dispositifs : la teinte suit le thème ; l'opacité de ZFANG/FRR est un `match` constant
  // (l'intensité du régime ne dépend pas du thème), on ne met à jour que la couleur (aplat + contour).
  set('ov-qpv', 'fill-color', t.qpv); set('ov-qpv', 'fill-opacity', t.qpvOpacity); set('ov-qpv', 'fill-outline-color', t.qpv)
  set('ov-tva_primo', 'fill-color', t.tvaPrimo); set('ov-tva_primo', 'fill-opacity', t.tvaPrimoOpacity); set('ov-tva_primo', 'fill-outline-color', t.tvaPrimo)
  // M137-X — aplat plein (une opacité) + hachure sur l'état « fort » ; le motif suit le thème.
  set('ov-zfang', 'fill-color', dispoColorExpr(t, 'zfang')); set('ov-zfang', 'fill-outline-color', dispoColorExpr(t, 'zfang')); set('ov-zfang', 'fill-opacity', t.dispoFillOpacity)
  set('ov-frr', 'fill-color', dispoColorExpr(t, 'frr')); set('ov-frr', 'fill-outline-color', dispoColorExpr(t, 'frr')); set('ov-frr', 'fill-opacity', t.dispoFillOpacity)
  for (const [src, , tok] of DISPO_TRAMES) {
    set(`${src}-trame`, 'fill-pattern', `trame-${tok}-${clair ? 'clair' : 'sombre'}`)
    set(`${src}-trame`, 'fill-opacity', t.aleaTrameOpacity)
  }
  set('ov-50pas', 'fill-color', t.cinquantePas); set('ov-50pas', 'fill-opacity', t.cinquantePasFillOpacity)
  set('ov-50pas-line', 'line-color', t.cinquantePas)
  set('parcels-brulantes', 'line-color', t.lisereBrulantes)
  // M106 : les deux couches d'aléa suivent le jeu du thème (teinte + gradation + contour).
  // RETOURS-13 R7 — plus de trame ; R8 — contour au ZOOM (mêmes expressions sur les 4 fonds).
  for (const c of ALEA_COUCHES) {
    set(c.id, 'fill-color', aleaColorExpr(t, c.ramp)); set(c.id, 'fill-opacity', t.aleaFillOpacity)
    set(`${c.id}-line`, 'line-color', t[c.token])
    set(`${c.id}-line`, 'line-width', ALEA_LINE_W); set(`${c.id}-line`, 'line-opacity', ALEA_LINE_OP)
  }
  // M106 P4 / M106-B : la couleur dit le RÉSEAU (expression par subtype), la forme dit le type ;
  // pôles neutres ; Papang = couleur Citalis ; axes ardoise ; HT anthracite — tokens par thème
  set('ov-trans-ligne', 'line-color', reseauColorExpr(t))
  set('ov-trans-arret', 'circle-color', reseauColorExpr(t))
  set('ov-tele', 'line-color', t.transportReseaux['Papang'])
  set('ov-tele-st', 'circle-color', t.transportReseaux['Papang'])
  set('ov-tele-st', 'circle-stroke-color', clair ? '#FFFFFF' : SOMBRE_BG)
  set('ov-pole', 'circle-color', t.pole); set('ov-pole', 'circle-stroke-color', t.pole)
  set('ov-axe', 'line-color', t.axe)
  set('ov-ht', 'line-color', t.ht)
  set('ov-mt', 'line-color', t.mt)       // RETOURS-13 R4 — moyenne tension HTA
  // RETOURS-14 S8 — TCSP : tronçons, stations et zone 800 m suivent le thème
  set('ov-tcsp', 'line-color', t.tcsp)
  set('ov-tcsp-zone-parcelles', 'fill-color', t.tcsp)
  set('ov-tcsp-zone-rayon', 'line-color', t.tcsp)
  set('ov-tcsp-st', 'circle-color', t.tcsp)
  set('ov-tcsp-st', 'circle-stroke-color', clair ? '#FFFFFF' : '#0A0F0C')

  // ═══ RETOURS-11 C4 — VARIANT LISIBILITÉ « fond photo/clair » (Plan & Ortho) ═══
  // Ce bloc s'exécute EN DERNIER : il écrase, pour les seuls fonds photo, les propriétés posées
  // plus haut (colonne « sombre » par défaut hors clair/sombre). Il ne s'exécute jamais en Clair ni
  // en Sombre → les deux témoins gardent EXACTEMENT leur rendu (les lignes ci-dessus les ré-appliquent
  // à chaque bascule, ce bloc étant sauté). Aucune couche neuve : uniquement setPaintProperty.
  if (photo) {
    // Limites parcelles : sur ortho/plan le beige fin (#8FA69A / 0,3 px) disparaît. Le vrai casing
    // (liseré sombre large SOUS un trait clair fin) demanderait une 2e couche — interdit ici (« pas
    // de couche dupliquée »). FAIT AUTREMENT : un TRAIT SOMBRE nettement plus large (jusqu'à 2,2 px)
    // et opaque, très lisible sur la photo (cf. rapport C4).
    // RETOURS-11 R5 (04/09) — sur ortho, TOUTES les limites parcellaires sur l'île entière =
    // illisible. La densité SUIT LE ZOOM : au zoom large seules les limites communes portent
    // (les parcelles sont éteintes, opacité → 0 sous ~14) ; en zoomant elles apparaissent
    // PROGRESSIVEMENT (opacité ET épaisseur montent). Gate sur photo uniquement → Sombre/Clair
    // (témoins) inchangés. Le contour des tiers (parcels-line/ile-line) suit la même rampe.
    for (const id of ['parcels-limites', 'ile-limites']) {
      set(id, 'line-color', '#0A0F0C')
      set(id, 'line-width', ['interpolate', ['linear'], ['zoom'], 13, 0.4, 15, 1.0, 17, 1.8, 19, 2.2])
      set(id, 'line-opacity', ['interpolate', ['linear'], ['zoom'], 13, 0, 14, 0.25, 16, 0.7, 18, 0.9])
    }
    for (const id of ['parcels-line', 'ile-line']) {
      set(id, 'line-opacity', ['interpolate', ['linear'], ['zoom'], 13, 0.2, 15, 0.6, 17, 0.9])
    }
    // Limites communes : même recette de casing — trait sombre large, très visible sur ortho/plan.
    set('communes-bounds', 'line-color', '#0A2417')
    set('communes-bounds', 'line-width', ['interpolate', ['linear'], ['zoom'], 8, 2.0, 13, 3.2])
    set('communes-bounds', 'line-opacity', 0.95)
    // Zonage (aplat) : plus opaque + contour sombre net — l'aplat clair ressort sur la photo.
    // RETOURS-11 R5 — l'aplat MONTE avec le zoom (au zoom large il noierait l'île entière) :
    // faible loin, ~0,34 en approche. Contour idem. Gate photo → Sombre/Clair intacts.
    for (const id of ['ov-zonage', 'ovmvt-zonage']) set(id, 'fill-opacity', ['interpolate', ['linear'], ['zoom'], 11, 0.10, 14, 0.22, 16, 0.34])
    for (const id of ['ov-zonage-line', 'ovmvt-zonage-line']) { set(id, 'line-color', '#0A0F0C'); set(id, 'line-width', 1.4) }
    // NB : l'aplat parcellaire (parcels-fill/ile-fill) est fondu au zoom sur photo AILLEURS — dans
    // l'effet qui possède fill-opacity (il la re-pilote à chaque filtre/couche) ; cf. photoFade().
    // Zonage — LETTRES (symbol) : halo SOMBRE épaissi → les lettres blanches restent lisibles sur photo.
    for (const id of ['parcels-zone-label', 'ile-zone-label']) {
      set(id, 'text-color', '#FFFFFF'); set(id, 'text-halo-color', '#000000'); set(id, 'text-halo-width', 2.2)
    }
    // Risques (PPR + aléas DEAL) : aplat plus opaque + contour sombre — même gain de lisibilité.
    for (const id of ['ov-ppr', 'ovmvt-ppr']) set(id, 'fill-opacity', 0.30)
    for (const id of ['ov-ppr-line', 'ovmvt-ppr-line']) { set(id, 'line-color', '#0A0F0C'); set(id, 'line-width', 1.4) }
    // RETOURS-13 R7/R8 — sur photo : aplat calibré (0,45, teintes par classe déjà vives) ; le
    // contour garde sa COULEUR sombre (lisible sur la photo) mais suit la MÊME règle de zoom que
    // les autres fonds (ALEA_LINE_W/OP) — fini la bouillie noire au zoom large sur ortho.
    for (const c of ALEA_COUCHES) {
      set(c.id, 'fill-opacity', 0.45)
      set(`${c.id}-line`, 'line-color', '#0A0F0C')
      set(`${c.id}-line`, 'line-width', ALEA_LINE_W); set(`${c.id}-line`, 'line-opacity', ALEA_LINE_OP)
    }
  }
}

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

// M105-B / M106 — motifs de TRAME (canvas → addImage, comme les icônes équipements).
// Trois ORIENTATIONS distinctes : la texture différencie des couches superposables même
// quand les teintes se rapprochent (doctrine M105-B, daltonisme). Segments décalés pour
// un raccord sans couture d'une tuile à l'autre.
function makeTrame(m: maplibregl.Map, id: string, color: string, orient: 'slash' | 'backslash' | 'horiz') {
  if (m.hasImage(id)) return
  const S = 12
  const cv = document.createElement('canvas')
  cv.width = cv.height = S
  const ctx = cv.getContext('2d')
  if (!ctx) return
  ctx.strokeStyle = color
  ctx.lineWidth = 2
  ctx.beginPath()
  if (orient === 'slash') {
    ctx.moveTo(0, S); ctx.lineTo(S, 0)
    ctx.moveTo(-S / 2, S / 2); ctx.lineTo(S / 2, -S / 2)
    ctx.moveTo(S / 2, S * 1.5); ctx.lineTo(S * 1.5, S / 2)
  } else if (orient === 'backslash') {
    ctx.moveTo(0, 0); ctx.lineTo(S, S)
    ctx.moveTo(S / 2, -S / 2); ctx.lineTo(S * 1.5, S / 2)
    ctx.moveTo(-S / 2, S / 2); ctx.lineTo(S / 2, S * 1.5)
  } else {
    ctx.moveTo(0, S / 4); ctx.lineTo(S, S / 4)
    ctx.moveTo(0, S * 3 / 4); ctx.lineTo(S, S * 3 / 4)
  }
  ctx.stroke()
  m.addImage(id, ctx.getImageData(0, 0, S, S), { pixelRatio: 2 })
}
// M105-B : trame ANRU (chartreuse claire — opacité 0 en Sombre, posée en Clair)
const makeTrameAnru = (m: maplibregl.Map) => makeTrame(m, 'trame-anru', MAP_THEME.clair.anru, 'slash')
// M137-X — les deux trames de dispositif : [source, subtype MARQUÉ par la hachure, token couleur, orientation].
// ZFANG renforcée (slash) · FRR en partie (backslash) — orientations distinctes (superposables).
// M137-Y — la hachure (SECOND signal) marque l'état MOINDRE : ZFANG standard, FRR en partie.
// [source, subtype hachuré, token couleur de l'état, orientation].
const DISPO_TRAMES = [
  ['ov-zfang', 'standard', 'zfangStandard', 'slash'],
  ['ov-frr', 'partie', 'frrPartie', 'backslash'],
] as const
// M106 : l'aplat des aléas est GRADUÉ par la classe servie — expression partagée
// création/bascule de thème (les valeurs vivent dans mapTheme, un seul endroit).
// RETOURS-13 R6 — la couleur suit la CLASSE RÉELLE du jeu (`classe`, dérivée du degré DEAL —
// repli `niveau` si absente) : le mouvement de terrain porte QUATRE classes (faible, moyen,
// élevé, très élevé — 360 zones élevées + 124 très élevées étaient écrasées en « moyen » et le
// rouge n'apparaissait jamais). Une teinte par classe, la plus grave en ROUGE. Le libellé
// officiel de l'aléa reste la vérité ; la couleur ne fait qu'ordonner.
const aleaColorExpr = (t: MapTokens, ramp: 'aleaInondationRamp' | 'aleaMvtRamp'): maplibregl.ExpressionSpecification => {
  const r = t[ramp] as unknown as Record<string, string>
  return ['match', ['coalesce', ['get', 'classe'], ['get', 'niveau'], 'moyen'],
    ...Object.entries(r).flatMap(([k, c]) => [k, c]),
    r.moyen] as unknown as maplibregl.ExpressionSpecification
}
// RETOURS-13 R8 — le CONTOUR des aléas est géré par le ZOOM : absent aux petits zooms (l'aplat
// suffit, les contours faisaient une bouillie noire sur ortho), il apparaît en zoomant — MÊME
// RÈGLE SUR LES 4 FONDS (sombre, clair, ortho, IGN) : expressions partagées, jamais re-décidées
// par fond.
const ALEA_LINE_W = ['interpolate', ['linear'], ['zoom'], 13, 0, 14, 0.8, 16, 1.4] as unknown as maplibregl.ExpressionSpecification
const ALEA_LINE_OP = ['interpolate', ['linear'], ['zoom'], 13, 0, 14, 0.5, 16, 0.9] as unknown as maplibregl.ExpressionSpecification
// M106-B — LA COULEUR DIT LE RÉSEAU : expression match sur subtype (= réseau GTFS), tokens
// par thème (mapTheme.transportReseaux) ; repli transportDefaut pour un réseau futur.
const reseauColorExpr = (t: MapTokens): maplibregl.ExpressionSpecification => [
  'match', ['coalesce', ['get', 'subtype'], ''],
  ...Object.entries(t.transportReseaux).flatMap(([k, c]) => [k, c]),
  t.transportDefaut,
] as unknown as maplibregl.ExpressionSpecification

//: M106 — les deux couches d'aléa DEAL (id, subtype du flux, token de teinte).
//: RETOURS-13 R7 — les TRAMES (hachures) d'aléa sont RETIRÉES (décision Vic : « enlève le
//: hachurage », illisibles) : aplats pleins semi-transparents seuls, opacité calibrée par fond.
const ALEA_COUCHES = [
  { id: 'ov-alea-inond', sub: 'inondation', token: 'aleaInondation', ramp: 'aleaInondationRamp' },
  { id: 'ov-alea-mvt', sub: 'mouvement_terrain', token: 'aleaMvt', ramp: 'aleaMvtRamp' },
] as const

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

// RETOURS-11F3 avenant R10 — la GOUTTE D'EAU des piscines, rendue en ICÔNE CANVAS (addImage) et non
// en `text-field:'💧'` : un emoji en text-field dépend des glyphes du style (souvent ABSENTS pour les
// emoji) → aucun marqueur ne s'affichait (échec silencieux). Le canvas rasterise l'emoji côté client
// (même mécanisme fiable que les équipements) : la goutte est TOUJOURS rendue.
function makePiscineIcon(m: maplibregl.Map) {
  if (m.hasImage('piscine-drop')) return
  const S = 40
  const cv = document.createElement('canvas'); cv.width = cv.height = S
  const ctx = cv.getContext('2d'); if (!ctx) return
  // pastille verte de marque + goutte, halo sombre pour la lisibilité sur ortho comme sur plan.
  ctx.beginPath(); ctx.arc(S / 2, S / 2, S / 2 - 3, 0, Math.PI * 2)
  ctx.fillStyle = '#4ADE80'; ctx.globalAlpha = 0.95; ctx.fill()
  ctx.globalAlpha = 1; ctx.lineWidth = 2; ctx.strokeStyle = '#06130C'; ctx.stroke()
  ctx.font = `${Math.round(S * 0.52)}px "Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",system-ui`
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
  ctx.fillText('💧', S / 2, S / 2 + 1)
  m.addImage('piscine-drop', ctx.getImageData(0, 0, S, S), { pixelRatio: 2 })
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
  // RETOURS-11 C8 — forme VALIDÉE (par Entrée) : la mesure est figée, le prochain clic repart à zéro.
  done?: boolean
}

// M55-G point 13 — BOUTON DE CARTE MOMENTANÉ (zoom +/−…) : au clic, flash mint ~180 ms puis
// retour — un feedback d'APPUI, pas un état. Les bascules à état (3D, fond, outils) gardent
// leur état persistant comme feedback ; ce patron est pour les boutons sans état.
function BoutonCarte({ onClick, title, children }: { onClick: () => void; title: string; children: React.ReactNode }) {
  const [flash, setFlash] = useState(false)
  const timer = useRef<number | null>(null)
  useEffect(() => () => { if (timer.current) window.clearTimeout(timer.current) }, [])
  const press = () => {
    onClick()
    setFlash(true)
    if (timer.current) window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => setFlash(false), 180)
  }
  return (
    <button onClick={press} title={title}
      /* M65 P5 : dimensions réduites à 70 % de l'état M62-P1 (60→42 px, glyphe 24→17 px,
         rayon 12→8 px). Le gap entre les deux boutons est réduit au prorata côté conteneur. */
      className={`flex h-[42px] w-[42px] items-center justify-center rounded-[8px] border text-[17px] leading-none shadow-elev-1 transition-colors duration-quick ${
        flash ? 'border-mint bg-mint text-mint-ink' : 'border-line-2 bg-surface-2 text-txt hover:text-txt-hi'}`}>
      {children}
    </button>
  )
}

// M129-D P2.2 — la glose de la palette NOMME son univers : le vivier servi (hors exclusions
// légales et physiques, motifs consultables), jamais un « > 20 000 » nu.
const getPaletteToast = (total?: number) =>
  'Résultat trop large pour peindre parcelle à parcelle (> 20 000'
  + (total ? ` sur ${total.toLocaleString('fr-FR')} parcelles servies — hors exclusions légales et physiques` : '')
  + ') — la carte montre l’approximation par critères ; la liste reste exacte.'

export function MapView() {
  const ref = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map | null>(null)
  const ready = useRef(false)
  const [mapReady, setMapReady] = useState(false) // state : re-déclenche les effets APRÈS le load (remontage CRM→cartes)
  const { selectedIdu, select, filters, layers, basemap, orthoYear, terrain3d, tool, setTool, zone, setZone, moduleMap, flyTo, setFlyTo, setPermitToOpen, commune, verdict, iaRestitution, module, comparePicking, view, focusIdu, focusNonce } = useApp()
  const bpeDomains = useApp((s) => s.bpeDomains)   // M137-V — filtre par domaine de la couche BPE
  const ile = commune == null
  // M55-G point 8 — décision Vic : sans analyse demandée, l'avis LABUSE ne s'affiche pas.
  // Les couleurs d'OPINION (palette tiers, lisérés promues/brûlantes, marqueurs « chauds »)
  // n'apparaissent qu'en mode ANALYSE, ou si la couche « Verdict » est cochée explicitement.
  // Le tri factuel (verdict=true, analyse OFF) peint une surbrillance NEUTRE.
  const opinion = (verdict && filters.analyseLabuse) || layers.couleurs_verdict
  const toolRef = useRef<MapTool | null>(null)
  toolRef.current = tool
  const [measure, setMeasure] = useState<Measure>({ pts: [], alti: null })
  const measureRef = useRef(measure)
  measureRef.current = measure
  const labelMarker = useRef<maplibregl.Marker | null>(null)
  const [tilesLoading, setTilesLoading] = useState(false)   // P5 : chargement des tuiles

  // M55-D stage 9 (responsive) : le CONTENEUR carte change de taille sans resize fenêtre (largeur
  // du panneau en clamp(), sections qui s'ouvrent) → ResizeObserver recale MapLibre à chaud.
  useEffect(() => {
    const el = ref.current
    const m = map.current
    if (!el || !m || !ready.current) return
    const ro = new ResizeObserver(() => m.resize())
    ro.observe(el)
    return () => ro.disconnect()
  }, [mapReady])

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
  // M137-U — ZNIEFF (162 polygones île, commune NULL → servis partout) : contrainte, opt-in.
  const znieff = useQuery({ queryKey: ['layer', 'znieff', commune], queryFn: () => getMapLayer('znieff'), enabled: layers.znieff })
  const anru = useQuery({ queryKey: ['layer', 'anru', commune], queryFn: () => getMapLayer('anru'), enabled: layers.anru })
  // M134 — couche « Dispositifs » (servie île entière : QPV 57, buffer 13, ZFANG 24, FRR 23 — léger)
  const qpv = useQuery({ queryKey: ['layer', 'qpv', commune], queryFn: () => getMapLayer('qpv'), enabled: layers.qpv })
  const tvaPrimo = useQuery({ queryKey: ['layer', 'tva_primo', commune], queryFn: () => getMapLayer('tva_primo'), enabled: layers.tva_primo })
  const zfang = useQuery({ queryKey: ['layer', 'zfang', commune], queryFn: () => getMapLayer('zfang'), enabled: layers.zfang })
  const frr = useQuery({ queryKey: ['layer', 'frr', commune], queryFn: () => getMapLayer('frr'), enabled: layers.frr })
  // SECTEUR-2 (T4) — prix du neuf VEFA (aplat commune), choropleth par tranche.
  const vefaNeuf = useQuery({ queryKey: ['layer', 'vefa_neuf', commune], queryFn: () => getMapLayer('vefa_neuf'), enabled: layers.vefa_neuf })
  // M55-E : la couche équipements COMPLÈTE (limit 20000 = plafond endpoint ; 15 214 en base,
  // 271 Ko gzippé) — le défaut 6000 tronquait 61 % des marqueurs en mode île (centre de
  // Saint-Denis vide, Hauts couverts : l'ordre des lignes décidait des survivants).
  const equip = useQuery({ queryKey: ['layer', 'equip', commune], queryFn: () => getMapLayer('amenite', 20_000), enabled: layers.equipements })
  // M137-U — équipements INSEE BPE (kind distinct 'amenite_bpe') : 2e item, servi comme OSM. Cercles
  // bleus (vs icônes OSM) = zéro doublon visuel. FIX-COUCHES P1 : plafond porté 20 000 → 40 000 pour
  // servir les 35 546 objets ENTIERS en vue île (payload mesuré ~8 Mo brut / ~0,7 Mo gzip) ; un garde
  // no-silent-caps couvre désormais AUSSI cette couche (avant : seul l'OSM avait le sien).
  const equipBpe = useQuery({ queryKey: ['layer', 'equip_bpe', commune], queryFn: () => getMapLayer('amenite_bpe', 40_000), enabled: layers.equipements_bpe })
  // M6.1 item 2 : 50 pas géométriques (163 polygones île, commune NULL → servis partout)
  const cinquantePas = useQuery({ queryKey: ['layer', 'cinquante_pas'], queryFn: () => getMapLayer('cinquante_pas'), enabled: layers.cinquante_pas })
  // M106 P1 : aléas DEAL (993 objets île, un seul fetch — les 2 couches filtrent par subtype)
  const alea = useQuery({ queryKey: ['layer', 'georisque_alea', commune], queryFn: () => getMapLayer('georisque_alea'), enabled: layers.alea_inondation || layers.alea_mvt })
  // M106 P4 : transport public (tracés + pôles + Papang, 3 kinds servis île) et lignes HT
  const transLignes = useQuery({ queryKey: ['layer', 'transport_ligne'], queryFn: () => getMapLayer('transport_ligne'), enabled: layers.transport })
  // RETOURS-14 S7 — les ARRÊTS sont FUSIONNÉS dans « Transport public (lignes et arrêts) »
  // (demande Vic) ; ils restent cliquables (bulle : nom + lignes + réseau — R9).
  const transArrets = useQuery({ queryKey: ['layer', 'transport_arret'], queryFn: () => getMapLayer('transport_arret', 20_000), enabled: layers.transport })
  // M137-X — les pôles d'échange rejoignent « Axes structurants » (nœuds du réseau structurant).
  const poles = useQuery({ queryKey: ['layer', 'pole_echange'], queryFn: () => getMapLayer('pole_echange'), enabled: layers.axes })
  const tele = useQuery({ queryKey: ['layer', 'telepherique'], queryFn: () => getMapLayer('telepherique'), enabled: layers.transport })
  const lignesHt = useQuery({ queryKey: ['layer', 'ligne_ht'], queryFn: () => getMapLayer('ligne_ht'), enabled: layers.lignes_ht })
  // RETOURS-14 S8 — « Stationnement allégé — TCSP » : voies en site propre + stations + ZONE
  // de 800 m matérialisée (rayon autour des stations + union des parcelles couvertes, teintées).
  const tcspTroncons = useQuery({ queryKey: ['layer', 'tcsp_troncon'], queryFn: () => getMapLayer('tcsp_troncon'), enabled: layers.tcsp })
  const tcspStations = useQuery({ queryKey: ['layer', 'tcsp_station'], queryFn: () => getMapLayer('tcsp_station'), enabled: layers.tcsp })
  const tcspZone = useQuery({ queryKey: ['layer', 'tcsp_zone'], queryFn: () => getMapLayer('tcsp_zone'), enabled: layers.tcsp })
  // RETOURS-14 S9 — lignes électriques FUSIONNÉES : la HTA suit la même entrée que la HTB.
  const lignesMt = useQuery({ queryKey: ['layer', 'ligne_mt'], queryFn: () => getMapLayer('ligne_mt', 40_000), enabled: layers.lignes_ht })
  // M106-B P3 : axes structurants (3 481 tronçons BD TOPO importance 1-2)
  const axes = useQuery({ queryKey: ['layer', 'axe_structurant'], queryFn: () => getMapLayer('axe_structurant', 5_000), enabled: layers.axes })
  // M-RENOUV : segment Renouvellement (occupées, potentiel) — OFF par défaut, top rangs servis
  const renouv = useQuery({ queryKey: ['layer', 'renouv', commune], queryFn: getRenouvGeojson, enabled: layers.renouv })
  // M6.1 item 1 : les tuiles île portent-elles zone_fam ? (sinon repli honnête au prochain build)
  const tilesMeta = useQuery({ queryKey: ['tiles-meta'], queryFn: getTilesMeta, staleTime: 60_000, retry: false })
  const communes = useQuery({ queryKey: ['communes'], queryFn: getCommunes })
  // M55-G suite (point 1) — RACCORD carte↔liste : quand un critère hors-tuiles est actif en
  // mode analyse, la palette ne peut pas être exacte par expression → on demande les IDU du
  // résultat courant (plafond serveur 20 000, drapeau tronqué). La couche « Verdict — toute
  // l'île » court-circuite ce raccord (peinture explicite de tout le classement).
  const besoinIdus = verdict && filters.analyseLabuse && !layers.couleurs_verdict
    && hasCriteresHorsTuiles(filters)
  const idusQ = useQuery({
    queryKey: ['filtre-idus', filters],
    queryFn: () => getFiltreIdus(filters),
    enabled: besoinIdus, staleTime: 30_000,
  })
  const resultIdus = besoinIdus && idusQ.data && !idusQ.data.idus_tronque ? idusQ.data.idus : null
  // no-silent-caps : résultat > plafond → la carte replie sur l'approximation, et le DIT
  useEffect(() => {
    if (besoinIdus && idusQ.data?.idus_tronque) {
      useApp.getState().setToast(
        getPaletteToast(idusQ.data?.total))
    }
  }, [besoinIdus, idusQ.data])

  // le remplissage zonage n'est appliqué que si la source ACTIVE porte zone_fam :
  // geojson commune = toujours (jointure live) ; tuiles île = au prochain build-mvt
  // M12 C5 : DEUX portes vers cette recoloration — « Zonage PLU (par parcelle) » (avec étiquette
  // au zoom + popup au clic) ET la nouvelle « Colorisation par type de zonage » (lecture
  // d'ensemble, sans clic). L'une OU l'autre allume le remplissage par famille.
  // M55-A (fusion A) : une seule couche parcellaire (`zonage_parcelle`) — elle colore d'emblée
  // toutes les parcelles par famille ET porte l'étiquette (zoom) + le popup (clic).
  const zonageColor = layers.zonage_parcelle
  const zonageFill = zonageColor && (!ile || tilesMeta.data?.zonage_parcelle === true)

  // M55-G point 10 — publier au store ce que la carte PEINT réellement (la légende ne décrit
  // jamais des couleurs absentes de l'écran) : parcelles = couche active ET zoom où elles se
  // colorent (île : z ≥ 10, le seuil du bandeau « Zoomez ou cliquez une commune ») ;
  // équipements = couche active ET z ≥ 12 (leur minzoom de rendu) ; zonage = remplissage
  // par famille effectivement appliqué (zonageFill).
  useEffect(() => {
    const m = map.current
    if (!m || !ready.current) return
    const upd = () => {
      const z = m.getZoom()
      const parcVis = layers.parcelles && (!ile || z >= 10)
      useApp.getState().setMapPeint({
        parcelles: parcVis,
        equipements: layers.equipements && z >= 12,
        // RETOURS-11 C1 — la légende du zonage suit l'aplat RÉELLEMENT peint (zonageFill au bon zoom),
        // indépendamment de la couche « Limites parcelles ».
        zonage: zonageFill && (!ile || z >= 10),
      })
    }
    upd()
    m.on('zoom', upd)
    return () => { m.off('zoom', upd) }
  }, [ile, layers.parcelles, layers.equipements, zonageFill, mapReady])

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
      // FIX-CARTE B1 : navigation bornée à La Réunion + zooms cohérents avec la source (parcelles
      // MVT z9-15 ; sous z8 l'île déborde du cadre, au-delà de z19 le sur-zoom de z15 est trop mou).
      maxBounds: REUNION_MAXBOUNDS,
      minZoom: 8,
      maxZoom: 19,
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
      // fonds de plan (tous chargés, visibilité pilotée par l'effet fond via activeBasemapKey —
      // FOND-SOMBRE : plus de fond visible à la création, le défaut « dark » n'a plus de raster)
      for (const [id, src] of Object.entries(BASEMAP_SOURCES)) {
        // RETOURS-12 C6 — `bounds` sur les fonds ortho (emprise 974) : maplibre ne demande plus les
        // tuiles no-data (blanches) au large → fini l'escalier de tuiles sur fond blanc en vue dézoomée.
        m.addSource(id, { type: 'raster', tiles: src.tiles, tileSize: 256, attribution: src.attribution, ...(src.maxzoom ? { maxzoom: src.maxzoom } : {}), ...(src.bounds ? { bounds: src.bounds } : {}) })
        m.addLayer({ id, type: 'raster', source: id, layout: { visibility: 'none' } })
      }
      // RETOURS-13 R1 — MASQUE DE MER sous les fonds ORTHO : les bounds C6 ne suffisaient pas —
      // les tuiles jpeg qui INTERSECTENT l'emprise sont quand même servies, et leur no-data est
      // BLANC OPAQUE → au cadrage « île entière » la mer restait un escalier de tuiles bleues sur
      // fond blanc (constat Vic, 04 ET 05/09). Le masque = un polygone monde TROUÉ par le contour
      // dissous de l'île (ile974.geojson), peint couleur de mer sombre AU-DESSUS des rasters ortho :
      // la mer est CONTINUE jusqu'aux bords, quel que soit ce qu'IGN sert. Visible sur les fonds
      // ortho seulement (Plan IGN dessine sa propre mer ; Sombre/Clair n'ont pas de raster).
      m.addSource('mer-mask', { type: 'geojson', data: EMPTY_FC as never })
      m.addLayer({ id: 'mer-mask', type: 'fill', source: 'mer-mask', layout: { visibility: 'none' },
        paint: { 'fill-color': SOMBRE_BG, 'fill-opacity': 1 } })
      fetch(`${(import.meta as unknown as { env: { BASE_URL: string } }).env.BASE_URL}ile974.geojson`)
        .then((r) => r.json())
        .then((fc: { features: { geometry: { type: string; coordinates: unknown } }[] }) => {
          const holes: unknown[] = []
          for (const f of fc.features ?? []) {
            const g = f.geometry
            if (g?.type === 'Polygon') holes.push((g.coordinates as unknown[])[0])
            else if (g?.type === 'MultiPolygon') for (const poly of g.coordinates as unknown[][]) holes.push(poly[0])
          }
          const world = [[54.0, -22.5], [57.5, -22.5], [57.5, -19.8], [54.0, -19.8], [54.0, -22.5]]
          const srcMask = m.getSource('mer-mask') as maplibregl.GeoJSONSource | undefined
          srcMask?.setData({ type: 'Feature', properties: {},
            geometry: { type: 'Polygon', coordinates: [world, ...holes] } } as never)
        })
        .catch(() => { /* masque absent = comportement C6 (dégradé, jamais bloquant) */ })
      // M65 P8 — MASSE TERRESTRE (île dissoute) : la terre sans parcelle (cirques, forêt, volcan)
      // prend l'aplat du thème — GRIS #C9C4B8 en Clair, terre mesurée SOMBRE_TERRE en Sombre
      // (FOND-SOMBRE ; applyClairMode pose teinte et visibilité). Posée TOUT EN BAS de la pile
      // vectorielle (juste au-dessus des rasters) → sous TOUS les overlays (risques, zonages) et
      // les parcelles, qui restent lisibles par-dessus. Masquée sous Plan/Ortho (elle recouvrirait
      // leurs tuiles). Source ile974.geojson = 24 communes DISSOUES.
      m.addSource('ile-mass', { type: 'geojson', data: `${(import.meta as unknown as { env: { BASE_URL: string } }).env.BASE_URL}ile974.geojson` })
      m.addLayer({ id: 'ile-mass', type: 'fill', source: 'ile-mass', layout: { visibility: 'none' },
        paint: { 'fill-color': '#C9C4B8', 'fill-opacity': 1 } })
      // MNT (relief 3D) — terrarium AWS (libre)
      m.addSource('dem', { type: 'raster-dem', encoding: 'terrarium', tileSize: 256, maxzoom: 13,
        tiles: ['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'] })

      m.addSource('parcels', { type: 'geojson', data: EMPTY_FC as never, promoteId: 'idu' })
      for (const k of Object.keys(OVERLAYS)) m.addSource(`ov-${k}`, { type: 'geojson', data: EMPTY_FC as never })
      for (const [k, o] of Object.entries(OVERLAYS)) {
        m.addLayer({ id: `ov-${k}`, type: 'fill', source: `ov-${k}`, layout: { visibility: 'none' }, paint: o.paint as never })
      }
      // M105-B : CONTOURS de zonage et PPR (teinte identitaire saturée) — c'est le contour qui
      // différencie les couches actives ensemble, pas l'aplat (doctrine arbitrée). Largeur portée
      // par le thème : 0 en Sombre (aucun contour, comme toujours), 1 px en Clair.
      m.addLayer({ id: 'ov-zonage-line', type: 'line', source: 'ov-zonage', layout: { visibility: 'none' },
        paint: { 'line-color': zonageFillExpr(T_SOMBRE), 'line-width': T_SOMBRE.zonageContourW, 'line-opacity': 0.9 } })
      m.addLayer({ id: 'ov-ppr-line', type: 'line', source: 'ov-ppr', layout: { visibility: 'none' },
        paint: { 'line-color': T_SOMBRE.ppr, 'line-width': T_SOMBRE.pprContourW, 'line-opacity': 0.9 } })
      // M105-B : TRAME diagonale ANRU (daltonisme — zonage U vert et ANRU chartreuse quasi
      // confondus en deutéranopie : la trame est la seconde variable). Opacité portée par le
      // thème : 0 en Sombre (invisible), posée en Clair par applyClairMode.
      makeTrameAnru(m)
      m.addLayer({ id: 'ov-anru-trame', type: 'fill', source: 'ov-anru', layout: { visibility: 'none' },
        paint: { 'fill-pattern': 'trame-anru', 'fill-opacity': T_SOMBRE.anruTrameOpacity } })
      // SECTEUR-2b (U1) — HACHURE GRISE des communes VEFA sous le seuil (subtype 'sous_seuil') : jamais
      // vides. Motif gris posé sur l'aplat gris muet ; « moins de 10 ventes » se lit dans le « i ».
      makeTrame(m, 'trame-vefa-sous', '#9AA0A6', 'backslash')
      m.addLayer({ id: 'ov-vefa_neuf-trame', type: 'fill', source: 'ov-vefa_neuf',
        filter: ['==', ['get', 'subtype'], 'sous_seuil'] as unknown as maplibregl.FilterSpecification,
        layout: { visibility: 'none' },
        paint: { 'fill-pattern': 'trame-vefa-sous', 'fill-opacity': 0.55 } })
      // SECTEUR-2b (U1) — CLIC sur une commune de la couche VEFA → panneau de détail. Le `name` porte
      // « Commune · … » : on en tire le nom, le panneau résout l'INSEE et lit les moteurs existants.
      m.on('click', 'ov-vefa_neuf', (e) => {
        if (!useApp.getState().layers.vefa_neuf) return
        const nom = String(e.features?.[0]?.properties?.name ?? '').split(' · ')[0].trim()
        if (nom) { useApp.getState().setVefaCommune(nom); (e as maplibregl.MapLayerMouseEvent).preventDefault() }
      })
      m.on('mouseenter', 'ov-vefa_neuf', () => { if (useApp.getState().layers.vefa_neuf) m.getCanvas().style.cursor = 'pointer' })
      m.on('mouseleave', 'ov-vefa_neuf', () => { m.getCanvas().style.cursor = '' })
      // P10 : liseré marron du Parc national (borne nette)
      m.addLayer({ id: 'ov-parc-line', type: 'line', source: 'ov-parc', layout: { visibility: 'none' },
        paint: { 'line-color': PARC_LINE, 'line-width': 1.2, 'line-opacity': 0.7 } })
      // M6.1 item 2 : 50 pas géométriques — remplissage léger + CONTOUR CÔTIER tireté
      // (style distinct : bande littorale, pas une couche de zonage pleine)
      m.addSource('ov-50pas', { type: 'geojson', data: EMPTY_FC as never })
      m.addLayer({ id: 'ov-50pas', type: 'fill', source: 'ov-50pas', layout: { visibility: 'none' },
        paint: { 'fill-color': T_SOMBRE.cinquantePas, 'fill-opacity': T_SOMBRE.cinquantePasFillOpacity } })
      m.addLayer({ id: 'ov-50pas-line', type: 'line', source: 'ov-50pas', layout: { visibility: 'none' },
        paint: { 'line-color': T_SOMBRE.cinquantePas, 'line-width': 1.6, 'line-dasharray': [2, 1.4], 'line-opacity': 0.9 } })
      // M106 P1 : ALÉAS DEAL SÉPARÉS — deux couches depuis un même flux (kind=georisque_alea,
      // filtrées par subtype), là où le zonage PPR réglementaire est multirisque insécable.
      // Aplat GRADUÉ par le niveau servi + contour + trame (superposables, doctrine M105-B) —
      // dans les DEUX thèmes ; les valeurs vivent dans mapTheme.
      m.addSource('ov-alea', { type: 'geojson', data: EMPTY_FC as never })
      for (const c of ALEA_COUCHES) {
        const filt = ['==', ['get', 'subtype'], c.sub] as unknown as maplibregl.FilterSpecification
        // R7 — plus de trame : aplat plein semi-transparent seul. R8 — contour géré par le zoom
        // (ALEA_LINE_W/OP, même règle sur les 4 fonds).
        m.addLayer({ id: c.id, type: 'fill', source: 'ov-alea', filter: filt, layout: { visibility: 'none' },
          paint: { 'fill-color': aleaColorExpr(T_SOMBRE, c.ramp), 'fill-opacity': T_SOMBRE.aleaFillOpacity } })
        m.addLayer({ id: `${c.id}-line`, type: 'line', source: 'ov-alea', filter: filt, layout: { visibility: 'none' },
          paint: { 'line-color': T_SOMBRE[c.token], 'line-width': ALEA_LINE_W, 'line-opacity': ALEA_LINE_OP } })
      }
      // M137-X — trame ZFANG/FRR : l'état « fort » (renforcée / en partie) se lit à la HACHURE
      // (aplat = état de base), texture catégorielle plutôt qu'un dégradé d'opacité ambigu.
      for (const [src, sub, tok, orient] of DISPO_TRAMES) {
        // hachure = shade PLUS FONCÉ de l'aplat → lisible quelle que soit la teinte de l'état.
        makeTrame(m, `trame-${tok}-sombre`, darken(MAP_THEME.sombre[tok], 0.6), orient)
        makeTrame(m, `trame-${tok}-clair`, darken(MAP_THEME.clair[tok], 0.55), orient)
        m.addLayer({ id: `${src}-trame`, type: 'fill', source: src,
          filter: ['==', ['get', 'subtype'], sub] as never, layout: { visibility: 'none' },
          paint: { 'fill-pattern': 'trame-' + tok + '-sombre', 'fill-opacity': T_SOMBRE.aleaTrameOpacity } })
      }
      // M106 P4 / M106-B : TRANSPORT PUBLIC — LA COULEUR DIT LE RÉSEAU, LA FORME DIT LE TYPE :
      // tracé = trait · arrêt = petit point (minzoom 12, sinon 9 956 points noient l'île) ·
      // pôle OSM (Sourcé) = disque plein NEUTRE · pôle dérivé (Estimé) = anneau ·
      // téléphérique = tireté couleur CINOR/Citalis. Plus les AXES STRUCTURANTS (BD TOPO,
      // importance IGN 1-2, trait plein ardoise) et les LIGNES HT (anthracite tireté).
      for (const src of ['ov-trans-ligne', 'ov-trans-arret', 'ov-pole', 'ov-tele', 'ov-axe', 'ov-ht', 'ov-mt', 'ov-tcsp', 'ov-tcsp-st', 'ov-tcsp-zone']) {
        m.addSource(src, { type: 'geojson', data: EMPTY_FC as never })
      }
      m.addLayer({ id: 'ov-axe', type: 'line', source: 'ov-axe', layout: { visibility: 'none' },
        paint: { 'line-color': T_SOMBRE.axe, 'line-width': 2.2, 'line-opacity': 0.85 } })
      m.addLayer({ id: 'ov-trans-ligne', type: 'line', source: 'ov-trans-ligne', layout: { visibility: 'none' },
        paint: { 'line-color': reseauColorExpr(T_SOMBRE), 'line-width': 1.3, 'line-opacity': 0.75 } })
      // RETOURS-12 C5 — arrêts NETTEMENT plus visibles : rayon proportionné au zoom (discret à
      // l'échelle île, franc à l'échelle quartier) + contour sombre pour tenir sur fond clair comme
      // sur ortho. Un arrêt se lit comme un arrêt, plus comme un pixel sur le trait.
      m.addLayer({ id: 'ov-trans-arret', type: 'circle', source: 'ov-trans-arret', minzoom: 11,
        layout: { visibility: 'none' },
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 11, 3, 14, 5.5, 16, 8, 18, 10] as unknown as maplibregl.ExpressionSpecification,
          'circle-color': reseauColorExpr(T_SOMBRE), 'circle-opacity': 0.9,
          'circle-stroke-color': '#0A0F0C', 'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 11, 0.8, 16, 1.6] as unknown as maplibregl.ExpressionSpecification,
        } })
      // RETOURS-13 R9 — arrêts CLIQUABLES : une bulle MINIMALE — nom de l'arrêt, ligne(s) qui le
      // desservent, réseau. Rien d'autre (demande Vic). Les noms de lignes viennent de routes.txt
      // (attrs.lignes_noms, backfillés + posés à l'ingestion) ; nested array → maplibre sérialise
      // en chaîne JSON dans les properties, on la reparse.
      const escHtml = (s: unknown) => String(s ?? '').replace(/[<>&"]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;' }[c] as string))
      m.on('click', 'ov-trans-arret', (e) => {
        const f = e.features?.[0]
        if (!f) return
        const p = f.properties as Record<string, unknown>
        let lignes: string[] = []
        try {
          lignes = typeof p.lignes_noms === 'string' ? JSON.parse(p.lignes_noms) : ((p.lignes_noms as string[]) ?? [])
        } catch { lignes = [] }
        const html = `<div style="${POPUP_BOX_CSS}">`
          + `<div style="font-weight:600">${escHtml(p.name)}</div>`
          + (lignes.length ? `<div style="margin-top:4px">Ligne${lignes.length > 1 ? 's' : ''} ${escHtml(lignes.join(' · '))}</div>` : '')
          + `<div style="margin-top:2px;color:#96A69C">${escHtml(p.reseau ?? p.subtype ?? '')}</div></div>`
        new maplibregl.Popup({ closeButton: false, maxWidth: '300px' }).setLngLat(e.lngLat).setHTML(html).addTo(m)
      })
      m.on('mouseenter', 'ov-trans-arret', () => { m.getCanvas().style.cursor = 'pointer' })
      m.on('mouseleave', 'ov-trans-arret', () => { m.getCanvas().style.cursor = '' })
      m.addLayer({ id: 'ov-tele', type: 'line', source: 'ov-tele', layout: { visibility: 'none' },
        filter: ['==', ['get', 'subtype'], 'ligne'] as never,
        paint: { 'line-color': T_SOMBRE.transportReseaux['Papang'], 'line-width': 2.4, 'line-dasharray': [1.6, 1.2], 'line-opacity': 0.95 } })
      m.addLayer({ id: 'ov-tele-st', type: 'circle', source: 'ov-tele', layout: { visibility: 'none' },
        filter: ['==', ['get', 'subtype'], 'station'] as never,
        paint: { 'circle-radius': 4, 'circle-color': T_SOMBRE.transportReseaux['Papang'], 'circle-stroke-color': SOMBRE_BG, 'circle-stroke-width': 1.2 } })
      m.addLayer({ id: 'ov-pole', type: 'circle', source: 'ov-pole', layout: { visibility: 'none' },
        paint: { 'circle-radius': 5,
                 'circle-color': T_SOMBRE.pole,
                 'circle-opacity': ['case', ['==', ['get', 'subtype'], 'osm'], 0.95, 0] as never,
                 'circle-stroke-color': T_SOMBRE.pole, 'circle-stroke-width': 2 } })
      m.addLayer({ id: 'ov-ht', type: 'line', source: 'ov-ht', layout: { visibility: 'none' },
        paint: { 'line-color': T_SOMBRE.ht, 'line-width': 1.6, 'line-dasharray': [5, 2.5], 'line-opacity': 0.9 } })
      // RETOURS-13 R4 — moyenne tension HTA (EDF open data) : même famille de contrainte que la
      // HTB mais tireté COURT et FIN (la forme et la valeur les séparent), teinte gris-sarcelle.
      m.addLayer({ id: 'ov-mt', type: 'line', source: 'ov-mt', layout: { visibility: 'none' },
        paint: { 'line-color': T_SOMBRE.mt, 'line-width': 1.1, 'line-dasharray': [2, 1.6], 'line-opacity': 0.85 } })
      // RETOURS-13 R5 — TCSP : trait PLEIN ÉPAIS pour les tronçons EN SITE PROPRE (la voie dédiée
      // se lit d'un coup) ; trait FIN TIRETÉ pour les simples couloirs bus (dits, jamais confondus) ;
      // STATIONS dérivées en disques (le drapeau < 800 m se mesure à la station, pas au tracé).
      // RETOURS-14 S8 — la ZONE d'abord (sous les tronçons) : parcelles couvertes TEINTÉES
      // (union exacte de leurs géométries) + contour du rayon de 800 m. Les couloirs bus ne
      // s'affichent plus ici (pas un site propre L151-36 — légende à 3 entrées).
      m.addLayer({ id: 'ov-tcsp-zone-parcelles', type: 'fill', source: 'ov-tcsp-zone',
        filter: ['==', ['get', 'subtype'], 'parcelles'] as never, layout: { visibility: 'none' },
        paint: { 'fill-color': T_SOMBRE.tcsp, 'fill-opacity': 0.22 } })
      m.addLayer({ id: 'ov-tcsp-zone-rayon', type: 'line', source: 'ov-tcsp-zone',
        filter: ['==', ['get', 'subtype'], 'rayon'] as never, layout: { visibility: 'none' },
        paint: { 'line-color': T_SOMBRE.tcsp, 'line-width': 1.6, 'line-dasharray': [3, 2], 'line-opacity': 0.85 } })
      m.addLayer({ id: 'ov-tcsp', type: 'line', source: 'ov-tcsp', layout: { visibility: 'none', 'line-cap': 'round' },
        filter: ['==', ['get', 'subtype'], 'site_propre'] as never,
        paint: { 'line-color': T_SOMBRE.tcsp, 'line-width': ['interpolate', ['linear'], ['zoom'], 9, 2.5, 13, 4, 16, 6] as unknown as maplibregl.ExpressionSpecification, 'line-opacity': 0.95 } })
      m.addLayer({ id: 'ov-tcsp-st', type: 'circle', source: 'ov-tcsp-st', layout: { visibility: 'none' },
        paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 10, 3.5, 14, 6, 17, 9] as unknown as maplibregl.ExpressionSpecification,
                 'circle-color': T_SOMBRE.tcsp, 'circle-opacity': 0.95,
                 'circle-stroke-color': '#0A0F0C', 'circle-stroke-width': 1.4 } })
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
      // M55-G suite (point 1) : TRAME NEUTRE sous la palette — quand la palette est restreinte
      // au résultat courant (IDU), le reste des parcelles reste visible en trame cadastrale
      // neutre au lieu de disparaître. Visible seulement dans ce mode (effet plus bas).
      m.addLayer({ id: 'parcels-base', type: 'fill', source: 'parcels', layout: { visibility: 'none' },
        paint: { 'fill-color': '#22302A', 'fill-opacity': 0.28 } })
      // RETOURS-11 R2 (04/09) — VERDICT : « Parcelles » (parcels-fill) est GARDÉE, distincte de
      // « Limites parcelles ». Mesure du paint : parcels-fill peint un APLAT COLORÉ PAR STATUT/TIER
      // (STATUS_COLOR/STATUS_OPACITY : brûlante, chaude, réserve, à creuser… teintes et opacités
      // par tier), info que « Limites parcelles » (parcels-limites) ne porte pas — celle-ci n'est
      // qu'un contour gris uni sans couleur. Les deux ne font PAS doublon → on garde le second
      // interrupteur et on précise son « i » (cf. lib/layers LAYER_INFO.parcelles).
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
        paint: { 'line-color': T_SOMBRE.lisereBrulantes, 'line-width': 1.8, 'line-opacity': 0.95 },
      })
      // M55-F point 4 (décision Vic) : les étiquettes « #rang » ont QUITTÉ la carte — la
      // référence cadastrale vit sur la fiche. Layer parcels-v-badge retirée (0-caller).
      // M6.1 item 1 : étiquette de la zone PLU PRÉCISE (zone_lib) — mode commune.
      // RETOURS-11 R1 (04/09) : les lettres apparaissent PLUS TÔT (minzoom 16 → 14, trop zoomé
      // avant). Pour ne pas saturer au zoom moyen, on laisse MapLibre trier naturellement les
      // étiquettes : text-allow-overlap=false + symbol-spacing large (250) → à ~14-15 on obtient
      // grosso modo UNE lettre par bloc de zone, pas une par parcelle ; en zoom rapproché la
      // densité remonte. text-size interpolée (plus petite à 14, 11 dès 16).
      const ZONE_LABEL_LAYOUT = {
        'text-field': ['coalesce', ['get', 'zone_lib'], ''] as never,
        'text-font': ['Open Sans Regular'] as string[],
        'text-size': ['interpolate', ['linear'], ['zoom'], 14, 9, 16, 11] as never,
        'text-optional': true, 'text-allow-overlap': false, 'text-ignore-placement': false,
        'symbol-spacing': 250,
      }
      m.addLayer({
        id: 'parcels-zone-label', type: 'symbol', source: 'parcels', minzoom: 14,
        // FOND-SOMBRE : text-font EXPLICITE = la pile du dossier de glyphs embarqué (cf. STYLE.glyphs)
        layout: { visibility: 'none', ...ZONE_LABEL_LAYOUT },
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
      // M105-B : contours jumeaux côté île (mêmes tokens de thème que ov-zonage-line/ov-ppr-line)
      m.addLayer({ id: 'ovmvt-zonage-line', type: 'line', source: 'ovmvt-zonage', 'source-layer': 'plu_gpu_zone',
        layout: { visibility: 'none' },
        paint: { 'line-color': zonageFillExpr(T_SOMBRE), 'line-width': T_SOMBRE.zonageContourW, 'line-opacity': 0.9 } })
      m.addLayer({ id: 'ovmvt-ppr-line', type: 'line', source: 'ovmvt-ppr', 'source-layer': 'ppr',
        layout: { visibility: 'none' },
        paint: { 'line-color': T_SOMBRE.ppr, 'line-width': T_SOMBRE.pprContourW, 'line-opacity': 0.9 } })

      // ── mode ÎLE : calques jumeaux sur tuiles MVT (431k parcelles — le GeoJSON ne tient pas) ──
      m.addSource('parcels-ile', { type: 'vector', minzoom: 9, maxzoom: 15,
        tiles: [`${window.location.origin}/map/tiles/{z}/{x}/{y}.pbf`] })
      const SL = { source: 'parcels-ile', 'source-layer': 'parcels' } as const
      // M55-G suite (point 1) : trame neutre jumelle côté île (cf. parcels-base)
      m.addLayer({ id: 'ile-base', type: 'fill', ...SL, layout: { visibility: 'none' },
        paint: { 'fill-color': '#22302A', 'fill-opacity': 0.28 } })
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
        paint: { 'line-color': '#4ADE80', 'line-width': 0.8, 'line-opacity': 0.85 } })
      // M6.1 : étiquette zone PLU en mode île — ne rend que si les tuiles portent zone_lib
      // (prochain build-mvt) ; d'ici là text-field vide = aucun rendu, rien ne casse
      m.addLayer({
        id: 'ile-zone-label', type: 'symbol', ...SL, minzoom: 14,   // RETOURS-11 R1 : idem parcels-zone-label
        // FOND-SOMBRE : text-font EXPLICITE = la pile du dossier de glyphs embarqué (cf. STYLE.glyphs)
        layout: { visibility: 'none', ...ZONE_LABEL_LAYOUT },
        paint: { 'text-color': '#ECF5EF', 'text-halo-color': '#06130C', 'text-halo-width': 1.3 },
      })

      // M65 P8 — TRAIT DE CÔTE : il sépare le noir de la mer et le clair de la terre. Posé
      // au-dessus des remplissages (parcelles/île). Sur le contour DISSOUS uniquement (jamais
      // les limites internes des communes). Masqué en Sombre. 2,2 px.
      // M105-B : la couche ne rend qu'en Clair — création directement au token clair
      // (#14713E, 3,49:1 sur la masse grise, son fond principal ; le #4ADE80 d'origine y
      // faisait 1,00 — invisible). Le vert reste vert, la famille mint est conservée.
      m.addLayer({ id: 'ile-cote', type: 'line', source: 'ile-mass', layout: { visibility: 'none' },
        paint: { 'line-color': MAP_THEME.clair.cote, 'line-width': 2.2, 'line-opacity': 0.95 } })

      // mesure (ligne + polygone + points + étiquette)
      m.addSource('measure', { type: 'geojson', data: EMPTY_FC as never })
      m.addLayer({ id: 'measure-fill', type: 'fill', source: 'measure', filter: ['==', ['geometry-type'], 'Polygon'], paint: { 'fill-color': '#5CE6A1', 'fill-opacity': 0.12 } })
      m.addLayer({ id: 'measure-line', type: 'line', source: 'measure', filter: ['in', ['geometry-type'], ['literal', ['LineString', 'Polygon']]], paint: { 'line-color': '#5CE6A1', 'line-width': 2, 'line-dasharray': [2, 1.5] } })
      m.addLayer({ id: 'measure-pts', type: 'circle', source: 'measure', filter: ['==', ['geometry-type'], 'Point'], paint: { 'circle-radius': 3.5, 'circle-color': '#5CE6A1', 'circle-stroke-color': '#06130C', 'circle-stroke-width': 1.5 } })

      // calques MODULE (violet) : surlignage de parcelles + géométries propres (lots, permis)
      m.addSource('module-extra', { type: 'geojson', data: EMPTY_FC as never })
      m.addLayer({ id: 'module-hl', type: 'line', source: 'parcels', filter: ['==', ['get', 'idu'], ''],
        paint: { 'line-color': '#4ADE80', 'line-width': 1.6, 'line-opacity': 0.95 } })
      m.addLayer({ id: 'ile-hl', type: 'line', source: 'parcels-ile', 'source-layer': 'parcels',
        layout: { visibility: 'none' }, filter: ['==', ['get', 'idu'], ''],
        paint: { 'line-color': '#4ADE80', 'line-width': 1.6, 'line-opacity': 0.95 } })
      m.addLayer({ id: 'module-lot', type: 'line', source: 'module-extra',
        filter: ['==', ['get', 'kind'], 'lot'],
        paint: { 'line-color': '#4ADE80', 'line-width': 1.8, 'line-dasharray': [2, 1.6] } })
      // ÉTUDE DE ZONE Z3/Z4 — l'isochrone (zone atteignable) : remplissage discret + liseré de marque,
      // SOUS les points (le point d'origine et les concurrents restent au-dessus). kind='zone-iso'.
      m.addLayer({ id: 'module-zone-fill', type: 'fill', source: 'module-extra',
        filter: ['==', ['get', 'kind'], 'zone-iso'],
        paint: { 'fill-color': '#4ADE80', 'fill-opacity': 0.08 } })
      m.addLayer({ id: 'module-zone-line', type: 'line', source: 'module-extra',
        filter: ['==', ['get', 'kind'], 'zone-iso'],
        paint: { 'line-color': '#4ADE80', 'line-opacity': 0.6, 'line-width': 2 } })
      m.addLayer({ id: 'module-pts', type: 'circle', source: 'module-extra',
        // LOT8b — la même couche de points sert les permis (radar) ET les piscines (« 💧 Voir sur la
        // carte » : toutes les piscines de l'île en marqueurs). Les deux ne coexistent jamais (outils
        // distincts alimentent module-extra), le clic route selon la propriété présente (permit_id/idu).
        // ÉTUDE DE ZONE Z4 — 'zone-concurrent' (SIRENE, ambre) et 'zone-origin' (le point étudié, mint)
        // partagent cette couche (outils distincts alimentent module-extra, jamais en même temps).
        // RETOURS-11 R8 (04/09) — les piscines ont QUITTÉ cette couche de ronds : elles sont rendues en
        // GOUTTE D'EAU par la couche symbol `module-piscine` juste dessous (plus parlant qu'un point vert).
        filter: ['in', ['get', 'kind'], ['literal', ['permis', 'radar', 'zone-concurrent', 'zone-origin', 'operation']]],
        // radar-permis (agrandissement) : rayon ZOOM-ADAPTATIF — modéré en vue île (limite le
        // chevauchement des permis groupés en centre-ville), NETTEMENT plus gros en zoom rue où
        // l'on clique un permis précis (cible large, prime sur la parcelle). Opacité < 1 + contour
        // sombre : les points qui se recouvrent restent lisibles (densité visible, bords séparés).
        // RADAR P3 — les pins Radar (kind='radar') sont différenciés par STATUT (jamais le mauve, réservé
        // IA) ; permis/piscine gardent le vert de marque.
        paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 10, 5, 13, 9, 15, 12, 18, 17],
                 'circle-color': ['case',
                   ['==', ['get', 'kind'], 'zone-concurrent'], '#E0A94F',
                   // SECTEUR-2 (T2) — opérations de promoteurs (veille) en AMBRE ; cité par une annonce
                   // neuve du Radar → menthe (l'œil repère les opérations déjà commercialisées).
                   ['all', ['==', ['get', 'kind'], 'operation'], ['==', ['get', 'radar_cite'], true]], '#4ADE80',
                   ['==', ['get', 'kind'], 'operation'], '#E0A94F',
                   ['==', ['get', 'kind'], 'zone-origin'], '#4ADE80',
                   // O2-1 (OUTILS-2) — permis au POINT MORT en ROUGE, en cours en VERT : l'œil sépare la
                   // veille concurrentielle des opportunités dormantes sans changer d'écran.
                   ['all', ['==', ['get', 'kind'], 'permis'], ['==', ['get', 'point_mort'], true]], '#E2726A',
                   ['==', ['get', 'kind'], 'radar'],
                   ['match', ['get', 'statut'],
                     'active', '#4ADE80', 'en_vente_longue', '#E0A94F', 'a_reverifier', '#8FB4F0',
                     'vendue', '#E2726A', '#8FB4F0'],
                   '#4ADE80'],
                 'circle-opacity': 0.8,
                 'circle-stroke-color': '#0b0f14', 'circle-stroke-width': 1.5 } })
      // RETOURS-11 R8 — PISCINES : marqueur GOUTTE D'EAU (emoji 💧) au lieu du rond vert. Même source
      // (module-extra) et même visibilité que module-pts ; le clic route par idu (cf. handler partagé).
      m.addLayer({ id: 'module-piscine', type: 'symbol', source: 'module-extra',
        filter: ['==', ['get', 'kind'], 'piscine'],
        // R10 — ICÔNE canvas (piscine-drop), plus jamais `text-field:'💧'` (glyphes emoji absents →
        // rien ne s'affichait). icon-allow-overlap : les gouttes proches ne se masquent pas.
        layout: { 'icon-image': 'piscine-drop', 'icon-allow-overlap': true, 'icon-ignore-placement': true,
          'icon-size': ['interpolate', ['linear'], ['zoom'], 10, 0.5, 15, 0.8, 18, 1.1] as never } })
      // PERMIS (refonte) — anneau de SURVOL : le point du permis survolé dans la liste « s'allume »
      // (source dédiée à UN point → aucun re-render des 8 000 points de la couche radar).
      m.addSource('permit-hover', { type: 'geojson', data: EMPTY_FC as never })
      m.addLayer({ id: 'permit-hover-ring', type: 'circle', source: 'permit-hover',
        paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 10, 9, 13, 14, 15, 18, 18, 24],
                 'circle-color': 'transparent', 'circle-stroke-color': '#ffffff', 'circle-stroke-width': 2.5,
                 'circle-stroke-opacity': 0.95 } })
      // radar-permis — les points permis sont CLIQUABLES : un clic ouvre la fiche permis (drawer M03,
      // détails + « localiser la parcelle »). Le permit_id voyage dans les properties de la feature.
      // La zone cliquable du point PRIME sur la parcelle : preventDefault() (comme les équipements,
      // M55-A) → les handlers parcels-fill / ile-fill et le clic universel testent `defaultPrevented`
      // et s'abstiennent (jamais la fiche parcelle sous le point). stopPropagation seul ne suffisait
      // PAS (il n'arrête pas les autres abonnés maplibre du même clic).
      const onModulePtClick = (e: maplibregl.MapLayerMouseEvent) => {
        const props = e.features?.[0]?.properties
        const pid = props?.permit_id
        if (props?.kind === 'radar' && props?.bien_id != null) {
          // RADAR P3 — clic sur un pin Radar → sélectionne la parcelle ET ouvre la fiche du bien.
          if (props?.idu) select(String(props.idu))
          useApp.getState().setRadarToOpen(Number(props.bien_id))
          ;(e as maplibregl.MapLayerMouseEvent).preventDefault()
        } else if (props?.kind === 'operation') {
          // RETOURS-3 R4.1 — clic sur une opération → POPUP des faits : propriétaire moral, nb de permis,
          // période, et le PROGRAMME rattaché (nom + lien) quand il existe. Puis deux chemins : la fiche
          // parcelle, et « voir son patrimoine » (Scan patrimoine, même SIREN). DOM textContent (anti-injection).
          const catLbl: Record<string, string> = { promoteur: 'Promoteur', bailleur: 'Bailleur social', sem: 'SEM' }
          // RETOURS-5 T3 — popup SOMBRE à la DA (jamais de fond blanc illisible) : le box porte la carte
          // (fond rgba(14,18,16,.97), bord --card-line, ombre) ; className 'labuse-popup' neutralise le
          // conteneur MapLibre blanc par défaut (contenu transparent, tip sombre).
          const box = document.createElement('div'); box.style.cssText = POPUP_BOX_CSS
          const nom = document.createElement('b'); nom.textContent = String(props.denomination || '(propriétaire non nommé)')
          nom.style.cssText = 'display:block;font-size:14px;font-weight:650;white-space:nowrap;overflow:hidden;text-overflow:ellipsis'; box.appendChild(nom)
          const cat = catLbl[String(props.categorie)] || String(props.categorie || '')
          const np = Number(props.n_permis) || 0
          const per = (() => {
            const fmtD = (s: string) => { const t = new Date(s); return Number.isNaN(t.getTime()) ? '' : t.toLocaleDateString('fr-FR') }
            const a = props.date_min ? fmtD(String(props.date_min)) : '', b = props.date_max ? fmtD(String(props.date_max)) : ''
            return a && b && a !== b ? `${a} → ${b}` : (b || a)
          })()
          // RETOURS-5 T3 — les faits sur DEUX lignes lisibles ; jamais deux dates collées bout à bout.
          const fx = document.createElement('div'); fx.style.cssText = 'color:#98a39d;font-size:12px;margin-top:5px;line-height:1.55'
          const l1 = `${cat}${cat ? ' · ' : ''}${np} permis${props.nb_logements ? ` · ${props.nb_logements} logement${Number(props.nb_logements) > 1 ? 's' : ''}` : ''}`
          const l2 = `${props.commune ? String(props.commune) : ''}${per ? `${props.commune ? ' · ' : ''}${per}` : ''}`
          fx.textContent = l1; if (l2) { const br = document.createElement('br'); fx.appendChild(br); fx.appendChild(document.createTextNode(l2)) }
          box.appendChild(fx)
          // le PROGRAMME rattaché (nom + lien externe) — un FAIT + un LIEN, jamais un visuel d'annonce.
          if (props.prog_nom) {
            const pg = document.createElement('div'); pg.style.cssText = 'margin-top:6px;padding:5px 7px;border:1px solid rgba(74,222,128,.25);background:rgba(74,222,128,.05);border-radius:6px'
            const pn = document.createElement('b'); pn.textContent = String(props.prog_nom); pn.style.color = '#e7e5e4'; pg.appendChild(pn)
            if (props.prog_url) {
              const a = document.createElement('a'); a.href = String(props.prog_url); a.target = '_blank'; a.rel = 'noreferrer noopener'
              a.textContent = ` · site de ${String(props.prog_promoteur || 'ce promoteur')} ↗`
              a.style.cssText = 'color:#4ADE80;font-size:11px;text-decoration:none'; pg.appendChild(a)
            }
            box.appendChild(pg)
          }
          // RETOURS-4 S5.3 / T3 — les deux actions CÔTE À CÔTE sur une ligne, chacune dans un cadre discret.
          const row = document.createElement('div'); row.style.cssText = 'display:flex;flex-wrap:nowrap;gap:7px;margin-top:11px'
          const actCss = 'flex:1;text-align:center;color:#4ADE80;background:none;border:1px solid rgba(74,222,128,.35);border-radius:8px;cursor:pointer;font:12px system-ui;padding:7px 6px;white-space:nowrap'
          if (props.idu) {
            const bp = document.createElement('button'); bp.textContent = 'voir la parcelle →'
            bp.style.cssText = actCss
            bp.addEventListener('click', () => { select(String(props.idu)); popup.remove() }); row.appendChild(bp)
          }
          if (props.siren) {
            const bs = document.createElement('button'); bs.textContent = 'son patrimoine →'
            bs.style.cssText = actCss
            bs.addEventListener('click', () => { const s = useApp.getState(); s.setM02Prefill(String(props.siren)); s.setModule('patrimoine'); popup.remove() }); row.appendChild(bs)
          }
          box.appendChild(row)
          const popup = new maplibregl.Popup({ offset: 12, className: 'labuse-popup' }).setLngLat((e as maplibregl.MapLayerMouseEvent).lngLat).setDOMContent(box).addTo(m)
          ;(e as maplibregl.MapLayerMouseEvent).preventDefault()
        } else if (props?.kind === 'zone-concurrent') {
          // F8 (OUTILS-3) — pastille concurrent CLIQUABLE : popup (nom, activité, date de création) +
          // lien vers la parcelle. Contenu construit en DOM (textContent) → aucun risque d'injection.
          const lon = Number(props.lon), lat = Number(props.lat)
          // RETOURS-5 T3 — popup SOMBRE (jamais de fond blanc).
          const box = document.createElement('div'); box.style.cssText = POPUP_BOX_CSS
          const nom = document.createElement('b'); nom.textContent = String(props.nom || 'Établissement (nom non diffusé)'); nom.style.cssText = 'display:block;font-size:14px;font-weight:650'; box.appendChild(nom)
          const sub = document.createElement('div'); sub.style.cssText = 'color:#98a39d;font-size:12px;margin-top:5px'
          sub.textContent = String(props.activite || '') + (props.annee ? ` · depuis ${props.annee}` : ''); box.appendChild(sub)
          const btn = document.createElement('button'); btn.textContent = 'voir la parcelle →'
          btn.style.cssText = 'margin-top:9px;color:#4ADE80;background:none;border:1px solid rgba(74,222,128,.35);border-radius:8px;cursor:pointer;font:12px system-ui;padding:7px 10px'
          box.appendChild(btn)
          const popup = new maplibregl.Popup({ offset: 12, className: 'labuse-popup' }).setLngLat([lon, lat]).setDOMContent(box).addTo(m)
          btn.addEventListener('click', () => { parcelAt(lon, lat).then((r) => { if (r.idu) select(String(r.idu)) }).catch(() => {}); popup.remove() })
          ;(e as maplibregl.MapLayerMouseEvent).preventDefault()
        } else if (pid) { setPermitToOpen(String(pid)); (e as maplibregl.MapLayerMouseEvent).preventDefault() }
        else if (props?.idu) { select(String(props.idu)); (e as maplibregl.MapLayerMouseEvent).preventDefault() }  // LOT8b : clic piscine → fiche parcelle
      }
      // RETOURS-11 R8 — même handler pour les ronds ET les gouttes piscine (clic idu → fiche parcelle).
      const enterPt = () => { m.getCanvas().style.cursor = 'pointer' }
      const leavePt = () => { m.getCanvas().style.cursor = '' }
      for (const lid of ['module-pts', 'module-piscine']) {
        m.on('click', lid, onModulePtClick)
        m.on('mouseenter', lid, enterPt)
        m.on('mouseleave', lid, leavePt)
      }

      // équipements (points OSM, affichage seul) — cercles colorés, plancher z13 (pas
      // d'icônes par milliers à l'écran), clic = nom de l'équipement
      makeEquipIcons(m)
      makePiscineIcon(m)   // R10 — la goutte des piscines en icône canvas (voir makePiscineIcon)
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
      // M137-U — équipements INSEE BPE : CERCLES BLEUS (pas d'icônes) → visuellement distincts d'OSM,
      // aucun doublon à l'écran quand les deux couches sont actives. Source et couche dédiées.
      m.addSource('ov-equip-bpe', { type: 'geojson', data: EMPTY_FC as never })
      // M137-V — couleur par DOMAINE (A..G) via match sur le subtype (data-driven, comme zfang/frr).
      const bpeColor = ['match', ['get', 'subtype'],
        ...BPE_DOM.flatMap((d) => [d.code, d.color]), T_SOMBRE.bpe] as never
      m.addLayer({ id: 'ov-equip-bpe', type: 'circle', source: 'ov-equip-bpe', minzoom: 12,
        layout: { visibility: 'none' },
        paint: { 'circle-color': bpeColor, 'circle-opacity': 0.85,
                 'circle-radius': ['interpolate', ['linear'], ['zoom'], 12, 2.2, 16, 4, 20, 6],
                 'circle-stroke-color': '#0d1420', 'circle-stroke-width': 0.8 } })
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
          if (st.comparePicking) {                       // M82 : le clic ajoute à la comparaison (max 3)
            st.addToCompare(idu)
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
    // FIX-CARTE C1 : montage UNIQUE — la carte se crée une fois (le `if (map.current) return` garde).
    // `select` est une action zustand STABLE (jamais recréée) ; on l'exclut des deps pour dire
    // explicitement « ne dépend de rien » plutôt que de laisser une dep trompeuse.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ───────────────────────── données ─────────────────────────
  useEffect(() => {
    const m = map.current
    if (m && ready.current && geo.data) (m.getSource('parcels') as maplibregl.GeoJSONSource | undefined)?.setData(geo.data as never)
  }, [geo.data, geo.dataUpdatedAt, mapReady])

  useEffect(() => {
    const m = map.current
    if (!m || !ready.current) return
    const pairs: [string, typeof zonage][] = [['zonage', zonage], ['ppr', ppr], ['parc', parc], ['znieff', znieff], ['anru', anru], ['alea', alea],
      ['trans-ligne', transLignes], ['trans-arret', transArrets], ['pole', poles], ['tele', tele], ['axe', axes], ['ht', lignesHt], ['mt', lignesMt], ['tcsp', tcspTroncons], ['tcsp-st', tcspStations], ['tcsp-zone', tcspZone],
      ['qpv', qpv], ['tva_primo', tvaPrimo], ['zfang', zfang], ['frr', frr], ['vefa_neuf', vefaNeuf]]   // M134 dispositifs · M137-U znieff · T4 vefa
    for (const [k, qy] of pairs) if (qy.data) (m.getSource(`ov-${k}`) as maplibregl.GeoJSONSource | undefined)?.setData(qy.data as never)
    // M137-U — équipements BPE (points, source dédiée) : bind comme les OSM.
    if (equipBpe.data) {
      (m.getSource('ov-equip-bpe') as maplibregl.GeoJSONSource | undefined)?.setData(equipBpe.data as never)
      // FIX-COUCHES P1 — garde no-silent-caps ÉTENDU à la BPE (avant : seul l'OSM l'avait). Le plafond
      // (40 000) couvre les 35 546 actuels ; ce filet parle si un futur millésime BPE le dépasse.
      if (layers.equipements_bpe && equipBpe.data.features.length >= 40_000) {
        useApp.getState().setToast('Équipements INSEE (BPE) : plus de 40 000 objets — l’affichage est tronqué au plafond du serveur.')
      }
    }
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
    // M134 — dispositifs activés mais vides sur le périmètre : le dire (jamais un silence).
    if (layers.qpv && qpv.data && qpv.data.features.length === 0) {
      useApp.getState().setToast(commune ? `Aucun quartier prioritaire (QPV) sur ${commune} — 13 communes en portent un.`
                                         : 'Aucun quartier prioritaire (QPV) sur ce cadrage.')
    }
    if (layers.tva_primo && tvaPrimo.data && tvaPrimo.data.features.length === 0) {
      useApp.getState().setToast(commune ? `Aucune bande TVA réduite (QPV + 500 m) sur ${commune}.`
                                         : 'Aucune bande TVA réduite (QPV + 500 m) sur ce cadrage.')
    }
    // M6.1 item 2 : 50 pas — servis île entière (commune NULL en base) ; en mode commune,
    // même pattern honnête que l'ANRU : commune SANS littoral → toast, jamais un silence.
    // M-RENOUV : calque Renouvellement — si le serveur tronque (top rangs), le DIRE (toast),
    // jamais un « tout » silencieux (règle no-silent-caps).
    if (renouv.data) {
      ;(m.getSource('ov-renouv') as maplibregl.GeoJSONSource | undefined)?.setData(renouv.data as never)
      if (layers.renouv && renouv.data.total > renouv.data.servis) {
        useApp.getState().setToast(
          `Densifier l'existant : ${renouv.data.servis.toLocaleString('fr-FR')} parcelles affichées sur ` +
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
  }, [zonage.data, ppr.data, parc.data, znieff.data, anru.data, alea.data, transLignes.data, transArrets.data, poles.data, tele.data, axes.data, lignesHt.data, lignesMt.data, tcspTroncons.data, tcspStations.data, tcspZone.data, equip.data, equipBpe.data, cinquantePas.data, renouv.data, qpv.data, tvaPrimo.data, zfang.data, frr.data, vefaNeuf.data, layers.qpv, layers.tva_primo, layers.cinquante_pas, layers.renouv, layers.vefa_neuf, commune, communes.data, mapReady])

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
    // M64-P1 (B) / FOND-SOMBRE : « Clair » ET « Sombre » ne sont PAS des rasters — canvas + masse
    // terrestre + nos couches. On masque donc TOUS les fonds de plan pour ces deux modes ; les
    // couches parcelles/overlays gardent leurs couleurs sombres.
    // FIX-FONDS B5 — mapping unifié (partagé avec l'attribution) : les 7 millésimes d'ortho sont
    // désormais sélectionnables, donc bm-ortho-2006/2011/2016/2021 ne sont plus des couches mortes.
    const active = activeBasemapKey(basemap, orthoYear)
    for (const id of Object.keys(BASEMAP_SOURCES)) {
      if (m.getLayer(id)) m.setLayoutProperty(id, 'visibility', id === active ? 'visible' : 'none')
    }
    // RETOURS-13 R1 — le masque de mer n'existe que sur les fonds ORTHO (tuiles jpeg au no-data
    // blanc) ; Plan IGN, Sombre et Clair gèrent leur propre mer.
    if (m.getLayer('mer-mask')) {
      m.setLayoutProperty('mer-mask', 'visibility', active?.startsWith('bm-ortho') ? 'visible' : 'none')
    }
    applyClairMode(m, basemap)   // mer/terre du thème + traits achromatiques (aucune autre couleur touchée)
    // sur ortho/plan (fonds clairs ou photo), les écartées quasi invisibles gênent moins que le voile sombre
    // M6.1 : couche zonage parcelle active → NE PAS écraser son opacité dédiée
    // M55-G point 8 : seulement en mode OPINION — le mode factuel garde sa surbrillance neutre
    const photo = basemap === 'plan' || basemap === 'ortho'   // RETOURS-11 R5 — gate fondu photo
    if (m.getLayer('parcels-fill') && !zonageFill && opinion) {
      // filtre actif → 0,72 constant (fondu R5 au zoom sur photo) ; sinon la table STATUS_OPACITY
      // (déjà par tier) reste — sur photo elle n'est pas fondue mais les écartées y sont ~0.
      const op = filters.tiers.length === 0 ? STATUS_OPACITY : photoFade(0.72, photo)
      m.setPaintProperty('parcels-fill', 'fill-opacity', op)
      m.setPaintProperty('ile-fill', 'fill-opacity', op)
    }
  }, [basemap, orthoYear, filters.tiers, mapReady, ile, lowZoom, zonageFill, opinion])

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
    const photo = basemap === 'plan' || basemap === 'ortho'   // RETOURS-11 R5 — gate fondu photo de l'aplat
    // deux jeux de calques (GeoJSON commune / MVT île) — un seul visible à la fois
    // RETOURS-11 C1 (03/09) — le REMPLISSAGE des parcelles porte AUSSI l'aplat de zonage (par famille).
    // Régression SECTEUR-2 (07d16986) : `parcels-fill` était gated sur `layers.parcelles` seul, donc
    // « Zonage PLU par parcelle » coché SANS « Limites parcelles » n'affichait que les lettres, aplat perdu.
    // Le fill est visible dès que les limites OU le zonage-par-parcelle (zonageFill) sont actifs.
    m.setLayoutProperty('parcels-fill', 'visibility', vis((layers.parcelles || zonageFill) && !ile))
    m.setLayoutProperty('parcels-line', 'visibility', vis(layers.parcelles && !ile))
    m.setLayoutProperty('parcels-limites', 'visibility', vis(layers.limites && !ile))
    m.setLayoutProperty('ile-fill', 'visibility', vis((layers.parcelles || zonageFill) && ile))
    m.setLayoutProperty('ile-line', 'visibility', vis(layers.parcelles && ile))
    m.setLayoutProperty('ile-limites', 'visibility', vis(layers.limites && ile))
    m.setLayoutProperty('ile-sel', 'visibility', vis(ile))
    m.setLayoutProperty('ile-hl', 'visibility', vis(ile))
    // M15 A1 : couche de picking Assemblage — contours violets visibles seulement quand l'outil est actif
    m.setLayoutProperty('ile-pick', 'visibility', vis((module === 'assemblage' || comparePicking) && ile))
    m.setLayoutProperty('ov-zonage', 'visibility', vis(layers.zonage && !ile))
    m.setLayoutProperty('ov-ppr', 'visibility', vis(layers.ppr && !ile))
    m.setLayoutProperty('ovmvt-zonage', 'visibility', vis(layers.zonage && ile))
    m.setLayoutProperty('ovmvt-ppr', 'visibility', vis(layers.ppr && ile))
    // M105-B : les contours suivent EXACTEMENT leur remplissage (largeur 0 en Sombre)
    m.setLayoutProperty('ov-zonage-line', 'visibility', vis(layers.zonage && !ile))
    m.setLayoutProperty('ov-ppr-line', 'visibility', vis(layers.ppr && !ile))
    m.setLayoutProperty('ovmvt-zonage-line', 'visibility', vis(layers.zonage && ile))
    m.setLayoutProperty('ovmvt-ppr-line', 'visibility', vis(layers.ppr && ile))
    m.setLayoutProperty('ov-parc', 'visibility', vis(layers.parc))
    m.setLayoutProperty('ov-parc-line', 'visibility', vis(layers.parc))
    m.setLayoutProperty('ov-znieff', 'visibility', vis(layers.znieff))   // M137-U — contrainte ZNIEFF
    m.setLayoutProperty('ov-anru', 'visibility', vis(layers.anru))
    m.setLayoutProperty('ov-anru-trame', 'visibility', vis(layers.anru))
    // M134 — couche « Dispositifs »
    m.setLayoutProperty('ov-qpv', 'visibility', vis(layers.qpv))
    m.setLayoutProperty('ov-tva_primo', 'visibility', vis(layers.tva_primo))
    m.setLayoutProperty('ov-zfang', 'visibility', vis(layers.zfang))
    m.setLayoutProperty('ov-zfang-trame', 'visibility', vis(layers.zfang))   // M137-Y — hachure ZFANG standard (moindre)
    m.setLayoutProperty('ov-frr', 'visibility', vis(layers.frr))
    m.setLayoutProperty('ov-frr-trame', 'visibility', vis(layers.frr))       // M137-Y — hachure FRR en partie (moindre)
    m.setLayoutProperty('ov-vefa_neuf', 'visibility', vis(layers.vefa_neuf)) // SECTEUR-2 (T4) — prix du neuf VEFA
    m.setLayoutProperty('ov-vefa_neuf-trame', 'visibility', vis(layers.vefa_neuf)) // U1 — hachure sous-seuil
    // M106 P1 : les deux couches d'aléa (aplat + contour suivent leur toggle — R7 : plus de trame)
    for (const [id, on] of [['ov-alea-inond', layers.alea_inondation], ['ov-alea-mvt', layers.alea_mvt]] as const) {
      m.setLayoutProperty(id, 'visibility', vis(on))
      m.setLayoutProperty(`${id}-line`, 'visibility', vis(on))
    }
    // M106 P4 / M106-B : transport public — RETOURS-14 S7 : lignes ET arrêts ensemble.
    for (const id of ['ov-trans-ligne', 'ov-trans-arret', 'ov-tele', 'ov-tele-st']) {
      m.setLayoutProperty(id, 'visibility', vis(layers.transport))
    }
    m.setLayoutProperty('ov-axe', 'visibility', vis(layers.axes))
    m.setLayoutProperty('ov-pole', 'visibility', vis(layers.axes))   // M137-X — pôles sur « Axes structurants »
    // RETOURS-14 S9 : lignes électriques fusionnées (HTB + HTA sous une entrée).
    m.setLayoutProperty('ov-ht', 'visibility', vis(layers.lignes_ht))
    m.setLayoutProperty('ov-mt', 'visibility', vis(layers.lignes_ht))
    // RETOURS-14 S8 : « Stationnement allégé » = zone 800 m + parcelles teintées + stations + voies.
    m.setLayoutProperty('ov-tcsp', 'visibility', vis(layers.tcsp))
    m.setLayoutProperty('ov-tcsp-zone-parcelles', 'visibility', vis(layers.tcsp))
    m.setLayoutProperty('ov-tcsp-zone-rayon', 'visibility', vis(layers.tcsp))
    m.setLayoutProperty('ov-tcsp-st', 'visibility', vis(layers.tcsp))
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
    m.setLayoutProperty('ov-equip-bpe', 'visibility', vis(layers.equipements_bpe))   // M137-U — 2e source
    // M137-V — filtre par domaine BPE (A..G) : n'afficher que les domaines cochés dans la légende.
    if (m.getLayer('ov-equip-bpe')) m.setFilter('ov-equip-bpe', ['in', ['get', 'subtype'], ['literal', bpeDomains]] as never)
    m.setLayoutProperty('communes-bounds', 'visibility', vis(layers.communes))   // P11
    // M55-G suite (point 1) — LE FILTRE DE PALETTE :
    //  · couche « Verdict — toute l'île » cochée → AUCUN filtre (peinture explicite du
    //    classement entier, indépendante des filtres — le libellé de la couche le dit) ;
    //  · analyse avec critères hors-tuiles → restriction aux IDU du résultat courant
    //    (liste N == parcelles peintes N) + trame neutre dessous pour « le reste » ;
    //  · sinon → l'expression client (exacte dans ce cas).
    const expr = toExpr(filters)
    const exprPalette: maplibregl.FilterSpecification = layers.couleurs_verdict
      ? (['all'] as unknown as maplibregl.FilterSpecification)
      : resultIdus
        ? (['all', expr, ['in', ['get', 'idu'], ['literal', resultIdus]]] as unknown as maplibregl.FilterSpecification)
        : expr
    const baseVisible = !zonageFill && opinion && !!resultIdus && !layers.couleurs_verdict
    m.setLayoutProperty('parcels-base', 'visibility', vis(baseVisible && layers.parcelles && !ile))
    m.setLayoutProperty('ile-base', 'visibility', vis(baseVisible && layers.parcelles && ile))
    for (const fill of ['parcels-fill', 'ile-fill']) {
      m.setFilter(fill, exprPalette)
      // M6.1 item 1 : la couche « Zonage PLU (parcelles) » PRIME sur le verdict — le
      // remplissage devient la famille de zone (palette dédiée), verdict rallumé au toggle off.
      // `zonageFill` déjà conditionné : geojson commune toujours, tuiles île si zone_fam servie.
      // RETOURS-11 R5 — sur photo, l'opacité cible est FONDUE au zoom (photoFade) : lisible au large,
      // pleine en approche. STATUS_OPACITY (table par tier, écartées ~0) reste non fondue (déjà éteinte).
      if (zonageFill) {
        m.setPaintProperty(fill, 'fill-color', ZONE_FAM_COLOR)
        m.setPaintProperty(fill, 'fill-opacity', photo ? photoFade(0.62, photo) : ZONE_FAM_OPACITY)
      } else if (opinion) {
        m.setPaintProperty(fill, 'fill-color', STATUS_COLOR)
        m.setPaintProperty(fill, 'fill-opacity', filters.tiers.length === 0 && !resultIdus ? STATUS_OPACITY : photoFade(0.72, photo))
      } else if (verdict) {
        // M55-G point 8 : TRI FACTUEL — les parcelles correspondantes en surbrillance NEUTRE
        // (aucune couleur de tier) ; la couche « Verdict » reste activable dans Couches.
        m.setPaintProperty(fill, 'fill-color', '#8FA69A')
        m.setPaintProperty(fill, 'fill-opacity', photoFade(0.42, photo))
      } else {
        // R1 : VERDICT ÉTEINT = trame cadastrale NEUTRE (le langage promoteur), aucune couleur.
        // M65 P8 : en mode CLAIR, cette trame neutre = les PARCELLES en BLANC CASSÉ #F4F2EC (opaques)
        // qui se détachent sur la terre grise ; en Sombre, la trame neutre d'origine (#22302A/0,28).
        const clair = basemap === 'clair'
        m.setPaintProperty(fill, 'fill-color', clair ? '#F4F2EC' : '#22302A')
        m.setPaintProperty(fill, 'fill-opacity', clair ? 1 : 0.28)
      }
    }
    // lisérés promues/brûlantes : des couleurs d'OPINION — mode analyse ou couche Verdict cochée ;
    // ils suivent la MÊME restriction que la palette (jamais un liseré hors résultat).
    m.setLayoutProperty('parcels-line', 'visibility', vis(layers.parcelles && !ile && opinion))
    m.setLayoutProperty('ile-line', 'visibility', vis(layers.parcelles && ile && opinion))
    m.setFilter('parcels-line', ['all', PROMUES_FILTER, exprPalette] as maplibregl.FilterSpecification)
    m.setFilter('ile-line', ['all', PROMUES_FILTER, exprPalette] as maplibregl.FilterSpecification)
    // M5.1 : liseré brûlantes v2 — opinion allumée, mode commune (M55-F : pastille #rang retirée)
    if (m.getLayer('parcels-brulantes')) {
      m.setLayoutProperty('parcels-brulantes', 'visibility', vis(!ile && opinion))
      m.setFilter('parcels-brulantes', ['all',
        ['==', TIER_V2, 'brulante'], ['!', ETAGE0], exprPalette] as never)
    }
    // M64-P1 (A) : `basemap` dans les deps — au changement de thème, cet effet (seul à connaître le
    // mode zonage/opinion/factuel/neutre) se ré-exécute et RE-POSE la bonne fill-color des parcelles.
    // Corrige la teinte rouge/brune au boot : la couleur des parcelles n'appartient plus à applyTheme.
  }, [filters, layers, bpeDomains, geo.dataUpdatedAt, mapReady, ile, verdict, opinion, zonageFill, module, comparePicking, resultIdus, basemap])

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
      // M105-B : hors restitution, le liseré suit le CONTOUR DE TIER du thème courant
      // (Clair = brûlante/chaude assombries ≥ 3:1, tokens lib/mapTheme ; Sombre = inchangé).
      m.setPaintProperty(id, 'line-color', active ? '#4ADE80' : statusLineExpr(basemap === 'clair'))
      m.setPaintProperty(id, 'line-width', active ? 2 : 0.6)
      m.setPaintProperty(id, 'line-opacity', active ? 1 : 0.9)
    }
  }, [iaRestitution, mapReady, ile, verdict, filters, basemap])

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
    // RETOURS-11 T7 (03/09) — pastilles de commune UNIFORMES sur toutes les couches et tous les fonds :
    // FOND VERT, liseré NOIR, nom en BLANC. Le vert est assez profond pour que le blanc reste lisible.
    // Le hot (commune à chaudes, mode opinion) ne change plus la couleur — il garde juste une lueur.
    const PAST_BG = '#0E7A43', PAST_BORDER = '#000000', PAST_TXT = '#FFFFFF'
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
      const hot = opinion && c.chaudes > 0   // R1/M55-G p8 : sans OPINION affichée, marqueurs NEUTRES
      const el = document.createElement('button')
      el.setAttribute('data-commune-marker', c.commune)
      // P8 (dernière passe) : le marqueur mène à la FICHE COMMUNE (contexte), plus « N chaudes »
      // en évidence ; le nombre de chaudes reste en INFO secondaire (survol).
      // M36 Lot A : depuis M35 `c.chaudes` = TIERS du run servi (brûlantes + chaudes) — l'ancienne
      // étiquette « (matrice Q×A) » était devenue FAUSSE. L'échelle thermique est la bonne (R3).
      // RETOURS-12 T5 — infobulle réduite au FAIT NON AFFICHÉ. La pastille dit déjà le nom de la
      // commune et le curseur dit qu'elle est cliquable : on ne répète ni l'un ni l'autre. Reste le
      // seul fait absent de la pastille — le nombre de parcelles chaudes — et seulement quand il existe.
      if (hot) el.title = `${c.chaudes} parcelles prioritaires ou à suivre au classement servi`
      else el.removeAttribute('title')
      // RETOURS-11 T6 (03/09) — l'article n'est élidé QUE pour les 21 autres communes ; « Le Port »,
      // « Le Tampon », « La Possession » gardent leur article (référentiel unique lib/communes).
      const name = communePastille(c.commune)
      // M62-P1 (e) : le libellé = le NOM SEUL (« · Fiche commune » retiré des 24). Le clic ouvre
      // toujours la fiche commune (inchangé) ; l'affordance reste dans le `title` au survol.
      el.innerHTML = `<span>${name}</span>`
      // RETOURS-11 T8 — taille de police et padding +20 %.
      const size = Math.min(13, 10 + (opinion ? Math.log10(Math.max(1, c.chaudes)) * 2 : 0)) * 1.2
      el.style.cssText = `cursor:pointer;white-space:nowrap;border-radius:9999px;padding:2.4px 10.8px;` +
        `display:inline-flex;align-items:center;gap:4px;` +
        `font:600 ${size}px Inter,sans-serif;border:1px solid ${PAST_BORDER};` +
        `background:${PAST_BG};color:${PAST_TXT};` +
        // le hot (opinion + chaudes) garde une lueur menthe pour rester une ancre forte.
        (hot ? 'box-shadow:0 0 10px rgba(92,230,161,.30);' : '')
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
  }, [ile, communes.data, mapReady, opinion])

  // changement de commune → recadrage sur son emprise (bbox servie par /communes)
  useEffect(() => {
    const m = map.current
    if (!m || !ready.current) return
    const pad = fitPadding(m.getContainer().clientWidth, m.getContainer().clientHeight)
    if (ile) { m.fitBounds(ileBounds(communes.data), { padding: pad, duration: 900 }); return }
    const info = communes.data?.find((c) => c.commune === commune)
    if (info?.bbox) m.fitBounds(info.bbox as [number, number, number, number], { padding: pad, duration: 900 })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [commune, communes.data, mapReady])

  useEffect(() => {
    const m = map.current
    if (!m || !ready.current || !m.getLayer('parcels-sel')) return
    // RETOURS-12 O1/O12/J1 — la CIBLE du zoom+surbrillance = la parcelle sélectionnée (fiche ouverte)
    // OU la parcelle mise au FOCUS par un outil (focusParcelle, SANS ouvrir la fiche). Même geste.
    const cible = selectedIdu ?? focusIdu
    m.setFilter('parcels-sel', ['==', ['get', 'idu'], cible ?? ''])
    m.setFilter('ile-sel', ['==', ['get', 'idu'], cible ?? ''])
    // PING SYSTÉMATIQUE : toute sélection/focus (liste, module, CRM, notification, outil) recentre + pulse
    if (!cible) return
    const feat = geo.data?.features.find((f) => (f.properties as { idu?: string }).idu === cible)
    let cancelled = false
    // RETOURS-13 R27/R32 — ZOOM FRANC (Vic : « le zoom est un peu timide ») : la parcelle doit se
    // lire COMME LA PARCELLE, pas comme un point dans un quartier. Cible selon la SURFACE : grande
    // parcelle (> 1 ha) → 16,5 ; moyenne (> 2 500 m²) → 17 ; standard → 18. Primitive PARTAGÉE
    // (Étudier un bien, Permis, œil ambre des Projets…) — le réglage vaut pour tous.
    const zoomCible = (surface: number | null | undefined): number =>
      surface != null && surface > 10_000 ? 16.5 : surface != null && surface > 2_500 ? 17 : 18
    const centroidReady = (c: [number, number] | null, surface?: number | null) => {
      if (!c || cancelled) return
      m.flyTo({ center: c, zoom: Math.max(m.getZoom(), zoomCible(surface)), duration: 800 })
    }
    if (feat) centroidReady(roughCentroid(feat.geometry), (feat.properties as { surface_m2?: number }).surface_m2)
    else {
      // mode île (ou parcelle hors du GeoJSON chargé) : le centroïde vient de la fiche API.
      // CONTRAT (Vic, 07/07) : un clic dans la liste = je VOIS la parcelle pulser, où qu'elle
      // soit — le champ est `coords` [lon, lat] (le fallback lat/lon muet était le bug).
      getFiche(cible).then((f) => {
        const c = (f as unknown as { coords?: [number, number] }).coords
        const s = (f as unknown as { surface_m2?: number }).surface_m2
        if (Array.isArray(c) && c.length === 2) centroidReady([c[0], c[1]], s)
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
    m.setFilter(pingId, ['==', ['get', 'idu'], cible])
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
  }, [selectedIdu, focusIdu, focusNonce, geo.data, mapReady])

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

  // PERMIS (refonte) — surligne le point du permis survolé dans la liste (source dédiée à un point).
  const permitHover = useApp((s) => s.permitHover)
  useEffect(() => {
    const m = map.current
    if (!m || !ready.current || !m.getSource('permit-hover')) return
    const fc = permitHover
      ? { type: 'FeatureCollection', features: [{ type: 'Feature', geometry: permitHover, properties: {} }] }
      : EMPTY_FC
    ;(m.getSource('permit-hover') as maplibregl.GeoJSONSource | undefined)?.setData(fc as never)
  }, [permitHover, mapReady])

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
      // ZONE-RECETTE LOT E : on IGNORE un sommet dupliqué (les deux clics d'un double-clic tombent au
      // même endroit) — plus de spike parasite en bout de tracé.
      setMeasure((s) => {
        // RETOURS-11 C8 — une forme VALIDÉE (Entrée) est figée : le prochain clic repart d'une forme neuve.
        if (s.done) return { pts: [p], alti: null }
        const last = s.pts[s.pts.length - 1]
        if (last && Math.abs(last[0] - p[0]) < 1e-6 && Math.abs(last[1] - p[1]) < 1e-6) return s
        return { ...s, pts: [...s.pts, p] }
      })
    }
    const onDbl = (e: maplibregl.MapMouseEvent) => {
      // RETOURS-11 C8 (décision Vic 03/09) : le double-clic ne VALIDE PLUS AUCUNE forme. La validation
      // passe UNIQUEMENT par Entrée (surface/zone ≥ 3 points, distance ≥ 2 points), Échap annule.
      // On neutralise seulement le zoom au double-clic (preventDefault) ; aucune finalisation ici.
      // Le double-clic reste disponible pour l'édition des points (glisser-déplacer : non implémenté,
      // cf. rapport C8) — il ne ferme jamais la forme en cours.
      e.preventDefault()
    }
    const onKey = (ev: KeyboardEvent) => {
      if (ev.key === 'Escape') { setMeasure({ pts: [], alti: null }); setTool(null); return }
      if (ev.key !== 'Enter') return
      // RETOURS-11 C8 — Entrée (et Entrée SEULE) valide la forme en cours :
      //  · zone   : ferme le polygone (≥ 3 sommets), applique le filtre et referme l'outil ;
      //  · surface: fige la mesure du polygone (≥ 3 sommets) — l'outil reste actif, prochain clic = neuve ;
      //  · distance: fige la mesure de la ligne (≥ 2 points) — idem.
      const pts = measureRef.current.pts
      if (tool === 'zone') {
        if (pts.length >= 3) { setZone(pts); setTool(null); setMeasure({ pts: [], alti: null }) }
      } else if (tool === 'surface') {
        if (pts.length >= 3) setMeasure((s) => ({ ...s, done: true }))
      } else if (tool === 'distance') {
        if (pts.length >= 2) setMeasure((s) => ({ ...s, done: true }))
      }
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

  // FIX-FONDS B2/B3 — attribution EXACTE du fond actif : celle de BASEMAP_SOURCES (par fond ET par
  // millésime d'ortho), plus le binaire codé en dur. En Sombre et en Clair (aucune tuile de fond
  // depuis FOND-SOMBRE), on crédite la seule donnée montrée : le cadastre DGFiP.
  const fondActif = activeBasemapKey(basemap, orthoYear)
  const attribution = fondActif ? BASEMAP_SOURCES[fondActif].attribution : 'Cadastre © DGFiP'
  // FIX-FONDS B4 — un fond ortho ANCIEN (millésime ≠ Actuelle) peut montrer des dalles noires (mer,
  // limites de mission) : même légende honnête que l'outil TEMPS, à la même condition.
  const orthoAncienActif = basemap === 'ortho' && orthoYear !== 'now'

  return (
    <div className="relative min-w-0 flex-1">
      {/* h-full w-full EN PLUS de `absolute inset-0` : maplibre-gl.css pose `.maplibregl-map{position:
          relative}` (même spécificité que Tailwind `.absolute`) et, depuis le lazy-load M-V, cette CSS
          se charge APRÈS le bundle app → elle gagne → le conteneur repasse en `relative`, `inset-0` ne
          l'étire plus, ses enfants sont absolus → hauteur 0 → carte clippée (noir). Les dimensions
          explicites survivent quel que soit le `position` gagnant. Cf. RAPPORT_M_W_CARTE_NOIRE.md. */}
      <div ref={ref} className="absolute inset-0 h-full w-full" />
      {/* M65 P5 : gap entre les deux boutons réduit au prorata (8→6 px). */}
      <div className="absolute left-4 top-4 flex flex-col gap-1.5">
        {(['+', '−'] as const).map((s) => (
          <BoutonCarte key={s} onClick={() => map.current?.[s === '+' ? 'zoomIn' : 'zoomOut']()}
            title={s === '+' ? 'Zoomer' : 'Dézoomer'}>
            {s}
          </BoutonCarte>
        ))}
      </div>
      <MapToolbar />
      {/* M12 C6/C7 : UN SEUL panneau de légendes (verdict replié + zonage + 50 pas +
          équipements), cohabitant sans se recouvrir. La légende « Équipements » a quitté son
          bloc flottant (qui masquait le verdict) pour rejoindre ce panneau. */}
      <Legend />
      <VefaDetail />{/* SECTEUR-2b (U1) — panneau de détail au clic sur une commune VEFA */}
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
            /* RETOURS-11 C8 (03/09) — libellé exact : Entrée valide, Échap annule (le double-clic ne valide plus). */
            : 'Cliquez pour placer les points · Entrée pour valider · Échap pour annuler')}
        </div>
      )}
      {!tool && (
        <div className="pointer-events-none absolute bottom-4 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full border border-line-2 bg-surface-2 px-4 py-1.5 text-xs text-txt-mut shadow-elev-1">
          {ile && lowZoom ? 'Zoomez ou cliquez une commune pour voir ses parcelles' : 'Cliquez une parcelle pour ouvrir sa fiche'}
        </div>
      )}
      {/* RETOURS-1 R8 (Vic) : la pastille « Carte à jour au JJ/MM/AAAA » est RETIRÉE. Seul
          l'avertissement de retard subsiste (doctrine fraîcheur, FIX-CARTE T1 : des tuiles plus
          vieilles que le run servi ne s'affichent jamais en silence). */}
      {tilesMeta.data?.carte_le && tilesMeta.data.perime && (
        <div data-carte-fraicheur
          className="pointer-events-none absolute bottom-2 left-3 rounded-full border bg-surface-2/90 px-2.5 py-1 text-[10.5px] shadow-elev-1"
          style={{ color: '#E8B44C', borderColor: '#E8B44C' }}
          title="Les données de la carte (SDP, densité…) sont plus anciennes que le dernier calcul du run servi. Un rebuild des tuiles (labuse build-mvt) est en attente.">
          {'⚠ Carte au ' + tilesMeta.data.carte_le.slice(0, 10).split('-').reverse().join('/') + ' — mise à jour en attente'}
        </div>
      )}
      <div className="absolute bottom-2 right-3 font-sans text-[11px] text-st-none">
        {attribution}
      </div>
      {/* RADAR-CATÉGORIE (T2) — la carte porte la LÉGENDE des couleurs de pins. RETOURS-8 (R8) : la
          pastille-hint « Bien rattaché… / non localisé… » est RETIRÉE (le comportement reste, sans texte). */}
      {view === 'radar' && (
        <div data-radar-maplegend className="pointer-events-none absolute bottom-4 left-4 z-10 flex gap-4 whitespace-nowrap rounded-lg border border-line-2 bg-surface-2/92 px-3 py-2.5 text-[11.5px] text-txt-mut">
          <b className="flex items-center gap-1.5 font-medium"><span className="h-2 w-2 rounded-full bg-mint" /> En vente</b>
          <b className="flex items-center gap-1.5 font-medium"><span className="h-2 w-2 rounded-full bg-amber" /> En vente longue</b>
        </div>
      )}
      {/* FIX-FONDS B4 — légende « zones noires » réutilisée du mandat TEMPS (même markup data-temps-legende),
          affichée dans la carte principale quand un fond ortho ANCIEN est actif. */}
      {orthoAncienActif && (
        <div data-temps-legende className="pointer-events-none absolute left-3 top-3 z-10 flex max-w-[19rem] items-start gap-2 rounded-lg border border-line-2 bg-surface-2/95 px-3 py-2">
          <span aria-hidden className="mt-0.5 h-3 w-3 shrink-0 rounded-[3px] border border-line-2 bg-black" />
          <span className="text-[10.5px] leading-snug text-txt-mut">
            <b className="text-txt">Zones noires</b> : secteurs non couverts par l'ortho ancienne (mer, limites
            de mission IGN) — ce n'est pas un défaut de chargement.
          </span>
        </div>
      )}
    </div>
  )
}
