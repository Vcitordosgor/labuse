// M63-P1 — PALETTE DE CARTE PAR FOND (sombre / clair). Point de vérité UNIQUE des couleurs de
// couches : plus aucune couleur en dur dans MapView. Le fond SOMBRE reproduit EXACTEMENT les
// valeurs d'avant M63 (garde-fou : « pas un pixel ne bouge »). Le fond CLAIR reçoit une valeur au
// contraste MESURÉ ≥ 3:1 sur le land Positron (~#F5F5F3, cf. contrast.py / RAPPORT_M63). Le RÔLE
// de chaque couleur est identique dans les deux fonds ; seule la valeur s'adapte.
//
// Les échelles SÉMANTIQUES (tiers de verdict, familles de zonage) sont reconstruites ici depuis
// la palette : le verdict garde son échelle (brûlante→écartée), les zonages gardent leur code —
// on ne change que la teinte pour rester lisible sur clair.

export type MapTheme = 'dark' | 'light'

// Chaque entrée : [sombre, clair]. Sombre = valeur historique EXACTE.
const PAIRS = {
  bgCanvas:        ['#060A08', '#EDEDEA'],   // fond du canvas sous les tuiles
  baseFill:        ['#22302A', '#C2CAC5'],   // trame cadastrale neutre (fill, opacité basse)
  limites:         ['#8FA69A', '#4A5F54'],   // limites de parcelles (le « vert pâle » invisible sur clair)
  factualFill:     ['#8FA69A', '#5E7268'],   // remplissage en tri factuel
  selection:       ['#ECF5EF', '#0A6B3F'],   // parcelle SÉLECTIONNÉE (le « blanc » invisible sur clair)
  ping:            ['#ECF5EF', '#0A6B3F'],   // pulsation de sélection
  labelText:       ['#ECF5EF', '#143A28'],   // texte des étiquettes de zone / sélection
  labelHalo:       ['#06130C', '#FFFFFF'],   // halo du texte (inversé selon le fond)
  labelHalo2:      ['#0F1A14', '#FFFFFF'],   // 2e ton de halo utilisé sur certaines étiquettes
  communes:        ['#5CE6A1', '#2E7D52'],   // limites de communes (mint invisible sur clair)
  communeTextHot:  ['#5CE6A1', '#1F7A46'],   // libellé commune — mode « chaud »
  communeTextCold: ['#8FA69A', '#4A5F54'],   // libellé commune — mode « froid »
  communeBorderHot:['#2E6B4F', '#2E7D52'],
  communeBorderCold:['#26302B', '#C4CCC7'],
  search:          ['#B497F0', '#6A4FB0'],   // résultats de recherche (violet)
  moduleStroke:    ['#120d1d', '#FFFFFF'],   // contour des points de module
  measure:         ['#5CE6A1', '#2E7D52'],   // outil de mesure
  measureStroke:   ['#06130C', '#FFFFFF'],
  zoneDraw:        ['#5CE6A1', '#2E7D52'],   // zone de filtre dessinée
  ppr:             ['#E8695A', '#C4402F'],   // PPR risque
  parc:            ['#8B5A2B', '#8B5A2B'],   // Parc national (le marron passe déjà 5.3:1 sur clair)
  parcLine:        ['#7A4A1E', '#5A3416'],
  anru:            ['#C6E82E', '#6E7D10'],   // ANRU (chartreuse) → olive foncé sur clair
  cinquantePas:    ['#4CC3E8', '#1C7A9E'],   // 50 pas (cyan)
  renouv:          ['#C9834E', '#9A5A28'],   // renouvellement (cuivre)
  brulanteOutline: ['#FF6B35', '#C4402F'],   // liseré brûlante v2
  vizGreenDeep:    ['#2E6B4F', '#2E7D52'],   // bordures/accents structurels verts
  none:            ['#39463F', '#9AA39E'],   // fallback / hors-zonage (quasi éteint)
  ecartee:         ['#E8695A', '#C4402F'],   // exclusion (étage 0 + tier écartée)
  // familles de zonage (échelle sémantique, code conservé)
  zonageUFill:     ['#5CE6A1', '#2E7D52'],   // fill zonage U (couche overlay)
  zonageNonUFill:  ['#8a6b3f', '#6B5228'],
} as const

// tiers de verdict (échelle sémantique) — sombre = valeur ALL_TIER_META, clair = teinte lisible.
const TIER_PAIRS: Record<string, [string, string]> = {
  brulante:         ['#E8695A', '#C4402F'],
  chaude:           ['#E8B44C', '#9A6A0C'],
  reserve_fonciere: ['#6FA8DC', '#2E6FA8'],
  a_creuser:        ['#8FA69A', '#4A5F54'],
  ecartee:          ['#E8695A', '#C4402F'],   // suit la doctrine écartée
  // les 6 déclassements partagent la teinte terre
  declasse:         ['#8C7468', '#6B5040'],
}
// familles de zonage PLU — sombre = ZONE_FAM_META, clair = teinte lisible (code conservé).
const ZONE_FAM_PAIRS: Record<string, [string, string]> = {
  U:    ['#E5417F', '#E5417F'],   // magenta : OK sur les deux
  AU:   ['#4C7DF0', '#4C7DF0'],   // bleu : OK sur les deux
  A:    ['#E8B23A', '#9A6A0C'],   // or → ocre foncé
  N:    ['#3FB56A', '#1F7D42'],   // vert → vert foncé
  autre:['#8A94A6', '#5A6472'],
}

const idx = (t: MapTheme) => (t === 'light' ? 1 : 0)

export type MapColors = { [K in keyof typeof PAIRS]: string } & {
  tier: (key: string) => string
  zoneFam: (fam: string) => string
}

export function mapColors(theme: MapTheme): MapColors {
  const i = idx(theme)
  const out = {} as Record<string, unknown>
  for (const [k, v] of Object.entries(PAIRS)) out[k] = v[i]
  out.tier = (key: string) => (TIER_PAIRS[key] ?? TIER_PAIRS.declasse)[i]
  out.zoneFam = (fam: string) => (ZONE_FAM_PAIRS[fam] ?? PAIRS.none)[i]
  return out as MapColors
}

// Clés de tiers connues (pour construire les expressions MapLibre par thème).
export const TIER_KEYS = Object.keys(TIER_PAIRS)
export const themeOf = (basemapClair: boolean): MapTheme => (basemapClair ? 'light' : 'dark')
