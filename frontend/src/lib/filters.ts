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
  v_score?: number | null  // Score V (Vendabilité, Stage 3)
  v_band?: string | null
  owner_type?: string | null
  brulante?: boolean
  v_sig?: string[]         // codes des signaux V retenus (filtre par signal)
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

//: filtres « par signal » du Score V — un libellé métier = un groupe de codes §5.3.
export const V_SIGNAL_DEFS: { key: string; label: string; codes: string[] }[] = [
  { key: 'pcl', label: 'Procédure collective',
    codes: ['BODACC_LJ', 'BODACC_LJ_CLOT', 'BODACC_RJ', 'BODACC_SAUVEGARDE', 'BODACC_RADIATION'] },
  { key: 'friche', label: 'Friche', codes: ['FRICHE'] },
  { key: 'hors_ile', label: 'Propriétaire hors île', codes: ['GEO_HORS_ILE'] },
  { key: 'dpe_fg', label: 'DPE F-G', codes: ['DPE_G_MULTI', 'DPE_G', 'DPE_F'] },
  { key: 'tenure', label: 'Détention longue', codes: ['DVF_TENURE_OBS5'] },
  { key: 'dirigeant', label: 'Dirigeant 65+',
    codes: ['RNE_DIRIGEANT_75', 'RNE_DIRIGEANT_70', 'RNE_DIRIGEANT_65'] },
]
export const vSignalCodes = (keys: string[]): string[] =>
  V_SIGNAL_DEFS.filter((d) => keys.includes(d.key)).flatMap((d) => d.codes)

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
  if (f.vBands.length && !f.vBands.includes(p.v_band ?? 'na')) return false
  if (f.vSignals.length && !vSignalCodes(f.vSignals).some((c) => p.v_sig?.includes(c))) return false
  if (f.brulantes && !p.brulante) return false
  if (zone && (!p.centroid || !pointInPolygon(p.centroid, zone))) return false
  return true
}

export const matchAll = (p: ParcelProps, f: Filters, zone: LngLat[] | null) =>
  matchScope(p, f, zone) && (f.statuts.length === 0 || f.statuts.includes(p.status))

export const hasScopeFilters = (f: Filters, zone: LngLat[] | null) =>
  f.scoreMin != null || f.surfaceMin != null || f.surfaceMax != null || f.sdpMin != null ||
  f.evenement || f.vueMer || f.flags.length > 0 || f.flagsExclus.length > 0 ||
  f.communes.length > 0 || f.vBands.length > 0 || f.vSignals.length > 0 || f.brulantes || !!zone

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
  if (f.brulantes) out.push({ token: 'brulantes', label: '🔥 Brûlantes' })
  for (const b of f.vBands) out.push({ token: `vband:${b}`, label: `V ${b}` })
  for (const s of f.vSignals) out.push({ token: `vsig:${s}`, label: V_SIGNAL_DEFS.find((d) => d.key === s)?.label ?? s })
  return out
}

export function removeToken(f: Filters, token: string): Filters {
  if (token.startsWith('statut:')) return { ...f, statuts: f.statuts.filter((s) => s !== token.slice(7)) }
  if (token.startsWith('flag:')) return { ...f, flags: f.flags.filter((x) => x !== token.slice(5)) }
  if (token.startsWith('flagx:')) return { ...f, flagsExclus: f.flagsExclus.filter((x) => x !== token.slice(6)) }
  if (token.startsWith('vband:')) return { ...f, vBands: f.vBands.filter((x) => x !== token.slice(6)) }
  if (token.startsWith('vsig:')) return { ...f, vSignals: f.vSignals.filter((x) => x !== token.slice(5)) }
  if (token === 'brulantes') return { ...f, brulantes: false }
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
  if (f.vBands.length) p.set('vb', f.vBands.join(','))
  if (f.vSignals.length) p.set('vs', f.vSignals.join(','))
  if (f.brulantes) p.set('br', '1')
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
      vBands: p.get('vb')?.split(',').filter(Boolean) ?? [],
      vSignals: p.get('vs')?.split(',').filter(Boolean) ?? [],
      brulantes: p.get('br') === '1',
    },
    zone: zone && zone.length >= 3 ? zone : null,
  }
}
