import type { Statut } from './types'

// Statuts de la matrice premium v2 (SCHEMA_SCORING_LABUSE). Couleurs : cf. DERIVATIONS.md.
// R3 (PJ5) — RÈGLE DE WORDING : l'échelle THERMIQUE (brûlante/chaude) est RÉSERVÉE au tier P
// servi (TIER_V2_META). La matrice Q×A parle « dossier » : son 1er rang s'affiche « Priorité
// dossier » (clé interne `chaude` inchangée — zéro régression API). Plus jamais deux échelles
// thermiques concurrentes à l'écran.
// Échelle descendante : priorité dossier (menthe la plus vive) → à surveiller (vert)
// → à creuser (ambre) → écartée (rouge). « exclue » = étage 0, repliée dans écartée.
// M135 — ÉCHELLE D'ACTION (chip court `label` + libellé long `long`), au registre CLIENT.
// MÊME mapping que le backend src/labuse/scoring/tiers_client.py (test anti-dérive). Les
// COULEURS ne bougent pas (la sémantique chaud→froid marche) ; seuls les MOTS changent.
export const STATUT_META: Record<Statut, { label: string; long: string; color: string }> = {
  chaude: { label: 'Priorité', long: 'À contacter en priorité', color: '#5CE6A1' },
  a_surveiller: { label: 'À suivre', long: 'À suivre de près', color: '#4ADE96' },
  a_creuser: { label: 'Sans signal', long: 'Sans signal de vente à court terme', color: '#E8B44C' },
  ecartee: { label: 'Écartée', long: 'Écartée — motif en fiche', color: '#E8695A' },
  exclue: { label: 'Écartée', long: 'Écartée — motif en fiche', color: '#6B7A72' },
}

// Ordre d'affichage de la légende (les 4 statuts de la matrice).
export const LEGEND_ORDER: Statut[] = ['chaude', 'a_surveiller', 'a_creuser', 'ecartee']

// ── PALIERS-1 — UN SEUL VOCABULAIRE : quatre paliers, aucune autre valeur ─────
// Le domaine de tier_opportunite est Priorité / À suivre / Sans signal / Écartée. Plus de
// brûlante / chaude / réserve / à creuser / déclassé, ni « Long terme / Neutre / Faible ».
// MÊME mapping que le backend src/labuse/scoring/tiers_client.py (test anti-dérive).
// REPARATIONS-1 lot 2b — DÉCISION DE VIC, RÉVERSIBLE : « Priorité » cesse d'être SERVI comme
// palier tant qu'aucune validation propre n'existe (×0,52 mesuré en marche avant, 1 vente sur
// 111, définition mécanique sur une seule variable). « À suivre » porte toute la tête classée.
// Affichage seul : les tiers stockés restent en base — repasser ce drapeau à true restitue le
// palier tel quel (même drapeau côté back : tiers_client.PRIORITE_SERVIE).
export const PRIORITE_SERVIE = false
export type Palier = 'priorite' | 'a_suivre' | 'sans_signal' | 'ecartee'
// `label` = chip COURT (écran), `long` = libellé long (« i », fiche).
export const PALIER_META: Record<Palier, { label: string; long: string; color: string }> = {
  priorite: { label: 'Priorité', long: 'À contacter en priorité', color: '#E8695A' },
  a_suivre: { label: 'À suivre', long: 'À suivre de près', color: '#E8B44C' },
  sans_signal: { label: 'Sans signal', long: 'Sans signal de vente à court terme', color: '#8FA69A' },
  ecartee: { label: 'Écartée', long: 'Écartée — motif en fiche', color: '#4A5A52' },
}
// CORRESPONDANCE EN LECTURE des anciens codes (runs jamais réécrits) → palier canonique.
export const CORRESPONDANCE_LEGACY: Record<string, Palier> = {
  brulante: 'priorite', chaude: 'a_suivre',
  a_creuser: 'sans_signal', reserve_fonciere: 'sans_signal',
  declasse_bati_sature: 'sans_signal', declasse_non_constructible: 'sans_signal',
  declasse_bati_revele: 'sans_signal', declasse_zone_fermee: 'sans_signal',
  declasse_au_statut_inconnu: 'sans_signal', declasse_au_fermee: 'sans_signal',
  exclue: 'ecartee',
}
// le CODE canonique d'un tier (nouveau ou ancien) — le seul point qui connaît les anciens codes.
// REPARATIONS-1 lot 2b — Priorité non servie : « priorite » (et donc « brulante ») se sert
// « a_suivre » — la tête classée entière porte À suivre.
export function codePalier(raw: string | null | undefined): Palier | null {
  if (!raw) return null
  const code = raw in PALIER_META ? (raw as Palier) : (CORRESPONDANCE_LEGACY[raw] ?? null)
  if (code === 'priorite' && !PRIORITE_SERVIE) return 'a_suivre'
  return code
}

// PALIERS-1 — les codes STOCKÉS possibles : les 4 paliers (runs v2) OU les codes par rang des
// ANCIENS runs (jamais réécrits). Le PLOMBERIE (filtres, compteurs) tolère les deux ; l'AFFICHAGE
// résout toujours vers le vocabulaire unique via TIER_V2_META / codePalier / verdictMeta.
export type LegacyTier = 'brulante' | 'chaude' | 'a_creuser' | 'reserve_fonciere' | 'exclue'
export type TierV2 = Palier | LegacyTier | TierDeclasse
// TIER_V2_META résout TOUT code (nouveau ou ancien) vers son palier canonique, pour que les
// consommateurs (Legend, TierBadge, fiche…) lisent le même vocabulaire quel que soit le run servi.
// REPARATIONS-1 lot 2b — dérivé VIA codePalier : tout code (dont « priorite »/« brulante »)
// résout vers le palier SERVI (À suivre tant que PRIORITE_SERVIE est false).
export const TIER_V2_META: Record<string, { label: string; long: string; color: string }> = {
  ...Object.fromEntries(
    [...Object.keys(PALIER_META), ...Object.keys(CORRESPONDANCE_LEGACY)]
      .map((code) => [code, PALIER_META[codePalier(code) ?? (code as Palier)]]),
  ),
}
// la légende ne liste que les paliers SERVIS (Priorité en est retirée tant que non validée).
export const LEGEND_V2_ORDER: Palier[] = PRIORITE_SERVIE
  ? ['priorite', 'a_suivre', 'sans_signal', 'ecartee']
  : ['a_suivre', 'sans_signal', 'ecartee']

// PALIERS-1 — les ex-tiers de DÉCLASSEMENT (bâti saturé, zone fermée, AU…) ne sont plus des
// paliers : ce sont des MOTIFS (affichés en fiche, filtrables), la parcelle GARDE son palier de
// probabilité (Sans signal ici, ou Priorité/À suivre selon p). On conserve les CODES pour le
// filtre par motif ; leur libellé de palier est « Sans signal » (un seul vocabulaire).
export type TierDeclasse =
  | 'declasse_bati_sature' | 'declasse_non_constructible' | 'declasse_bati_revele'
  | 'declasse_zone_fermee' | 'declasse_au_statut_inconnu' | 'declasse_au_fermee'
export type FilterTier = TierV2
export const TIER_DECLASSE_META: Record<TierDeclasse, { label: string; long: string; color: string }> = {
  declasse_bati_sature: { ...PALIER_META.sans_signal },
  declasse_non_constructible: { ...PALIER_META.sans_signal },
  declasse_bati_revele: { ...PALIER_META.sans_signal },
  declasse_zone_fermee: { ...PALIER_META.sans_signal },
  declasse_au_statut_inconnu: { ...PALIER_META.sans_signal },
  declasse_au_fermee: { ...PALIER_META.sans_signal },
}
export const DECLASSE_ORDER = Object.keys(TIER_DECLASSE_META) as TierDeclasse[]
export const ALL_TIER_META: Record<string, { label: string; color: string }> =
  { ...TIER_V2_META, ...TIER_DECLASSE_META }

// Le CHIP d'un palier de la légende (« i » des paliers) — résout tout code vers le vocabulaire
// unique. Le groupe « declassees » n'est plus un palier : son chip est « Sans signal ».
export function tierChipLabel(key: string): string {
  if (key === 'declassees') return PALIER_META.sans_signal.label
  const code = codePalier(key)
  return code ? PALIER_META[code].label : key
}

// ══════════ ANALYSE-1 — LE NOUVEAU MOTEUR (Score LABUSE + Signal de mutation) ══════════
// VOCABULAIRE CLIENT GRAVÉ (mandat §2, ne pas réinventer) : la BANDE de Score en toutes lettres +
// couleur FRANCHE (jamais de camaïeu entre bandes), et le Signal de mutation en BADGE SECONDAIRE
// (jamais au même niveau visuel que la bande). Aucun chiffre brut de score ni de probabilité au client.
// La bande vient du moteur TELLE QUELLE (aucun quota, rang ni percentile côté écran) ; « Sans potentiel
// constructible » (score 0) est une catégorie À PART, jamais confondue avec « Faible ».
export type Bande = 'A' | 'B' | 'C' | 'D' | '0' | 'NC'
export const BANDE_META: Record<Bande, { label: string; long: string; color: string }> = {
  A: { label: 'Excellente', long: 'Excellente — le meilleur potentiel constructible', color: '#5CE6A1' }, // menthe vive
  B: { label: 'Bonne', long: 'Bonne — potentiel constructible solide', color: '#46A0E0' },                // bleu franc
  C: { label: 'À étudier', long: 'À étudier — potentiel réel sous conditions', color: '#E8B23A' },          // or / ambre
  D: { label: 'Faible', long: 'Faible — potentiel constructible limité', color: '#C4653C' },               // terracotta
  '0': { label: 'Sans potentiel constructible', long: 'Sans potentiel constructible — aucun droit à bâtir résiduel', color: '#5C7268' }, // gris-vert neutre (catégorie à part)
  NC: { label: 'Analyse incomplète', long: 'Analyse incomplète — une donnée manque pour conclure', color: '#8A8FA0' },                   // gris-bleu neutre
}
// ordre lexicographique d'affichage (identique au moteur) : bandes de qualité, incomplète, sans potentiel.
export const BANDE_ORDER: Bande[] = ['A', 'B', 'C', 'D', 'NC', '0']
export const BANDE_QUALITE: Bande[] = ['A', 'B', 'C', 'D']
export function bandeMeta(b: string | null | undefined) {
  return (b && BANDE_META[b as Bande]) || null
}

// Signal de mutation — badge SECONDAIRE (Fort / Moyen / Faible). Teinte braise (le signal « chauffe »),
// distincte de l'échelle des bandes ; jamais au même poids visuel que la bande (mandat §2/§4).
export type SignalNiveau = 'fort' | 'moyen' | 'faible'
export const SIGNAL_META: Record<SignalNiveau, { label: string; long: string; color: string }> = {
  fort: { label: 'Signal fort', long: 'Signal de mutation fort', color: '#FF8A50' },
  moyen: { label: 'Signal moyen', long: 'Signal de mutation moyen', color: '#E0A845' },
  faible: { label: 'Signal faible', long: 'Signal de mutation faible', color: '#7E9488' },
}
export function signalMeta(s: string | null | undefined) {
  return (s && SIGNAL_META[s as SignalNiveau]) || null
}

// Correctif M5 (verdict d'en-tête) — règle UNIQUE, partout où un verdict s'affiche :
// 1. exclusion dure étage 0 (run servi) → « Écartée » legacy, motifs sourcés (l'étage 0 prime) ;
// 2. sinon, un run v2 existe → le TIER v2 est le verdict (avec rang/×N côté appelant) ;
// 3. sinon → statut matrice legacy (parcs sans run v2).
// M131 P3 — BADGE D'ÉTAT DU BIEN (affichage pur du fait M125/M129-D, aucun calcul côté
// client : le serveur envoie `etat_bien` ∈ nu | bati_encore | bati_max). Trois états, jamais
// un slug à l'écran. `short` pour les cartes denses, `label` complet en tooltip.
export const ETAT_BIEN_META: Record<string, { label: string; short: string; color: string }> = {
  nu: { label: 'Nu', short: 'Nu', color: '#6FA8DC' },
  bati_encore: { label: 'Bâtie — on peut encore construire', short: 'Bâtie · encore', color: '#5CE6A1' },
  bati_max: { label: 'Bâtie — construite au maximum', short: 'Bâtie · au max', color: '#8C7468' },
}
export function etatBienMeta(e: string | null | undefined) {
  return (e && ETAT_BIEN_META[e]) || null
}

// M137-V — les 7 domaines BPE (INSEE) : code → libellé + couleur. Les cercles carte de la couche
// « Équipements (INSEE BPE) » sont colorés par domaine (le bleu unique était illisible) ; la légende
// et le filtre par domaine lisent la MÊME table. « A services » (le plus nombreux, ~16 k) en gris
// neutre pour ne pas saturer ; les familles à enjeu (santé rouge, enseignement bleu) ressortent.
export const BPE_DOM: { code: string; label: string; color: string }[] = [
  { code: 'A', label: 'Services aux particuliers', color: '#7C8AA0' },
  { code: 'B', label: 'Commerces', color: '#E0A23C' },
  { code: 'C', label: 'Enseignement', color: '#4C8DD6' },
  { code: 'D', label: 'Santé et social', color: '#D9534F' },
  { code: 'E', label: 'Transports', color: '#3CB6A8' },
  { code: 'F', label: 'Sport et loisirs', color: '#6FBF52' },
  { code: 'G', label: 'Tourisme', color: '#B06FD6' },
]
export const BPE_DOM_CODES = BPE_DOM.map((d) => d.code)

export function verdictMeta(
  statut: Statut | null | undefined,
  tierV2: string | null | undefined,
  etage0?: boolean | number | null,
): { label: string; long: string; color: string; v2: boolean; tier: TierV2 | null } {
  if (etage0) return { ...STATUT_META.ecartee, v2: false, tier: null }
  // PALIERS-1 — tout code (nouveau OU ancien) est résolu vers son palier canonique (les 4 valeurs).
  const code = codePalier(tierV2)
  if (code) {
    // palier « ecartee » = étage 0 → rendu écartée legacy (couleur/teinte historique)
    if (code === 'ecartee') return { ...STATUT_META.ecartee, v2: true, tier: code }
    return { ...PALIER_META[code], v2: true, tier: code }
  }
  // M-Q P2-69 : repli sur la matrice legacy (éteinte M37). Sur le parc servi, TOUTES les parcelles
  // portent un tier v2 → ce repli ne s'arme jamais. S'il s'armait (parc sans run v2), il ne doit
  // JAMAIS se faire passer pour un verdict servi : libellé DISTINCT + couleur NEUTRE (modèle
  // Legend.tsx « Classement historique »), jamais une teinte thermique ni un statut matriciel
  // indistinguable du vrai verdict. Le motif legacy reste lisible ailleurs (section Qualité).
  if (statut && STATUT_META[statut]) {
    return { label: 'Classement historique', long: 'Classement historique', color: NONE_COLOR, v2: false, tier: null }
  }
  return { label: '—', long: '—', color: NONE_COLOR, v2: false, tier: null }
}

// M5.1 : le TIER EFFECTIF d'une parcelle — la même règle que verdictMeta, sous forme de
// valeur filtrable (compteurs, chips, filtres carte/liste du mode commune).
// étage 0 servi → 'ecartee' ; sinon tier v2 ; sans run v2 → null (repli legacy).
export function effectiveTier(
  tierV2: string | null | undefined,
  etage0?: boolean | number | null,
): TierV2 | null {
  if (etage0) return 'ecartee'
  // Renvoie le code STOCKÉ (ancien ou nouveau) pour la plomberie compteurs/filtres ; l'AFFICHAGE
  // le résout vers le vocabulaire unique (TIER_V2_META[t].label). 'ecartee' commun aux deux.
  const t = tierV2 as TierV2 | null | undefined
  return t && TIER_V2_META[t] ? t : null
}

// M30 item 3 : même règle qu'effectiveTier, DÉCLASSEMENTS compris — pour le filtre tiers
// uniquement (les compteurs restent sur effectiveTier : rien ne bouge par défaut).
export function filterableTier(
  tierV2: string | null | undefined,
  etage0?: boolean | number | null,
): FilterTier | null {
  if (etage0) return 'ecartee'
  const t = tierV2 as FilterTier | null | undefined
  return t && ALL_TIER_META[t] ? t : null
}

export const NONE_COLOR = '#39463F'

export const statutColor = (s: Statut | null | undefined) =>
  (s && STATUT_META[s]?.color) || NONE_COLOR

// Anneau/indicateur de complétude : sous 50 % = incomplet (règle d'or, exigence #1).
export const completudeColor = (c: number) => (c >= 50 ? '#5CE6A1' : '#E8B44C')

// ── Score V (Vendabilité) — bandes D2 : fort (50-100) / présents (25-49) / faible (1-24)
// / aucun (0) / N.A. (public, bailleur). Palette : orange braise (le V « chauffe »), distincte
// de l'échelle verte des statuts Q×A.
import type { VBand } from './types'
export const V_BAND_META: Record<VBand, { label: string; color: string }> = {
  fort: { label: 'Signal fort', color: '#FF8A50' },
  present: { label: 'Signaux présents', color: '#E8B44C' },
  faible: { label: 'Signal faible', color: '#8FA69A' },
  aucun: { label: 'Aucun signal', color: '#5C7268' },
  na: { label: 'N.A.', color: '#4A5A52' },
}
// ALGO-1 item 2 : vBandColor RETIRÉE — le Score V n'est plus affiché (contre-prédictif,
// RR@1158 = 0,51, SCORING_SPEC §7-D). V_BAND_META reste : types du payload (backtest/audit).

// ── M6.1 / M12 C5 : couche « Zonage PLU (parcelles) » — familles U/AU/A/N ────────────────
// Palette DISTINCTE du verdict v2 (braise #E8695A, ambre #E8B44C, gris-vert #8FA69A, bleu
// #6FA8DC, menthe #5CE6A1) pour éviter toute confusion.
// M12 C5 — écart de teinte MAXIMISÉ entre familles voisines (le grief « U1a/U1c trop proches »
// est un grief d'écart de teinte : on écarte les 4 familles autour du cercle chromatique).
// U = magenta franc (rose→magenta), AU = bleu roi (nettement décollé du magenta), A = or/ambre
// chaud, N = vert franc. Voisins : magenta↔bleu, bleu↔or, or↔vert — chacun à ≥90° de teinte.
// `autre` = typezone hors U/AU/A/N (rare, gris neutre) ; hors zonage GPU = null.
export type ZoneFam = 'U' | 'AU' | 'A' | 'N' | 'autre'
export const ZONE_FAM_META: Record<ZoneFam, { label: string; color: string }> = {
  U: { label: 'U — urbaine', color: '#E5417F' },      // magenta franc
  // M30-revue (arbitrage Vic) : « à urbaniser » seul promettait l'ouverture — le statut est
  // suffixé avec le vocabulaire des motifs existants (fermée / à statut inconnu). Libellé de
  // FAMILLE (légende) : le statut PAR PARCELLE vit dans les motifs de déclassement/fiche.
  AU: { label: 'AU — à urbaniser (statut : ouverte / fermée / inconnue)', color: '#4C7DF0' }, // bleu roi
  A: { label: 'A — agricole', color: '#E8B23A' },      // or / ambre chaud
  N: { label: 'N — naturelle', color: '#3FB56A' },     // vert franc
  autre: { label: 'Autre zonage', color: '#8A94A6' },
}
export const ZONE_FAM_ORDER: ZoneFam[] = ['U', 'AU', 'A', 'N', 'autre']
//: couleur « 50 pas géométriques » (M6.1 item 2) — bande littorale, cyan-bleu côtier
export const CINQUANTE_PAS_COLOR = '#4CC3E8'

// ── ÉQUIPEMENTS (contexte promotrice, affichage seul) — 7 catégories différenciées.
// M12 C6 : la META est REMONTÉE ici (lib partagée) pour que la légende (Legend.tsx) et le rendu
// carte (MapView) tirent la même source — la légende « Équipements » cohabite dans le panneau
// unique au lieu d'un bloc flottant qui recouvrait le verdict.
export const EQUIP_META: { key: string; emoji: string; color: string; label: string }[] = [
  { key: 'mairie', emoji: '🏛️', color: '#B497F0', label: 'Mairie' },
  { key: 'ecole', emoji: '🏫', color: '#5CE6A1', label: 'École' },
  { key: 'sante', emoji: '🏥', color: '#E8695A', label: 'Santé' },
  { key: 'commerce', emoji: '🛒', color: '#F0A868', label: 'Commerce' },
  { key: 'tcsp', emoji: '🚌', color: '#6FD3C6', label: 'Transport' },
  { key: 'police', emoji: '🚓', color: '#8FB4F0', label: 'Police / gendarmerie' },
  { key: 'sport', emoji: '⚽', color: '#E8B44C', label: 'Sport' },
  // M55-A (10/08) : élargissement borné validé Vic — marché forain, crèche, collège/lycée.
  { key: 'marche', emoji: '🧺', color: '#E59BC4', label: 'Marché forain' },
  { key: 'creche', emoji: '🧸', color: '#F2B08A', label: 'Crèche' },
  { key: 'college_lycee', emoji: '🎓', color: '#79C9A0', label: 'Collège / lycée' },
]

// Item 7 (UX V1) : définitions Q/A/V — UNE phrase chacune, identique partout où la lettre
// apparaît (fiche, liste, restitution, CRM). Jamais un sigle nu pour un nouvel utilisateur.
export const SCORE_TIP = {
  q: 'Q — Qualité intrinsèque de la parcelle (règles PLU, risques, terrain)',
  a: 'A — Accessibilité du dossier (contraintes d’acquisition et de montage)',
} as const


// CRED-4 (revue externe 12/07) : âge d'un signal V d'un coup d'œil — pastille verte < 6 mois,
// ambre 6-18, rouge > 18. Affichage seulement : aucune re-pondération.
export function ageSignal(dateIso: string | null | undefined): { mois: number; color: string; label: string } | null {
  if (!dateIso) return null
  const mois = Math.max(0, Math.floor((Date.now() - new Date(dateIso).getTime()) / (30.44 * 86_400_000)))
  return {
    mois,
    color: mois < 6 ? '#5CE6A1' : mois <= 18 ? '#E8B44C' : '#E8695A',
    label: mois < 1 ? 'ce mois-ci' : mois === 1 ? 'il y a 1 mois' : `il y a ${mois} mois`,
  }
}
