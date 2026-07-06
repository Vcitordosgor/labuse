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
