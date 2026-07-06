import type { Filters } from '../store/useApp'
import { STATUT_META } from './status'
import type { Statut } from './types'

export interface ParcelProps {
  idu: string
  surface_m2: number | null
  status: Statut
  q_score: number
  a_score: number
  a_completude: number | null
  completeness_score: number
  sdp_residuelle_m2: number | null
  sous_densite: number | null
  evenement: string | null
}

// Correspondance SCOPE (score + surface, indépendante du statut) → compteurs par statut.
export const matchScope = (p: ParcelProps, f: Filters) =>
  (f.scoreMin == null || p.q_score >= f.scoreMin) &&
  (f.surfaceMin == null || (p.surface_m2 ?? 0) >= f.surfaceMin)

// Correspondance COMPLÈTE (statut inclus) → carte + liste.
export const matchAll = (p: ParcelProps, f: Filters) =>
  matchScope(p, f) && (f.statut === 'all' || p.status === f.statut)

// Chips actifs de l'omnibox, dérivés des filtres (chacun supprimable via sa clé).
export function activeChips(f: Filters): { key: keyof Filters; label: string }[] {
  const out: { key: keyof Filters; label: string }[] = []
  if (f.statut !== 'all') out.push({ key: 'statut', label: STATUT_META[f.statut].label })
  if (f.scoreMin != null) out.push({ key: 'scoreMin', label: `Q ≥ ${f.scoreMin}` })
  if (f.surfaceMin != null)
    out.push({ key: 'surfaceMin', label: `Surface ≥ ${f.surfaceMin.toLocaleString('fr-FR')} m²` })
  return out
}

export const PROMUES: Statut[] = ['chaude', 'a_surveiller', 'a_creuser']
