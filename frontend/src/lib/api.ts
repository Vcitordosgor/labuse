import type { Fiche, ParcelResult, Stats } from './types'

export interface ParcelFeatureCollection {
  type: 'FeatureCollection'
  features: Array<{ type: 'Feature'; geometry: unknown; properties: Record<string, unknown> }>
}

// SOURCE DE VÉRITÉ du Socle V1 : le scoring premium v2, run q_v2 (dryrun_parcel_evaluations).
// JAMAIS parcel_evaluations (éval historique). Cf. brief « NOTE SOURCE DE VÉRITÉ ».
export const SOURCE = 'q_v2'
export const COMMUNE = 'Saint-Paul'

async function j<T>(url: string): Promise<T> {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`${url} → ${r.status}`)
  return r.json() as Promise<T>
}

const q = (extra: Record<string, string | number> = {}) =>
  new URLSearchParams({ source: SOURCE, commune: COMMUNE, ...Object.fromEntries(Object.entries(extra).map(([k, v]) => [k, String(v)])) }).toString()

export const getStats = () => j<Stats>(`/stats?${q()}`)
export const getResults = () => j<ParcelResult[]>(`/parcels?${q({ limit: 500 })}`)
export const getParcelsGeojson = () =>
  j<ParcelFeatureCollection>(`/map/parcels.geojson?${q({ limit: 60000 })}`)
export const getFiche = (idu: string) => j<Fiche>(`/parcels/${idu}?source=${SOURCE}`)
