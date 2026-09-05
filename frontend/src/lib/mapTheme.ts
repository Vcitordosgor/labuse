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
  /** M137-U — ZNIEFF (contrainte patrimoine naturel) : vert olive, distinct du marron Parc et du rouge PPR */
  znieff: string
  znieffOpacity: number
  /** M137-U — équipements INSEE BPE (points, cercles) : distinct des icônes OSM */
  bpe: string
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
  /** RETOURS-12 C3 — RAMPES par NIVEAU (teintes franchement distinctes, plus le camaïeu d'opacité).
   *  Inondation : bleu (faible) → orange (moyen) → rouge (fort, le plus grave).
   *  Mouvement de terrain : beige (faible) → marron (moyen) → rouge (fort). La couleur ORDONNE
   *  les niveaux ; le libellé officiel reste la vérité. `aleaInondation`/`aleaMvt` gardent leur
   *  rôle d'identité (contour + trame, distinction entre les deux aléas superposés). */
  aleaInondationRamp: { faible: string; moyen: string; fort: string }
  aleaMvtRamp: { faible: string; moyen: string; fort: string }
  /** opacité d'aplat UNIQUE une fois la teinte porteuse du niveau (plus de gradient d'opacité). */
  aleaFillOpacity: number
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
  /** RETOURS-12 C2 — axe de transport structurant (BAOBAB Express) : trait PLEIN épais, teinte
   *  identitaire forte distincte des réseaux de bus (ni rose Citalis, ni ardoise des axes routiers). */
  tcsp: string
  /** M134 / M137-Y — couche « Dispositifs ». QPV orange · ANRU chartreuse · TVA cyan. Pour ZFANG et
   *  FRR, l'ÉTAT se lit à la COULEUR (une par état, ci-dessous) + hachures en second signal sur
   *  l'état moindre — plus une teinte déclinée en opacité (illisible à l'échelle île). */
  qpv: string
  qpvOpacity: number
  tvaPrimo: string
  tvaPrimoOpacity: number
  // M137-Y — ZFANG/FRR : une COULEUR PAR ÉTAT (plus une teinte déclinée en opacité). Aplat plein
  // sur l'état avantageux (renforcée / totalité) ; aplat + hachures sur l'état moindre (standard /
  // en partie). 4 hues franchement distinctes, contrastes M105-B mesurés dans les deux thèmes.
  zfangRenforce: string   // bleu roi (avantageux, aplat plein)
  zfangStandard: string   // sable désaturé (clair = version foncée pour passer M105-B)
  frrTotalite: string     // émeraude (avantageux, aplat plein)
  frrPartie: string       // améthyste
  dispoFillOpacity: number
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
    znieff: '#8F9E4B', znieffOpacity: 0.20,                 // vert olive (contrainte naturelle)
    bpe: '#5AA9E8',                                          // bleu — cercles BPE, distinct des icônes OSM
    anru: '#C6E82E',
    anruOpacity: 0.30,
    anruTrameOpacity: 0,
    cinquantePas: CINQUANTE_PAS_COLOR,               // même source que la légende — pas de littéral recopié
    cinquantePasFillOpacity: 0.16,
    cote: '#4ADE80',
    contourBrulante: TIER_V2_META.brulante.color,    // le liseré sombre suit la palette des tiers
    contourChaude: TIER_V2_META.chaude.color,
    lisereBrulantes: '#FF6B35',
    aleaInondation: '#45B4C6',   // pétrole clair — 7,21 sur fond sombre (identité/contour/trame)
    aleaMvt: '#D9A05B',          // ocre clair — 7,66 sur fond sombre (identité/contour/trame)
    aleaOpacity: { faible: 0.14, moyen: 0.22, fort: 0.34 },
    aleaContourW: 0.8,
    aleaTrameOpacity: 0.4,
    // C3 — teintes vives sur fond sombre, franchement distinctes (bleu→orange→rouge / beige→marron→rouge)
    aleaInondationRamp: { faible: '#4EA8F0', moyen: '#F0913D', fort: '#E8564A' },
    aleaMvtRamp: { faible: '#D9C08A', moyen: '#B5732E', fort: '#E8564A' },
    aleaFillOpacity: 0.45,
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
    pole: '#FF6DB3',            // M137-X — magenta vif : les pôles RESSORTENT sur l'axe gris — 8,9
    axe: '#8FA6C4',             // bleu-gris — 7,06
    ht: '#B9C4C0',              // 9,83 sur fond sombre
    tcsp: '#3FE0C8',             // C2 — turquoise vif structurant (fond sombre)
    // M134 dispositifs (sombre = tints vifs, tous > 5:1 sur fond sombre)
    qpv: '#E8934A', qpvOpacity: 0.28,                     // orange (opérationnel)
    tvaPrimo: '#56C5D0', tvaPrimoOpacity: 0.24,           // cyan (fiscal, dérivé)
    // M137-Y — 4 états, 4 couleurs (aplat @0,24) — contrastes M105-B mesurés sur fond sombre :
    zfangRenforce: '#3E74F0', zfangStandard: '#C6B08A',   // bleu roi 1,33 · sable 1,62
    frrTotalite: '#17B26A', frrPartie: '#9B6BE0',         // émeraude 1,48 · améthyste 1,37
    dispoFillOpacity: 0.24,
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
    znieff: '#6E7A2E', znieffOpacity: 0.24,                 // vert olive foncé (contrainte naturelle)
    bpe: '#2E77C2',                                          // bleu foncé — cercles BPE (mode clair)
    anru: '#8FA818',           // chartreuse foncée — aplat @0,30 → 1,28 ✓ ; trame compense le trait 2,41
    anruOpacity: 0.30,
    anruTrameOpacity: 0.6,
    cinquantePas: '#1777A3',   // cyan profond — aplat @0,20 → 1,30 ✓ ; tireté 4,46 ✓
    cinquantePasFillOpacity: 0.20,
    cote: '#14713E',           // vert de la famille mint — 3,49 ✓ sur la masse #C9C4B8 (son fond principal)
    contourBrulante: '#C23A28', // 4,77 ✓ (braise assombrie)
    contourChaude: '#A8720F',   // 3,69 ✓ (ambre assombri)
    lisereBrulantes: '#C1440E', // 4,57 ✓ (orange assombri)
    aleaInondation: '#0F6B7A',  // pétrole profond — contour 5,51 ✓ (identité/contour/trame)
    aleaMvt: '#935F0C',         // ocre profond — contour 4,83 ✓ (identité/contour/trame)
    aleaOpacity: { faible: 0.18, moyen: 0.28, fort: 0.40 },
    aleaContourW: 1,
    aleaTrameOpacity: 0.5,
    // C3 — teintes profondes sur terre claire, franchement distinctes (bleu→orange→rouge / beige→marron→rouge)
    aleaInondationRamp: { faible: '#2563EB', moyen: '#D97706', fort: '#DC2626' },
    aleaMvtRamp: { faible: '#B08A4A', moyen: '#8A4B12', fort: '#B91C1C' },
    aleaFillOpacity: 0.55,
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
    pole: '#C21F7E',            // M137-X — magenta profond : ressort sur l'axe et l'ortho claire — 5,6
    axe: '#33506B',             // bleu-gris profond — 7,50
    ht: '#3F4A47',              // 8,22 terre / 5,29 masse ✓
    tcsp: '#0E8F7E',             // C2 — turquoise profond structurant (terre claire)
    // M134 dispositifs (clair = teintes profondes, mesurées sur terre #F4F2EC)
    qpv: '#C25E1B', qpvOpacity: 0.28,                     // orange — aplat 1,40 ✓ ; contour 3,82 ✓
    tvaPrimo: '#1487A0', tvaPrimoOpacity: 0.24,           // cyan — aplat 1,34 ✓ ; contour 3,75 ✓
    // M137-Y — clair : le SABLE est FONCÉ (#8A7A52) pour passer M105-B sur l'ortho (le clair #C6B08A
    // échouait à 1,12) — « version plus foncée du même sable, pas un retour au chaud ».
    zfangRenforce: '#2A54C8', zfangStandard: '#8A7A52',   // bleu roi 1,43 · sable foncé 1,31
    frrTotalite: '#0C8A50', frrPartie: '#6E3FB5',         // émeraude 1,35 · améthyste 1,44
    dispoFillOpacity: 0.24,
  },
}

// Conformes SANS changement au critère aplat ≥ 1,25 sur la terre claire (mesuré, pas modifié) :
// Parc #8B5A2B @0,22 → 1,34 · AU (fill zonage parcelles #4C7DF0 @0,55) → 1,89 ·
// réserve foncière #6FA8DC @0,55 → 1,54 · à creuser #8FA69A @0,45 → 1,41 ·
// limites parcelles noires (M105) 18,8 · limites communes #2E7D52 4,50.
