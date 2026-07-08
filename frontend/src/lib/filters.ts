import type { Filters } from '../store/useApp'
import { pointInPolygon, type LngLat } from './geo'
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
  vue_mer: string | null
  evenement: string | null
  flags: string[]
  cluster?: number | null  // « même propriétaire ×N » (groupe SIREN parmi les chaudes île)
  proprio?: string | null
  centroid?: LngLat | null // calculé une fois côté client (filtre zone)
}

export const PROMUES: Statut[] = ['chaude', 'a_surveiller', 'a_creuser']

//: flags métier proposés au filtre (couches à drapeau) — libellés humains.
export const FLAG_DEFS: { key: string; label: string }[] = [
  { key: 'sol_pollue', label: 'Pollution' },
  { key: 'abf', label: 'ABF' },
  { key: 'icpe', label: 'ICPE' },
  { key: 'risques', label: 'Risques (PPR/aléa)' },
  { key: 'prescription_plu', label: 'Prescription PLU' },
]

// Correspondance SCOPE (tout SAUF le statut) → les compteurs par statut restent lisibles.
export function matchScope(p: ParcelProps, f: Filters, zone: LngLat[] | null): boolean {
  if (f.scoreMin != null && p.q_score < f.scoreMin) return false
  if (f.surfaceMin != null && (p.surface_m2 ?? 0) < f.surfaceMin) return false
  if (f.surfaceMax != null && (p.surface_m2 ?? Infinity) > f.surfaceMax) return false
  if (f.sdpMin != null && (p.sdp_residuelle_m2 ?? -1) < f.sdpMin) return false
  if (f.evenement && p.evenement !== 'rouge') return false
  if (f.vueMer && p.vue_mer !== 'oui') return false
  if (f.flags.length && !f.flags.some((fl) => p.flags?.includes(fl))) return false
  if (f.flagsExclus.length && f.flagsExclus.some((fl) => p.flags?.includes(fl))) return false
  if (zone && (!p.centroid || !pointInPolygon(p.centroid, zone))) return false
  return true
}

export const matchAll = (p: ParcelProps, f: Filters, zone: LngLat[] | null) =>
  matchScope(p, f, zone) && (f.statuts.length === 0 || f.statuts.includes(p.status))

export const hasScopeFilters = (f: Filters, zone: LngLat[] | null) =>
  f.scoreMin != null || f.surfaceMin != null || f.surfaceMax != null || f.sdpMin != null ||
  f.evenement || f.vueMer || f.flags.length > 0 || f.flagsExclus.length > 0 ||
  f.communes.length > 0 || !!zone

// ── Chips actifs (token → suppression ciblée) ──
export interface Chip { token: string; label: string }

export function activeChips(f: Filters): Chip[] {
  const out: Chip[] = []
  for (const s of f.statuts) out.push({ token: `statut:${s}`, label: STATUT_META[s].label })
  if (f.scoreMin != null) out.push({ token: 'scoreMin', label: `Q ≥ ${f.scoreMin}` })
  if (f.surfaceMin != null) out.push({ token: 'surfaceMin', label: `≥ ${f.surfaceMin.toLocaleString('fr-FR')} m²` })
  if (f.surfaceMax != null) out.push({ token: 'surfaceMax', label: `≤ ${f.surfaceMax.toLocaleString('fr-FR')} m²` })
  if (f.sdpMin != null) out.push({ token: 'sdpMin', label: `SDP ≥ ${f.sdpMin.toLocaleString('fr-FR')} m²` })
  if (f.evenement) out.push({ token: 'evenement', label: '● Événement' })
  if (f.vueMer) out.push({ token: 'vueMer', label: 'Vue mer' })
  for (const fl of f.flags) out.push({ token: `flag:${fl}`, label: FLAG_DEFS.find((d) => d.key === fl)?.label ?? fl })
  for (const fl of f.flagsExclus) out.push({ token: `flagx:${fl}`, label: `Sans ${FLAG_DEFS.find((d) => d.key === fl)?.label ?? fl}` })
  if (f.communes.length) out.push({ token: 'communes', label: `Secteur (${f.communes.length} communes)` })
  return out
}

export function removeToken(f: Filters, token: string): Filters {
  if (token.startsWith('statut:')) return { ...f, statuts: f.statuts.filter((s) => s !== token.slice(7)) }
  if (token.startsWith('flag:')) return { ...f, flags: f.flags.filter((x) => x !== token.slice(5)) }
  if (token.startsWith('flagx:')) return { ...f, flagsExclus: f.flagsExclus.filter((x) => x !== token.slice(6)) }
  if (token === 'communes') return { ...f, communes: [] }
  if (token === 'evenement') return { ...f, evenement: false }
  if (token === 'vueMer') return { ...f, vueMer: false }
  return { ...f, [token]: null }
}

// ── URL partageable (hash #f=…) : une recherche = un lien ──
export function filtersToHash(f: Filters, zone: LngLat[] | null): string {
  const p = new URLSearchParams()
  if (f.statuts.length) p.set('st', f.statuts.join(','))
  if (f.scoreMin != null) p.set('q', String(f.scoreMin))
  if (f.surfaceMin != null) p.set('smin', String(f.surfaceMin))
  if (f.surfaceMax != null) p.set('smax', String(f.surfaceMax))
  if (f.sdpMin != null) p.set('sdp', String(f.sdpMin))
  if (f.evenement) p.set('ev', '1')
  if (f.vueMer) p.set('vm', '1')
  if (f.flags.length) p.set('fl', f.flags.join(','))
  if (f.flagsExclus.length) p.set('fx', f.flagsExclus.join(','))
  if (f.communes.length) p.set('cs', f.communes.join(','))
  if (zone) p.set('z', zone.map(([x, y]) => `${x.toFixed(5)}_${y.toFixed(5)}`).join('~'))
  const s = p.toString()
  return s ? `#f=1&${s}` : ''
}

export function filtersFromHash(hash: string): { filters: Partial<Filters>; zone: LngLat[] | null } | null {
  if (!hash.includes('f=1')) return null
  const p = new URLSearchParams(hash.replace(/^#/, ''))
  const num = (k: string) => (p.get(k) != null && p.get(k) !== '' ? Number(p.get(k)) : null)
  const zone = p.get('z')
    ? (p.get('z')!.split('~').map((s) => s.split('_').map(Number) as LngLat)) : null
  return {
    filters: {
      statuts: (p.get('st')?.split(',').filter(Boolean) ?? []) as Statut[],
      scoreMin: num('q'),
      surfaceMin: num('smin'),
      surfaceMax: num('smax'),
      sdpMin: num('sdp'),
      evenement: p.get('ev') === '1',
      vueMer: p.get('vm') === '1',
      flags: p.get('fl')?.split(',').filter(Boolean) ?? [],
      flagsExclus: p.get('fx')?.split(',').filter(Boolean) ?? [],
      communes: p.get('cs')?.split(',').filter(Boolean) ?? [],
    },
    zone: zone && zone.length >= 3 ? zone : null,
  }
}
