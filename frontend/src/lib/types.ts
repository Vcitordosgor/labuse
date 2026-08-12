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
  // M-Q P2-69 : `status` (matrice legacy éteinte M37) OPTIONNEL — le verdict vient du tier v2 ;
  // le repli legacy (verdictMeta) ne s'arme jamais sur le parc servi et, s'il s'armait, s'affiche
  // en « Classement historique » distinct. Consommé seulement via `verdictMeta(p.status, …)`.
  status?: Statut
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
  tone?: 'cold' | 'warm' | 'hot' | 'reject' | null
  id?: number
}

export interface PipelineMeta {
  columns: PipelineColumn[]
  priorities: { key: string; label: string }[]
  defaults: { status?: string; priority?: string }
}

// M12 LOT H — colonnes CRM personnalisables (par tenant)
export interface CrmColumn {
  id: number
  key: string
  label: string
  tone: 'cold' | 'warm' | 'hot' | 'reject' | null
  position: number
  is_default: boolean
  cards: number
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
  // Phase 2 : d'où vient la piste (projet) + contact proprio (PRIVACY : PM publique OU particulier masqué)
  projet?: { id: number; nom: string } | null
  proprietaire_public?: { type: 'personne_morale'; denomination: string; siren: string | null; groupe: string | null }
    | { type: 'particulier' } | null
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
  derniere_donnee?: string | null   // J+2 : date de la dernière DONNÉE en base (≠ ingestion)
  ingestion_runs: number
  // VUES item 4 : vérification « dernière version publiée » (source_checks) — NULL tant que
  // le mandat d'audit data n'a pas tourné ; la mention ne s'affiche qu'avec cette date
  verified_at: string | null
  // B3 (BLOC B) : l'état du RADAR de publication amont — null tant que `labuse
  // radar-sources` n'a jamais tourné. Le radar signale, l'humain décide.
  radar: {
    mode: 'auto' | 'manuel'
    cadence: string | null
    sonde: string
    valeur: string | null
    derniere_verif: string | null
    dernier_changement: string | null
    statut: 'a_jour' | 'nouvelle_publication' | 'non_sondable' | 'erreur'
    detail: string | null
  } | null
  // M71 BLOC A : ligne marquée DOUBLON au catalogue (même donnée qu'une autre ligne) —
  // listée pour la traçabilité mais EXCLUE du comptage du bandeau.
  doublon?: boolean
  // M74 C bis : NATURE de la source (proxy / servi par proxys) — visible, jamais repliée :
  // une source proxy ne doit pas être présentée comme la source officielle.
  nature?: { label: string; detail: string } | null
}

// M33 — mode B (réhabilitation) : lecture de fiche, TOUJOURS Estimé, jamais persisté.
export interface ModeB {
  disponible: boolean
  motif?: string
  trop_petit?: boolean   // M59-P1 (Q4) : SHAB < 50 m² → thèse non pertinente, on le DIT
  shab_rehabilitable_m2?: number   // servi au niveau racine quand trop_petit (message)
  population_tier?: string
  etiquette?: string
  achat_max_eur?: number
  achat_max_libelle?: string   // M37 Lot 0.1 : formaté k€ côté serveur (point unique)
  negatif?: boolean
  message_negatif?: string | null
  surface_parcelle_m2?: number | null   // M59-P1 (Q1) : foncier, pour « hors valeur du terrain »
  // M59-P1 (Q1) : repère « terrain nu au prix du secteur » (Estimé, hors formule réhab) + drapeau
  // « valeur portée par le terrain » (le foncier vaut plus que ce que le bâti justifie).
  terrain_nu?: { valeur_eur: number; valeur_libelle: string; prix_m2: number; surface_m2: number
    niveau: string; libelle: string; etiquette: string } | null
  porte_par_terrain?: boolean
  composantes?: {
    surface: { emprise_bati_m2: number; niveaux: number; niveaux_reels: boolean
      niveaux_etiquette: string; sdp_existante_m2: number; shab_rehabilitable_m2: number
      source_emprise: string; etiquette_emprise: string }
    prix_sortie: { prix_m2: number; niveau: string; libelle: string; etiquette: string; perimetre?: string }
    travaux: { hypothese_m2: number; defaut_m2: number; bornes: [number, number]
      etiquette: string; libelle: string }
    frais_marge: { coef_ca: number; libelle: string; etiquette: string }
  }
  formule?: string
  avertissement?: string
  // M44 — sortie LOCATIVE, côte à côte avec la revente (jamais fusionnée). Loyer plafond Sourcé
  // ou marché Estimé ; prix d'achat max à rendement cible (Estimé, contient les travaux).
  sortie_locative?: {
    loyer: { m2_mois_effectif: number; plafond_brut_m2: number | null; coef_surface: number | null
      regime: string; mensuel_eur: number; annuel_eur: number; etiquette: string
      source: string | null; date: string | null }
    rendement_cible_pct: number; rendement_cible_etiquette: string
    etiquette: string; achat_max_eur: number; achat_max_libelle: string
    negatif: boolean; message_negatif: string | null; formule: string; mention_fiscale: string
  } | null
}

// M52 L4 — qualité par commune, DITE (mesure réelle gelée, audit RR fold 2025 OOS).
export interface QualiteCommune {
  commune: string; insee: string; rr_intra: number; rr_ile: number | null
  rr_ile_dit?: string | null   // M52-B : RR île DIT en ordre de grandeur (« ~6,7 ») — jamais la fausse précision
  echantillon: number; taux_base_pct: number | null; fragile: boolean; degradee: boolean
  libelle: string; source: string
}

export interface Fiche {
  idu: string
  commune: string
  adresse?: string | null   // M6 2a (§1.8) : meilleure adresse postale BAN — null si aucune
  proprietaire_moral: {
    denomination: string | null; siren: string | null; groupe_label: string | null
    etat_societe?: {
      etats: { type: string; date: string | null; libelle: string; source: string; etiquette: string }[]
      libelle: string; note: string
    } | null
  } | null
  surface_m2: number | null
  statut?: Statut   // M48 (F4) : retiré du payload (matrice morte) — le tier vient de score_v2 ; repli legacy seulement
  mode_b?: ModeB
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
  score_v2: {
    tier: string; rang: number | null; mult_base: number | null; percentile: number | null; copro: boolean
    // M52 Lot 1 (présentation) : mot verbal + ⓘ + fréquence par tier + « pourquoi » (top5 traduites).
    verbal?: {
      mot?: string; cle?: string; info: string; reglette_pct?: number
      frequence?: { sur_100: number; base_sur_100: number; fenetre: string; sous_moyenne: boolean; source_dite: string }
    }
    pourquoi?: { feature: string; libelle: string; phrase?: string; signe?: string }[]
  } | null
  etage0: boolean
  parc_analysees?: number | null   // M52 L2 — théâtre « N parcelles analysées » (compte gelé du run)
  // M52 L3 — « Les données » : sources réellement utilisées sur cette fiche (0 nouvelle donnée).
  data_sources?: { nom: string; categorie: string | null; fournisseur: string | null; millesime: string | null; fiabilite: string | null }[]
  // M52 L4 — qualité par commune, DITE (mesure réelle gelée ; degradee = arme le rappel discret).
  qualite_commune?: QualiteCommune | null
  // M9 lot 1 : indice de confiance données (ICD) — méta d'affichage, CLOISONNÉE du score P.
  icd?: IcdBlock | null
  // M9 lot 2 : lien règlement PLU par zone (article/page ou document + repli GPU).
  reglement_plu?: ReglementPlu | null
  // M32 §2 : fraîcheur GPU-vs-mairie du zonage (horizon = date mairie ; statut = écart exposé).
  plu_fraicheur?: {
    idurba: string | null; horizon: string | null
    statut: 'a_jour' | 'annule_partiel' | 'opposabilite_en_attente' | 'rnu'
    libelle: string; note?: string | null; cadence?: string
    // M40 : les 3 choses distinctes (jamais mélangées) + action.
    document_servi?: string | null; fait_foi?: string | null
    en_cours?: string | null; action?: string | null; fait_foi_ok?: boolean
  } | null
  // M41 : radar procédures PLU (stade + conséquences parcellaires servables ; jamais l'issue).
  radar_procedure?: {
    commune?: string; confiance?: string
    synthese?: { etat: string; prochaine_etape?: string | null; servi_en_vigilance?: boolean } | null
    sursis?: { texte: string; base_legale: string } | null
    veille_au?: string | null
  } | null
  // M42 : « Sur cette parcelle » (historique permis + caducité) — contexte, 0 tier.
  historique_site?: {
    titre: string; n_permis: number; source: string; honnetete: string
    permis: { permit_id: string; type: string | null; date_autorisation: string | null; date_depot: string | null }[]
    caducite?: { pc_annee?: number; caduc_depuis?: string | null; libelle_court?: string | null; detail?: string | null } | null
  } | null
  // M42 : « Autour, à moins de 100 m » (ventes DVF + permis, 36 mois) — contexte, 0 tier.
  voisinage_proche?: {
    titre: string; rayon_m: number; fenetre_mois: number
    ventes_dvf: number; prix_median_eur: number | null; prix_note: string | null; permis: number
    source: string; honnetete: string
  } | null
  // M9 lot 4 : potentiel de transformation (fond de l'ancien outil Mutabilité).
  potentiel_transformation?: PotentielTransformation | null
  // M-VIA : indicateur de viabilisation (faisceau de preuves) + gestionnaires (contact admin).
  viabilisation?: Viabilisation | null
  gestionnaires?: Gestionnaires | null
  // M19 : marché DVF de la parcelle (présent dans le payload) — typé pour la valeur fermée du
  // tiroir Marché (médiane €/m² structurée = donnée propre, ≠ nombre brut de la ligne dvf).
  dvf_parcelle?: DvfParcelle | null
  // M-RENOUV : segment Renouvellement (parcelle OCCUPÉE, potentiel de renouvellement urbain —
  // jamais « opportunité »). Le verdict d'en-tête reste « Écartée » ; badge + pourquoi seulement.
  renouvellement?: Renouvellement | null
  // MANDAT RNU : commune sans document local (flag général config/rnu_communes.yaml) —
  // étiquetage obligatoire, jamais une affirmation de constructibilité.
  rnu?: { libelle: string; detail: string; commune_nom: string | null; statut_detail: string | null; verifie_le: string | null; dans_pau: boolean | null; avertissement_pau: string } | null
  // M38 — activité de dépôt (Sitadel3 date_depot), informatif seul ; null hors couverture.
  depots?: {
    fenetre_mois: number; source: string; sourcage: string; millesime: string | null
    libelle: string; granularite: string
    parcelle: { count: number; dernier: string | null } | null
    secteur: { count: number; dernier: string | null; maille?: string } | null
  } | null
}

export interface Renouvellement {
  libelle: string
  // M47 : étiquette source · millésime (run servi + date de matérialisation).
  source: string
  run_label: string
  maj: string | null
  renouv_score: number
  rang_segment: number
  total_segment: number
  rang_commune: number
  total_commune: number
  code_bati_origine: string
  zone_plu: string | null
  sdp_residuelle_m2: number | null
  surface_m2: number | null
  composantes: { cle: string; points: number; max: number; libelle: string }[]
}

export interface DvfSecteur {
  type_bien: string
  n_ventes: number | null
  mediane_valeur: number | null
  mediane_prix_m2: number | null
  fenetre?: string | null
}
export interface DvfParcelle {
  derniere_mutation?: unknown
  secteur?: DvfSecteur[] | null
}

export interface IcdBlock {
  score: number
  bande: 'haute' | 'partielle' | 'faible' | 'inconnu'
  libelle: string
  detail: Record<string, boolean>
  manquants: string[]
  cloisonnement: string
}

export interface ReglementZone {
  zone: string
  calibree: boolean
  document: string | null
  url: string | null
  url_document?: string | null
  approbation?: string | null
  edition?: string | null
  idurba?: string | null
  articles: { regle: string; reference: string; page_imprimee: number | null; url: string | null }[]
  annuaire?: { insee: string | null; zone: string | null } | null   // M51 — deep-link outil O13
  note: string | null
}
export interface ReglementPlu { zones: ReglementZone[]; disclaimer: string }

export interface PotentielTransformation {
  niveau: 'fort' | 'modere' | 'faible' | 'nul' | 'indetermine'
  libelle: string
  pct_consomme: number | null
  pct_residuel: number | null
  sdp_residuelle_m2: number | null
  sous_densite: boolean | null
  capacite_estimee: boolean | null
  surelevation_possible: boolean | null
  hauteur_bati_m: number | null
  hauteur_max_m: number | null
  hauteur_marge_m: number | null
  confiance: string | null
  source: string
  note: string
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
