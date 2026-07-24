import type { Statut } from './types'

// Statuts de la matrice premium v2 (SCHEMA_SCORING_LABUSE). Couleurs : cf. DERIVATIONS.md.
// R3 (PJ5) — RÈGLE DE WORDING : l'échelle THERMIQUE (brûlante/chaude) est RÉSERVÉE au tier P
// servi (TIER_V2_META). La matrice Q×A parle « dossier » : son 1er rang s'affiche « Priorité
// dossier » (clé interne `chaude` inchangée — zéro régression API). Plus jamais deux échelles
// thermiques concurrentes à l'écran.
// Échelle descendante : priorité dossier (menthe la plus vive) → à surveiller (vert)
// → à creuser (ambre) → écartée (rouge). « exclue » = étage 0, repliée dans écartée.
export const STATUT_META: Record<Statut, { label: string; color: string }> = {
  chaude: { label: 'Priorité dossier', color: '#5CE6A1' },
  a_surveiller: { label: 'À surveiller', color: '#4ADE96' },
  a_creuser: { label: 'À creuser', color: '#E8B44C' },
  ecartee: { label: 'Écartée', color: '#E8695A' },
  exclue: { label: 'Exclue', color: '#6B7A72' },
}

// Ordre d'affichage de la légende (les 4 statuts de la matrice).
export const LEGEND_ORDER: Statut[] = ['chaude', 'a_surveiller', 'a_creuser', 'ecartee']

// ── Scoring v2 (M5, P×C) — tiers et verdict effectif ─────────────────────────
// Palette gravée au lot 4 (bloc « Pourquoi ce score ») : source de vérité UNIQUE ici.
export type TierV2 = 'brulante' | 'chaude' | 'a_creuser' | 'reserve_fonciere' | 'ecartee'
export const TIER_V2_META: Record<TierV2, { label: string; color: string }> = {
  brulante: { label: 'Brûlante v2', color: '#E8695A' },
  chaude: { label: 'Chaude v2', color: '#E8B44C' },
  a_creuser: { label: 'À creuser', color: '#8FA69A' },
  reserve_fonciere: { label: 'Réserve foncière', color: '#6FA8DC' },
  ecartee: { label: 'Écartée', color: '#4A5A52' },
}
export const LEGEND_V2_ORDER: TierV2[] = ['brulante', 'chaude', 'reserve_fonciere', 'a_creuser', 'ecartee']

// Correctif M5 (verdict d'en-tête) — règle UNIQUE, partout où un verdict s'affiche :
// 1. exclusion dure étage 0 (run servi) → « Écartée » legacy, motifs sourcés (l'étage 0 prime) ;
// 2. sinon, un run v2 existe → le TIER v2 est le verdict (avec rang/×N côté appelant) ;
// 3. sinon → statut matrice legacy (parcs sans run v2).
export function verdictMeta(
  statut: Statut | null | undefined,
  tierV2: string | null | undefined,
  etage0?: boolean | number | null,
): { label: string; color: string; v2: boolean; tier: TierV2 | null } {
  if (etage0) return { ...STATUT_META.ecartee, v2: false, tier: null }
  const t = tierV2 as TierV2 | null | undefined
  if (t && TIER_V2_META[t]) {
    // tier v2 « ecartee » = étage 0 vu du pipeline v2 → rendu écartée legacy (règle 1)
    if (t === 'ecartee') return { ...STATUT_META.ecartee, v2: true, tier: t }
    return { ...TIER_V2_META[t], v2: true, tier: t }
  }
  return { ...(statut ? STATUT_META[statut] : { label: '—', color: NONE_COLOR }), v2: false, tier: null }
}

// M5.1 : le TIER EFFECTIF d'une parcelle — la même règle que verdictMeta, sous forme de
// valeur filtrable (compteurs, chips, filtres carte/liste du mode commune).
// étage 0 servi → 'ecartee' ; sinon tier v2 ; sans run v2 → null (repli legacy).
export function effectiveTier(
  tierV2: string | null | undefined,
  etage0?: boolean | number | null,
): TierV2 | null {
  if (etage0) return 'ecartee'
  const t = tierV2 as TierV2 | null | undefined
  return t && TIER_V2_META[t] ? t : null
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
export const vBandColor = (b: VBand | null | undefined) => (b && V_BAND_META[b]?.color) || NONE_COLOR

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
  AU: { label: 'AU — à urbaniser', color: '#4C7DF0' }, // bleu roi (décollé du magenta)
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
]

// Item 7 (UX V1) : définitions Q/A/V — UNE phrase chacune, identique partout où la lettre
// apparaît (fiche, liste, restitution, CRM). Jamais un sigle nu pour un nouvel utilisateur.
export const SCORE_TIP = {
  q: 'Q — Qualité intrinsèque de la parcelle (règles PLU, risques, terrain)',
  a: 'A — Accessibilité du dossier (contraintes d’acquisition et de montage)',
  v: 'V — Vendabilité : signaux publics indiquant un propriétaire susceptible de vendre',
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
