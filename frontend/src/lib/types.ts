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
  etat_bien?: string | null   // M131 P3 : nu | bati_encore | bati_max (affichage)
  fraction?: string | null    // M135 P2 : probabilité en fraction humaine
  raison?: string | null      // M135 P3 : raison dominante (chip)
  top5?: unknown[] | null      // M135 P3 : contributions (raison front pour geojson)
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
  millesime_amont: string | null   // FIX-FICHE F4 — vraie fraîcheur AMONT (data_sources.source_millesime), affichée inline
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
  proprietaire_statuts?: { key: string; label: string }[]   // M137 — pour l'écran d'édition de carte
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
  reminder_date?: string | null   // M137 — date de relance (éditable via l'écran de carte)
  prospection?: Record<string, string>   // M137 — statut proprio + contact manuel (édité via PATCH)
  proprietaire_label?: string
  has_manual_contact?: boolean
  created_at: string | null
  archived_at?: string | null   // M137 — archivage réversible (NULL = active)
  parcel: { commune: string; section: string; surface_m2: number | null }
  // M137 Lot 2 — `premium` (score/rang : q_score/a_score/rang_v2…) RETIRÉ du payload CRM et du type
  // (M133 B.6 ; plus rien ne le rend depuis P1 ; type `q_score`/`a_score` était mensonger).
  // Phase 2 : d'où vient la piste (projet) + contact proprio (PRIVACY : PM publique OU particulier masqué)
  projet?: { id: number; nom: string } | null
  proprietaire_public?: { type: 'personne_morale'; denomination: string; siren: string | null; groupe: string | null }
    | { type: 'particulier' } | null
  // CONNEXIONS-2 Lot 4 (KO-6) — statut du courrier rattaché à cette piste (relu sur la carte Kanban)
  courrier?: { statut: string; libelle: string; demande_id: number; ts: string | null } | null
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
  // FIX-SOURCES S6 — licence DÉRIVÉE de legal_notes CÔTÉ SERVEUR (libellé court + lien officiel) :
  // le front ne code plus aucune licence en dur, il rend ce que la base dit.
  license_label?: string | null
  license_url?: string | null
  testable: boolean
  // UX V1 ajout A : fraîcheur RÉELLE lue dans ingestion_runs (jamais codée en dur)
  derniere_ingestion: string | null
  derniere_donnee?: string | null   // J+2 : date de la dernière DONNÉE en base (≠ ingestion)
  source_millesime?: string | null   // M86 : millésime amont centralisé (lu ici, plus jamais en dur au front)
  // M84 : verdict de fraîcheur live (seuil = 2× cadence). « en_retard » = décrochage à VOIR ;
  // « cadence_libre »/« sans_donnee » ne sont jamais une alerte (anti-faux-positif).
  // CRON-2 — vocabulaire du job sources-fraicheur (persisté) : en_panne / sans_echeance, en plus des
  // valeurs du calcul live historique (cadence_libre / sans_donnee).
  fraicheur_statut?: 'en_retard' | 'en_panne' | 'a_jour' | 'sans_echeance' | 'cadence_libre' | 'sans_donnee' | 'en_erreur' | null
  fraicheur_seuil_jours?: number | null
  fraicheur_delta_jours?: number | null
  // CONNEXIONS-2 Lot 6.2 (KO-14) — dernier échec d'ingestion : badge rouge « en erreur » + date + motif.
  fraicheur_erreur_at?: string | null
  fraicheur_erreur_message?: string | null
  // RETOURS-8 (R2) — l'état CLIENT à deux valeurs (arbitre unique etats_sources) + publication producteur
  // et cadence habituelle, à titre d'information. « pas_a_jour » = mise à jour en cours, jamais « retard ».
  etat_client?: 'a_jour' | 'pas_a_jour'
  publie_le?: string | null
  cadence_mention?: string | null
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
    statut: 'a_jour' | 'nouvelle_publication' | 'verification_manuelle' | 'non_sondable' | 'erreur'
    detail: string | null
  } | null
  // M71 BLOC A : ligne marquée DOUBLON au catalogue (même donnée qu'une autre ligne) —
  // listée pour la traçabilité mais EXCLUE du comptage du bandeau.
  doublon?: boolean
  // M74 C bis : NATURE de la source (proxy / servi par proxys) — visible, jamais repliée :
  // une source proxy ne doit pas être présentée comme la source officielle.
  // `dashed` (M87) : proxy / servi par proxys / curée manuellement → rendu badge en pointillé.
  nature?: { label: string; detail: string; dashed?: boolean } | null
}

// M33 — mode B (réhabilitation) : lecture de fiche, TOUJOURS Estimé, jamais persisté.
// M125 (boussole) — état PANNE d'un bloc de fiche : un builder back qui LÈVE renvoie
// `{ indisponible: true, raison: 'erreur technique' }` au lieu de null. À rendre EN CLAIR
// (« Donnée indisponible — erreur technique »), jamais en absence/« rien à signaler ».
export interface Indisponible { indisponible?: boolean; raison?: string }

export interface ModeB extends Indisponible {
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
  // M101 A2 : la PORTE du mode B — pourquoi cette parcelle est « bâtie », en français lisible
  // (phrase unique servie par compute_mode_b, calée sur la règle mesurée — jamais de jargon).
  porte?: string | null
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
  // L1 (KF-2) — historique du propriétaire PM par millésime + diff CONSTATÉ (hors scoring, PM only)
  proprietaire_historique?: {
    source: string; note: string; n_millesimes: number; n_changements: number
    millesimes: { millesime: number; situation: string; siren: string | null; denomination: string | null; forme_juridique: string | null; groupe: string | null }[]
    changements: { de_millesime: number; a_millesime: number; siren_avant: string | null; denomination_avant: string | null; siren_apres: string | null; denomination_apres: string | null }[]
  } | null
  surface_m2: number | null
  statut?: Statut   // M48 (F4) : retiré du payload (matrice morte) — le tier vient de score_v2 ; repli legacy seulement
  mode_b?: ModeB
  q_score: number
  a_score: number
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
    tier: string; rang: number | null; mult_base: number | null; fraction?: string | null; percentile: number | null; copro: boolean
    hors_classement?: string | null   // M89 — copro : motif « hors univers de classement » (fiche)
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
    indisponible?: boolean; raison?: string   // M125 — état PANNE (≠ absence)
    commune?: string; confiance?: string
    synthese?: { etat: string; prochaine_etape?: string | null; servi_en_vigilance?: boolean } | null
    sursis?: { texte: string; base_legale: string } | null
    veille_au?: string | null
  } | null
  // M42 : « Sur cette parcelle » (historique permis + caducité) — contexte, 0 tier.
  historique_site?: {
    indisponible?: boolean; raison?: string   // M125 — état PANNE (≠ absence)
    titre: string; n_permis: number; source: string; honnetete: string
    permis: { permit_id: string; type: string | null; date_autorisation: string | null; date_depot: string | null }[]
    caducite?: { pc_annee?: number; caduc_depuis?: string | null; libelle_court?: string | null; detail?: string | null } | null
  } | null
  // M42 : « Autour, à moins de 100 m » (ventes DVF + permis, 36 mois) — contexte, 0 tier.
  voisinage_proche?: {
    indisponible?: boolean; raison?: string   // M125 — état PANNE (≠ absence)
    titre: string; rayon_m: number; fenetre_mois: number
    ventes_dvf: number; prix_median_eur: number | null; prix_note: string | null; permis: number
    source: string; honnetete: string
  } | null
  // M9 lot 4 : potentiel de transformation (fond de l'ancien outil Mutabilité).
  potentiel_transformation?: PotentielTransformation | null
  // M-VIA : indicateur de viabilisation (faisceau de preuves) + gestionnaires (contact admin).
  viabilisation?: Viabilisation | null
  // M88 : assainissement (ANC / tout-à-l'égout) — Sourcé / Sourcé secteur (taux INSEE) / Absent.
  anc?: AncStatut | null
  gestionnaires?: Gestionnaires | null
  // M75 : obligation APER (ombrières PV, grand parking > 1 500 m²) — tiroir Urbanisme, information.
  // `note` = libellé client (point de calcul unique = mêmes mots que les exports).
  aper?: { surface_m2: number; echeance: string | null; equipe: boolean; note: string; etat: string } | null
  // M19 : marché DVF de la parcelle (présent dans le payload) — typé pour la valeur fermée du
  // tiroir Marché (médiane €/m² structurée = donnée propre, ≠ nombre brut de la ligne dvf).
  dvf_parcelle?: DvfParcelle | null
  // M-RENOUV : segment Renouvellement (parcelle OCCUPÉE, potentiel de renouvellement urbain —
  // jamais « opportunité »). Le verdict d'en-tête reste « Écartée » ; badge + pourquoi seulement.
  renouvellement?: Renouvellement | null
  // M106 P3 — dispositifs fiscaux territoriaux (ZFANG / FRR ex-ZRR) : attribut de COMMUNE,
  // des ÉTATS sourcés + lien vers le texte — JAMAIS un chiffre fiscal (interdit du mandat).
  territoire_fiscal?: {
    commune: string
    zfang: { regime: 'standard' | 'renforce'; libelle: string; source_ref: string; lien: string }
    frr: { classement: 'totalite' | 'partie' | 'hors'; libelle: string; source_ref: string; lien: string }
    avertissement: string
    // M134 — les périmètres FINS qui touchent la parcelle (QPV dedans, ou bande TVA 500 m dérivée)
    perimetres?: { libelle: string; detail: string; source: string; derive: boolean }[]
  } | null
  // M106 P4 — PROXIMITÉS (distance, jamais un booléen) : transport + ligne HT (contrainte).
  proximites?: {
    indisponible?: boolean; raison?: string   // M125 — état PANNE (≠ absence)
    arret?: { nom: string; reseau: string | null; distance_m: number }
    pole?: { nom: string; distance_m: number; statut: 'Sourcé' | 'Estimé'; source: string
      concordance: string | null; nb_lignes: number | null }
    telepherique?: { station: string; distance_m: number; licence: string }
    // M106-B P3 — axe structurant (BD TOPO importance 1-2) : libellé à DEUX FACES
    axe?: { nom: string; nature: string; distance_m: number; libelle: string; source: string }
    ligne_ht?: { distance_m: number; tension: string; libelle: string; source: string }
  } | null
  // RETOURS-7 Z5 — « À proximité » : équipements du quotidien nommés + distance (moteur BPE branché).
  proximites_equipements?: {
    indisponible?: boolean; raison?: string
    items?: { cat: string; nom: string; distance_m: number }[]
    source?: string
  } | null
  // MANDAT RNU : commune sans document local (flag général config/rnu_communes.yaml) —
  // étiquetage obligatoire, jamais une affirmation de constructibilité.
  rnu?: { libelle: string; detail: string; commune_nom: string | null; statut_detail: string | null; verifie_le: string | null; dans_pau: boolean | null; avertissement_pau: string } | null
  // M38 — activité de dépôt (Sitadel3 date_depot), informatif seul ; null hors couverture.
  // M125 — peut porter l'état PANNE `{ indisponible: true }` (≠ absence, ≠ null).
  depots?: {
    indisponible?: boolean; raison?: string
    fenetre_mois: number; source: string; sourcage: string; millesime: string | null
    libelle: string; granularite: string
    parcelle: { count: number; dernier: string | null } | null
    secteur: { count: number; dernier: string | null; maille?: string } | null
  } | null
  // M125-2 — copropriété(s) RNIC rattachées (cible bailleur/copro) ; [] hors couverture.
  coproprietes?: Copropriete[]
  // RADAR P3 (C3) — un bien du Radar en vente rattaché à cette parcelle (fait + statut + lien), hors scoring.
  radar_bien?: { bien_id: number; statut: string; rattachement_niveau: string; prix: number | null; type_bien: string | null; portail: string; url_sortante: string } | null
  // M125-2 — contexte socio-éco du secteur (Filosofi 200 m + parc social RPLS), hors scoring.
  marche_secteur?: MarcheSecteur | null
  // fiche-secteur — compte d'opportunités de la SECTION cadastrale (ex-carnet) : parcelles des tiers
  // « Priorité » (brulante) + « À suivre » (chaude) du run servi. Cliquable → carte sur la section.
  secteur_opportunites?: { section: string; n: number } | null
}

// M125-2 — copropriété immatriculée (RNIC) rattachée à la parcelle. Information, jamais un verdict.
export interface Copropriete {
  numero_immatriculation: string
  nom_usage: string | null
  adresse: string | null
  nb_lots_total: number | null
  nb_lots_habitation: number | null
  periode_construction: string | null
  syndic_type: string | null
  syndic_nom: string | null
  rattachement: string | null
}

// M125-2 — contexte socio-économique du secteur. Chaque sous-bloc porte SON millésime (daté).
export interface MarcheSecteur {
  filosofi_200m: {
    ind: number; men: number; men_pauv: number; men_prop: number
    nivvie_moyen_eur: number | null; taux_pauvrete_pct: number | null; millesime: string
  } | null
  rpls_commune: {
    nb_logements: number; construct_median: number | null; pct_qpv: number | null; millesime: string
  } | null
}

// ÉTUDE DE ZONE Z3 — le tiroir « Autour de cette parcelle ». Un seul moteur ; ici en mode fiche
// (isochrone auto depuis le centroïde). Le REVENU reste la valeur au centroïde servie par la fiche
// (source unique). Dégradé honnête si l'isochrone IGN est indisponible (`disponible=false`).
export interface ZonePopulation {
  inhabitee: boolean
  habitants?: number; menages?: number
  revenu_median_eur?: number | null; revenu_estime?: boolean; revenu_source?: string
  revenu_impute_n?: number | null; revenu_carreaux_n?: number | null; revenu_majorite_imputee?: boolean
  pct_moins_25?: number | null; taux_pauvrete_pct?: number | null
  n_carreaux?: number; millesime: string
}
export interface ZoneEquipement { domaine: string; nom: string; temps_min: number | null }
export interface ParcelleZone {
  disponible: boolean
  statut: string        // 'ign' | 'cache' | 'indisponible' | 'polygone'
  mode: 'pied' | 'voiture'
  minutes: number
  hors_trafic: boolean
  renvoi: string
  note: string
  detail?: string       // présent si disponible=false (échec nommé)
  geom?: { type: 'Polygon' | 'MultiPolygon'; coordinates: number[][][] | number[][][][] }
  population?: ZonePopulation
  equipements?: ZoneEquipement[]
}

// ÉTUDE DE ZONE Z4 — l'outil de chalandise. Faits sourcés, aucune prévision de CA.
export interface NafOption { code: string; label: string }
export interface NafFamille { section: string; nom: string; activites: NafOption[] }
export interface ZoneConcurrent { siret: string; naf: string; nom: string; diffusible: boolean; lon: number; lat: number; temps_min: number | null; annee_creation: number | null; date_maj: string | null; maj_ancienne?: boolean }
// F3 (OUTILS-4) — toutes les entreprises de la zone, groupées par famille d'activité (section NAF).
export interface ZoneEntreprise { siret: string; naf: string; naf_label: string | null; nom: string; diffusible: boolean; lon: number; lat: number; annee_creation: number | null; date_maj: string | null }
export interface ZoneFamille { section: string; nom: string; n: number; etablissements: ZoneEntreprise[]; charges: number }
export interface ZoneEntreprises { total: number; familles: ZoneFamille[]; n_charges: number; cap_carte: number; millesime: string | null }
export interface ZoneGenerateur { label: string; source: string }
export interface ZoneMarche { ventes_12m: number; prix_m2_median_bati: number | null; annonces_actives: number; permis_36m: number }
export type ZoneCouverture = 'servie' | 'non_couverte' | 'erreur'
export interface EtudeZoneResult {
  statut: string
  zone_disponible: boolean
  detail?: string
  minutes: number
  mode: 'pied' | 'voiture'
  entree?: 'point' | 'polygone'
  surface_ha?: number | null
  adresse?: string | null
  geom?: { type: 'Polygon' | 'MultiPolygon'; coordinates: number[][][] | number[][][][] }
  bandes?: { minutes: number; geom: { type: 'Polygon' | 'MultiPolygon'; coordinates: number[][][] | number[][][][] } }[]
  origine?: { lon: number; lat: number }
  naf_label?: string | null
  population?: ZonePopulation
  emplois?: { postes_min: number; postes_max: number; postes_max_ouvert: boolean; n_etablissements: number; n_avec_tranche: number; n_sans_tranche: number; libelle: string }
  emplois_couverture?: ZoneCouverture
  equipements?: ZoneEquipement[]
  generateurs_flux?: ZoneGenerateur[]
  marche?: ZoneMarche
  concurrents?: { n: number; naf: string; naf_label?: string | null; seuil_fraicheur_mois?: number; items: ZoneConcurrent[]; couverture?: ZoneCouverture; millesime?: string }
  zone_demain?: { logements_autorises_36m: number | null; permis_36m: number | null; au_zones_n: number | null; au_zones_ha: number | null; source: string }
  contraintes_plu?: { zones: { zone: string; part_pct: number; commune: string | null; document: string | null }[]; cdac_vigilance?: string; note?: string }
  trafic?: { couverte: boolean; axes: { route: string; tmja: number; annee: number }[]; libelle?: string; vide?: boolean }
  habitants_par_concurrent?: number | null
  note?: string
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
  // M101 B2 : le NEUF que l'acte déclare (VEFA), grain commune, profil dvf_profils.yaml —
  // sous le seuil, insuffisant_libelle est servi À LA PLACE de la médiane (état normal, dit).
  neuf_vefa?: { grandeur: string; grain: string; fenetre_ans: number; n: number
    seuil_effectif: number; effectif_suffisant: boolean
    mediane_prix_m2_bati: number | null; insuffisant_libelle: string | null
    reserve: string } | null
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
export interface ReglementPlu extends Indisponible { zones: ReglementZone[]; disclaimer: string }

export interface PotentielTransformation extends Indisponible {
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
// M86-B — état ANC servi (point de calcul unique côté back). M95 : 3 ÉCHELLES de Sourcé (parcelle /
// secteur / commune), + Absent — l'échelle est DITE, jamais confondue.
export interface AncStatut {
  // M88 : plus d'« estime » (proba_anc retiré) — « source_secteur » = taux INSEE brut du secteur.
  // M95 : « source_commune » = commune classée intégralement en ANC (Office de l'eau).
  statut: 'source' | 'source_secteur' | 'source_commune' | 'absent'
  libelle: string
  phrase: string
  anc?: boolean            // pour Sourcé : true = ANC, false = collectif
  commune?: string | null
  source?: string
  maille?: string          // « secteur IRIS « … » » | « commune de … » (maille DITE à l'écran)
  maille_type?: string     // 'iris' | 'commune'
  millesime?: string       // 'RP2022' (millésime DIT à l'écran)
  taux_non_racc?: number   // % de logements non raccordés du secteur (fait, jamais un verdict)
  methode?: string
  couverture?: { communes_avec_zonage: number; communes_total: number }
}

export interface Viabilisation {
  score: number
  band: 'confirmee' | 'probable' | 'incertaine' | 'lourde'
  libelle: string
  contributions: ViaContribution[]
  cout_raccordement: { niveau: string; assainissement: string; disclaimer: string }
  disclaimer: string
  elec_pv?: { statut: string; note: string; source?: string; disclaimer: string } | null
  // M75 — gisement solaire PVGIS (INFORMATION seule) : le libellé client `note` est le point de
  // calcul unique (fiche + exports au mot près). `prod_kwh_kwc` sourcé PVGIS, jamais de score /100.
  solaire?: { prod_kwh_kwc: number; qualite: string; ombrage: boolean; note: string; etat: string } | null
}
export interface GestOperateur { operateur: string; type?: string; confidence?: 'high' | 'med' | 'low' }
export interface Gestionnaires extends Indisponible {
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
