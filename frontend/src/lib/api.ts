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
