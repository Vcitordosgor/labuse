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
  'bm-plan': { tiles: [WMTS('GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2', 'image/png')], attribution: '© IGN Géoplateforme' },
  'bm-ortho-now': { tiles: [WMTS('ORTHOIMAGERY.ORTHOPHOTOS', 'image/jpeg')], attribution: '© IGN BD ORTHO' },
  'bm-ortho-2000': { tiles: [WMTS('ORTHOIMAGERY.ORTHOPHOTOS2000-2005', 'image/jpeg')], attribution: '© IGN ortho 2000-2005', maxzoom: 17 },
  // le millésime 1950 s'arrête ~z15 : overzoom (maxzoom) plutôt que des tuiles NOIRES au-delà.
  'bm-ortho-1950': { tiles: [WMTS('ORTHOIMAGERY.ORTHOPHOTOS.1950-1965', 'image/png')], attribution: '© IGN ortho 1950-1965', maxzoom: 15 },
}

// Choix proposés au comparateur de fonds (ordre + libellés courts). Sous-ensemble ordonné du registre.
export const BASEMAP_CHOICES: { key: keyof typeof BASEMAP_SOURCES; label: string }[] = [
  { key: 'bm-ortho-now', label: 'Ortho actuelle' },
  { key: 'bm-ortho-2000', label: 'Ortho 2000-2005' },
  { key: 'bm-ortho-1950', label: 'Ortho 1950-1965' },
  { key: 'bm-plan', label: 'Plan IGN' },
  { key: 'bm-carto', label: 'Fond sombre' },
]

export const basemapLabel = (key: string) =>
  BASEMAP_CHOICES.find((c) => c.key === key)?.label ?? key
