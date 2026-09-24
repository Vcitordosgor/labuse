import { useQuery, useIsFetching } from '@tanstack/react-query'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useRef, useState } from 'react'
import { getBatiments, getCommunes, getFiche, getFiltreIdus, getParcelsGeojson, getRenouvGeojson, getTilesMeta, parcelAt } from '../../lib/api'
import { ALL_TIER_META, ZONE_FAM_META, ZONE_FAM_ORDER } from '../../lib/status'
import { MAP_THEME } from '../../lib/mapTheme'
import { TOKENS } from '../../lib/tokens'
import { PERMIS_ETAT_COLOR } from '../../lib/permisEtats'
import { fmtArea, fmtDistance, pathLength, polygonArea, roughCentroid, type LngLat } from '../../lib/geo'
import { communePastille } from '../../lib/communes'
import { useApp, type Filters, type MapTool } from '../../store/useApp'
import { BASEMAP_SOURCES, ORTHO_MONDE, activeBasemapKey } from './basemaps'
import { Legend } from './Legend'
import { CouchesTuyauLayers } from './CouchesTuyau'  // COUCHES-TUYAU-1 lot 2
import { VefaDetail } from './VefaDetail'
import { MapToolbar } from './MapToolbar'
import { Squelette } from '../Loading'

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
// RECETTE-5 (V15, décision Vic) — LA CARTE ROUGE corrigée. L'écartée (et l'étage 0) était peinte en
// BRAISE #E8695A — la MÊME teinte que le palier « Priorité » (PALIER_META.priorite). Tant que les
// écartées étaient quasi éteintes (opacité 0,04), le rouge ne se voyait pas ; mais RECETTE-2 a rendu
// l'opacité UNIFORME (0,72) en mode analyse → toute l'île (majoritairement écartée/étage 0) virait au
// ROUGE, indiscernable de la Priorité. On revient à la teinte MUETTE du vocabulaire PALIERS-1
// (TIER_V2_META.ecartee = #4A5A52) : le rouge reste réservé à la Priorité, l'écartée s'efface. La
// carte et la légende (qui lisait déjà #4A5A52) redisent enfin la même chose.
const ECARTEE_COLOR = ALL_TIER_META['ecartee'].color   // #4A5A52 (muet) — plus le braise qui rougissait l'île
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
// RECETTE-2 (S11, R36 tranché par Vic) — en mode ANALYSE (opinion), l'opacité des parcelles est
// UNIFORME : plus de voile gris (les écartées ne sont plus estompées à 0,04). Le palier reste porté
// par la COULEUR seule (STATUS_COLOR). Même valeur que le cas filtré (0,72) → cohérent quel que soit
// le filtre. Hors opinion (tri factuel / verdict éteint), les opacités dédiées sont inchangées.
const OPINION_OPACITY = 0.72
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
      // PALIERS-1 — priorite/a_suivre (codes v2 q_v14) colorés comme brulante/chaude (codes servis)
      k === 'brulante' || k === 'priorite' ? MAP_THEME.sombre.contourBrulante
        : k === 'chaude' || k === 'a_suivre' ? MAP_THEME.sombre.contourChaude
          : k === 'ecartee' ? ECARTEE_COLOR : mt.color]),
    LEGACY_COLOR],
] as unknown as maplibregl.ExpressionSpecification
// liseré des promues : pipeline v2 (brûlante/chaude, hors étage 0). M48 (F4) : la branche de repli
// `status` (matrice morte) est retirée — le liseré suit le tier v2 servi.
// PALIERS-1 — les DEUX vocabulaires : servi (brulante/chaude) + q_v14 (priorite/a_suivre)
const PROMUES_TIERS = ['brulante', 'chaude', 'priorite', 'a_suivre']
const PROMUES_FILTER: maplibregl.FilterSpecification = [
  'all', ['in', TIER_V2, ['literal', PROMUES_TIERS]], ['!', ETAGE0],
] as unknown as maplibregl.FilterSpecification
// RECETTE-12 B1 — les NON-promues (« Sans signal » + « Écartée » + étage 0 + déclassements) :
// étage 0, ou un tier hors des quatre promus. Elles ne sont plus PEINTES en mode analyse (voir
// `opinionOpacityExpr`) — un aplat gris pour 50 000 parcelles noyait les 212 qui comptent — mais
// gardent un CONTOUR discret qui n'apparaît qu'au zoom (couches `parcels-muet`/`ile-muet`, minzoom).
const NON_PROMUES_FILTER: maplibregl.FilterSpecification = [
  'any', ETAGE0, ['!', ['in', TIER_V2, ['literal', PROMUES_TIERS]]],
] as unknown as maplibregl.FilterSpecification
// RECETTE-12 B1 (révise l'arbitrage RECETTE-2 S11 « opacité uniforme ») — en mode ANALYSE, SEULES
// Priorité et À suivre sont peintes ; tout le reste a une opacité NULLE (aucun remplissage). Le fondu
// R5 au zoom sur photo est conservé pour les promues. Rendu du même patron `case` que STATUS_OPACITY.
const opinionOpacityExpr = (photo: boolean): maplibregl.ExpressionSpecification => ([
  'case',
  ['all', ['!', ETAGE0], ['in', TIER_V2, ['literal', PROMUES_TIERS]]],
  photoFade(OPINION_OPACITY, photo),
  0,
] as unknown as maplibregl.ExpressionSpecification)

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

// COUCHES-1 lot 1 (E2) — remonte des POLYGONES en POINTS (centroïde du bbox) pour les couches
// dont les emprises sont trop petites pour être vues en aplat à l'échelle île (cas SIS : 4 périmètres
// de 0,6 à 1,4 ha). Le marqueur reste visible à toute échelle ; l'aplat sert au zoom parcelle.
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

const T_SOMBRE = MAP_THEME.sombre



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
const SOMBRE_BG = '#060A08'   // canvas historique — mer du mode Clair (et sous les tuiles Plan).
// RETOURS-16 V1 — APLAT DE MER des fonds ortho : UNE seule couleur, posée par le canvas sur
// l'emprise entière (jamais par tuile). Bleu profond MESURÉ sur la mosaïque monde IGN au large
// du 974 (moyenne rgb(10,59,89)) — même valeur que MER_HEX côté proxy (api/ortho_proxy.py).
// Le proxy fond la photo vers cet aplat au-delà de la bande côtière : la mer est uniforme.
const MER_ORTHO = '#0A3B59'
function applyBasemapStyle(m: maplibregl.Map, basemap: string) {
  const sombre = basemap === 'dark'
  // RETOURS-11 C4 — fonds PHOTO/CLAIR (Plan IGN, Ortho IGN, tous millésimes) : les traits fins et
  // les aplats sombres se noient sur la tuile claire/photographique. On applique un variant de style
  // « lisibilité fond clair » en surcouche, PILOTÉ ICI (seul propriétaire du paint basemap-dépendant),
  // sans DUPLIQUER de couche. Clair et Sombre (témoins) ne passent JAMAIS par ce bloc.
  const set = (id: string, prop: string, val: unknown) => { if (m.getLayer(id)) m.setPaintProperty(id, prop as never, val as never) }
  const vis = (id: string, on: boolean) => { if (m.getLayer(id)) m.setLayoutProperty(id, 'visibility', on ? 'visible' : 'none') }
  // FOND-SOMBRE : la mer du Sombre = teinte mesurée du rendu raster d'avant ; Clair garde le noir.
  // V1 : sous un fond ORTHO, le canvas EST la mer (aplat unique MER_ORTHO — le proxy fond la
  // photo vers lui au large) ; le Plan IGN dessine sa propre mer, Sombre/Clair gardent la leur.
  set('bg', 'background-color', basemap === 'ortho' ? MER_ORTHO : sombre ? SOMBRE_MER : SOMBRE_BG)
  // COUCHES-RECETTE-1 A6 : le voile gris n'est présent qu'en ORTHO (0 partout ailleurs → aucun effet
  // sur Sombre/Clair/Plan). ~0,3 : assez pour que les aplats/traits des couches ressortent sur la photo.
  set('ortho-veil', 'background-opacity', basemap === 'ortho' ? 0.3 : 0)
  // TERRE : masse île dissoute — grise en Clair, terre mesurée en Sombre ; CACHÉE sous Plan/Ortho
  // (dans la pile elle est AU-DESSUS des rasters de fond, elle les recouvrirait).
  vis('ile-mass', sombre)
  set('ile-mass', 'fill-color', SOMBRE_TERRE)
  // traits achromatiques (#ECF5EF) invisibles sur terre claire → foncés en Clair (bascule M64).
  const selLine = '#ECF5EF'
  for (const id of ['parcels-sel', 'ile-sel', 'parcels-ping', 'ile-ping']) set(id, 'line-color', selLine)
  // FINITIONS-1 (P8) — sous la Vue ORTHO, le contour PERSISTANT de la parcelle sélectionnée (2 px,
  // quasi-blanc) se noyait dans la photo une fois le pulse d'arrivée estompé (~3 s) : il SEMBLAIT
  // disparaître. On l'ÉPAISSIT en ortho pour qu'il RESTE nettement lisible tant que la parcelle est
  // sélectionnée (le voile sombre 0,3 de l'ortho assure le contraste, même sur les toits clairs).
  // Largeur d'origine (2) restaurée sur les autres fonds — le ternaire suit chaque changement de fond.
  const selWidth = basemap === 'ortho' ? 3.5 : 2
  for (const id of ['parcels-sel', 'ile-sel']) set(id, 'line-width', selWidth)
  // RETOURS-11 C4 — text-halo-width réappliqué à sa valeur de création (1.3) hors fond photo, pour
  // que le retour en Clair/Sombre efface l'épaississement du variant photo (témoins intacts).
  for (const id of ['parcels-zone-label', 'ile-zone-label']) { set(id, 'text-color', '#ECF5EF'); set(id, 'text-halo-color', '#06130C'); set(id, 'text-halo-width', 1.3) }
  // COUCHES-RETRAIT-1 lot 2 — le liseré des « brûlantes » (opinion) suit le thème ; toutes les
  // autres couches d'information sont désormais servies par le tuyau (fin de l'ancien overlay V1).
  set('parcels-brulantes', 'line-color', MAP_THEME.sombre.lisereBrulantes)
}

//: ÉQUIPEMENTS (contexte promotrice, affichage seul) — 7 catégories, pictogramme + pastille.
// Point 13 : un SYMBOLE parlant par type d'équipement. La META est partagée (lib/status.ts) :
// même source pour la légende (Legend.tsx) et le rendu carte. Émoji rendu via canvas → addImage
// (aucune lib ; repli = la pastille colorée + la légende si l'OS n'a pas la police émoji).




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
    <button onClick={press} aria-label={title}
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
  const { selectedIdu, select, filters, layers, basemap, orthoYear, terrain3d, batiVisible, tool, setTool, zone, setZone, moduleMap, flyTo, setFlyTo, setPermitToOpen, commune, verdict, iaRestitution, module, comparePicking, view, focusIdu, focusNonce } = useApp()
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
  // COUCHES-2 point 2 — ÉTAT DE CHARGEMENT D'UNE COUCHE : quand on allume un overlay, sa requête
  // (queryKey ['layer', …]) est en vol ; sans témoin l'écran restait MUET jusqu'à l'arrivée des
  // données (geom_simple a réduit l'attente, pas supprimé le geste). On compte les requêtes de
  // couche en cours → un bandeau « Chargement de la couche… » tant qu'au moins une charge.
  const layersFetching = useIsFetching({ queryKey: ['layer'] })

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
        // RETOURS-11 C1 — la légende du zonage suit l'aplat RÉELLEMENT peint. COUCHES-1 lot 2 (A1) :
        // l'aplat zonage est servi par la tuile vectorielle dès z8 (ovmvt-zonage, minzoom 8), donc il
        // PEINT toute l'île en vue d'ensemble — la légende doit alors s'afficher. `zonageFill` encode
        // déjà « peint ? » (à l'île, exige que la tuile porte le zonage) ; le garde z≥10 masquait à tort
        // la légende de la couche vitrine pendant qu'elle peignait l'île (constat A1).
        zonage: zonageFill,
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
      // RETOURS-15 U1 — SOUS-COUCHE ortho monde (mosaïque ORTHOPHOTOS, mer comprise), posée SOUS
      // tous les fonds : aux petits zooms elle EST la mer (photographiée jusqu'à z12 mesuré) ; au
      // delà, MapLibre étire ses tuiles z12 (source maxzoom 12) → la mer reste CONTINUE sous
      // l'Ortho Express (qui ne couvre que la terre + la mer côtière). Le masque de mer R1 et les
      // `bounds` C6 sont RETIRÉS : ils découpaient jetées et ports en biseau (constat Vic 05/09) —
      // rien ne découpe une orthophoto. Sous tout ça, le canvas sombre : jamais de blanc.
      m.addSource('bm-ortho-monde', { type: 'raster', tiles: ORTHO_MONDE.tiles, tileSize: 256,
        attribution: ORTHO_MONDE.attribution, maxzoom: ORTHO_MONDE.maxzoom })
      // V1 — raster-fade-duration 0 sur les fonds ortho : le fondu d'apparition de MapLibre
      // laissait voir le canvas au travers des tuiles pendant 300 ms (liserés aux jointures au
      // moindre zoom) ; l'aplat de mer et le fondu du proxy suffisent, pas de crossfade.
      m.addLayer({ id: 'bm-ortho-monde', type: 'raster', source: 'bm-ortho-monde',
        layout: { visibility: 'none' }, paint: { 'raster-fade-duration': 0 } })
      for (const [id, src] of Object.entries(BASEMAP_SOURCES)) {
        m.addSource(id, { type: 'raster', tiles: src.tiles, tileSize: 256, attribution: src.attribution, ...(src.maxzoom ? { maxzoom: src.maxzoom } : {}) })
        // U1 — bascule par zoom : l'Ortho Express (terre seule) n'apparaît qu'aux GRANDS zooms
        // (minzoom 12) ; en dessous, la mosaïque monde seule peint — sans ça, les tuiles
        // côtières Express faisaient un liseré bleu vif en escalier autour de l'île.
        m.addLayer({ id, type: 'raster', source: id, layout: { visibility: 'none' },
          ...(id.startsWith('bm-ortho') ? { paint: { 'raster-fade-duration': 0 } } : {}),
          ...(id === 'bm-ortho-now' ? { minzoom: 12 } : {}) })
      }
      // M65 P8 — MASSE TERRESTRE (île dissoute) : la terre sans parcelle (cirques, forêt, volcan)
      // prend l'aplat du thème — GRIS #C9C4B8 en Clair, terre mesurée SOMBRE_TERRE en Sombre
      // (FOND-SOMBRE ; applyBasemapStyle pose teinte et visibilité). Posée TOUT EN BAS de la pile
      // vectorielle (juste au-dessus des rasters) → sous TOUS les overlays (risques, zonages) et
      // les parcelles, qui restent lisibles par-dessus. Masquée sous Plan/Ortho (elle recouvrirait
      // leurs tuiles). Source ile974.geojson = 24 communes DISSOUES.
      m.addSource('ile-mass', { type: 'geojson', data: `${(import.meta as unknown as { env: { BASE_URL: string } }).env.BASE_URL}ile974.geojson` })
      m.addLayer({ id: 'ile-mass', type: 'fill', source: 'ile-mass', layout: { visibility: 'none' },
        paint: { 'fill-color': '#C9C4B8', 'fill-opacity': 1 } })
      // COUCHES-RECETTE-1 A6 — VOILE ORTHO : un voile gris translucide entre l'orthophoto et les
      // couches, UNIQUEMENT en vue ortho, pour que les couleurs des couches ressortent. Posé
      // au-dessus des rasters de fond et sous les overlays/parcelles (donc sous les couches du tuyau,
      // ajoutées après). Opacité pilotée par applyBasemapStyle (0 hors ortho → aucun effet ailleurs).
      m.addLayer({ id: 'ortho-veil', type: 'background',
        paint: { 'background-color': '#20242A', 'background-opacity': 0 } })
      // MNT (relief 3D) — terrarium AWS (libre)
      m.addSource('dem', { type: 'raster-dem', encoding: 'terrarium', tileSize: 256, maxzoom: 13,
        tiles: ['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'] })

      m.addSource('parcels', { type: 'geojson', data: EMPTY_FC as never, promoteId: 'idu' })
      // RECETTE-6 (A3) — source du bâti 3D (empreinte + hauteur), remplie par BBOX quand le 3D est actif.
      m.addSource('batiments', { type: 'geojson', data: EMPTY_FC as never })
      // M-RENOUV : segment Renouvellement (occupees, potentiel) — cuivre dedie.
      m.addSource('ov-renouv', { type: 'geojson', data: EMPTY_FC as never })
      m.addLayer({ id: 'ov-renouv', type: 'fill', source: 'ov-renouv', layout: { visibility: 'none' },
        paint: { 'fill-color': TOKENS.renouv, 'fill-opacity': 0.38 } })
      m.addLayer({ id: 'ov-renouv-line', type: 'line', source: 'ov-renouv', layout: { visibility: 'none' },
        paint: { 'line-color': TOKENS.renouv, 'line-width': 1.1, 'line-opacity': 0.85 } })
      // COUCHES-RETRAIT-1 lot 2 — la ligne « Limites communes » (repère) est désormais servie par le
      // tuyau (couche `limites_communes`, famille Repères). On garde la SOURCE communes974.geojson : elle
      // alimente le voile d'atténuation `commune-attenuation` (clic commune, ci-dessous).
      m.addSource('communes-bounds', { type: 'geojson', data: `${(import.meta as unknown as { env: { BASE_URL: string } }).env.BASE_URL}communes974.geojson` })
      // COUCHES-RECETTE-2 C4 — clic commune : la commune choisie garde sa valeur, le RESTE de l'île est
      // ATTÉNUÉ (voile sombre sur les autres communes). Filtre piloté par l'état `commune` (effet plus bas).
      m.addLayer({ id: 'commune-attenuation', type: 'fill', source: 'communes-bounds',
        layout: { visibility: 'none' }, filter: ['==', ['get', 'nom'], '__none__'],
        paint: { 'fill-color': '#050706', 'fill-opacity': 0.55 } })
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
      // contours promues (statut) — la couche « Limites parcelles » (repère cadastral) est servie par
      // le tuyau (couche `limites_parcelles`, famille Repères). COUCHES-RETRAIT-1 lot 2.
      m.addLayer({ id: 'parcels-line', type: 'line', source: 'parcels', filter: PROMUES_FILTER, paint: { 'line-color': STATUS_COLOR, 'line-width': 0.6, 'line-opacity': 0.9 } })
      // RECETTE-12 B1 — contour DISCRET des non-promues (Sans signal/Écartée), en mode analyse
      // SEULEMENT et au ZOOM SEULEMENT (minzoom) : elles ne sont plus peintes (aucun aplat gris), mais
      // le lecteur qui zoome voit qu'elles existent et les sélectionne. Masqué par défaut (effet mode).
      m.addLayer({ id: 'parcels-muet', type: 'line', source: 'parcels', minzoom: 15, filter: NON_PROMUES_FILTER,
        layout: { visibility: 'none' }, paint: { 'line-color': '#5F7267', 'line-width': 0.3, 'line-opacity': 0.5 } })
      m.addLayer({ id: 'parcels-sel', type: 'line', source: 'parcels', filter: ['==', ['get', 'idu'], ''], paint: { 'line-color': '#ECF5EF', 'line-width': 2 } })
      // RECETTE-6 (A3) — BÂTI 3D : extrusion de l'empreinte au sol à sa hauteur BD TOPO (la même que
      // l'Apporteur). Posée sur le relief (setTerrain → l'extrusion part du sol du MNT, jamais d'un
      // plan). Masquée par défaut ; allumée avec le bouton 3D (effet plus bas). Hauteur absente = pas
      // d'extrusion (le serveur exclut déjà ces bâtiments).
      m.addLayer({ id: 'batiments-3d', type: 'fill-extrusion', source: 'batiments', layout: { visibility: 'none' },
        paint: {
          'fill-extrusion-color': '#9FB3A8',
          'fill-extrusion-height': ['coalesce', ['get', 'h'], 0],
          'fill-extrusion-base': 0,
          'fill-extrusion-opacity': 0.88,
        } })
      // M5.1 — badge carte : liseré braise sur les BRÛLANTES v2 (hors étage 0), et pastille
      // « #rang » sur les opportunités v2 au zoom rapproché (mode commune). Le badge « V nn »
      // v1.3 a disparu : un seul monde visible, le v2.
      m.addLayer({
        id: 'parcels-brulantes', type: 'line', source: 'parcels',
        filter: ['all', ['in', TIER_V2, ['literal', ['brulante', 'priorite']]], ['!', ETAGE0]] as never,
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

      // ── mode ÎLE : calques jumeaux sur tuiles MVT (431k parcelles — le GeoJSON ne tient pas) ──
      m.addSource('parcels-ile', { type: 'vector', minzoom: 9, maxzoom: 15,
        tiles: [`${window.location.origin}/map/tiles/{z}/{x}/{y}.pbf`] })
      const SL = { source: 'parcels-ile', 'source-layer': 'parcels' } as const
      // M55-G suite (point 1) : trame neutre jumelle côté île (cf. parcels-base)
      m.addLayer({ id: 'ile-base', type: 'fill', ...SL, layout: { visibility: 'none' },
        paint: { 'fill-color': '#22302A', 'fill-opacity': 0.28 } })
      m.addLayer({ id: 'ile-fill', type: 'fill', ...SL, layout: { visibility: 'none' },
        paint: { 'fill-color': STATUS_COLOR, 'fill-opacity': STATUS_OPACITY } })
      m.addLayer({ id: 'ile-line', type: 'line', ...SL, layout: { visibility: 'none' },
        filter: PROMUES_FILTER, paint: { 'line-color': STATUS_COLOR, 'line-width': 0.6, 'line-opacity': 0.9 } })
      // RECETTE-12 B1 — jumeau île du contour discret des non-promues (minzoom, mode analyse seul)
      m.addLayer({ id: 'ile-muet', type: 'line', ...SL, minzoom: 15, filter: NON_PROMUES_FILTER,
        layout: { visibility: 'none' }, paint: { 'line-color': '#5F7267', 'line-width': 0.3, 'line-opacity': 0.5 } })
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
        paint: { 'line-color': MAP_THEME.sombre.cote, 'line-width': 2.2, 'line-opacity': 0.95 } })

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
                   // RETOURS-17 W3 — la COULEUR DU POINT PERMIS SUIT SON ÉTAT (avant : tout en vert →
                   // « 47 000 verts, lit 5 580 récents », Vic 05/09). Récent vert · Dormant corail ·
                   // Achevé/Autre gris — MÊME source que les pastilles du panneau (lib/permisEtats).
                   ['==', ['get', 'kind'], 'permis'],
                     ['match', ['get', 'etat'],
                       'recent', PERMIS_ETAT_COLOR.recent,
                       'dormant', PERMIS_ETAT_COLOR.dormant,
                       'gris', PERMIS_ETAT_COLOR.gris,
                       PERMIS_ETAT_COLOR.recent],
                   ['==', ['get', 'kind'], 'radar'],
                   /* DA-FIX-4 Lot 3 (DA-039) — plus de bleu d'interface : « à revérifier » passe en ambre,
                      l'état par défaut en neutre. (La symbologie carte police/BPE, elle, n'est pas touchée.) */
                   ['match', ['get', 'statut'],
                     'active', '#4ADE80', 'en_vente_longue', '#E0A94F', 'a_reverifier', '#E0A94F',
                     'vendue', '#E2726A', '#8A968F'],
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
            // OUTILS-FIX-4 A3 — date Sit@del : année seule au 1ᵉʳ janvier (année seule connue), sinon date réelle.
            const fmtD = (s: string) => { const t = new Date(s); return Number.isNaN(t.getTime()) ? '' : (t.getMonth() === 0 && t.getDate() === 1 ? String(t.getFullYear()) : t.toLocaleDateString('fr-FR')) }
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

      makePiscineIcon(m)   // R10 — la goutte des piscines en icône canvas (voir makePiscineIcon)

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
    // M-RENOUV : calque Renouvellement — si le serveur tronque (top rangs), le DIRE (toast).
    if (renouv.data) {
      ;(m.getSource('ov-renouv') as maplibregl.GeoJSONSource | undefined)?.setData(renouv.data as never)
      if (layers.renouv && renouv.data.total > renouv.data.servis) {
        useApp.getState().setToast(
          `Densifier l'existant : ${renouv.data.servis.toLocaleString('fr-FR')} parcelles affichées sur ` +
          `${renouv.data.total.toLocaleString('fr-FR')} (meilleurs rangs)${commune ? ` — ${commune}` : ' — île entière'}.`)
      }
    }
  }, [renouv.data, layers.renouv, commune, mapReady])

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

  // COUCHES-RECETTE-2 C4 — clic commune : la commune choisie garde sa valeur, les AUTRES sont
  // atténuées (voile sombre). Sans commune sélectionnée, le masque est éteint (île entière en valeur).
  useEffect(() => {
    const m = map.current
    if (!m || !mapReady || !m.getLayer('commune-attenuation')) return
    if (commune) {
      m.setFilter('commune-attenuation', ['!=', ['get', 'nom'], commune])
      m.setLayoutProperty('commune-attenuation', 'visibility', 'visible')
    } else {
      m.setLayoutProperty('commune-attenuation', 'visibility', 'none')
    }
  }, [commune, mapReady])

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
    // RETOURS-15 U1 — la sous-couche monde accompagne TOUT fond ortho (mer continue à tous les
    // zooms sous le millésime actif) ; Plan IGN dessine sa propre mer, Sombre/Clair n'ont pas de raster.
    if (m.getLayer('bm-ortho-monde')) {
      m.setLayoutProperty('bm-ortho-monde', 'visibility', active?.startsWith('bm-ortho') ? 'visible' : 'none')
    }
    applyBasemapStyle(m, basemap)   // mer/terre du thème + traits achromatiques (aucune autre couleur touchée)
    // sur ortho/plan (fonds clairs ou photo), les écartées quasi invisibles gênent moins que le voile sombre
    // M6.1 : couche zonage parcelle active → NE PAS écraser son opacité dédiée
    // M55-G point 8 : seulement en mode OPINION — le mode factuel garde sa surbrillance neutre
    const photo = basemap === 'plan' || basemap === 'ortho'   // RETOURS-11 R5 — gate fondu photo
    if (m.getLayer('parcels-fill') && !zonageFill && opinion) {
      // RECETTE-12 B1 (révise RECETTE-2 S11) — SEULES Priorité et À suivre sont peintes ; les non-
      // promues (Sans signal/Écartée) ont une opacité NULLE (aucun aplat gris). Fondu R5 conservé.
      const op = opinionOpacityExpr(photo)
      m.setPaintProperty('parcels-fill', 'fill-opacity', op)
      m.setPaintProperty('ile-fill', 'fill-opacity', op)
    }
  }, [basemap, orthoYear, filters.tiers, mapReady, ile, lowZoom, zonageFill, opinion])

  useEffect(() => {
    const m = map.current
    if (!m || !ready.current) return
    // RECETTE-6 (A3) — le bouton 3D allume le RELIEF (setTerrain) ET le BÂTI extrudé (batiments-3d),
    // ensemble : l'extrusion part du sol du MNT (jamais d'un plan). Le bâti se charge par BBOX au zoom
    // rapproché (≥ 15, où l'extrusion est visible), rafraîchi au déplacement ; borné à la vue courante.
    const BATI_MINZOOM = 15
    const chargerBati = () => {
      // RETOURS-13 P4 — le bâti extrudé n'apparaît QUE si le chip « Bâtiments » est actif (batiVisible).
      // Chip off en 3D → relief seul (aucune extrusion) ; le relief (setTerrain) reste allumé plus bas.
      if (!terrain3d || !batiVisible || m.getZoom() < BATI_MINZOOM) {
        if (m.getLayer('batiments-3d')) m.setLayoutProperty('batiments-3d', 'visibility', 'none')
        return
      }
      const b = m.getBounds()
      const bbox: [number, number, number, number] = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()]
      getBatiments(bbox).then((fc) => {
        const src = m.getSource('batiments') as maplibregl.GeoJSONSource | undefined
        if (src && terrain3d && batiVisible) {
          src.setData(fc as never)
          m.setLayoutProperty('batiments-3d', 'visibility', 'visible')
        }
      }).catch(() => { /* le bâti 3D ne casse jamais la carte */ })
    }
    if (terrain3d) {
      m.setTerrain({ source: 'dem', exaggeration: 1.35 })
      if (m.getPitch() < 20) m.easeTo({ pitch: 55, duration: 800 })
      chargerBati()
      m.on('moveend', chargerBati)
    } else {
      m.setTerrain(null)
      m.easeTo({ pitch: 0, duration: 600 })
      if (m.getLayer('batiments-3d')) m.setLayoutProperty('batiments-3d', 'visibility', 'none')
    }
    return () => { m.off('moveend', chargerBati) }
  }, [terrain3d, batiVisible])

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
    m.setLayoutProperty('ile-fill', 'visibility', vis((layers.parcelles || zonageFill) && ile))
    m.setLayoutProperty('ile-line', 'visibility', vis(layers.parcelles && ile))
    m.setLayoutProperty('ile-sel', 'visibility', vis(ile))
    m.setLayoutProperty('ile-hl', 'visibility', vis(ile))
    // M15 A1 : couche de picking Assemblage — contours violets visibles seulement quand l'outil est actif
    m.setLayoutProperty('ile-pick', 'visibility', vis((module === 'assemblage' || comparePicking) && ile))
    // M-RENOUV : segment Renouvellement (cuivre) — OFF par défaut
    m.setLayoutProperty('ov-renouv', 'visibility', vis(layers.renouv))
    m.setLayoutProperty('ov-renouv-line', 'visibility', vis(layers.renouv))
    // M6.1 item 1 : étiquette de zone PRÉCISE (zone_lib, z ≥ 16) — suit la couche zonage
    m.setLayoutProperty('parcels-zone-label', 'visibility', vis(layers.zonage_parcelle && !ile))
    m.setLayoutProperty('ile-zone-label', 'visibility', vis(layers.zonage_parcelle && ile))
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
    // RECETTE-8 W9 (A1) — plus de GRIS DE FOND sous les parcelles hors sélection en mode Analyse.
    // La trame neutre (#22302A/0,28) peignait « le reste » d'un gris sale : une parcelle doit
    // porter la COULEUR DE SON PALIER ou RIEN, jamais un gris. Les parcelles hors sélection restent
    // délimitées par leurs contours (couche « Limites parcelles ») et sélectionnables — sans voile.
    const baseVisible = false
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
        // RECETTE-12 B1 (révise RECETTE-2 S11) — SEULES Priorité et À suivre sont peintes ; les non-
        // promues ont une opacité NULLE (plus d'aplat gris pour 50 000 parcelles). Le palier reste
        // porté par la couleur (STATUS_COLOR). Fondu R5 conservé sur photo pour les promues.
        m.setPaintProperty(fill, 'fill-color', STATUS_COLOR)
        m.setPaintProperty(fill, 'fill-opacity', opinionOpacityExpr(photo))
      } else {
        // RECETTE-5 (V1, décision Vic) — plus de VOILE GRIS sur le chemin factuel. Le tri factuel
        // (« Voir les parcelles », verdict=true & analyse OFF) partageait la surbrillance grise
        // #8FA69A/0,42 qui, sans filtre, lavait TOUTE l'île en gris. Il rejoint désormais la trame
        // cadastrale NEUTRE de « verdict éteint » : les parcelles restent délimitées par leurs
        // contours (parcels-limites, toujours affichés) et sélectionnables, sans aucun voile.
        // Le voile avait déjà été retiré du mode ANALYSE (opinion, opacité uniforme) en RECETTE-2 S11.
        // M65 P8 : en CLAIR, trame neutre = PARCELLES en BLANC CASSÉ #F4F2EC (opaques) sur la terre
        // grise ; en Sombre, la trame neutre d'origine (#22302A/0,28).
              // RECETTE-9 T5 — le test décisif (captures A→E) tranche : le GRIS est le FOND DE PLAN Sombre
        // (analyse ON/OFF donne une image IDENTIQUE → ce n'est pas l'analyse ; passer en Clair/Ortho le
        // fait disparaître → c'est bien le fond). Le SEUL gris que peignent NOS calques (pas le fond) est
        // ce remplissage neutre #22302A/0,28 : sur le Sombre il a quasi la couleur du fond → il ne
        // distingue rien, il WASHE juste les parcelles en gris. On l'éteint sur Sombre/photo (les
        // parcelles restent délimitées par « Limites parcelles » et sélectionnables via parcelAt),
        // achevant sur le BON calque la règle W9/S11/V1 « couleur de palier ou RIEN, jamais un gris ».
        // En CLAIR le remplissage blanc reste utile (parcelles blanches sur terre claire) → conservé.
        m.setPaintProperty(fill, 'fill-color', '#22302A')
        m.setPaintProperty(fill, 'fill-opacity', 0)
      }
    }
    // lisérés promues/brûlantes : des couleurs d'OPINION — mode analyse ou couche Verdict cochée ;
    // ils suivent la MÊME restriction que la palette (jamais un liseré hors résultat).
    m.setLayoutProperty('parcels-line', 'visibility', vis(layers.parcelles && !ile && opinion))
    m.setLayoutProperty('ile-line', 'visibility', vis(layers.parcelles && ile && opinion))
    m.setFilter('parcels-line', ['all', PROMUES_FILTER, exprPalette] as maplibregl.FilterSpecification)
    m.setFilter('ile-line', ['all', PROMUES_FILTER, exprPalette] as maplibregl.FilterSpecification)
    // RECETTE-12 B1 — contour discret des non-promues : en mode analyse, au zoom (minzoom porté par
    // la couche). Non restreint par la palette — c'est justement « le reste » (Sans signal/Écartée).
    if (m.getLayer('parcels-muet')) m.setLayoutProperty('parcels-muet', 'visibility', vis(layers.parcelles && !ile && opinion))
    if (m.getLayer('ile-muet')) m.setLayoutProperty('ile-muet', 'visibility', vis(layers.parcelles && ile && opinion))
    // M5.1 : liseré brûlantes v2 — opinion allumée, mode commune (M55-F : pastille #rang retirée)
    if (m.getLayer('parcels-brulantes')) {
      m.setLayoutProperty('parcels-brulantes', 'visibility', vis(!ile && opinion))
      m.setFilter('parcels-brulantes', ['all',
        ['in', TIER_V2, ['literal', ['brulante', 'priorite']]], ['!', ETAGE0], exprPalette] as never)
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
    // RECETTE-1 R39 — « Sainte-Suzanne » chevauchait « Saint-André » : on la REMONTE (y plus négatif,
    // -6 → -22) et on descend légèrement Saint-André pour dégager les deux étiquettes.
    const OFFSETS: Record<string, [number, number]> = {
      'Saint-Denis': [-14, -10], 'Sainte-Marie': [16, 8], 'Sainte-Suzanne': [26, -22],
      'Saint-André': [0, 12],
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
      {/* COUCHES-TUYAU-1 lot 2 — le tuyau : sources vectorielles des 52 couches + légende bas-droite */}
      <CouchesTuyauLayers map={map} ready={mapReady} />
      <VefaDetail />{/* SECTEUR-2b (U1) — panneau de détail au clic sur une commune VEFA */}
      {/* B1/P5 : chargement carte DISCRET (données GeoJSON + tuiles MVT) — jamais figé */}
      {(geo.isFetching || tilesLoading || layersFetching > 0) && (
        <div data-carte-loading className="pointer-events-none absolute left-1/2 top-4 w-40 -translate-x-1/2 rounded-full border border-mint/30 bg-surface-2 px-4 py-2 shadow-elev-2">
          {/* COUCHES-2 point 2 — priorité au message le plus précis : parcelles > couche > carte. */}
          {/* DA — squelette unique (plus de gros points Loading) ; le message précis reste en aria. */}
          <Squelette lignes={1} label={geo.isFetching ? 'Chargement des parcelles' : layersFetching > 0 ? 'Chargement de la couche…' : 'Chargement de la carte…'} />
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
        <div data-carte-banner className="pointer-events-none absolute bottom-4 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full border border-line-2 bg-surface-2 px-4 py-1.5 text-xs text-txt-mut shadow-elev-1">
          {/* COUCHES-2 point 1 — le bandeau ne CONTREDIT plus la carte : quand le zonage PLU peint déjà
              l'aperçu d'ensemble par famille à l'échelle île (zonageFill), il ne dit plus « zoomez pour
              voir les parcelles » (elles sont peintes) mais annonce l'aperçu + le geste pour le DÉTAIL.
              Sans aperçu peint (couche éteinte), le message d'origine reste (rien n'est peint → zoomer). */}
          {ile && lowZoom
            ? (zonageFill
              ? 'Vue d’ensemble par zone PLU — zoomez ou cliquez une commune pour le détail parcelle'
              : 'Zoomez ou cliquez une commune pour voir ses parcelles')
            : 'Cliquez une parcelle pour ouvrir sa fiche'}
        </div>
      )}
      {/* FINITIONS-1 (P10) — la pastille « Carte au JJ/MM/AAAA — mise à jour en attente » (bas-gauche)
          est RETIRÉE. */}
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
