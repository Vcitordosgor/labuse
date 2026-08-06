import type { Filters } from '../store/useApp'
import { pointInPolygon, type LngLat } from './geo'
import { ALL_TIER_META, effectiveTier, filterableTier, type FilterTier } from './status'
import type { Statut } from './types'

export interface ParcelProps {
  idu: string
  adresse?: string | null   // M6 2a (§1.8) : adresse postale BAN (properties geojson)
  surface_m2: number | null
  status: Statut
  q_score: number
  a_score: number
  a_completude: number | null
  completeness_score: number
  sdp_residuelle_m2: number | null
  sous_densite: number | null
  evenement: string | null
  evenement_date?: string | null   // événement daté v1.3 (badge secondaire)
  flags: string[]
  cluster?: number | null  // « même propriétaire ×N » (groupe SIREN parmi les opportunités v2)
  proprio?: string | null
  centroid?: LngLat | null // calculé une fois côté client (filtre zone)
  v_score?: number | null  // Score V (signaux propriétaire — dossier de la fiche)
  v_dernier_signal?: string | null   // CRED-4 : fraîcheur du dernier signal daté
  v_band?: string | null
  owner_type?: string | null
  // M5.1 : le verdict v2 PILOTE (tier + étage 0 du run servi) — cf. verdictMeta()
  tier_v2?: string | null
  rang_v2?: number | null
  mult_v2?: number | null
  copro_v2?: boolean
  veille?: boolean
  etage0?: boolean | number
}

//: flags métier proposés au filtre (couches à drapeau) — libellés humains.
export const FLAG_DEFS: { key: string; label: string }[] = [
  { key: 'sol_pollue', label: 'Pollution' },
  { key: 'abf', label: 'ABF' },
  { key: 'icpe', label: 'ICPE' },
  { key: 'risques', label: 'Risques (PPR/aléa)' },
  { key: 'prescription_plu', label: 'Prescription PLU' },
]

// M45 (P1) : filtre « par signal » (Score V) RETIRÉ — anti-filtre acté au cadrage. Score V est
// retiré du scoring (RR 0,51, M11 Phase 0) et de l'affichage (M35) ; filtrer sur un signal mort
// est un vestige. `V_SIGNAL_DEFS`/`vSignalCodes`/`f.vSignals` supprimés (front + API). L'option
// masquée « dirigeant 65+ » disparaît avec — un critère personne physique n'a pas sa place (RGPD).

// M5.1 : appartenance au PÉRIMÈTRE PAR DÉFAUT (univers v2 hors étage 0 servi) — une
// brûlante v2 « écartée matrice » appartient au périmètre ; l'étage 0 dur n'y est pas.
export const inDefaultPerimetre = (p: ParcelProps): boolean =>
  effectiveTier(p.tier_v2, p.etage0) !== 'ecartee'

// Correspondance SCOPE (tout SAUF le tier) → les compteurs par tier restent lisibles.
export function matchScope(p: ParcelProps, f: Filters, zone: LngLat[] | null): boolean {
  if (f.scoreMin != null && p.q_score < f.scoreMin) return false
  if (f.surfaceMin != null && (p.surface_m2 ?? 0) < f.surfaceMin) return false
  if (f.surfaceMax != null && (p.surface_m2 ?? Infinity) > f.surfaceMax) return false
  if (f.sdpMin != null && (p.sdp_residuelle_m2 ?? -1) < f.sdpMin) return false
  if (f.evenement && p.evenement !== 'rouge') return false
  if (f.veille && !p.veille) return false
  if (f.horsCopro && p.copro_v2) return false
  if (f.flags.length && !f.flags.some((fl) => p.flags?.includes(fl))) return false
  if (f.flagsExclus.length && f.flagsExclus.some((fl) => p.flags?.includes(fl))) return false
  if (zone && (!p.centroid || !pointInPolygon(p.centroid, zone))) return false
  return true
}

// filtre COMPLET : scope + tiers (vide = périmètre par défaut ; « ecartee » = étage 0 dur).
// M30 item 3 : filterableTier — les declasse_* sont sélectionnables ; vide inchangé.
export const matchAll = (p: ParcelProps, f: Filters, zone: LngLat[] | null) => {
  if (!matchScope(p, f, zone)) return false
  const t = filterableTier(p.tier_v2, p.etage0)
  if (f.tiers.length === 0) return t !== 'ecartee'
  return t != null && f.tiers.includes(t)
}

export const hasScopeFilters = (f: Filters, zone: LngLat[] | null) =>
  f.scoreMin != null || f.surfaceMin != null || f.surfaceMax != null || f.sdpMin != null ||
  f.evenement || f.veille || f.horsCopro || f.flags.length > 0 ||
  f.flagsExclus.length > 0 || f.communes.length > 0 || !!zone

// ── Chips actifs (token → suppression ciblée) ──
export interface Chip { token: string; label: string }

export function activeChips(f: Filters): Chip[] {
  const out: Chip[] = []
  for (const t of f.tiers) out.push({ token: `tier:${t}`, label: ALL_TIER_META[t].label })
  if (f.scoreMin != null) out.push({ token: 'scoreMin', label: `Q ≥ ${f.scoreMin}` })
  if (f.surfaceMin != null) out.push({ token: 'surfaceMin', label: `≥ ${f.surfaceMin.toLocaleString('fr-FR')} m²` })
  if (f.surfaceMax != null) out.push({ token: 'surfaceMax', label: `≤ ${f.surfaceMax.toLocaleString('fr-FR')} m²` })
  if (f.sdpMin != null) out.push({ token: 'sdpMin', label: `SDP ≥ ${f.sdpMin.toLocaleString('fr-FR')} m²` })
  if (f.evenement) out.push({ token: 'evenement', label: '● Événement' })
  if (f.veille) out.push({ token: 'veille', label: 'Veille succession' })
  if (f.horsCopro) out.push({ token: 'horsCopro', label: 'Hors copro' })
  for (const fl of f.flags) out.push({ token: `flag:${fl}`, label: FLAG_DEFS.find((d) => d.key === fl)?.label ?? fl })
  for (const fl of f.flagsExclus) out.push({ token: `flagx:${fl}`, label: `Sans ${FLAG_DEFS.find((d) => d.key === fl)?.label ?? fl}` })
  if (f.communes.length) out.push({ token: 'communes', label: `Secteur (${f.communes.length} communes)` })
  return out
}

export function removeToken(f: Filters, token: string): Filters {
  if (token.startsWith('tier:')) return { ...f, tiers: f.tiers.filter((t) => t !== token.slice(5)) }
  if (token.startsWith('flag:')) return { ...f, flags: f.flags.filter((x) => x !== token.slice(5)) }
  if (token.startsWith('flagx:')) return { ...f, flagsExclus: f.flagsExclus.filter((x) => x !== token.slice(6)) }
  if (token === 'communes') return { ...f, communes: [] }
  if (token === 'evenement') return { ...f, evenement: false }
  if (token === 'veille') return { ...f, veille: false }
  if (token === 'horsCopro') return { ...f, horsCopro: false }
  return { ...f, [token]: null }
}

// ── URL partageable (hash #f=…) : une recherche = un lien ──
// M5.1 : `tv` (tiers v2) remplace `st` (statuts matrice) — les anciens liens `st=`
// sont ignorés proprement (périmètre par défaut), consigné au rapport.
export function filtersToHash(f: Filters, zone: LngLat[] | null): string {
  const p = new URLSearchParams()
  if (f.tiers.length) p.set('tv', f.tiers.join(','))
  if (f.scoreMin != null) p.set('q', String(f.scoreMin))
  if (f.surfaceMin != null) p.set('smin', String(f.surfaceMin))
  if (f.surfaceMax != null) p.set('smax', String(f.surfaceMax))
  if (f.sdpMin != null) p.set('sdp', String(f.sdpMin))
  if (f.evenement) p.set('ev', '1')
  if (f.veille) p.set('vs2', '1')
  if (f.horsCopro) p.set('hc', '1')
  if (f.flags.length) p.set('fl', f.flags.join(','))
  if (f.flagsExclus.length) p.set('fx', f.flagsExclus.join(','))
  if (f.communes.length) p.set('cs', f.communes.join(','))
  if (zone) p.set('z', zone.map(([x, y]) => `${x.toFixed(5)}_${y.toFixed(5)}`).join('~'))
  const s = p.toString()
  return s ? `#f=1&${s}` : ''
}

const TIER_KEYS = Object.keys(ALL_TIER_META)   // M30 : liens partagés avec declasse_* valides

export function filtersFromHash(hash: string): { filters: Partial<Filters>; zone: LngLat[] | null } | null {
  if (!hash.includes('f=1')) return null
  const p = new URLSearchParams(hash.replace(/^#/, ''))
  const num = (k: string) => (p.get(k) != null && p.get(k) !== '' ? Number(p.get(k)) : null)
  const zone = p.get('z')
    ? (p.get('z')!.split('~').map((s) => s.split('_').map(Number) as LngLat)) : null
  return {
    filters: {
      tiers: (p.get('tv')?.split(',').filter((t) => TIER_KEYS.includes(t)) ?? []) as FilterTier[],
      scoreMin: num('q'),
      surfaceMin: num('smin'),
      surfaceMax: num('smax'),
      sdpMin: num('sdp'),
      evenement: p.get('ev') === '1',
      veille: p.get('vs2') === '1',
      horsCopro: p.get('hc') === '1',
      flags: p.get('fl')?.split(',').filter(Boolean) ?? [],
      flagsExclus: p.get('fx')?.split(',').filter(Boolean) ?? [],
      communes: p.get('cs')?.split(',').filter(Boolean) ?? [],
    },
    zone: zone && zone.length >= 3 ? zone : null,
  }
}
