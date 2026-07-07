import type { Fiche, ParcelResult, PipelineEntry, PipelineMeta, SourceInfo, Stats } from './types'

export interface ParcelFeatureCollection {
  type: 'FeatureCollection'
  features: Array<{ type: 'Feature'; geometry: unknown; properties: Record<string, unknown> }>
}

import { useApp, type Filters } from '../store/useApp'

// SOURCE DE VÉRITÉ du Socle V1 : le scoring premium v2, run q_v2 (dryrun_parcel_evaluations).
// JAMAIS parcel_evaluations (éval historique). Cf. brief « NOTE SOURCE DE VÉRITÉ ».
export const SOURCE = 'q_v2'
/** Commune active — depuis le store (null = « Toute l'île »). L'ancienne constante Saint-Paul
 *  est devenue un état : TOUTE requête commune-scopée passe par ici. */
export const commune = () => useApp.getState().commune

async function j<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init)
  if (!r.ok) throw new Error(`${url} → HTTP ${r.status}`)
  return r.json() as Promise<T>
}

const q = (extra: Record<string, string | number> = {}) => {
  const c = commune()
  return new URLSearchParams({
    source: SOURCE, ...(c ? { commune: c } : {}),
    ...Object.fromEntries(Object.entries(extra).map(([k, v]) => [k, String(v)])),
  }).toString()
}

/** Filtres chips → query params serveur (mode île : la liste et les compteurs sont SQL). */
export const filterParams = (f: Filters): Record<string, string | number> => ({
  ...(f.statuts.length ? { statuts: f.statuts.join(',') } : {}),
  ...(f.scoreMin != null ? { score_min: f.scoreMin } : {}),
  ...(f.surfaceMin != null ? { surface_min: f.surfaceMin } : {}),
  ...(f.surfaceMax != null ? { surface_max: f.surfaceMax } : {}),
  ...(f.sdpMin != null ? { sdp_min: f.sdpMin } : {}),
  ...(f.evenement ? { evenement: 'true' } : {}),
  ...(f.vueMer ? { vue_mer: 'true' } : {}),
  ...(f.flags.length ? { flags: f.flags.join(',') } : {}),
})

export interface CommuneInfo { commune: string; insee: string; parcelles: number; chaudes: number; evaluees: number; bbox: [number, number, number, number]; note: string | null }
export const getCommunes = () => j<CommuneInfo[]>('/communes')
export interface ContexteCommune {
  commune: string; epci: string | null; epci_nom: string | null
  sru: { taux_lls: number; objectif_pct: number; statut: string; prelevement_eur: number; millesime: string; detail: { nb_lls?: number }; source_nom: string; source_url: string } | null
  anru: { nom: string; interet: string; code_qpv: string; source_nom: string; source_url: string }[]
  qpv: { nom: string; code: string }[]
  plh: { periode: string; statut: string; obj_logements_an: number | null; part_sociale_pct: number | null; refs: { doc: string; url?: string; page?: string | number }[] } | null
  marche: { millesime: string; logements: number; vacants: number; proprietaires_pct: number; locataires_pct: number; maisons_pct: number; apparts_pct: number; typologie: Record<string, any>; source_nom: string; source_url: string } | null
  notes: string[]
}
export const getContexteCommune = (commune: string) =>
  j<ContexteCommune>(`/communes/${encodeURIComponent(commune)}/contexte`)
export const searchParcels = (needle: string) =>
  j<{ idu: string; commune: string; status: string | null; q_score: number | null }[]>(
    `/parcels/search?q=${encodeURIComponent(needle)}${commune() ? `&commune=${encodeURIComponent(commune()!)}` : ''}`)

export const getStats = (f?: Filters) => j<Stats>(`/stats?${q(f ? filterParams(f) : {})}`)
export const getResults = (f?: Filters) => j<ParcelResult[]>(`/parcels?${q({ limit: 500, ...(f ? filterParams(f) : {}) })}`)
export const getParcelsGeojson = () =>
  j<ParcelFeatureCollection>(`/map/parcels.geojson?${q({ limit: 60000 })}`)
export const getFiche = (idu: string) => j<Fiche>(`/parcels/${idu}?source=${SOURCE}`)
export const getMapLayer = (kind: string) => {
  const c = commune()
  return j<ParcelFeatureCollection>(`/map/layers.geojson?kind=${kind}${c ? `&commune=${encodeURIComponent(c)}` : ''}`)
}
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
export const modDivision = (minScore = 0) => j<{ total: number; items: Record<string, unknown>[] }>(`/modules/division?min_score=${minScore}&limit=300&${cq()}`)
export const modPatrimoineSearch = (q: string) => j<{ siren: string; nom: string; n: number }[]>(`/modules/patrimoine/search?q=${encodeURIComponent(q)}`)
export const modPatrimoine = (siren: string) => j<Record<string, unknown>>(`/modules/patrimoine?siren=${siren}`)
const cq = () => (commune() ? `commune=${encodeURIComponent(commune()!)}` : '')
export const modPermis = (months: number) => j<Record<string, unknown>>(`/modules/permis?${cq()}&months=${months}`)
export const modPromesses = (months: number) => j<Record<string, unknown>>(`/modules/promesses?${cq()}&months=${months}`)
export const modVelocite = () => j<{ note: string; communes: Record<string, unknown>[] }>('/modules/velocite')
export const modBailleur = () => j<Record<string, unknown>>(`/modules/bailleur?${cq()}`)
export const modFantome = () => j<Record<string, unknown>>(`/modules/fantome?${cq()}`)
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
export const motSimulPluZones = () => j<{ zone: string; n_ilots: number }[]>(`/moteurs/simulplu/zones?${cq()}`)
export const motSimulPlu = (zone: string) => j<Record<string, any>>(`/moteurs/simulplu?zone=${encodeURIComponent(zone)}&${cq()}`)
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

// ── M22 + Bilan (faisabilité bidirectionnelle) ──
export const getFaisabilite = (idu: string) => j<Record<string, any>>(`/modules/faisabilite/${idu}`)
export const postProgramme = (body: Record<string, unknown>) =>
  j<Record<string, any>>('/modules/programme', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
