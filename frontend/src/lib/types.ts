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
  evenement_date?: string | null   // événement daté v1.3 (badge secondaire)
  cluster?: number | null   // taille du groupe « même propriétaire » parmi les opportunités v2 (île)
  proprio?: string | null
  v_score?: number | null
  v_dernier_signal?: string | null   // CRED-4 : date du signal V daté le plus récent
  v_band?: VBand | null
  owner_type?: OwnerType | null
  // M5.1 : le scoring v2 pilote — tier/rang/×N + étage 0 servi, copro, veille succession
  tier_v2?: string | null
  rang_v2?: number | null
  mult_v2?: number | null
  copro_v2?: boolean
  veille?: boolean
  etage0?: boolean
}

// M5.1 : /stats ventile par TIERS v2 effectifs (l'étage 0 du run servi prime).
// « Opportunités » = brûlantes v2 + chaudes v2. La ventilation matrice n'existe
// plus qu'en legacy=1 (non requêtée par le front).
export interface Stats {
  total: number
  tiers: { brulante: number; chaude: number; reserve_fonciere: number;
           a_creuser: number; ecartee: number }
  opportunites: number
  opportunites_evenement: number
  // dossiers = propriétaires uniques identifiés (SIREN) parmi les opportunités v2 ; le
  // reliquat « sans identité » est affiché tel quel (jamais un total prétendu exact)
  dossiers_opportunites: number
  opportunites_avec_dossier: number
  opportunites_sans_identite: number
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
  premium: { statut: Statut; q_score: number; a_score: number; completeness_score: number;
             etage0?: boolean; tier_v2?: string | null; rang_v2?: number | null } | null
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
  // VUES item 4 : vérification « dernière version publiée » (source_checks) — NULL tant que
  // le mandat d'audit data n'a pas tourné ; la mention ne s'affiche qu'avec cette date
  verified_at: string | null
}

export interface Fiche {
  idu: string
  commune: string
  adresse?: string | null   // M6 2a (§1.8) : meilleure adresse postale BAN — null si aucune
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
  // correctif M5 : verdict d'en-tête piloté par le tier v2 quand un run existe ;
  // etage0 = exclusion dure du run SERVI (prime toujours sur le tier v2)
  score_v2: { tier: string; rang: number | null; mult_base: number | null; percentile: number | null; copro: boolean } | null
  etage0: boolean
  // M-VIA : indicateur de viabilisation (faisceau de preuves) + gestionnaires (contact admin).
  viabilisation?: Viabilisation | null
  gestionnaires?: Gestionnaires | null
}

export interface ViaContribution { libelle: string; points: number; detail: string; signe: '+' | '−' | '·' }
export interface Viabilisation {
  score: number
  band: 'confirmee' | 'probable' | 'incertaine' | 'lourde'
  libelle: string
  contributions: ViaContribution[]
  cout_raccordement: { niveau: string; assainissement: string; disclaimer: string }
  disclaimer: string
  elec_pv?: { statut: string; note: string; source?: string; disclaimer: string } | null
}
export interface GestOperateur { operateur: string; type?: string; confidence?: 'high' | 'med' | 'low' }
export interface Gestionnaires {
  commune: string
  a_jour_au: string | null
  epci: { code: string | null; nom: string | null; contact: string | null }
  eau: GestOperateur | null
  assainissement: GestOperateur | null
  spanc: string | null
  electricite: { gestionnaire: string; detail?: string; raccordement?: string } | null
  note: string | null
  disclaimer: string | null
}
