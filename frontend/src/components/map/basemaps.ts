// Fonds de plan — source de vérité PARTAGÉE (carte principale ET comparateur de fonds).
// Géoplateforme IGN (tuiles libres « essentiels », TESTÉES sur le 974) ; pas de tuiles Google (CGU).
// Extrait de MapView pour être réutilisé par le comparateur swipe (point 24) sans dupliquer les URLs.
import type { OrthoYear } from '../../store/useApp'
export const WMTS = (layer: string, format: string) =>
  `https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&STYLE=normal&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&LAYER=${layer}&FORMAT=${format}`

export type BasemapDef = { tiles: string[]; attribution: string; maxzoom?: number }

// RETOURS-16 V1 — TOUTES les sources ortho passent par le PROXY backend (api/ortho_proxy.py) :
// aucune tuile ortho brute. Le proxy garde la photo sur la terre et une bande côtière (~700 m
// pleine, fondu jusqu'à ~1,6 km — jetées et ports restent entiers), rogne le blanc no-data, et
// répond 404 au large : la mer est l'APLAT UNIQUE du canvas (MER_ORTHO, MapView), jamais un
// patchwork de tuiles. Constat Vic 05/09 (4e recette) : rectangles bleus en escalier au large —
// c'était la mer PHOTO de l'Express (dalles) sur la mer de la mosaïque monde (autre bleu).
export const ORTHO_PROXY = (couche: string) =>
  `${window.location.origin}/map/tiles/ortho/${couche}/{z}/{x}/{y}`

export const ORTHO_MONDE: BasemapDef = {
  // sous-couche des fonds ortho : la TERRE aux petits zooms (mer fondue vers l'aplat par le
  // proxy) ; maxzoom 12 = au-delà, MapLibre ÉTIRE les tuiles z12 sous l'Express (jamais de
  // tuile z13+ demandée à cette couche, l'IGN n'y sert plus la mosaïque).
  tiles: [ORTHO_PROXY('monde')],
  attribution: '© IGN Géoplateforme — mosaïque ORTHOPHOTOS',
  maxzoom: 12,
}

export const BASEMAP_SOURCES: Record<string, BasemapDef> = {
  // FOND-SOMBRE : le raster CARTO dark_nolabels (bm-carto) est RETIRÉ — CARTO exige désormais une
  // clé (« API KEY REQUIRED » en filigrane) et le raster n'apportait rien à l'échelle de l'île
  // (décision Vic, captures à l'appui). « Sombre » = canvas + masse terrestre + nos couches, même
  // mécanisme que « Clair » (cf. MapView.applyClairMode), aux teintes MESURÉES du rendu d'avant.
  // La décision R4 (aucun nom de localité sur le Sombre, à tous les zooms) tient de fait : plus
  // aucune tuile de labels ; le Plan IGN reste disponible pour qui veut des labels.
  // M64-P1 : le fond « Clair » n'est PLUS un raster (Positron retiré) — c'est le rendu SOMBRE avec le
  // fond du canvas passé au blanc (cf. MapView.applyClairMode). Aucune tuile claire à charger.
  // RETOURS-11F4 C6 (révisé) — GetCapabilities + GetTile RÉELS Géoplateforme (2026-09-04) sur St-Denis,
  // St-Pierre, St-Paul + 5 points intérieur/est (cirques, Mafate) : la MOSAÏQUE `ORTHOIMAGERY.ORTHOPHOTOS`
  // ne sert QUE 2022 au 974 (les annuels 2023/2024 → 404), MAIS la couche `ORTHO-EXPRESS.2025`
  // (« Ortho-express RVB 2025 », 20 cm, PM_0_19) sert des dalles NON VIDES sur les 8 points de contrôle
  // aux zooms 15/18/19 → c'est le millésime réellement le plus récent servi île-entière au 974.
  // Décision F4 : « Actuelle » = Ortho Express 2025 (au lieu de la mosaïque 2022) ; le libellé de l'outil
  // Solaire (« 20 cm 2025 ») est désormais VRAI côté fond. Plan IGN v2 = couche courante (rien de plus récent).
  // Historiques : les 6 orthos-période servent au 974 ; 1965-1980 et 1980-1995 → 404 (métropole seule, exclus).
  'bm-plan': { tiles: [WMTS('GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2', 'image/png')], attribution: '© IGN Géoplateforme — Plan IGN v2' },
  // V1 — l'Express (comme tous les fonds ortho) passe par le proxy : blanc no-data rogné en
  // fondu, mer photo limitée à la bande côtière, aplat unique dessous. Jamais de blanc, jamais
  // de marche de dalles.
  'bm-ortho-now': { tiles: [ORTHO_PROXY('express')], attribution: '© IGN Ortho Express RVB 2025 (20 cm) — millésime le plus récent au 974', maxzoom: 19 },
  'bm-ortho-2000': { tiles: [ORTHO_PROXY('2000')], attribution: '© IGN ortho 2000-2005', maxzoom: 17 },
  // le millésime 1950 s'arrête ~z15 : overzoom (maxzoom) plutôt que des tuiles NOIRES au-delà.
  'bm-ortho-1950': { tiles: [ORTHO_PROXY('1950')], attribution: '© IGN ortho 1950-1965', maxzoom: 15 },
  // TEMPS (refonte) — frise des millésimes : mosaïques-période IGN VÉRIFIÉES sur le 974 (GetTile réel,
  // 3 points de contrôle St-Denis/St-Paul/St-Pierre → dalles servies ; 1965-80 et 1980-95 s'arrêtent en
  // métropole → EXCLUES). maxzoom = un cran sous le dernier zoom servi (convention 2000-2005), pour de
  // l'overzoom au lieu de tuiles noires aux limites de mission.
  'bm-ortho-2006': { tiles: [ORTHO_PROXY('2006')], attribution: '© IGN ortho 2006-2010', maxzoom: 17 },
  'bm-ortho-2011': { tiles: [ORTHO_PROXY('2011')], attribution: '© IGN ortho 2011-2015', maxzoom: 17 },
  'bm-ortho-2016': { tiles: [ORTHO_PROXY('2016')], attribution: '© IGN ortho 2016-2020', maxzoom: 18 },
  'bm-ortho-2021': { tiles: [ORTHO_PROXY('2021')], attribution: '© IGN ortho 2021-2023', maxzoom: 18 },
}

// Frise des millésimes « avant » — ordre chronologique, tous vérifiés servant des dalles sur le 974.
// L'« après » du comparateur reste toujours aujourd'hui (bm-ortho-now, verrouillé). SOURCE DE VÉRITÉ
// du sélecteur M08 et des libellés du comparateur.
export const TEMPS_MILLESIMES: { key: keyof typeof BASEMAP_SOURCES; an: string; label: string }[] = [
  { key: 'bm-ortho-1950', an: '1950', label: '1950-1965' },
  { key: 'bm-ortho-2000', an: '2000', label: '2000-2005' },
  { key: 'bm-ortho-2006', an: '2006', label: '2006-2010' },
  { key: 'bm-ortho-2011', an: '2011', label: '2011-2015' },
  { key: 'bm-ortho-2016', an: '2016', label: '2016-2020' },
  { key: 'bm-ortho-2021', an: '2021', label: '2021-2023' },
]

// FIX-FONDS B5 — millésimes d'ortho du SÉLECTEUR PRINCIPAL, dérivés de la MÊME source de vérité que
// l'outil TEMPS : « Actuelle » (bm-ortho-now) + les 6 millésimes vérifiés (TEMPS_MILLESIMES). Un seul
// jeu de millésimes pour les deux surfaces. Le libellé `an` est l'identifiant OrthoYear (store).
export const ORTHO_YEARS: { key: keyof typeof BASEMAP_SOURCES; an: OrthoYear; label: string }[] = [
  { key: 'bm-ortho-now', an: 'now', label: 'Actuelle · Ortho Express 2025' },
  ...TEMPS_MILLESIMES.map((m) => ({ key: m.key, an: m.an as OrthoYear, label: m.label })),
]

// FIX-FONDS B2/B5 — mapping UNIQUE (basemap, orthoYear) → clé de fond raster (null pour Sombre ET
// Clair, qui n'ont pas de tuile depuis FOND-SOMBRE). Consommé par la bascule de visibilité ET
// l'attribution (plus de logique dupliquée entre le rendu et l'effet).
export function activeBasemapKey(basemap: string, orthoYear: string): keyof typeof BASEMAP_SOURCES | null {
  if (basemap === 'clair' || basemap === 'dark') return null
  if (basemap === 'plan') return 'bm-plan'
  return ORTHO_YEARS.find((y) => y.an === orthoYear)?.key ?? 'bm-ortho-now'   // 'ortho' : le millésime pilote
}

// FIX-FONDS B6 — `BASEMAP_CHOICES` (ancienne liste du comparateur, sans consommateur comme sélecteur)
// RETIRÉ. Les libellés viennent d'ORTHO_YEARS (now + millésimes) + les deux fonds non-ortho.
const _FOND_LABELS: Record<string, string> = { 'bm-plan': 'Plan IGN' }
export const basemapLabel = (key: string) =>
  ORTHO_YEARS.find((y) => y.key === key)?.label ?? _FOND_LABELS[key] ?? key
