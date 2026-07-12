export type Statut = 'chaude' | 'a_surveiller' | 'a_creuser' | 'ecartee' | 'exclue'

// ── Score V (Vendabilité, Stage 3) ──
export type VBand = 'fort' | 'present' | 'faible' | 'aucun' | 'na'
export type OwnerType = 'pm' | 'pp' | 'public' | 'bailleur' | 'copro'

export interface VSignal {
  code: string
  famille: string
  label: string
  points: number
  source: string
  ref: string | null
  url: string | null
  date_evenement: string | null
  match: { type: string; valeur: string; confiance: number } | null
}

export interface ScoreV {
  v_score: number | null        // NULL = non applicable (public / bailleur social)
  v_band: VBand | null
  v_band_label: string | null
  v_coverage: 'full' | 'partial'
  v_confidence: number | null
  owner_type: OwnerType | null
  owner_siren: string | null
  owner_denomination: string | null
  brulante: boolean
  badge: string | null          // « Foncier public — démarche dédiée », « Bailleur social »…
  signals: VSignal[]
  computed_at: string | null
}

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
  cluster?: number | null   // taille du groupe « même propriétaire » parmi les chaudes (île)
  proprio?: string | null
  v_score?: number | null
  v_band?: VBand | null
  owner_type?: OwnerType | null
  brulante?: boolean
}

export interface Stats {
  total: number
  chaude: number
  a_surveiller: number
  a_creuser: number
  ecartee: number
  // dossiers = propriétaires uniques identifiés (SIREN) parmi les chaudes ; le reliquat
  // « sans identité » est affiché tel quel (honnêteté : jamais un total prétendu exact)
  dossiers_chaudes?: number
  chaudes_avec_dossier?: number   // CRED-3 : parcelles chaudes COUVERTES par un dossier (la somme redevient lisible)
  chaudes_sans_identite?: number
  chaude_evenement?: number   // décomposition « dont N par événement » (survol du compteur)
  brulantes?: number          // 🔥 chaudes Q×A ∧ V ≥ seuil (tier combiné)
  v_fort?: number
  v_present?: number
  v_faible?: number
  v_aucun?: number
  v_na?: number
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
  legal_notes: string | null
  testable: boolean
  // UX V1 ajout A : fraîcheur RÉELLE lue dans ingestion_runs (jamais codée en dur)
  derniere_ingestion: string | null
  ingestion_runs: number
}

export interface Fiche {
  idu: string
  commune: string
  proprietaire_moral: { denomination: string | null; siren: string | null; groupe_label: string | null } | null
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
  score_v: ScoreV | null
}
