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
  etat_bien?: string | null   // M131 P3 : nu | bati_encore | bati_max (affichage)
  fraction?: string | null    // M135 P2 : « 1/5 » ou null (« — »)
  raison?: string | null      // M135 P3 : chip raison dominante (liste île, servi)
  top5?: unknown[] | null      // M135 P3 : contributions (geojson → raison au front)
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
  // FIX-SCOREMIN : le filtre scoreMin (sur q_score, matrice morte M129-B, jamais servi →
  // p.q_score toujours absent) est RETIRÉ — il ne filtrait rien côté client non plus.
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
  f.surfaceMin != null || f.surfaceMax != null || f.sdpMin != null ||
  f.evenement || f.veille || f.horsCopro || f.flags.length > 0 ||
  f.flagsExclus.length > 0 || f.communes.length > 0 || !!zone

// ── Chips actifs (token → suppression ciblée) ──
export interface Chip { token: string; label: string }

// M55-D (phase 2) : le badge « Filtres (N) » du header compte TOUS les critères actifs, où qu'ils
// aient été posés (rapides du header OU panneau). Le MODE (analyseLabuse) n'est PAS un filtre → exclu.
const F_ARRAYS: (keyof Filters)[] = ['tiers', 'flags', 'flagsExclus', 'communes', 'zonagePlu',
  'constructibilite', 'etatSol', 'zonePlu', 'proprietaireType', 'etatSociete', 'copro', 'signaux', 'droitsResiduels']
const F_NUMS: (keyof Filters)[] = ['surfaceMin', 'surfaceMax', 'sdpMin', 'sdpMax',
  'capaciteMin', 'multMin', 'rangMax', 'budgetMax', 'chargeMin', 'chargeMax',
  'prixMarcheMin', 'prixMarcheMax', 'caMin']
const F_BOOLS: (keyof Filters)[] = ['evenement', 'veille', 'horsCopro', 'personneMorale',
  'sousDensite', 'renouvellement', 'npnru', 'adresseAbsente', 'marcheFiable', 'modeBRentable']

export function countActiveFilters(f: Filters): number {
  let n = 0
  for (const k of F_ARRAYS) if ((f[k] as unknown[]).length) n++
  for (const k of F_NUMS) if (f[k] != null) n++
  for (const k of F_BOOLS) if (f[k]) n++
  return n
}

// M55-D stage 4 : ÉTAGE① « le terrain » = faits objectifs, valables sans aucune analyse. Tout le
// RESTE = ÉTAGE② « le regard LABUSE » (opinion, issue du scoring). Un critère d'opinion actif
// ALLUME l'interrupteur (biunivoque) ; le défaut est ÉTEINT (analyse coupée, tri factuel).
const TERRAIN_FIELDS = new Set<keyof Filters>(['surfaceMin', 'surfaceMax', 'zonagePlu', 'zonePlu',
  'etatSol', 'flags', 'flagsExclus', 'communes',
  'signaux'])   // M55-D stage 6 : les Signaux de vie = ÉVÉNEMENTS SOURCÉS, filtrables sans analyse
export function hasOpinion(f: Filters): boolean {
  for (const k of F_ARRAYS) if (!TERRAIN_FIELDS.has(k) && (f[k] as unknown[]).length) return true
  for (const k of F_NUMS) if (!TERRAIN_FIELDS.has(k) && f[k] != null) return true
  for (const k of F_BOOLS) if (!TERRAIN_FIELDS.has(k) && f[k]) return true
  return false
}

// M55-D stage 6 : RÉCAP des critères pour la phrase de la Révélation — les plus parlants,
// plafonné à `max` (4 par défaut, sinon « … ») ; vide → null (la phrase dit « Selon vos
// critères : » tel quel). M55-M point 3 : `max` réglable — le bandeau d'analyse stocke le récap
// COMPLET (max=Infinity, aucun « … ») pour le title/survol, la troncature d'affichage étant
// portée par le CSS (truncate). Les appelants historiques gardent le plafond 4.
export function resumeCriteres(f: Filters, signalLabels: Record<string, string> = {}, max = 4): string | null {
  const parts: string[] = []
  if (f.communes.length) parts.push(f.communes.length === 1 ? f.communes[0] : `${f.communes.length} communes`)
  if (f.surfaceMin != null && f.surfaceMax != null) parts.push(`${f.surfaceMin.toLocaleString('fr-FR')}–${f.surfaceMax.toLocaleString('fr-FR')} m²`)
  else if (f.surfaceMin != null) parts.push(`> ${f.surfaceMin.toLocaleString('fr-FR')} m²`)
  else if (f.surfaceMax != null) parts.push(`< ${f.surfaceMax.toLocaleString('fr-FR')} m²`)
  if (f.zonagePlu.length) parts.push(`zone ${f.zonagePlu.join('/')}`)
  if (f.etatSol.length === 1) parts.push(f.etatSol[0] === 'nu' ? 'terrain nu' : 'bâti')
  for (const sg of f.signaux) parts.push(signalLabels[sg] ?? sg)
  if (f.tiers.length) parts.push(`tiers ${f.tiers.length}`)
  if (!parts.length) return null
  return parts.length > max ? parts.slice(0, max).join(', ') + ', …' : parts.join(', ')
}

export function activeChips(f: Filters): Chip[] {
  const out: Chip[] = []
  for (const t of f.tiers) out.push({ token: `tier:${t}`, label: ALL_TIER_META[t].label })
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
// M55-D (phase 2, Q2 Vic) : persistance COMPLÈTE — CHAQUE champ de `Filters` a une clé courte, si
// bien que l'URL, « Mes vues » et les veilles (qui appellent tous filtersToHash) capturent enfin
// tout (avant : 11 champs sur ~35, le reste session-only). Piloté par tables → aucun oubli
// possible. Clés HISTORIQUES conservées (tv/smin/smax/sdp/ev/vs2/hc/fl/fx/cs/z) : un ancien
// lien s'ouvre à l'identique. FIX-SCOREMIN : la clé `q` (scoreMin, matrice morte) est RETIRÉE —
// un vieux lien portant `q=` est désormais ignoré proprement (au lieu d'être lu puis jamais filtré).
const NUM_KEYS: [keyof Filters, string][] = [
  ['surfaceMin', 'smin'], ['surfaceMax', 'smax'], ['sdpMin', 'sdp'],
  ['sdpMax', 'sdpx'], ['capaciteMin', 'cap'], ['multMin', 'mm'], ['rangMax', 'rm'],
  ['budgetMax', 'bud'], ['chargeMin', 'chmin'], ['chargeMax', 'chmax'],
  ['prixMarcheMin', 'pmin'], ['prixMarcheMax', 'pmax'], ['caMin', 'ca'],
]
const BOOL_KEYS: [keyof Filters, string][] = [
  ['evenement', 'ev'], ['veille', 'vs2'], ['horsCopro', 'hc'], ['personneMorale', 'pm'],
  ['sousDensite', 'sd'], ['renouvellement', 'rnv'], ['npnru', 'np'],
  ['adresseAbsente', 'aa'], ['marcheFiable', 'mf'], ['modeBRentable', 'mb'],
]
// M55-D stage 7 : la clé legacy `fl` (flags contraintes de secteur) n'est PLUS lue ni écrite —
// la sous-section a quitté le panneau (les flags restent en fiche/couches). Un vieux lien
// portant fl=… s'ouvre SANS erreur, la clé est simplement ignorée (aucun état filtre orphelin).
const CSV_KEYS: [keyof Filters, string][] = [
  ['flagsExclus', 'fx'], ['communes', 'cs'], ['zonagePlu', 'zf'],
  ['signaux', 'sv'],
  ['constructibilite', 'cst'], ['etatSol', 'es'], ['zonePlu', 'zpx'],
  ['proprietaireType', 'pt'], ['etatSociete', 'soc'], ['copro', 'cp'], ['droitsResiduels', 'drr'],
]

export function filtersToHash(f: Filters, zone: LngLat[] | null): string {
  const p = new URLSearchParams()
  if (f.tiers.length) p.set('tv', f.tiers.join(','))
  for (const [k, key] of NUM_KEYS) { const v = f[k] as number | null; if (v != null) p.set(key, String(v)) }
  for (const [k, key] of BOOL_KEYS) { if (f[k]) p.set(key, '1') }
  for (const [k, key] of CSV_KEYS) { const a = f[k] as string[]; if (a.length) p.set(key, a.join(',')) }
  // M55-D stage 4 : l'interrupteur « analyse » est ÉTEINT par défaut — on écrit l'exception (allumé).
  if (f.analyseLabuse) p.set('al', '1')
  if (zone) p.set('z', zone.map(([x, y]) => `${x.toFixed(5)}_${y.toFixed(5)}`).join('~'))
  const s = p.toString()
  return s ? `#f=1&${s}` : ''
}

const TIER_KEYS = Object.keys(ALL_TIER_META)   // M30 : liens partagés avec declasse_* valides
// M55-G suite point 4 : les 7 signaux SERVIS par l'UI (même liste que le panneau Filtres) —
// toute autre clé sv= est ignorée à la lecture (nu_pm / cession supprimés de l'UI).
// FILTRE-NETTOYAGE #4 — « succession » (parcel_veille_succession) rejoint les signaux servis ;
// « assemblage » reste valide (relocalisé dans « Le bien », toujours un signal backend).
const SIGNAUX_VALIDES = ['pm_privee', 'procedure', 'permis_actif', 'permis_caduc',
  'friche', 'assemblage', 'defisc', 'succession']

export function filtersFromHash(hash: string): { filters: Partial<Filters>; zone: LngLat[] | null } | null {
  if (!hash.includes('f=1')) return null
  const p = new URLSearchParams(hash.replace(/^#/, ''))
  const num = (k: string) => (p.get(k) != null && p.get(k) !== '' ? Number(p.get(k)) : null)
  const zone = p.get('z')
    ? (p.get('z')!.split('~').map((s) => s.split('_').map(Number) as LngLat)) : null
  const f: Record<string, unknown> = {
    tiers: (p.get('tv')?.split(',').filter((t) => TIER_KEYS.includes(t)) ?? []) as FilterTier[],
  }
  for (const [k, key] of NUM_KEYS) f[k] = num(key)
  for (const [k, key] of BOOL_KEYS) f[k] = p.get(key) === '1'
  for (const [k, key] of CSV_KEYS) f[k] = p.get(key)?.split(',').filter(Boolean) ?? []
  // M55-G suite point 4 : seules les clés de signaux SERVIES par l'UI passent — un vieux lien
  // portant `sv=nu_pm` ou `sv=cession` (signaux supprimés) s'ouvre sans erreur, la clé est
  // ignorée (jamais un filtre actif invisible ; le backend, lui, reste intact).
  f.signaux = (f.signaux as string[]).filter((s) => SIGNAUX_VALIDES.includes(s))
  // M101 A2 : les clés legacy d'état du sol (bati_marginal/bati_sature/bati_revele) se PLIENT
  // sur 'bati' — un vieux lien reste actif (jamais un no-op silencieux), le backend fait de même.
  f.etatSol = Array.from(new Set((f.etatSol as string[])
    .map((s) => (['bati_marginal', 'bati_sature', 'bati_revele'].includes(s) ? 'bati' : s))
    .filter((s) => ['nu', 'bati'].includes(s))))
  // M55-D stage 6 : le flag binaire « Avec événement (BODACC) » est REMPLACÉ par le groupe
  // Signaux de vie — un vieux lien `ev=1` mappe vers le signal « procédure collective ».
  if (p.get('ev') === '1') {
    f.evenement = false
    f.signaux = Array.from(new Set([...(f.signaux as string[]), 'procedure']))
  }
  // M55-D stage 4 : interrupteur ALLUMÉ si `al=1` OU si un critère d'opinion est présent (vieux lien
  // `tv=chaude` → allumé, « il porte un tier »). Terrain-only (ex. `smin=2000`) → éteint.
  f.analyseLabuse = p.get('al') === '1' || hasOpinion(f as unknown as Filters)
  return { filters: f as Partial<Filters>, zone: zone && zone.length >= 3 ? zone : null }
}
