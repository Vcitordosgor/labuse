// Fonds de plan — source de vérité PARTAGÉE (carte principale ET comparateur de fonds).
// Géoplateforme IGN (tuiles libres « essentiels », TESTÉES sur le 974) ; pas de tuiles Google (CGU).
// Extrait de MapView pour être réutilisé par le comparateur swipe (point 24) sans dupliquer les URLs.
import type { OrthoYear } from '../../store/useApp'
export const WMTS = (layer: string, format: string) =>
  `https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&STYLE=normal&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&LAYER=${layer}&FORMAT=${format}`

export type BasemapDef = { tiles: string[]; attribution: string; maxzoom?: number }

export const BASEMAP_SOURCES: Record<string, BasemapDef> = {
  // R4 (revue Vic n°2, reprise du C3) : sur le fond SOMBRE, les noms de localités disparaissent
  // À TOUS LES ZOOMS (décision ferme — Saint-Gilles-les-Bains en gros par-dessus la carte).
  // La variante nolabels retire AUSSI les noms de rues : assumé — la fiche porte l'adresse,
  // le Plan IGN reste disponible pour qui veut des labels. Ortho : pas de labels par nature.
  'bm-carto': {
    tiles: ['https://a.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}.png', 'https://b.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}.png'],
    attribution: '© OSM · CARTO',
  },
  // M64-P1 : le fond « Clair » n'est PLUS un raster (Positron retiré) — c'est le rendu SOMBRE avec le
  // fond du canvas passé au blanc (cf. MapView.applyClairMode). Aucune tuile claire à charger.
  'bm-plan': { tiles: [WMTS('GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2', 'image/png')], attribution: '© IGN Géoplateforme' },
  'bm-ortho-now': { tiles: [WMTS('ORTHOIMAGERY.ORTHOPHOTOS', 'image/jpeg')], attribution: '© IGN BD ORTHO' },
  'bm-ortho-2000': { tiles: [WMTS('ORTHOIMAGERY.ORTHOPHOTOS2000-2005', 'image/jpeg')], attribution: '© IGN ortho 2000-2005', maxzoom: 17 },
  // le millésime 1950 s'arrête ~z15 : overzoom (maxzoom) plutôt que des tuiles NOIRES au-delà.
  'bm-ortho-1950': { tiles: [WMTS('ORTHOIMAGERY.ORTHOPHOTOS.1950-1965', 'image/png')], attribution: '© IGN ortho 1950-1965', maxzoom: 15 },
  // TEMPS (refonte) — frise des millésimes : mosaïques-période IGN VÉRIFIÉES sur le 974 (GetTile réel,
  // 3 points de contrôle St-Denis/St-Paul/St-Pierre → dalles servies ; 1965-80 et 1980-95 s'arrêtent en
  // métropole → EXCLUES). maxzoom = un cran sous le dernier zoom servi (convention 2000-2005), pour de
  // l'overzoom au lieu de tuiles noires aux limites de mission.
  'bm-ortho-2006': { tiles: [WMTS('ORTHOIMAGERY.ORTHOPHOTOS2006-2010', 'image/jpeg')], attribution: '© IGN ortho 2006-2010', maxzoom: 17 },
  'bm-ortho-2011': { tiles: [WMTS('ORTHOIMAGERY.ORTHOPHOTOS2011-2015', 'image/jpeg')], attribution: '© IGN ortho 2011-2015', maxzoom: 17 },
  'bm-ortho-2016': { tiles: [WMTS('ORTHOIMAGERY.ORTHOPHOTOS2016-2020', 'image/jpeg')], attribution: '© IGN ortho 2016-2020', maxzoom: 18 },
  'bm-ortho-2021': { tiles: [WMTS('ORTHOIMAGERY.ORTHOPHOTOS2021-2023', 'image/jpeg')], attribution: '© IGN ortho 2021-2023', maxzoom: 18 },
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
  { key: 'bm-ortho-now', an: 'now', label: 'Actuelle' },
  ...TEMPS_MILLESIMES.map((m) => ({ key: m.key, an: m.an as OrthoYear, label: m.label })),
]

// FIX-FONDS B2/B5 — mapping UNIQUE (basemap, orthoYear) → clé de fond raster (null en mode Clair,
// qui n'a pas de tuile). Consommé par la bascule de visibilité ET l'attribution (plus de logique
// dupliquée entre le rendu et l'effet).
export function activeBasemapKey(basemap: string, orthoYear: string): keyof typeof BASEMAP_SOURCES | null {
  if (basemap === 'clair') return null
  if (basemap === 'dark') return 'bm-carto'
  if (basemap === 'plan') return 'bm-plan'
  return ORTHO_YEARS.find((y) => y.an === orthoYear)?.key ?? 'bm-ortho-now'   // 'ortho' : le millésime pilote
}

// FIX-FONDS B6 — `BASEMAP_CHOICES` (ancienne liste du comparateur, sans consommateur comme sélecteur)
// RETIRÉ. Les libellés viennent d'ORTHO_YEARS (now + millésimes) + les deux fonds non-ortho.
const _FOND_LABELS: Record<string, string> = { 'bm-plan': 'Plan IGN', 'bm-carto': 'Fond sombre' }
export const basemapLabel = (key: string) =>
  ORTHO_YEARS.find((y) => y.key === key)?.label ?? _FOND_LABELS[key] ?? key
