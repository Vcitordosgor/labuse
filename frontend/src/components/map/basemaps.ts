// Fonds de plan — source de vérité PARTAGÉE (carte principale ET comparateur de fonds).
// Géoplateforme IGN (tuiles libres « essentiels », TESTÉES sur le 974) ; pas de tuiles Google (CGU).
// Extrait de MapView pour être réutilisé par le comparateur swipe (point 24) sans dupliquer les URLs.
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

// Choix proposés au comparateur de fonds (ordre + libellés courts). Sous-ensemble ordonné du registre.
export const BASEMAP_CHOICES: { key: keyof typeof BASEMAP_SOURCES; label: string }[] = [
  { key: 'bm-ortho-now', label: 'Ortho actuelle' },
  { key: 'bm-ortho-2000', label: 'Ortho 2000-2005' },
  { key: 'bm-ortho-1950', label: 'Ortho 1950-1965' },
  { key: 'bm-plan', label: 'Plan IGN' },
  { key: 'bm-carto', label: 'Fond sombre' },
]

export const basemapLabel = (key: string) =>
  BASEMAP_CHOICES.find((c) => c.key === key)?.label
    ?? TEMPS_MILLESIMES.find((m) => m.key === key)?.label
    ?? key
