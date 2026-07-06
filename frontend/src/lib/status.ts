import type { Statut } from './types'

// Statuts de la matrice premium v2 (SCHEMA_SCORING_LABUSE). Couleurs : cf. DERIVATIONS.md.
// Échelle descendante : chaude (menthe la plus vive) → à surveiller (vert) → à creuser (ambre)
// → écartée (rouge). « exclue » = exclusion étage 0, repliée dans écartée au niveau matrice.
export const STATUT_META: Record<Statut, { label: string; color: string }> = {
  chaude: { label: 'Chaude', color: '#5CE6A1' },
  a_surveiller: { label: 'À surveiller', color: '#4ADE96' },
  a_creuser: { label: 'À creuser', color: '#E8B44C' },
  ecartee: { label: 'Écartée', color: '#E8695A' },
  exclue: { label: 'Exclue', color: '#6B7A72' },
}

// Ordre d'affichage de la légende (les 4 statuts de la matrice).
export const LEGEND_ORDER: Statut[] = ['chaude', 'a_surveiller', 'a_creuser', 'ecartee']

export const NONE_COLOR = '#39463F'

export const statutColor = (s: Statut | null | undefined) =>
  (s && STATUT_META[s]?.color) || NONE_COLOR

// Anneau/indicateur de complétude : sous 50 % = incomplet (règle d'or, exigence #1).
export const completudeColor = (c: number) => (c >= 50 ? '#5CE6A1' : '#E8B44C')
