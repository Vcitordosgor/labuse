// M105-B — LE JEU DE TOKENS PAR THÈME des couches d'information de la carte.
// Un thème = un jeu de valeurs, au MÊME endroit que les valeurs sombres — jamais de
// conditions `clair ? … : …` éparpillées dans les couches (interdit du mandat).
// Consommé par MapView : à la création des couches (colonne `sombre`, valeurs d'origine
// verbatim) et par `applyClairMode` (bascule de thème, un seul point).
//
// Doctrine arbitrée (AUDIT_M105B) : un aplat d'information est distinguable à
// ratio composite/fond ≥ 1,25:1 ET porte un contour de SA teinte à ≥ 3:1 ; un trait
// seul vise ≥ 3:1. La différenciation ENTRE couches par l'aplat plafonne ≈ 1,1 →
// c'est le CONTOUR et la TRAME qui différencient les couches actives ensemble.
// AUCUNE couche ne change de teinte identitaire (vert reste vert, rouge reste rouge,
// chartreuse reste chartreuse, cyan reste cyan) — seuls saturation/valeur/opacité
// bougent. Les fonds clairs réels : terre #F4F2EC (dominant), masse #C9C4B8.
//
// Ratios mesurés (WCAG, composite alpha exact sur la terre #F4F2EC) en colonne clair.

import { CINQUANTE_PAS_COLOR, TIER_V2_META } from './status'

export type MapThemeName = 'sombre' | 'clair'

export type MapTokens = {
  /** zonage GPU : famille U (la couche la plus consultée) / autres familles */
  zonageU: string
  zonageAutre: string
  zonageOpacity: number
  /** contour des zones — largeur 0 = pas de contour (le sombre n'en a jamais eu) */
  zonageContourW: number
  ppr: string
  pprOpacity: number
  pprContourW: number
  anru: string
  anruOpacity: number
  /** trame diagonale ANRU (daltonisme : U vert vs ANRU chartreuse confondus en
   *  deutéranopie — la trame est la seconde variable). Opacité 0 = pas de trame. */
  anruTrameOpacity: number
  cinquantePas: string
  cinquantePasFillOpacity: number
  /** trait de côte (couche `ile-cote`, rendue en Clair seulement) */
  cote: string
  /** contours de tiers (liseré des promues, PROMUES_FILTER = brûlante/chaude) */
  contourBrulante: string
  contourChaude: string
  /** liseré épais des brûlantes (couche parcels-brulantes) */
  lisereBrulantes: string
}

export const MAP_THEME: Record<MapThemeName, MapTokens> = {
  // Colonne SOMBRE = les valeurs historiques, verbatim — la vue sombre ne bouge pas.
  sombre: {
    zonageU: '#5CE6A1',
    zonageAutre: '#8a6b3f',
    zonageOpacity: 0.10,
    zonageContourW: 0,
    ppr: '#E8695A',
    pprOpacity: 0.14,
    pprContourW: 0,
    anru: '#C6E82E',
    anruOpacity: 0.30,
    anruTrameOpacity: 0,
    cinquantePas: CINQUANTE_PAS_COLOR,               // même source que la légende — pas de littéral recopié
    cinquantePasFillOpacity: 0.16,
    cote: '#4ADE80',
    contourBrulante: TIER_V2_META.brulante.color,    // le liseré sombre suit la palette des tiers
    contourChaude: TIER_V2_META.chaude.color,
    lisereBrulantes: '#FF6B35',
  },
  // Colonne CLAIR = les valeurs arbitrées M105-B (mêmes teintes, assombries/saturées).
  clair: {
    zonageU: '#1E9E58',        // mint CANON DA (M73-G) — aplat @0,22 → 1,26 ✓ ; contour 3,08 ✓
    zonageAutre: '#6E4F27',    // brun foncé — aplat 1,39 ✓ ; contour 6,67 ✓
    zonageOpacity: 0.22,
    zonageContourW: 1,
    ppr: '#D14432',            // rouge profond — aplat @0,20 → 1,31 ✓ ; contour 4,09 ✓
    pprOpacity: 0.20,
    pprContourW: 1,
    anru: '#8FA818',           // chartreuse foncée — aplat @0,30 → 1,28 ✓ ; trame compense le trait 2,41
    anruOpacity: 0.30,
    anruTrameOpacity: 0.6,
    cinquantePas: '#1777A3',   // cyan profond — aplat @0,20 → 1,30 ✓ ; tireté 4,46 ✓
    cinquantePasFillOpacity: 0.20,
    cote: '#14713E',           // vert de la famille mint — 3,49 ✓ sur la masse #C9C4B8 (son fond principal)
    contourBrulante: '#C23A28', // 4,77 ✓ (braise assombrie)
    contourChaude: '#A8720F',   // 3,69 ✓ (ambre assombri)
    lisereBrulantes: '#C1440E', // 4,57 ✓ (orange assombri)
  },
}

// Conformes SANS changement au critère aplat ≥ 1,25 sur la terre claire (mesuré, pas modifié) :
// Parc #8B5A2B @0,22 → 1,34 · AU (fill zonage parcelles #4C7DF0 @0,55) → 1,89 ·
// réserve foncière #6FA8DC @0,55 → 1,54 · à creuser #8FA69A @0,45 → 1,41 ·
// limites parcelles noires (M105) 18,8 · limites communes #2E7D52 4,50.
