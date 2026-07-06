import type { Fiche, ParcelResult, PipelineEntry, PipelineMeta, SourceInfo, Stats } from './types'

export interface ParcelFeatureCollection {
  type: 'FeatureCollection'
  features: Array<{ type: 'Feature'; geometry: unknown; properties: Record<string, unknown> }>
}

// SOURCE DE VÉRITÉ du Socle V1 : le scoring premium v2, run q_v2 (dryrun_parcel_evaluations).
// JAMAIS parcel_evaluations (éval historique). Cf. brief « NOTE SOURCE DE VÉRITÉ ».
export const SOURCE = 'q_v2'
export const COMMUNE = 'Saint-Paul'

async function j<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init)
  if (!r.ok) throw new Error(`${url} → HTTP ${r.status}`)
  return r.json() as Promise<T>
}

const q = (extra: Record<string, string | number> = {}) =>
  new URLSearchParams({
    source: SOURCE, commune: COMMUNE,
    ...Object.fromEntries(Object.entries(extra).map(([k, v]) => [k, String(v)])),
  }).toString()

export const getStats = () => j<Stats>(`/stats?${q()}`)
export const getResults = () => j<ParcelResult[]>(`/parcels?${q({ limit: 500 })}`)
export const getParcelsGeojson = () =>
  j<ParcelFeatureCollection>(`/map/parcels.geojson?${q({ limit: 60000 })}`)
export const getFiche = (idu: string) => j<Fiche>(`/parcels/${idu}?source=${SOURCE}`)
export const getMapLayer = (kind: string) =>
  j<ParcelFeatureCollection>(`/map/layers.geojson?kind=${kind}&commune=${encodeURIComponent(COMMUNE)}`)
export const pdfUrl = (idu: string) => `/parcels/${idu}/export.pdf?source=${SOURCE}`

// ── Pipeline (CRM kanban) ──
export const getPipelineMeta = () => j<PipelineMeta>('/pipeline/meta')
export const getPipeline = () => j<PipelineEntry[]>('/pipeline')
export const getPipelineForParcel = (idu: string) =>
  j<{ in_pipeline: boolean; entry: PipelineEntry | null }>(`/pipeline/parcel/${idu}`)
export const addToPipeline = (idu: string) =>
  j<{ ok: boolean; already: boolean; entry: PipelineEntry }>('/pipeline', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ idu }),
  })
export const patchPipeline = (id: number, body: Record<string, unknown>) =>
  j<{ ok: boolean; entry: PipelineEntry }>(`/pipeline/${id}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  })
export const deletePipeline = (id: number) => j<{ ok: boolean }>(`/pipeline/${id}`, { method: 'DELETE' })

// ── Sources ──
export const getSources = () => j<SourceInfo[]>('/sources')

// ── Modules outils (Vague 1) ──
export const modDivision = (minScore = 0) => j<{ total: number; items: Record<string, unknown>[] }>(`/modules/division?min_score=${minScore}&limit=300`)
export const modPatrimoineSearch = (q: string) => j<{ siren: string; nom: string; n: number }[]>(`/modules/patrimoine/search?q=${encodeURIComponent(q)}`)
export const modPatrimoine = (siren: string) => j<Record<string, unknown>>(`/modules/patrimoine?siren=${siren}`)
export const modPermis = (months: number) => j<Record<string, unknown>>(`/modules/permis?commune=${encodeURIComponent(COMMUNE)}&months=${months}`)
export const modPromesses = (months: number) => j<Record<string, unknown>>(`/modules/promesses?commune=${encodeURIComponent(COMMUNE)}&months=${months}`)
export const modVelocite = () => j<{ note: string; communes: Record<string, unknown>[] }>('/modules/velocite')
export const modBailleur = () => j<Record<string, unknown>>(`/modules/bailleur?commune=${encodeURIComponent(COMMUNE)}`)
export const modFantome = () => j<Record<string, unknown>>(`/modules/fantome?commune=${encodeURIComponent(COMMUNE)}`)
export const modCourriers = (idus: string[], contexte: string) =>
  j<{ n: number; courriers: { idu: string; texte?: string; erreur?: string }[]; rappel_identite: string }>('/modules/courriers', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ idus, contexte }) })
export const modDueDiligence = (refs: string) =>
  j<{ n_demandes: number; n_trouvees: number; items: Record<string, unknown>[] }>('/modules/duediligence', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refs }) })

// ── Copilote IA (Vague 2) — jamais d'accès base, filtres validés par schéma côté API ──
export const iaStatus = () => j<{ provider: string }>('/ia/status')
export const iaSearch = (text: string) =>
  j<{ stub: boolean; filters?: Record<string, unknown>; explanation?: string; out_of_scope?: string }>('/ia/search', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) })
export const iaSynthese = (idu: string) =>
  j<{ stub: boolean; texte: string; mention: string }>(`/ia/synthese/${idu}`, { method: 'POST' })
export const iaPourquoi = (idu: string) =>
  j<{ stub: boolean; texte: string; mention: string }>(`/ia/pourquoi/${idu}`, { method: 'POST' })

// ── Événements (Vague 3 : M11-M14) ──
export interface LabuseEvent { id: number; date: string; kind: string; idu: string | null; titre: string; detail: string | null; demo: boolean; lu: boolean; statut: string | null }
export const getEvents = () => j<{ unread: number; items: LabuseEvent[] }>('/events?limit=100')
export const getEventsCount = () => j<{ unread: number; par_parcelle: Record<string, number> }>('/events/count')
export const markEventRead = (id: number) => j<{ ok: boolean }>(`/events/${id}/read`, { method: 'POST' })
export const markAllEventsRead = () => j<{ ok: boolean }>('/events/read-all', { method: 'POST' })
export const getWatch = (idu: string) => j<{ watched: boolean }>(`/events/watch/${idu}`)
export const toggleWatch = (idu: string) => j<{ watched: boolean }>(`/events/watch/${idu}`, { method: 'POST' })
export const getSavedSearches = () => j<{ id: number; nom: string; hash: string; date: string }[]>('/events/searches')
export const saveSearch = (nom: string, hash: string) =>
  j<{ ok: boolean }>('/events/searches', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nom, hash }) })
export const deleteSearch = (id: number) => j<{ ok: boolean }>(`/events/searches/${id}`, { method: 'DELETE' })

// ── Moteurs (Vague 4) ──
export const motSimulPluZones = () => j<{ zone: string; n_ilots: number }[]>('/moteurs/simulplu/zones')
export const motSimulPlu = (zone: string) => j<Record<string, any>>(`/moteurs/simulplu?zone=${encodeURIComponent(zone)}`)
export const motAssemblage = (idus: string[]) =>
  j<Record<string, any>>('/moteurs/assemblage', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ idus }) })
export const motZan = () => j<Record<string, any>>('/moteurs/zan')
export const motBarometre = () => j<Record<string, any>>('/moteurs/barometre')

// ── Vague 5 : matching + partage ──
export const getProfiles = () => j<Record<string, any>[]>('/partners/profiles')
export const addProfile = (p: Record<string, unknown>) =>
  j<{ ok: boolean }>('/partners/profiles', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(p) })
export const runMatch = () => j<{ matches: number }>('/partners/match/run', { method: 'POST' })
export const createShare = (idu: string) => j<{ token: string; url: string }>(`/partners/share/${idu}`, { method: 'POST' })
export const listShares = (idu: string) => j<{ token: string; date: string; views: number }[]>(`/partners/share/${idu}/list`)
