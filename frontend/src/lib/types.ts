export type Statut = 'chaude' | 'a_surveiller' | 'a_creuser' | 'ecartee' | 'exclue'

export interface ParcelResult {
  idu: string
  commune: string
  surface_m2: number | null
  lieu_dit: string | null
  status: Statut
  q_score: number
  a_score: number
  a_completude: number | null
  completeness_score: number
  evenement: string | null
}

export interface Stats {
  total: number
  chaude: number
  a_surveiller: number
  a_creuser: number
  ecartee: number
}

export type MapMode = 'verdict' | 'mutabilite'

export type Onglet = 'regles' | 'risques' | 'marche' | 'proprio'

export interface FicheLine {
  layer: string
  axis: 'q' | 'a'
  onglet: Onglet
  result: string
  severity: string | null
  weight: number | null
  detail: string
  source: string | null
  source_table: string | null
  source_id: number | string | null
  date: string | null
}

export interface PipelineColumn {
  key: string
  label: string
  tone?: 'cold' | 'warm' | 'hot' | 'reject'
}

export interface PipelineMeta {
  columns: PipelineColumn[]
  priorities: { key: string; label: string }[]
  defaults: { status?: string; priority?: string }
}

export interface PipelineEntry {
  id: number
  idu: string
  status: string
  priority: string
  notes: string
  created_at: string | null
  parcel: { commune: string; section: string; surface_m2: number | null }
  premium: { statut: Statut; q_score: number; a_score: number; completeness_score: number } | null
}

export interface SourceInfo {
  id: number
  name: string
  category: string | null
  provider: string | null
  access_type: string | null
  status: string | null
  reliability_level: string | null
  last_sync_at: string | null
  documentation_url: string | null
  testable: boolean
}

export interface Fiche {
  idu: string
  commune: string
  surface_m2: number | null
  statut: Statut
  q_score: number
  a_score: number
  a_completude: number | null
  completeness_score: number
  coords: [number, number]
  evenement: string | null
  evenement_detail: string | null
  lines: FicheLine[]
  flags: FicheLine[]
}
