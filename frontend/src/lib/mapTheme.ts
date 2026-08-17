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
  /** M106 — aléas DEAL séparés (le zonage PPR réglementaire est multirisque INSÉCABLE ;
   *  la typologie inondation/mouvement de terrain vit dans kind=georisque_alea).
   *  Réglementaires superposables → contour ET trame dans LES DEUX thèmes (doctrine M105-B).
   *  L'aplat est gradué par le niveau d'aléa servi (faible/moyen/fort). */
  aleaInondation: string
  aleaMvt: string
  aleaOpacity: { faible: number; moyen: number; fort: number }
  aleaContourW: number
  aleaTrameOpacity: number
  /** M106-B — LA COULEUR DIT LE RÉSEAU (arbitrage : « tout en rose, on ne distingue rien »).
   *  Une teinte par réseau, critère M105-B dans les deux thèmes ; ni mint, ni mauve, ni
   *  #F5C518. Papang = couleur Citalis (même réseau CINOR), la FORME (tireté) dit le type. */
  transportReseaux: Record<string, string>
  /** repli d'un réseau inconnu (GTFS futur) — jamais un trou de couleur */
  transportDefaut: string
  /** pôle d'échange : NEUTRE fort (un nœud où les réseaux se croisent, pas un réseau) —
   *  la forme dit la source : disque plein = OSM (Sourcé), anneau = dérivé (Estimé). */
  pole: string
  /** M106-B P3 — axes structurants BD TOPO (importance IGN 1-2) : bleu-gris ardoise, trait
   *  PLEIN épais (l'HT anthracite reste tiretée — la forme les sépare). */
  axe: string
  /** M106 P4 — lignes haute tension : anthracite/argent NEUTRE (une CONTRAINTE d'infrastructure,
   *  pas une couleur d'opportunité), tireté long — distinct des limites parcellaires continues. */
  ht: string
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
    aleaInondation: '#45B4C6',   // pétrole clair — 7,21 sur fond sombre
    aleaMvt: '#D9A05B',          // ocre clair — 7,66 sur fond sombre
    aleaOpacity: { faible: 0.14, moyen: 0.22, fort: 0.34 },
    aleaContourW: 0.8,
    aleaTrameOpacity: 0.4,
    transportReseaux: {
      'Car Jaune': '#E3B93C',   // or — 9,46 sur fond sombre (≠ #F5C518 Pages Jaunes, moins saturé)
      'Citalis': '#E87BB0',     // rose — 6,62
      "Kar'Ouest": '#6FA8E8',   // azur — 7,08
      'Alternéo': '#45D0B8',    // turquoise — 9,20
      'Estival': '#E8935A',     // orange — 6,71
      'Carsud': '#B8C24A',      // olive — 9,11
      'Papang': '#E87BB0',      // = Citalis (réseau CINOR) ; le tireté dit « téléphérique »
    },
    transportDefaut: '#E87BB0',
    pole: '#E8EFEA',            // blanc cassé — 15,1
    axe: '#8FA6C4',             // bleu-gris — 7,06
    ht: '#B9C4C0',              // 9,83 sur fond sombre
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
    aleaInondation: '#0F6B7A',  // pétrole profond — contour 5,51 ✓ ; aplats 1,29/1,51/1,83 ✓
    aleaMvt: '#935F0C',         // ocre profond — contour 4,83 ✓ ; aplats 1,26/1,45/1,74 ✓
    aleaOpacity: { faible: 0.18, moyen: 0.28, fort: 0.40 },
    aleaContourW: 1,
    aleaTrameOpacity: 0.5,
    transportReseaux: {
      'Car Jaune': '#8A6D08',   // or profond — 4,39 sur terre claire
      'Citalis': '#B01E63',     // rose — 5,84
      "Kar'Ouest": '#1D5FC2',   // azur — 5,41
      'Alternéo': '#0B7D68',    // turquoise — 4,52
      'Estival': '#A34A00',     // orange — 5,30
      'Carsud': '#667000',      // olive — 4,83
      'Papang': '#B01E63',      // = Citalis
    },
    transportDefaut: '#B01E63',
    pole: '#14181A',            // quasi-noir — 15,9
    axe: '#33506B',             // bleu-gris profond — 7,50
    ht: '#3F4A47',              // 8,22 terre / 5,29 masse ✓
  },
}

// Conformes SANS changement au critère aplat ≥ 1,25 sur la terre claire (mesuré, pas modifié) :
// Parc #8B5A2B @0,22 → 1,34 · AU (fill zonage parcelles #4C7DF0 @0,55) → 1,89 ·
// réserve foncière #6FA8DC @0,55 → 1,54 · à creuser #8FA69A @0,45 → 1,41 ·
// limites parcelles noires (M105) 18,8 · limites communes #2E7D52 4,50.
