// M105-B — LE JEU DE TOKENS PAR THÈME des couches d'information de la carte.
// Un thème = un jeu de valeurs, au MÊME endroit que les valeurs sombres — jamais de
// conditions `clair ? … : …` éparpillées dans les couches (interdit du mandat).
// Consommé par MapView : à la création des couches (colonne `sombre`, valeurs d'origine
// verbatim) et par `applyBasemapStyle` (bascule de thème, un seul point).
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

// COUCHES-RETRAIT-1 lot 1 — le thème « clair » est retiré (le fond Clair a quitté le sélecteur en
// STYLE-6, applyBasemapStyle n'est plus atteignable). Un seul thème demeure : sombre.
export type MapThemeName = 'sombre'

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
  /** RETOURS-13 R6 — le flux DEAL mouvement de terrain porte QUATRE classes réelles (élevé et
   *  très élevé existent — 360 + 124 zones — et étaient écrasées en « moyen » : jamais de rouge
   *  à l'écran). Une teinte par classe, la plus grave en ROUGE ; `fort` reste accepté en repli
   *  (si la DEAL publiait un jour ce libellé) et pointe le rouge. */
  aleaMvtRamp: { faible: string; moyen: string; eleve: string; tres_eleve: string; fort: string }
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
  /** RETOURS-13 R4 — lignes moyenne tension HTA (EDF open data) : gris-sarcelle, tireté COURT et
   *  FIN — même famille de contrainte que la HTB, la forme et la valeur les séparent. */
  mt: string
  /** RETOURS-13 R5 — transport en commun en site propre (tronçons OSM + stations) : trait PLEIN
   *  épais, teinte identitaire forte distincte des réseaux de bus et des axes routiers. */
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
  /** SOURCES-1 lot 1 — contraintes du droit des sols (ER / EBC / DPU / PEB / SUP).
   *  ER or foncé (emprise grevée), EBC vert forêt (boisement, ≠ mint des statuts),
   *  DPU bleu moyen (transaction), SUP framboise (≠ améthyste FRR). PEB gradué par
   *  zone : A rouge (interdite) → B orange → C jaune-ocre → D gris (information). */
  er: string
  erOpacity: number
  ebc: string
  ebcOpacity: number
  dpu: string
  dpuOpacity: number
  pebRamp: { a: string; b: string; c: string; d: string }
  pebOpacity: number
  sup: string
  supOpacity: number
  /** SOURCES-1 lot 2 — nature et eau : DPF (trait d'eau), zones humides (sarcelle),
   *  ENP (vert profond ≠ parc marron), RPG (paille — sole agricole). */
  dpf: string
  endiguement: string
  zoneHumide: string
  zoneHumideOpacity: number
  enp: string
  enpOpacity: number
  rpg: string
  rpgOpacity: number
  /** SOURCES-1 lot 3 — sols (SIS brun, CASIAS ocre point) et bruit (classement violet
   *  gradué par catégorie, cartes de bruit prune). */
  sis: string
  sisOpacity: number
  casias: string
  bruitRamp: { cat1: string; cat2: string; cat3: string; cat4: string; cat5: string }
  bruitOpacity: number
  bruitCarte: string
  bruitCarteOpacity: number
}

export const MAP_THEME: Record<MapThemeName, MapTokens> = {
  // Colonne SOMBRE = les valeurs historiques, verbatim — la vue sombre ne bouge pas.
  sombre: {
    zonageU: '#5CE6A1',
    zonageAutre: '#8a6b3f',
    zonageOpacity: 0.10,
    zonageContourW: 0,
    ppr: '#E8695A',
    pprOpacity: 0.24,        // COUCHES-1 lot 5 (D3) — 0,14 → 0,24 : le PPR était quasi invisible
    pprContourW: 1,          // COUCHES-1 lot 5 (D3) — contour ajouté (le seul aplat sans liseré)
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
    // COUCHES-1 lot 5 (D2) — rampe 4 crans FRANCHEMENT distincts (avant beige/brun se confondaient) :
    // or pâle → ambre → orange → rouge. La classe la plus grave reste ROUGE (doctrine R6).
    aleaMvtRamp: { faible: '#F2D98A', moyen: '#E8A33D', eleve: '#E8721F', tres_eleve: '#E8564A', fort: '#E8564A' },
    aleaFillOpacity: 0.36,      // COUCHES-1 lot 5 (D4) — 0,45 → 0,36 : le mvt de terrain écrasait l'île
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
    ht: '#B9C4C0',              // 9,83 sur fond sombre (HTB argent)
    mt: '#6E86C4',              // COUCHES-1 lot 5 (D2) — HTA passe en ARDOISE-BLEU (ex gris-sarcelle) :
                                //   HTB argent vs HTA bleu = franchement distinctes (avant : deux gris ~blancs)
    tcsp: '#3FE0C8',             // C2 — turquoise vif structurant (fond sombre)
    // M134 dispositifs (sombre = tints vifs, tous > 5:1 sur fond sombre)
    qpv: '#E8934A', qpvOpacity: 0.28,                     // orange (opérationnel)
    tvaPrimo: '#56C5D0', tvaPrimoOpacity: 0.24,           // cyan (fiscal, dérivé)
    // M137-Y — 4 états, 4 couleurs (aplat @0,24) — contrastes M105-B mesurés sur fond sombre :
    zfangRenforce: '#3E74F0', zfangStandard: '#C6B08A',   // bleu roi 1,33 · sable 1,62
    // COUCHES-1 lot 5 (D1) — FRR totalité était VERT (émeraude) sur fond vert : passé en SARCELLE
    // profond, franchement distinct des verts (parc/EBC/ENP) et de l'améthyste FRR-partie.
    frrTotalite: '#1AA3B8', frrPartie: '#9B6BE0',         // sarcelle · améthyste
    // COUCHES-2 point 4 — opacité TRÈS BASSE (0,10) : ZFANG/FRR sont des aplats COMMUNE ; le
    // parcellaire et les limites de communes doivent rester lisibles DESSOUS quand la couche est
    // allumée. (Étaient 0,24 → 0,16 au Lot 5 ; abaissés encore ici, + empilement sous le parcellaire.)
    dispoFillOpacity: 0.10,
    // SOURCES-1 lot 1 — contraintes du droit des sols (tints vifs, fond sombre)
    er: '#D4A017', erOpacity: 0.30,                       // or foncé — emprise grevée (ER)
    // COUCHES-1 lot 5 (D1) — EBC était vert forêt, en camaïeu avec le mint du zonage (même famille
    // Urbanisme) : passé en forêt PROFOND/bleuté, nettement plus sombre que le mint vitrine + contour.
    ebc: '#1B7A4A', ebcOpacity: 0.30,                     // vert forêt profond — boisement classé
    dpu: '#6B8FD4', dpuOpacity: 0.30,                     // COUCHES-1 lot 5 (D3) — 0,22 → 0,30 (DPU invisible)
    pebRamp: { a: '#E8564A', b: '#F0913D', c: '#E3C13C', d: '#9AA0A6' },
    pebOpacity: 0.28,
    sup: '#C05884', supOpacity: 0.16,                     // COUCHES-1 lot 5 (D4) — 0,24 → 0,16 (SUP magenta écrasait tout)
    // SOURCES-1 lot 2 — nature et eau (fond sombre)
    dpf: '#4FC3E8',                                       // trait d'eau vif — DPF (ligne)
    endiguement: '#7FD4C1',                               // vert d'eau — digues et zones protégées
    zoneHumide: '#2E9E8F', zoneHumideOpacity: 0.30,       // sarcelle — zones humides
    // COUCHES-1 lot 5 (D1) — ENP était VERT profond, en camaïeu avec parc/EBC/ZNIEFF. Passé en
    // INDIGO-VIOLET profond : une protection réglementaire forte, franchement hors de la famille verte.
    enp: '#6A4CC2', enpOpacity: 0.28,                     // indigo — espaces naturels protégés (rédhibitoire)
    rpg: '#C9B458', rpgOpacity: 0.22,                     // paille — cultures déclarées
    // SOURCES-1 lot 3 — sols et bruit (fond sombre)
    sis: '#A0522D', sisOpacity: 0.34,                     // brun sol — SIS (4 périmètres)
    casias: '#D9973B',                                    // ocre — sites CASIAS (points)
    // COUCHES-1 lot 5 (D2) — les deux paliers servis (cat 1-2 / cat 3-5) plus séparés : violet
    // PROFOND (le plus sévère, bandes 250-300 m) → lavande CLAIRE (le moindre). Gradient lisible.
    bruitRamp: { cat1: '#7A2FC7', cat2: '#9B6BD6', cat3: '#A98BD9', cat4: '#C9BCE6', cat5: '#DAD2EE' },
    bruitOpacity: 0.26,                                   // violet gradué — classement sonore
    bruitCarte: '#B03A6B', bruitCarteOpacity: 0.30,       // COUCHES-1 lot 5 (D3) — 0,22 → 0,30 (CBS quasi invisible)
  },
}

// Conformes SANS changement au critère aplat ≥ 1,25 sur la terre claire (mesuré, pas modifié) :
// Parc #8B5A2B @0,22 → 1,34 · AU (fill zonage parcelles #4C7DF0 @0,55) → 1,89 ·
// réserve foncière #6FA8DC @0,55 → 1,54 · à creuser #8FA69A @0,45 → 1,41 ·
// limites parcelles noires (M105) 18,8 · limites communes #2E7D52 4,50.
