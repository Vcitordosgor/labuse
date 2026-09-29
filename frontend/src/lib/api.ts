import type { CrmColumn, EtudeZoneResult, Fiche, NafFamille, NafOption, ParcelleZone, ParcelResult, PipelineEntry, PipelineMeta, SourceInfo, Stats } from './types'

export interface ParcelFeatureCollection {
  type: 'FeatureCollection'
  features: Array<{ type: 'Feature'; geometry: unknown; properties: Record<string, unknown> }>
  // FIX-COUCHES P3 — /map/layers.geojson distingue le millésime AMONT (fraîcheur réelle de la donnée)
  // de la date d'INTÉGRATION (ingestion). Absents sur /map/parcels.geojson (d'où l'optionalité).
  millesime_integration?: string | null
  source_millesime?: string | null
}

import { EMPTY_FILTERS, useApp, type Filters } from '../store/useApp'

// M31 (arbitrage Vic) : run servi = point de vérité UNIQUE versionné config/served_run.txt (=
// q_v8_calibre depuis la bascule M28). `vite.config.ts` lit ce fichier au build et injecte
// VITE_RUN_LABEL → SOURCE. Pour BASCULER : changer config/served_run.txt puis `npm run build`.
// M-Q P2-70 — repli VIDE (jamais un run codé en dur) : si l'injection manque (env absente, build
// hors script, cache Vite), un littéral figé servirait SILENCIEUSEMENT l'ancien run après une
// bascule (front sur l'ancien, backend sur le nouveau → listes vides, aucun message). Le repli ''
// + la garde de démarrage (main.tsx : refuse de booter si SOURCE est vide) rendent l'erreur
// FRANCHE. La cohérence du bundle réel reste garantie par test_bundle_front_construit_sur_le_run_servi.
//
// ALGO-FIX-1 (point 4) — le run est désormais LU À L'EXÉCUTION, plus figé au build : VITE_RUN_LABEL
// n'est que la valeur INITIALE (repli). Au démarrage, main.tsx fetch `/config/run` (runs.current()
// vivant) et appelle `_setServedRun()` — `SOURCE` est un binding VIVANT lu à CHAQUE requête (qf/q/
// getFiche), donc après une bascule un simple rechargement suffit : plus de `npm run build` pour que
// le front cesse d'épingler l'ancien run via `?source=`. Réassigné UNIQUEMENT par _setServedRun.
export let SOURCE = import.meta.env.VITE_RUN_LABEL ?? ''

/** ALGO-FIX-1 (point 4) — fixe le run servi lu à l'exécution (appelé une fois au boot, main.tsx).
 *  N'écrase jamais avec une valeur vide (garde le repli build plutôt qu'un run indéterminé). */
export function _setServedRun(run: string | null | undefined): void {
  if (run) SOURCE = run
}

/** Le run servi VIVANT côté backend (runs.current()), pour l'aligner au démarrage. */
export const fetchServedRun = () => j<{ run: string }>('/config/run')
/** Commune active — depuis le store (null = « Toute l'île »). L'ancienne constante Saint-Paul
 *  est devenue un état : TOUTE requête commune-scopée passe par ici. */
export const commune = () => useApp.getState().commune

/** Erreur API typée : le statut HTTP voyage avec l'erreur (le 429 a son propre message
 *  côté UI — ne jamais afficher « serveur périmé » sur un rate-limit). */
export class ApiError extends Error {
  status: number
  detail?: string
  constructor(url: string, status: number, detail?: string) {
    super(detail || `${url} → HTTP ${status}`)
    this.status = status
    this.detail = detail
  }
}

export const is429 = (e: unknown): boolean => e instanceof ApiError && e.status === 429

async function j<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init)
  if (!r.ok) {
    const detail = (await r.json().catch(() => null))?.detail
    throw new ApiError(url, r.status, typeof detail === 'string' ? detail : undefined)
  }
  return r.json() as Promise<T>
}

// M55-D stage 9 bloc 3 (« le périmètre propose, le filtre dispose ») : les appels /filtre ne
// portent PLUS la commune-VUE de la carte — le périmètre du compteur est `filters.communes`
// (décocher au panneau → compteur île, la carte reste où elle est). Les autres endpoints
// (couches, geojson…) gardent la vue : ils servent CE QUE la carte regarde.
const qf = (extra: Record<string, string | number> = {}) =>
  new URLSearchParams({ source: SOURCE,
    ...Object.fromEntries(Object.entries(extra).map(([k, v]) => [k, String(v)])) }).toString()

const q = (extra: Record<string, string | number> = {}) => {
  const c = commune()
  return new URLSearchParams({
    source: SOURCE, ...(c ? { commune: c } : {}),
    ...Object.fromEntries(Object.entries(extra).map(([k, v]) => [k, String(v)])),
  }).toString()
}

/** Filtres chips → query params serveur (mode île : la liste et les compteurs sont SQL).
 *  M5.1 : `tiers` (v2) pilote. M45 (P1) : `v_signal` (Score V) retiré — anti-filtre acté. */
export const filterParams = (f: Filters): Record<string, string | number> => ({
  ...(f.tiers.length ? { tiers: f.tiers.join(',') } : {}),
  // M129-B : score_min (matrice morte) ne s'envoie plus — le rang/tier remplace.
  ...(f.surfaceMin != null ? { surface_min: f.surfaceMin } : {}),
  ...(f.surfaceMax != null ? { surface_max: f.surfaceMax } : {}),
  ...(f.sdpMin != null ? { sdp_min: f.sdpMin } : {}),
  ...(f.evenement ? { evenement: 'true' } : {}),
  ...(f.veille ? { veille: 'true' } : {}),
  ...(f.horsCopro ? { hors_copro: 'true' } : {}),
  ...(f.flags.length ? { flags: f.flags.join(',') } : {}),
  ...(f.flagsExclus.length ? { flags_exclus: f.flagsExclus.join(',') } : {}),
  ...(f.communes.length ? { communes: f.communes.join(',') } : {}),
  ...(f.personneMorale ? { personne_morale: 'true' } : {}),        // M11 B2 : propriétaire personne morale
  ...(f.zonagePlu.length ? { zonage: f.zonagePlu.join(',') } : {}), // M11 B2 : zonage PLU (familles U/AU/A/N)
  // M45 (P2a) — barre niveau 1 + tiroir droit
  ...(f.sdpMax != null ? { sdp_max: f.sdpMax } : {}),
  ...(f.constructibilite.length ? { constructibilite: f.constructibilite.join(',') } : {}),
  ...(f.etatSol.length ? { etat_sol: f.etatSol.join(',') } : {}),
  ...(f.capaciteMin != null ? { capacite_min: f.capaciteMin } : {}),
  ...(f.destinationAutorisee ? { destination: f.destinationAutorisee } : {}),   // FAISABILITE-1 lot B
  ...(f.zonePlu.length ? { zone_plu: f.zonePlu.join(',') } : {}),
  // M45 (P2d) — tiroirs éco / mutation / propriété / veille
  ...(f.sousDensite ? { sous_densite: 'true' } : {}),
  ...(f.multMin != null ? { mult_min: f.multMin } : {}),
  ...(f.rangMax != null ? { rang_max: f.rangMax } : {}),
  ...(f.renouvellement ? { renouvellement: 'true' } : {}),
  ...(f.proprietaireType.length ? { proprietaire_type: f.proprietaireType.join(',') } : {}),
  ...(f.droitsResiduels?.length ? { droits_residuels: f.droitsResiduels.join(',') } : {}),
  ...(f.etatSociete.length ? { etat_societe: f.etatSociete.join(',') } : {}),
  ...(f.copro.length ? { copro: f.copro.join(',') } : {}),
  ...(f.npnru ? { npnru: 'true' } : {}),
  ...(f.adresseAbsente ? { adresse_absente: 'true' } : {}),
  // COUCHES-2 point 4 — statut ZFANG / FRR (source unique territoire_fiscal, cf. carte + fiche commune).
  ...(f.zfangRegime?.length ? { zfang: f.zfangRegime.join(',') } : {}),
  ...(f.frrClassement?.length ? { frr: f.frrClassement.join(',') } : {}),
  // M45-B (L1) — tiroir Économie
  ...(f.budgetMax != null ? { budget_max: f.budgetMax } : {}),
  ...(f.chargeMin != null ? { charge_min: f.chargeMin } : {}),
  ...(f.chargeMax != null ? { charge_max: f.chargeMax } : {}),
  ...(f.prixMarcheMin != null ? { prix_marche_min: f.prixMarcheMin } : {}),
  ...(f.prixMarcheMax != null ? { prix_marche_max: f.prixMarcheMax } : {}),
  ...(f.marcheFiable ? { marche_fiable: 'true' } : {}),
  // M55-D stage 6 — Signaux de vie (OU dans le groupe, ET avec le reste)
  ...(f.signaux.length ? { signaux: f.signaux.join(',') } : {}),
  // KF1 (rattrapage KelFoncier) — section « Propriétaire » (facettes DGFiP, millésime 2025).
  // personne_morale est déjà envoyé plus haut (f.personneMorale). Les critères fins :
  ...(f.pmDenom ? { pm_denom: f.pmDenom } : {}),
  ...(f.pmSiren ? { pm_siren: f.pmSiren } : {}),
  ...(f.pmForme?.length ? { pm_forme: f.pmForme.join(',') } : {}),
  ...(f.pmApe?.length ? { pm_ape: f.pmApe.join(',') } : {}),
  ...(f.pmDirigMin != null ? { pm_dirig_min: f.pmDirigMin } : {}),
  ...(f.pmDirigMax != null ? { pm_dirig_max: f.pmDirigMax } : {}),
  ...(f.pmAge?.length ? { pm_age: f.pmAge.join(',') } : {}),   // KELFONCIER-FIX-1 (Lot B) — tranche d'âge dirigeant
  // KELFONCIER-FIX-1 (Lot D) — filtres bâti : hauteur LiDAR faîtage (m) + emprise bâtie (%).
  ...(f.hauteurMin != null ? { hauteur_min: f.hauteurMin } : {}),
  ...(f.hauteurMax != null ? { hauteur_max: f.hauteurMax } : {}),
  ...(f.empriseMin != null ? { emprise_min: f.empriseMin } : {}),
  ...(f.empriseMax != null ? { emprise_max: f.empriseMax } : {}),
  ...(f.caMin != null ? { ca_min: f.caMin } : {}),
  // mode B rentable : porte AUSSI les paramètres du curseur SESSION partagé (L2)
  ...(f.modeBRentable ? {
    mode_b_rentable: 'true',
    modeb_travaux_m2: useApp.getState().modeB.travauxM2,
    modeb_loyer_m2: useApp.getState().modeB.loyerM2,
    modeb_rendement_pct: useApp.getState().modeB.rendementPct,
  } : {}),
})

/** M45 (P2a) — filtre v2 des tiers selon l'interrupteur « Analyse LABUSE » :
 *  ACTIF → on applique le classement (les tiers choisis, défaut = univers hors écartées) ;
 *  COUPÉ → voie manuelle pure : on n'impose AUCUN tier (le classement ne pilote plus). */
// Univers « hors exclusions dures » (étage 0 écarté) = ce que l'analyse RETIENT — déclassements
// INCLUS (doctrine « tout montrer », M30). Écartée = l'exclusion dure (étage 0). Les deux réunis
// = la trame entière (le cadastre analysé). Réconcilie le compteur avec « 431 663 analysées ».
const TIERS_ANALYSE = [
  // PALIERS-1 — les DEUX vocabulaires : servi (codes par rang) + q_v14 (paliers v2). Un run ne
  // porte qu'un vocabulaire ; l'autre ne matche aucune ligne. L'écartée reste hors univers analysé.
  'brulante', 'chaude', 'reserve_fonciere', 'a_creuser',
  'declasse_bati_sature', 'declasse_non_constructible', 'declasse_bati_revele',
  'declasse_zone_fermee', 'declasse_au_statut_inconnu', 'declasse_au_fermee',
  'priorite', 'a_suivre', 'sans_signal',
]
const tiersParam = (f: Filters): Record<string, string> =>
  f.analyseLabuse
    ? { tiers: (f.tiers.length ? f.tiers : TIERS_ANALYSE).join(',') }   // l'analyse retient (hors exclusions dures)
    : { tiers: [...TIERS_ANALYSE, 'ecartee'].join(',') }               // toute la trame (le cadastre analysé)

export interface FiltreReponse {
  compte: number
  total: number
  tiers: { brulante: number; chaude: number; reserve_fonciere: number; a_creuser: number; ecartee: number }
  // RECETTE-3 (T4) — comptes des 4 segments du listing d'analyse (hors étage 0, ordre fixe).
  segments?: { permis_pro: number; terrain_nu: number; bati_densifier: number; reste: number }
  // ANALYSE-1 — ventilation par BANDE du run candidat (Excellente A / Bonne B / À étudier C / Faible D /
  // Sans potentiel 0 / Analyse incomplète NC), comptes bruts du moteur (aucun quota/rang/percentile).
  bandes?: Record<'A' | 'B' | 'C' | 'D' | '0' | 'NC', number>
  bande_total?: number
  // ANALYSE-2/3 — croisement bande × Signal sur TOUTES les bandes (compteur filtré + preuve 20 combos
  // + cross-filtrage des 5 pastilles de l'encart par le Signal).
  bandes_signal?: Record<'A' | 'B' | 'C' | 'D' | '0' | 'NC', Record<'fort' | 'moyen' | 'faible', number>>
  opportunites: number
  opportunites_evenement: number
  dossiers_opportunites: number
  opportunites_avec_dossier: number
  opportunites_sans_identite: number
  page: ParcelResult[]
  limit: number; offset: number; sort: string
}
/** Endpoint UNIFIÉ M45 (« théâtre ») : compte exact + ventilation tier + page en un appel. */
export const getFiltre = (f: Filters, limit = 20, sort: SortKey = 'rang', offset = 0, groupes = false, segment?: string) => {
  const { tiers: _t, ...rest } = filterParams(f)   // le tier passe par l'interrupteur (tiersParam)
  return j<FiltreReponse>(`/filtre?${qf({ limit, offset, sort, ...(groupes ? { groupes: 1 } : {}), ...(segment ? { segment } : {}), ...rest, ...tiersParam(f) })}`)
}
/** M55-D stage 7 — COMPTE SEUL, annulable (AbortController) : le compteur vivant du panneau
 *  Filtres. Même construction que getFiltre (limit 0), jamais une estimation locale. */
export const getFiltreCount = (f: Filters, signal?: AbortSignal) => {
  const { tiers: _t, ...rest } = filterParams(f)
  return j<FiltreReponse>(`/filtre?${qf({ limit: 0, ...rest, ...tiersParam(f) })}`, { signal })
}
/** M55-G suite (point 1) — les IDU du résultat courant (mêmes critères, plafond serveur
 *  20 000 + drapeau tronqué) : la CARTE raccorde sa palette au résultat exact de la liste. */
export const getFiltreIdus = (f: Filters) => {
  const { tiers: _t, ...rest } = filterParams(f)
  return j<FiltreReponse & { idus: string[] | null; idus_tronque: boolean }>(
    `/filtre?${qf({ limit: 0, idus: 1, ...rest, ...tiersParam(f) })}`)
}

/** M99 Phase 3 — zones du sélecteur par famille : familles triées par volume réel, zones en
 *  graphie réglementaire MAJUSCULE (zone_filtre) avec compte CALCULÉ ; portée île ou communes. */
export type ZonageZones = {
  portee: 'ile' | 'commune'; communes: string[]
  familles: { fam: string; n: number; zones: { zone: string; n: number }[] }[]
}
export const getZonageZones = (communes: string[]) =>
  j<ZonageZones>(`/zonage/zones${communes.length ? `?communes=${encodeURIComponent(communes.join(','))}` : ''}`)

/** Tris de la liste (M5.1) : rang P par défaut ; ×N, surface, commune en options. */
// M55-H point 4 : 'surface_asc' = le sens inverse du tri Surface (re-clic sur la pill)
// RECETTE-3 (T3) : 'potentiel' = ancien tri du listing FACTUEL (adressées, puis SDP résiduelle).
// RECETTE-5 (V2) : le tri factuel devient 'adresse' (adressées d'abord, puis surface décroissante) —
// que du fait ; 'potentiel' (SDP résiduelle = calcul LABUSE) ne sert plus qu'en analyse, nulle part ailleurs.
// ANALYSE-1 : 'labuse' = le classement du NOUVEAU moteur (bande lexicographique puis Signal de mutation).
export type SortKey = 'rang' | 'mult' | 'surface' | 'surface_asc' | 'commune' | 'potentiel' | 'adresse' | 'labuse'
// ANALYSE-1/2 — le param serveur `bande` : `qualite` (les 4 bandes de qualité), une bande PRÉCISE
// (A/B/C/D — filtre Classement), ou un groupe de fin de liste (`nc`, `zero`).
export type BandeGroupe = 'qualite' | 'nc' | 'zero' | 'A' | 'B' | 'C' | 'D'
export type SignalNiveauKey = 'fort' | 'moyen' | 'faible'
export type QualiteKey = 'A' | 'B' | 'C' | 'D'

export interface CommuneInfo { commune: string; insee: string; parcelles: number; chaudes: number; evaluees: number; bbox: [number, number, number, number]; note: string | null }
export const getCommunes = () => j<CommuneInfo[]>('/communes')
// RECETTE-10 T11 — ce que le score apporte, mesuré (taux de mutation 12 mois par palier vs filtre
// simple) + une phrase chiffrée/datée pour le client. Mémorisé 6h côté serveur.
export interface ScoringBacktest { phrase_client: string | null; fenetre_fin?: string; base_pct?: number }
export const getScoringBacktest = () => j<ScoringBacktest>('/scoring/backtest')
// FRONT-CHIFFRES-2 (F26) — le seuil bas de la fraction de probabilité (« sous 1/d → peu probable »)
// servi depuis config/scoring_client.yaml : le front n'écrit plus « 1/50 » en dur, il lit le seuil
// (une bascule de bandes le met à jour partout). Le verdict lui-même (fraction ou « — ») est déjà
// calculé au serveur et cohérent fiche/filtres/Dossier/Copilote.
export const getScoringFraction = () => j<{ seuil_bas_denominateur: number; paliers: number[] }>('/vocabulaire/scoring-fraction')
// RETOURS-1 R3 — acquisitions PM d'une commune : constat DGFiP (changement de propriétaire moral
// d'un millésime au suivant), hors scoring. Servi par le bloc contexte ET le listing dédié.
export interface AcquisitionsPm {
  commune?: string; source: string | null; note: string; depuis_millesime: number
  n: number; n_total: number; tronquee: boolean
  acquisitions: { idu: string; de_millesime: number; a_millesime: number; siren_avant: string | null; denomination_avant: string | null; siren_apres: string | null; denomination_apres: string | null }[]
}
export const getCommuneAcquisitions = (commune: string, limit = 200) =>
  j<AcquisitionsPm>(`/communes/${encodeURIComponent(commune)}/acquisitions-pm?limit=${limit}`)

export interface ContexteCommune {
  commune: string; insee: string | null; epci: string | null; epci_nom: string | null
  // FICHE-COMMUNE-2 (C2) — signaux nommés (règle en constante ; n'apparaissent que si vrais) qui
  // remplacent « signal : prudence ». (C1) `cache_calcule_le` = date du précalcul (pied de fiche ; null = calcul direct).
  signaux?: { code: string; ton: 'rouge' | 'orange'; libelle: string }[]
  cache_calcule_le?: string | null
  // M55-C : bandeau RNU générique (null hors commune au règlement national d'urbanisme)
  rnu: { libelle: string; detail: string } | null
  // K2 — coordonnées de la mairie (Annuaire de l'administration). Champs absents = null → « Absent ».
  mairie: {
    commune: string; nom: string | null; adresse: string | null; code_postal: string | null
    telephone: string | null; email: string | null; site_officiel: string | null
    url_annuaire: string | null; source: string; date_import: string | null
  } | null
  // COMMUNE-RANGEMENT-1 lot 3 — `acquisitions_pm` a été RETIRÉE du payload contexte (elle avait quitté
  // la fiche en RETOURS-1 R3 → outil Communes « Acquisitions récentes », via getCommuneAcquisitions, et
  // le back cessait de la calculer). Le type AcquisitionsPm reste servi par cet endpoint dédié.
  // M83 C1 — le foncier de la commune (points de calcul existants réutilisés)
  // OUTILS-6 C1 : repartition_zonage passe en parts de SURFACE (somme = 100 %, ha par famille) ;
  // stock_opportunites porte le stock foncier EN PARCELLES ET EN HA (même compte que le comparateur).
  foncier: {
    n_parcelles: number; surface_ha: number | null
    repartition_zonage: {
      base: 'surface'; total_ha: number
      familles: Record<'U' | 'AU' | 'A' | 'N', { ha: number; pct: number; n: number }>
    } | null
    stock_opportunites: { n: number; ha: number }
    classement: { evaluees: number; sans_zonage: number; raison_sans_zonage: string }
    prix_terrain_nu: { par_zone: Record<string, { median_eur_m2: number | null; n: number | null; calculable: boolean }> | null; calculable: boolean; motif: string | null; seuil_n: number; etiquette: string | null }
    mutations_12m: number
    permis_12m: { n: number; reserve: string }
  } | null
  // OUTILS-6 C2 — les chiffres COMMUNS au comparateur des 24 communes (même moteur, même run)
  comparable: {
    ancien_median_eur_m2: number | null; ancien_n: number | null; neuf_eur_m2: number | null
    permis_5a: number | null; delai_median_mois: number | null; stock_opportunites_n: number | null; source: string
  } | null
  // OUTILS-6 C5 — les blocs ajoutés, chacun depuis le moteur de son outil d'origine
  marche_annonces: {
    biens: number; seuil_n: number; sous_seuil: boolean
    // COMMUNE-FIX-1 (A2) — seuil Radar (30) : sous ce seuil, ni médian ni écart (demande_sous_seuil)
    demande_seuil_n?: number; demande_sous_seuil?: boolean
    prix_demande_median_eur_m2: number | null; prix_demande_n: number | null
    ecart_demande_acte_pct: number | null; prix_acte_eur_m2: number | null; source: string
  } | null
  risques: { ppr_pct: number | null; mouvement_terrain_pct: number | null; catnat_arretes: number; catnat_detail?: { type_peril: string; date_debut: string | null; date_fin: string | null; date_arrete: string | null; code_national: string | null; date_publication_jo: string | null }[]; parc_national: boolean; azi_tri?: { azi: { libelle?: string }[]; tri: { libelle?: string }[]; detail?: string } | null; source: string }
  population: {
    habitants: number | null; menages: number | null; niveau_vie_moyen_eur: number | null
    // COMMUNE-FIX-1 (A1) — population LÉGALE INSEE (municipale) : millésime + population totale
    habitants_millesime?: string | null; habitants_pop_totale?: number | null; menages_millesime?: string | null
    // COHERENCE-FIX-1 (lot E) — étiquette prête (« Population légale 2023 (INSEE) »), année comprise.
    habitants_etiquette?: string | null
    logements: number | null; vacants: number | null; vacance_pct: number | null; source: string
    // DONNEES-1 lot 2.4 — part du parc construit avant 1991 (RP2022 ACHL). null = non ingéré.
    parc_ancien_pct?: number | null
    // SOURCES-1 lot 6 — l'affinage par quartier (IRIS RP2022), maille dite
    quartiers?: { n_iris: number; vacance_min_pct: number; vacance_max_pct: number
      vacance_mediane_pct: number; source: string } | null
  }
  plu_statut: {
    statut: string; libelle: string | null; procedure?: string | null; date_reglement: string | null
    confiance?: string | null; recherche_verbatim: boolean; source: string | null
    // COMMUNE-FIX-1 (D12) — procédure PLU en cours au dernier relevé Sudocuh
    procedure_sudocuh?: { document: string | null; etat: string | null; prescription: string | null; millesime: string | null } | null
  }
  // GEOPF-3 — SCOT (planification supra-communale, GPU) : nom + date d'approbation. null = hors périmètre.
  scot?: { nom: string; date_approbation: string | null; statut: string | null; source: string } | null
  permis_bloc: {
    permis_12m: number; permis_5a: number | null; logements_12m: number | null
    delai_median_mois: number | null; point_mort: number; source: string
    // KELFONCIER-FIX-1 (Lot C) servis, KELFONCIER-FIX-2 (Lot D) affichés : ventilation PC/PA/DP/PD
    // (autorisés, 12 mois) + annulés (12 mois), même source SITADEL que le chiffre existant.
    permis_type_12m?: Record<string, number>; permis_annules_12m?: number
  }
  densifiables: { parcelles: number | null; sdp_residuelle_m2: number | null; source: string | null } | null
  loyer: { median_eur_m2: number; type: string | null; source: string } | null
  // COMMUNE-RANGEMENT-1 lot 2 — parc social RPLS (SDES), fait communal. null = non ingéré.
  parc_social: { logements: number; construct_median: number | null; millesime: string; source: string } | null
  // COMMUNE-RANGEMENT-2 lot 2 — prix du neuf OBSERVÉ (commune), aux côtés du VEFA à l'acte. null = absent.
  prix_neuf_observe: { eur_m2: number; niveau: string; n: number | null; source: string } | null
  // SOURCES-1 lot 1 — zonage A/B/C (DHUP, arrêté national) : passe-plat sourcé + daté. null = non ingéré.
  zonage_abc: { zone: string; millesime: string; source: string } | null
  // SOURCES-1 lot 5 — taux fonciers (REI) + ACV/PVD/ORT (Denormandie)
  fiscalite: { tfpb_commune_pct: number | null; tfpb_epci_pct: number | null
    tfpnb_commune_pct?: number | null; tfpnb_epci_pct?: number | null
    teom_pct: number | null; millesime: string; source: string
    maj_at?: string | null; perime?: boolean } | null
  // COMMUNE-FIX-1 (D10) — taux communal de la taxe d'aménagement (même source que l'outil Taxe)
  taxe_amenagement: { part_communale_pct: number | null; millesime?: string | null
    delib_date?: string | null; perime?: boolean; source: string } | null
  ort: { statut: 'acv' | 'pvd' | 'autre' | 'hors'; commune?: string
    ort_signee: boolean; date_signature?: string | null
    denormandie: string; millesime?: string; source?: string } | null
  // COUCHES-2 point 4 — ZFANG / FRR (source unique territoire_fiscal, la même qui peint la carte
  // et qui filtre les parcelles). regime ZFANG : renforce | standard ; classement FRR : totalite |
  // partie | hors.
  zfang_frr: {
    zfang: { regime: 'renforce' | 'standard'; libelle: string; source_ref: string; lien: string }
    frr: { classement: 'totalite' | 'partie' | 'hors'; libelle: string; source_ref: string; lien: string }
    avertissement?: string | null
  } | null
  outils: {
    permis_en_cours: number; permis_point_mort: number; densifiables: number
    radar_biens: number; scan_pm: number; solaire_piscines: number
  }
  // M36 Lot D : le compteur du tier haut EN DUR (même point de calcul que /communes)
  classement: { tiers_hauts: number; dossiers: number; libelle: string; source: string } | null
  // RETOURS-12 O8 — `deficit` (objectif − taux, en points) servi par le backend, MÊME arithmétique que
  // la colonne « Déficit SRU (pts) » du tableau des 24 communes (jamais recalculé au front → jamais divergent).
  sru: { taux_lls: number; objectif_pct: number; deficit?: number | null; statut: string; prelevement_eur: number; millesime: string; detail: { nb_lls?: number }; source_nom: string; source_url: string } | null
  anru: { nom: string; interet: string; code_qpv: string; source_nom: string; source_url: string }[]
  qpv: { nom: string; code: string }[]
  plh: { periode: string; statut: string; obj_logements_an: number | null; part_sociale_pct: number | null; refs: { doc: string; url?: string; page?: string | number }[] } | null
  marche: { millesime: string; logements: number; vacants: number; proprietaires_pct: number; locataires_pct: number; maisons_pct: number; apparts_pct: number; typologie: Record<string, any>; source_nom: string; source_url: string } | null
  notes: string[]
}
export interface Entonnoir {
  commune: string | null; analysees: number; opportunites: number
  tiers?: { brulante: number; chaude: number; reserve_fonciere: number; a_creuser: number; ecartee: number }
  motifs: { motif: string; n: number }[]; note: string
}
export const getContexteCommune = (commune: string) =>
  j<ContexteCommune>(`/communes/${encodeURIComponent(commune)}/contexte`)
export const parcelAt = (lon: number, lat: number) =>
  j<{ idu: string | null }>(`/parcels/at?lon=${lon}&lat=${lat}`)
export const searchParcels = (needle: string, opts?: { ileEntiere?: boolean }) =>
  j<{ idu: string; commune: string; surface_m2: number | null; status: string | null; q_score: number | null;
      tier_v2: string | null; rang_v2: number | null; etage0: boolean;
      adresse?: string | null }[]>(
    `/parcels/search?q=${encodeURIComponent(needle)}${!opts?.ileEntiere && commune() ? `&commune=${encodeURIComponent(commune()!)}` : ''}`)

// M45-B (L3) — UNIFICATION : compteur/cartouches ET liste passent par /filtre (FiltreCriteres),
// donc portent EXACTEMENT les mêmes facettes que le compteur du panneau. Plus jamais un compteur
// filtré et une liste qui ignore les filtres. `f` absent = univers par défaut (analyse active).
export const getStats = (f?: Filters) => getFiltre(f ?? EMPTY_FILTERS, 0).then((r) => r as unknown as Stats)
// E3 (M12) : `offset` exposé — pagination « Charger plus ». La page vient de /filtre (mêmes facettes).
// M55-H point 5 : `groupes` = liste groupée par tier (mode analyse), tri secondaire dedans
// RECETTE-12 B2 — `segment` : le back pagine à 200 SUR LES LIGNES DE CE SEGMENT (permis_pro /
// terrain_nu / bati_densifier / reste), dès le 1er appel. Sans segment : la page globale (inchangé).
export const getResults = (f?: Filters, limit = 200, sort: SortKey = 'rang', offset = 0, groupes = false, segment?: string) =>
  getFiltre(f ?? EMPTY_FILTERS, limit, sort, offset, groupes, segment).then((r) => r.page)

// ── ANALYSE-1 — l'écran ANALYSE lit le NOUVEAU moteur (table score_labuse du run candidat) ──────────
// Une SEULE liste, classée par bande de Score puis par Signal de mutation (sort=labuse, lexicographique).
// Le périmètre = les FILTRES GLOBAUX (commune, surface, zonage, nu/bâti, signaux) — MAIS PAS le filtre
// « tiers » de l'ancien classement (le nouveau moteur porte son propre verdict, la bande) : d'où le
// dépouillement de `tiers` ici. `bande` scope le groupe (qualité A-D / incomplète / sans potentiel),
// `signal` filtre le Signal (propre à l'Analyse, mandat §1.4).
export const getAnalyse = (
  f: Filters, bande: BandeGroupe, opts: { limit?: number; offset?: number; signal?: SignalNiveauKey } = {},
) => {
  const { tiers: _t, ...rest } = filterParams(f)   // filtres globaux SANS le tier de l'ancien classement
  const { limit = 200, offset = 0, signal } = opts
  return j<FiltreReponse>(`/filtre?${qf({
    limit, offset, sort: 'labuse', bande, ...(signal ? { signal } : {}), ...rest,
  })}`).then((r) => r.page)
}
// ANALYSE-1 — la ventilation par bande du périmètre courant (récapitulatif « LABUSE a analysé N »),
// en UN appel limit=0 (comme le compteur vivant) : mêmes filtres globaux, sans tier ni bande.
export const getAnalyseStats = (f: Filters) => {
  const { tiers: _t, ...rest } = filterParams(f)
  return j<FiltreReponse>(`/filtre?${qf({ limit: 0, ...rest })}`)
}
// SUITE-1 S7 — `csvExportUrl` + l'endpoint `/parcels/export.csv` SUPPRIMÉS (sans appelant depuis
// RETOURS-7 Z11, décision Vic). L'export CSV du projet (`projetCsvUrl`) est distinct et conservé.
export const getParcelsGeojson = () =>
  j<ParcelFeatureCollection>(`/map/parcels.geojson?${q({ limit: 60000 })}`)
// RECETTE-6 (A3) — le bâti de la BBOX pour l'extrusion 3D (empreinte au sol + hauteur BD TOPO). Borné
// à la vue courante (jamais l'île entière) ; sans hauteur → exclu côté serveur (pas d'extrusion inventée).
export const getBatiments = (bbox: [number, number, number, number]) =>
  j<{ type: 'FeatureCollection'; features: { type: 'Feature'; geometry: unknown; properties: { h: number } }[] }>(
    `/map/batiments.geojson?bbox=${bbox.join(',')}`)
// OUTILS-2 (O2-4) — géométrie d'UNE parcelle (Feature + centroïde) pour tracer son contour sur l'écran
// « Remonter le temps » sans charger tout le GeoJSON commune.
export const getParcelGeojson = (idu: string) =>
  j<{ type: 'Feature'; geometry: unknown; properties: { idu: string }; centroid: [number, number] }>(`/parcels/${encodeURIComponent(idu)}/geojson`)
export const getFiche = (idu: string) => j<Fiche>(`/parcels/${idu}?source=${SOURCE}`)
// RECETTE-8 W22 — l'exposition (orientation du versant + pente) calculée sur le MNT RGE ALTI,
// lazy (fetch WMS + gdaldem ~0,5 s). Remplace la vue mer abandonnée dans la tête de fiche.
export interface Exposition { idu: string; orientation: string | null; aspect_deg?: number | null; pente_moyenne_deg?: number | null; erreur?: string }
export const getParcelExposition = (idu: string) =>
  j<Exposition>(`/parcels/${encodeURIComponent(idu)}/exposition`)
// RETOURS-13 P6 — PROFIL ALTIMÉTRIQUE (coupe le long d'une ligne), lu LIVE dans le RGE ALTI.
export interface ProfilPoint { dist_m: number; alt_m: number | null }
export interface ProfilAltimetrique {
  disponible: boolean
  axe: 'parcelle' | 'trace'
  source: string
  points: ProfilPoint[]
  motif?: string | null
  distance_m?: number
  denivele_positif_m?: number
  denivele_negatif_m?: number
  pente_moyenne_pct?: number
  pente_max_pct?: number
  altitude_min_m?: number
  altitude_max_m?: number
}
export const getProfilParcelle = (idu: string) =>
  j<ProfilAltimetrique>(`/parcels/${encodeURIComponent(idu)}/profil-altimetrique`)
export const postProfilLigne = (ligne: [number, number][]) =>
  j<ProfilAltimetrique>('/parcels/profil-altimetrique', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ligne }) })
// ÉTUDE DE ZONE Z3 — le tiroir « Autour de cette parcelle » (isochrone IGN + Filosofi/BPE).
export const getParcelleZone = (idu: string, mode: 'pied' | 'voiture', minutes: number) =>
  j<ParcelleZone>(`/parcels/${idu}/zone?${q({ mode, minutes })}`)
// ÉTUDE DE ZONE Z4 — l'outil de chalandise (recherche NAF + agrégat de zone).
export const nafSearch = (query: string) =>
  j<{ resultats: NafOption[] }>(`/outils/etude-zone/naf?${q({ q: query })}`)
// RECETTE-2 C4 — la nomenclature groupée par famille, pour le déroulé parcourable.
export const nafFamilles = () =>
  j<{ familles: NafFamille[] }>('/outils/etude-zone/naf/familles')
export interface EtudeZoneInput {
  idu?: string | null; lon?: number | null; lat?: number | null
  geom?: unknown | null; naf?: string | null; minutes: number; mode: 'pied' | 'voiture'
  rayon_km?: number | null           // RETOURS-15 B9 — ampleur par défaut : rayon (0,5/1/2/5 km)
  sous_destination?: string | null   // DESTINATIONS-1 (X4.1) — slug R151-28 (verdict par zone PLU)
  titre?: string | null
}
// DESTINATIONS-1 (X4.1) — référentiel R151-27/28 (sélecteur « Activité (destination) », libellés officiels).
export const etudeZoneDestinationsRef = () =>
  j<import('./types').DestinationsReferentiel>('/outils/etude-zone/destinations')
export const etudeZone = (body: EtudeZoneInput) =>
  j<EtudeZoneResult>('/outils/etude-zone', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
// F3 (OUTILS-4) — toutes les entreprises de la zone, groupées par famille (appelé à la demande).
export const etudeZoneEntreprises = (body: EtudeZoneInput) =>
  j<import('./types').ZoneEntreprises>('/outils/etude-zone/entreprises', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
export const etudeZonePdfUrl = '/outils/etude-zone/export.pdf'

// M41 (Phase 2.6) — outil « Vérif procédure » : un IDU → procédure PLU en cours OUI/NON + conséquences.
// L'outil LIT le radar (point de calcul unique), il ne calcule rien. L'absence est datée elle aussi.
export interface VerifProcedure {
  idu: string; commune: string; insee: string; tier_servi: string | null; consulte_le: string
  procedure_en_cours: boolean | null; message?: string
  type?: string; stade?: string; date_acte?: string; source?: string; source_url?: string | null
  date_constat?: string; confiance?: string; synthese?: string
  consequences?: { sursis: { texte: string; base_legale: string } | null; veille_au: string | null }
}
export const verifProcedure = (idu: string) => j<VerifProcedure>(`/modules/verif-procedure/${idu}`)

// M51 — Annuaire PLU : recherche verbatim sourcé dans le règlement opposable (article, page PDF, lien).
// Aucun résumé. doute + pagination_ambigue rendus. RNU / hors-corpus = message honnête.
export interface PluExtrait {
  insee: string; commune: string; idurba: string; millesime: string | null; document: string
  zone: string | null; article_ref: string | null; page_pdf: number
  texte_verbatim: string; doute: boolean; doute_motif: string | null
  pagination_ambigue: boolean; pagination_note?: string; source_url: string; gpu_consult?: string
}
export interface PluSearch {
  query: string; insee: string | null; n: number; resultats: PluExtrait[]; message?: string; avis?: string
}
export interface PluCommune {
  insee: string; commune: string; statut: string; idurba?: string; millesime?: string
  extraits: number; doutes?: number; pagination_ambigue?: boolean; message?: string
  // M137-P — le « PLU intégral » = pack officiel GPU (.zip) à télécharger (aucun PDF en base).
  source_url?: string | null; document?: string | null
  // RETOURS-12 O4 — procédure PLU EN COURS (source unique veille_plu) : « révision générale »… ou null.
  procedure_active?: string | null; procedure_date?: string | null
}
export const pluAnnuaireSearch = (qy: string, insee?: string, zone?: string) =>
  j<PluSearch>(`/modules/plu-annuaire/search?q=${encodeURIComponent(qy)}${insee ? `&insee=${insee}` : ''}${zone ? `&zone=${encodeURIComponent(zone)}` : ''}`)
export const pluAnnuaireCommunes = () =>
  j<{ n_communes: number; servables: number; n_plu_vigueur: number; non_servis: string[]; n_revision: number; n_rnu: number; n_non_ingere: number
      // RETOURS-12 O4 — compteur RÉCONCILIÉ des procédures PLU en cours (source unique veille_plu).
      n_procedures: number; procedures_par_etat: Record<string, number>; communes: PluCommune[] }>(`/modules/plu-annuaire/communes`)
// RETOURS-15 U8 — pack .zip du PLU EN VIGUEUR résolu en direct sur le GPU (commune en révision
// comprise). Trois issues distinctes : trouvé / GPU vide (mairie servie) / GPU injoignable.
export interface PluPack { insee: string; disponible: boolean; erreur?: string | null; message?: string
  idurba?: string; millesime?: string | null; statut_gpu?: string; url?: string
  mairie?: { nom: string; telephone: string | null; email: string | null; site_officiel: string | null } | null }
export const pluAnnuairePack = (insee: string) => j<PluPack>(`/modules/plu-annuaire/pack/${insee}`)

// M33 — recalcul mode B avec le paramètre CLIENT travaux (état UI seulement, rien persisté)
export const getModeB = (idu: string, travauxM2?: number) =>
  j<import('./types').ModeB>(`/parcels/${idu}/mode-b${travauxM2 != null ? `?travaux_m2=${travauxM2}` : ''}`)

// ── R5 (reliquats front) — UI des outils O2/O3 ────────────────────────────────────────────
// ETUDIER-BIEN-2 (Lot C) — `ScoreurResult` + `scoreurAdresse` (binding front de l'outil « Étudier un
// bien », O2) RETIRÉS : l'outil est supprimé, ses faits de marché sont dans la §Marché de la fiche et
// l'entrée par adresse dans la barre de recherche → fiche. L'endpoint POST /scoreur-adresse reste au
// dépôt (dormant, partage `_geocode`) — plus aucun appelant front.

// K3 (rattrapage KelFoncier) · calculette « Taxe d'aménagement ». Backend maître : aucun montant/taux
// écrit en dur côté front — la config (valeurs forfaitaires, abattement, forfaits, taux plafonds/défauts)
// et le calcul viennent des endpoints. Le taux communal N'A JAMAIS de défaut (l'outil ne l'invente pas).
export interface TaxeConfig {
  meta: { annee: number; source: string; url: string; releve_le: string; note: string }
  valeur_forfaitaire_m2: { hors_idf: number; idf: number }
  abattement: { taux_pct: number; plafond_m2_residence_principale: number }
  forfaits: {
    piscine_m2: number; panneau_pv_sol_m2: number; eolienne_mat: number
    stationnement_ext_place: number; stationnement_ext_place_max_delib: number
  }
  taux: {
    part_communale_plafond_pct: number; part_communale_defaut: number | null
    part_departementale_plafond_pct: number; part_departementale_defaut: number
    part_departementale_confirmee_974: boolean
  }
  exoneration_surface_min_m2: number | null   // RV2-V2 — exonération petites surfaces (CGI 1635 quater D)
}
export const getTaxeConfig = () => j<TaxeConfig>('/outils/taxe-amenagement/config')

export interface TaxeLigne { poste: string; detail: string; assiette_eur: number }
export interface TaxeResult {
  annee: number; source: string; url: string; note: string
  valeur_forfaitaire_m2: number
  lignes: TaxeLigne[]
  assiette_eur: number
  taux_communal_pct: number | null
  taux_departemental_pct: number
  part_departementale_confirmee: boolean
  part_communale_eur: number | null
  part_departementale_eur: number | null
  total_eur: number | null
  // TAXE-FIX-1 point 2 — redevance d'archéologie préventive (0,40 % de la même assiette, art. L524-7).
  rap_pct?: number
  rap_eur?: number
  rap_source?: string
  taux_communal_manquant: boolean
  message_taux_communal: string | null
  // TAXE-AMÉNAGEMENT-1 lot C — millésime + fraîcheur du taux communal public (null si saisi/absent).
  taux_communal_source?: 'public' | 'saisi' | null
  taux_communal_millesime?: string | null
  taux_communal_delib_date?: string | null
  taux_communal_perime?: boolean | null
  // TAXE-FIX-1 point 3 — le taux servi vient-il d'un secteur à taux majoré ?
  taux_communal_secteur_majore?: boolean | null
}
export interface TaxeParams {
  surface_taxable_m2: number
  residence_principale?: boolean
  logement_aide?: boolean
  // TAXE-FIX-1 point 1 — exonération de plein droit (CGI 1635 quater D) : la surface portée ici ne
  // produit aucune part (0 €), le motif nomme l'article (agricole 3° / plai 2° / reconstruction 9°).
  surface_exoneree_m2?: number
  motif_exoneration?: 'agricole' | 'plai' | 'reconstruction' | null
  piscine_m2?: number
  pv_sol_m2?: number
  stationnement_ext_places?: number
  eoliennes_mats?: number
  taux_communal_pct?: number | null
  taux_departemental_pct?: number | null
  insee?: string | null   // OUTILS-FIX-5 L2 — clé de la table des taux : le back sert le taux public de la commune
  idu?: string | null      // TAXE-FIX-1 point 3 — résolution PAR PARCELLE (secteur à taux majoré prioritaire)
}
export const getTaxeAmenagement = (p: TaxeParams) => {
  const params = new URLSearchParams({ surface_taxable_m2: String(p.surface_taxable_m2) })
  if (p.residence_principale) params.set('residence_principale', 'true')
  if (p.logement_aide) params.set('logement_aide', 'true')
  if (p.surface_exoneree_m2) params.set('surface_exoneree_m2', String(p.surface_exoneree_m2))
  if (p.motif_exoneration) params.set('motif_exoneration', p.motif_exoneration)
  if (p.piscine_m2) params.set('piscine_m2', String(p.piscine_m2))
  if (p.pv_sol_m2) params.set('pv_sol_m2', String(p.pv_sol_m2))
  if (p.stationnement_ext_places) params.set('stationnement_ext_places', String(p.stationnement_ext_places))
  if (p.eoliennes_mats) params.set('eoliennes_mats', String(p.eoliennes_mats))
  if (p.taux_communal_pct != null) params.set('taux_communal_pct', String(p.taux_communal_pct))
  if (p.taux_departemental_pct != null) params.set('taux_departemental_pct', String(p.taux_departemental_pct))
  if (p.insee) params.set('insee', p.insee)
  if (p.idu) params.set('idu', p.idu)
  return j<TaxeResult>(`/outils/taxe-amenagement?${params.toString()}`)
}

// GABARIT-1 — outil « Gabarit réglementaire ». Le front N'AFFICHE que ce que sert le moteur pur
// (doctrine LABUSE : zéro recalcul au front). Aucun champ estimatif. GeoJSON en 4326.
export interface GabRegSource {
  document?: string | null; zone?: string | null; article?: string | null
  versionDate?: string | null; provider?: string | null
}
export interface GabAppliedRule {
  ruleId: string; category: string; label: string
  value?: number | null; unit?: string | null; detail?: string | null; source: GabRegSource
}
export interface GabNonIntegratedRule { id?: string | null; label: string; detail?: string | null; source: GabRegSource }
export interface GabCoverage { reculs: boolean; hauteur: boolean; emprise: boolean; risques: boolean }
export type GabGeom = { type: string; coordinates: unknown } | null
export interface GabaritResult {
  status: 'ok' | 'incomplete'
  message?: string | null
  validationErrors: string[]
  raccordement?: Record<string, unknown> | null
  surfaceParcelleM2?: number | null
  zoneImplantationM2?: number | null
  plafondEmpriseM2?: number | null
  plafondEmpriseStatus?: string | null   // 'absent' → « Non réglementé »
  hauteurReglementaireM?: number | null
  hauteurSource?: GabRegSource | null
  hauteurStatus?: string | null          // 'not_integrated' → « Non chiffrée » (prospect)
  hauteurBase?: string | null            // 'faitage' | 'egout' — ce que porte hauteurReglementaireM
  hauteurEgoutM?: number | null          // égout en sous-ligne quand la règle distingue faîtage/égout
  coverage?: GabCoverage | null
  appliedRules: GabAppliedRule[]
  nonIntegratedRules: GabNonIntegratedRule[]
  contourGeoJSON?: GabGeom
  zoneImplantationGeoJSON?: GabGeom
  retraitsGeoJSON?: GabGeom
  exclusionsGeoJSON?: GabGeom
  // GABARIT-6 P4 — bâti existant (emprise BD TOPO + hauteur LiDAR HD), fait contextuel
  batiExistantGeoJSON?: GabFeatureCollection | null
}
export interface GabBatiProps { hauteur_m?: number | null; h_source?: string | null }
export interface GabFeatureCollection {
  type: 'FeatureCollection'
  features: Array<{ type: 'Feature'; properties: GabBatiProps; geometry: GabGeom }>
}
export const getGabarit = (idu: string) =>
  j<GabaritResult>(`/outils/gabarit/${encodeURIComponent(idu)}`)

// SECTEUR-1 (S1) — outil « Mon secteur » : prix du secteur autour d'une parcelle (médiane locale par
// type + tendance 12 mois + annonces Radar dans le rayon). Chaque chiffre porte son n/millésime.
export interface DistribRepere { n: number; min: number | null; p25: number | null; median: number | null; p75: number | null; max: number | null }
export interface Distribution { avant: DistribRepere; apres: DistribRepere; n_exclus_extremes: number; n_min_vise: number; periode_segment?: string }
export interface EcartCommune { secteur_eur_m2: number | null; rayon_m: number; commune_eur_m2: number; n_commune: number | null; ecart_pct: number | null; phrase: string; sens?: 'sous' | 'au_dessus' | null }
export interface LocalMed { eur_m2: number; n: number | null; millesime: string | null; rayon_m: number | null; perimetre: string | null; distribution?: Distribution | null }
export interface MonSecteurData {
  idu: string; commune: string; adresse: string | null
  secteur_bati: {
    median_eur_m2: number | null; q1: number | null; q3: number | null; n: number | null
    rayon_m: number | null; type_prix: string | null; fiabilite: string | null
    commune_seule: boolean | null; periode: number[] | null; tendance_pct: number | null; tendance: string | null
    distribution?: Distribution | null; ecart_commune?: EcartCommune | null
  } | null
  par_type: { maison: LocalMed | null; appartement: LocalMed | null; terrain_nu: LocalMed | null }
  annonces_radar: { commune: string; type_bien: string; prix: number | null; distance_m: number | null; prix_m2_affiche: number | null; ecart_pct: number | null; reference_locale: boolean }[]
  sources: string[]; note: string
}
export const getMonSecteur = (idu: string) => j<MonSecteurData>(`/outils/mon-secteur?idu=${encodeURIComponent(idu)}`)

// SECTEUR-1 (S3) — outil « Veille promoteurs » : permis déposés par promoteurs / bailleurs / SEM.
// PROMO-1 (P4) — le programme publié rattaché (FAITS + LIEN seulement, jamais un visuel).
export interface ProgrammeLie { nom: string; url: string | null; promoteur_nom: string | null }
// SECTEUR-2 (T2) — une OPÉRATION (groupe de permis contigus, même propriétaire moral, même période).
export interface OperationPromoteur {
  siren: string; denomination: string | null; categorie: string; commune: string
  nb_logements: number; n_permis: number; date_min: string | null; date_max: string | null
  annee: number | null; etat: string | null; etat_libelle: string | null; lon: number | null; lat: number | null
  idus: string[]; libelle: string; radar_bien_id: number | null; radar_cite: boolean
  programme?: ProgrammeLie | null
}
export interface VeillePromoteurs {
  n_total: number; n_servi: number; tronquee: boolean; plafond: number; n_logements_total: number
  categories: { cle: string; label: string }[]; millesime: string | null
  regle: { contiguite_m: number; periode_mois: number; phrase: string }
  operations: OperationPromoteur[]; note: string
}
export const getVeillePromoteurs = (p: { commune?: string; categorie?: string; depuis?: string; siren?: string; limit?: number } = {}) => {
  const q = new URLSearchParams()
  if (p.commune) q.set('commune', p.commune)
  if (p.categorie) q.set('categorie', p.categorie)
  if (p.depuis) q.set('depuis', p.depuis)
  if (p.siren) q.set('siren', p.siren)   // ADMIN-1 (AD3) — restreindre aux opérations d'UN propriétaire
  if (p.limit) q.set('limit', String(p.limit))
  return j<VeillePromoteurs>(`/outils/veille-promoteurs${q.toString() ? `?${q}` : ''}`)
}
export interface ProgrammePublie { id: number; nom: string; commune: string | null; url: string | null; annee: number | null }
export interface PromoteurFrise {
  siren: string; denomination: string | null; n_operations: number; n_logements: number
  // RETOURS-13 R29 — le chiffre dit ce qu'il compte + activité de pétitionnaire (Sitadel 2013+).
  perimetre_note: string
  petitionnaire: { n_permis: number; n_logements: number; note: string }
  filiales_identifiees: { siren: string; nom: string | null; n_permis: number; n_logements: number }[]
  frise: { annee: number; n_operations: number; n_logements: number }[]
  operations: { annee: number | null; commune: string; nb_logements: number; libelle: string; programme?: ProgrammeLie | null }[]
  programmes_publies: ProgrammePublie[]
  scan_patrimoine: { n_parcelles: number; endpoint: string }; note: string
}
// PROMO-1 (P2/P3) — collecte assistée + rattachement (admin).
export interface ProgrammeCandidat { nom: string; commune: string | null; url: string | null; annee: number | null }
export interface CollecteResult { ok: boolean; motif?: string; promoteur_siren: string | null; promoteur_nom: string; url_portfolio?: string; programmes?: ProgrammeCandidat[]; n?: number; note?: string }
export const collecterProgrammes = (body: { url: string; promoteur_siren?: string; promoteur_nom?: string }) =>
  j<CollecteResult>('/admin/programmes/collecter', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
export const validerProgrammes = (body: { promoteur_siren?: string; promoteur_nom?: string; url_portfolio: string; programmes: ProgrammeCandidat[] }) =>
  j<{ ok: boolean; insere: number; ignore_doublon: number; rattache_auto: number; lignes: { id: number; nom: string; rattache: boolean }[]; note: string }>('/admin/programmes/valider', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
export interface ProgrammeAdmin { id: number; promoteur_siren: string | null; promoteur_nom: string; nom: string; commune: string | null; url: string | null; url_portfolio: string; source: string; annee: number | null; date_releve: string | null; op_siren: string | null; op_commune: string | null; op_annee: number | null; rattachement_mode: string | null; rattachement_confiance: number | null }
export const getProgrammes = (promoteur_siren?: string) =>
  j<{ n: number; programmes: ProgrammeAdmin[] }>(`/admin/programmes${promoteur_siren ? `?promoteur_siren=${encodeURIComponent(promoteur_siren)}` : ''}`)
export const supprimerProgramme = (id: number) =>
  j<{ ok: boolean }>(`/admin/programmes/${id}`, { method: 'DELETE' })
export const delierProgramme = (id: number) =>
  j<{ ok: boolean }>(`/admin/programmes/${id}/delier`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
export const getPromoteurFrise = (siren: string) => j<PromoteurFrise>(`/outils/veille-promoteurs/${encodeURIComponent(siren)}/frise`)
export interface PromoteurAcquisitions { siren: string; denomination: string | null; n_parcelles: number; par_commune: { commune: string; n: number }[]; note: string }
export const getPromoteurAcquisitions = (siren: string) => j<PromoteurAcquisitions>(`/outils/veille-promoteurs/${encodeURIComponent(siren)}/acquisitions`)

// RETOURS-15 U6 — deja_batie : le chiffre pré-rempli est un RÉSIDUEL sur une parcelle bâtie, l'écran le nomme.
// OUTILS-FIX-5 L2 — insee (clé de la table des taux) + taux communal PUBLIC daté, servis par la MÊME
// résolution que la fiche §7 (taux_communal_public(idu[:5])) : l'outil affiche le taux, ne le fait plus saisir.
export interface TaxePrefill {
  idu: string; commune: string; insee: string
  surface_terrain_m2: number | null; zone_plu: string | null; sdp_gabarit_m2: number | null; deja_batie?: boolean
  zone_famille?: string | null   // FRONT-CHIFFRES-2 (F28) — U/AU/A/N servie (exonération locaux agricoles = 'A')
  taux_communal_pct: number | null
  taux_communal_source: 'public' | null
  taux_communal_millesime: string | null
  taux_communal_perime: boolean | null
  // TAXE-FIX-1 point 3 — la parcelle est-elle dans un secteur à taux majoré voté par la commune ?
  secteur_majore?: boolean
}
export const getTaxePrefill = (idu: string) => j<TaxePrefill>(`/outils/taxe-amenagement/prefill?idu=${encodeURIComponent(idu)}`)

// M13-B1 · autocomplétion d'adresse INTERNE : on interroge NOTRE table `adresses` (BAN
// rattachée aux parcelles à ~99,99 %) via l'endpoint /adresses/autocomplete — plus fiable que
// l'appel navigateur vers l'API BAN externe (qui pouvait échouer/être bloqué) et aligné sur
// notre trame. Chaque suggestion porte DÉJÀ son `idu` : atterrissage direct sur la fiche.
// Une sélection retourne TOUJOURS une adresse normalisée + coordonnées (jamais une chaîne libre).
export interface BanFeature {
  label: string          // adresse normalisée (jamais la saisie brute)
  lon: number
  lat: number
  idu: string | null     // parcelle rattachée (source interne) — landing direct
  type: string | null    // housenumber / street / municipality …
  postcode: string | null
}
export async function banAutocomplete(q: string, signal?: AbortSignal): Promise<BanFeature[]> {
  const needle = q.trim()
  if (needle.length < 3) return []
  const r = await j<{ features?: BanFeature[] }>(
    `/adresses/autocomplete?q=${encodeURIComponent(needle)}&limit=6`, { signal })
  return r.features ?? []
}

// RETOURS-16 V5 — suggestion UNIFIÉE des barres de recherche (un endpoint, six grammaires,
// groupées par type, 8 max). `types` = les grammaires que la barre appelante sait consommer.
export type SuggestType = 'adresse' | 'cadastre' | 'proprietaire' | 'siren' | 'commune' | 'projet' | 'lieu_dit'
export interface SuggestItem {
  type: SuggestType; label: string; sub?: string
  idu?: string | null; lon?: number; lat?: number
  siren?: string; commune?: string; insee?: string; projet_id?: number
  // RECHERCHE-2 Lot 3 (b) — ligne d'information NON cliquable (ex. « SIREN inconnu des fichiers
  // fonciers 2025 ») : honnête, mais rien à ouvrir (pas de siren/idu). Rendu grisé, aria-disabled.
  note?: boolean
}
export interface SuggestReponse {
  q: string; groupes: { type: SuggestType; items: Omit<SuggestItem, 'type'>[] }[]
  total: number; ms: number; formats: string
}
export const rechercheSuggest = (q: string, types: SuggestType[], signal?: AbortSignal) =>
  j<SuggestReponse>(`/api/recherche/suggest?q=${encodeURIComponent(q)}&types=${types.join(',')}`, { signal })

// O3 · anti-fiche « pourquoi pas » : motifs d'écartement hiérarchisés, sourcés (cascade servie).
export interface AntiFicheMotif { couche: string; motif: string; source: string }
export interface AntiFiche {
  idu: string; tier: string | null; cadre: string; synthese: string
  redhibitoire: AntiFicheMotif[]; vigilance: AntiFicheMotif[]
  n_redhibitoire: number; n_vigilance: number; avertissement: string
}
export const getAntiFiche = (idu: string) => j<AntiFiche>(`/anti-fiche/${idu}`)

// COUCHES-RETRAIT-1 lot 3 — `getMapLayer` (client de l'ancien `/map/layers.geojson`) retiré avec
// l'endpoint : les 56 couches sont servies par le tuyau (tuiles MVT `/map/tiles/{kind}`, cf.
// CouchesTuyau). Plus aucun appelant front depuis le retrait du lot 2.
// M6.1 : capacités des tuiles île — `zonage_parcelle` dit si mvt_parcels embarque zone_fam
// (sinon la couche « Zonage PLU (parcelles) » est grisée en mode île jusqu'au prochain build).
// FIX-CARTE T1 — `carte_le` = date de la donnée peinte (build des tuiles) ; `perime` = tuiles en
// retard sur le dernier re-score/résiduel du run servi (péremption VISIBLE au runtime, pas au build).
export const getTilesMeta = () => j<{ run_label: string | null; zonage_parcelle: boolean;
  carte_le: string | null; amont_le: string | null; perime: boolean }>('/map/tiles/meta')
// M55-D stage 5 : la DATE du run servi (champ `gel` du modèle épinglé) — pour la ligne de contexte
// de la Révélation (« classement du … »). Introuvable → null, la ligne s'affiche sans date.
// M55-H point 11 : getV2Modele retiré (0-caller — la date du run ne s'affiche plus côté client ;
// la page Sources interroge /v2/modele directement, sans gel ni dernier_run désormais).
// M55-D stage 9 — les chiffres PROUVÉS de l'accueil (endpoint agrégé, cache serveur 1 h).
// null = chiffre indisponible → le front le MASQUE, il ne l'invente pas.
export interface AccueilChiffres {
  parcelles: number | null; communes: number | null; sources: number | null
  ventes_train: number | null; communes_calibrees: number | null
  golden_parcelles: number | null; golden_verifs: number | null
  defisc_actives: number | null; permis_caducs: number | null
  ensembles_fonciers: number | null; bascules_tiers_hauts: number | null
  run_label: string
}
export const getAccueilChiffres = () => j<AccueilChiffres>('/accueil/chiffres')

// FRONT-CHIFFRES-2 (F13/F29) — la DA d'un palier servie depuis la source unique (scoring/
// tiers_client) : jeton DA (variable CSS) + ton du Badge + libellés. Le front ne code plus la
// correspondance palier→couleur (pastille Projets, badge Outils) ; à q_v15 seul le back change.
export interface PalierDA { code?: string; chip: string; long: string; jeton: string; ton: 'vert' | 'ambre' | 'neutre' | 'rouge' }
export const getPaliersDA = () => j<{ paliers: Record<string, PalierDA> }>('/vocabulaire/paliers')

// RETOURS-8 (R2) — la ligne d'accueil n'annonce plus de « retard » : deux chiffres réels (sources
// affichées · parcelles couvertes) → « voir les données ». `ton` toujours 'ok' (aucun rouge client).
export interface AccueilFraicheur {
  ton: 'ok' | 'warn' | 'error'; phrase: string
  n_sources: number; n_parcelles: number; pas_a_jour: number; cta: string
}
export const getAccueilFraicheur = () => j<AccueilFraicheur>('/accueil/fraicheur')

// M83 B4 — « CETTE SEMAINE » : trois signaux mesurés, avec fraîcheur (un zéro n'est pas une absence).
export interface AccueilCetteSemaine {
  permis: { n_7j: number; frais: boolean; derniere: string | null }
  ventes: { n_7j: number; frais: boolean; dernier_trimestre: string | null; sans_date_publication: boolean }
  communes_procedure_plu: number | null
}

// M78 — Copilote v2 : le client écrit, le routeur décide. Réponse instruite (QUESTION/OUTIL/refus)
// OU aiguillage vers une mission (RECHERCHE → run M26-A ; VERIFICATION/PROJET/VEILLE → phases 3/4).
export interface CopiloteV2Reponse {
  text: string
  intent: 'QUESTION' | 'OUTIL' | 'RECHERCHE' | 'VERIFICATION' | 'VEILLE' | 'PROJET' | 'HORS_SUJET' | null
  tool?: string | null
  refus?: string | null
  porte?: string | null
  prefill?: string | null
  prefill_idu?: string | null
  prefill_plu?: { insee: string; zone: string | null } | null
  prefill_programme?: Record<string, number> | null   // Q11 — pré-remplit la Faisabilité (bâtiments/niveaux/logements)
  // DESTINATIONS-1 (X4.4) — outil destination_zone : la phrase SOURCÉE (servie telle quelle, jamais
  // reformulée) + le préremplissage de l'Étude de zone (porte 'etude-zone').
  destination_phrase?: string | null
  prefill_etude_zone?: { idu?: string | null; commune?: string | null; zone?: string | null; sous_destination: string } | null
  partiel?: boolean
  sources?: string[]
  clarification?: boolean
  degraded?: boolean
  erreur?: boolean          // M102 garde générale /ask — incident serveur (gabarit erreur M117)
  en_construction?: boolean
  web?: boolean                          // M78-ter — réponse issue du web (marquage distinct)
  general?: boolean                      // COPILOTE-REFONTE — voie b : connaissance générale HORS données LABUSE (badgée, mauve IA)
  tenue?: boolean                        // COPILOTE-REFONTE — tenue de position (« t'es sûr ? » → on maintient)
  compris?: string | null               // M102-B2 — récap systématique : « J'ai compris : … » (une phrase)
  conversation_id?: number | null       // §2b — la conversation persistée (reprise)
  contexte_ttl_minutes?: number         // M107 P3 — TTL d'inactivité du fil (servi, jamais recopié)
  // §M78-bis — récap-confirmation avant mission lourde (RECHERCHE/VERIFICATION)
  needs_confirmation?: boolean
  recap?: string
  brief_json?: Record<string, unknown>
  chips?: string[]
  suggestions?: { label: string; ajout: string | null }[]
  clarification_recap?: { question: string; options: string[]; champ: string | null }
  // M107 — le BRIEF EFFECTIF composé du fil (serveur) : le récap et le run repartent de lui,
  // jamais de la réponse nue (« 15 logements » seul perdait la commune du tour d'avant).
  brief_effectif?: string
  // M112 — GUIDAGE vers les surfaces (portes cliquables, jamais « rendez-vous dans X ») :
  carte_filtre?: { commune: string | null; filtres: Record<string, unknown>; libelle: string } | null
  surveillance?: { volet: 'parcelles' | 'secteurs' | 'criteres' } | null
  document?: { kind: string; idu: string; libelle: string } | null
  // M113 — le scénario (chip) qui a servi ce tour + le parcours projet guidé (Phase 3, jamais de
  // création directe : le serveur renvoie le préremplissage compris, le front ouvre le formulaire).
  scenario?: string | null
  projet_form?: { prefill: Record<string, unknown> } | null
  // M116 · D4 — « ouvrir un outil » sans outil précis → proposer la LISTE des outils (voie, pas refus).
  outils_liste?: boolean
  // M118 — le Copilote resserré à 4 missions : ce qui QUITTE le chat (instruire, créer un projet,
  // surveiller, ouvrir un outil, rédiger un courrier, vérifier un prix) reçoit un refus + une VOIE
  // cliquable (NAVIGATION pure vers la surface qui le fait). cible ∈ projets/surveillance/outils/fiche/courriers.
  voie?: { cible: 'projets' | 'surveillance' | 'outils' | 'fiche' | 'courriers'; libelle: string; idu?: string } | null
  // COPILOTE-2 lot 1 — LE CHEMIN FICHE : résumé déterministe d'une parcelle/commune (mêmes ids que la
  // fiche + le Dossier), ou la valeur d'un champ précis (ligne déclarée + id). Le `text` porte déjà la
  // phrase servie ; ces objets structurés sont un appoint (rendu riche possible), jamais recalculés côté client.
  champ_id?: string | null
  resume_fiche?: { idu: string; commune: string; tuiles: { id: string; libelle: string; valeur: string }[]; sections: { id: string; titre: string; verdict: string; ton: string }[]; source: string; millesime: string | null } | null
  resume_commune?: { commune: string; tuiles: { libelle: string; valeur: string }[]; cartes: { titre: string; verdict: string }[]; source: string; millesime: string | null } | null
  prefill_commune?: string | null       // porte 'communes' préremplie de la commune du résumé
  // COPILOTE-2 lot 7 — la ligne de JOURNAL lisible du tour (« J'ai lu la fiche… », « J'ai ouvert
  // Faisabilité… », « J'ai cherché sur le web : 3 sources »). Le payload brut reste en admin.
  journal?: string | null
}
export const copiloteV2Ask = (message: string, opts?: {
  history?: { role: string; content: string }[]; contexte?: Record<string, unknown>
  conversation_id?: number | null; confirme?: boolean; scenario?: string | null }) =>
  j<CopiloteV2Reponse>('/api/copilote-v2/ask', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, ...opts }) })

// M113 · Phase 2 — les missions, servies par le serveur (jamais en dur au front).
export interface CopiloteScenario { cle: string; libelle: string; sub: string; placeholder: string; exemple: string }
// M133 · Accueil Copilote v3 — le hero (titre/sous-titre/placeholder/aide) + les 4 capacités en
// TEXTE (libellé + exemple réel), servis. Plus aucun mode à choisir : le champ passe en premier.
export interface CopiloteCapacite { cle: string; libelle: string; exemple: string }
export interface AccueilCopiloteMeta {
  titre: string; sous_titre: string; placeholder: string; aide: string; capacites: CopiloteCapacite[]
}
export const getAccueilCopilote = () =>
  j<{ scenarios: CopiloteScenario[]; accueil: AccueilCopiloteMeta }>('/api/copilote-v2/scenarios')
    .then((r) => r.accueil)

// §2b — l'historique : missions passées du compte + reprise d'une conversation.
export interface CopiloteMission {
  id: number; titre: string; statut: string; run_id: string | null
  updated_at: string; n_messages: number
}
export interface CopiloteConversation extends CopiloteMission {
  created_at: string
  messages: { role: 'client' | 'copilote'; texte: string; intent: string | null; ts: string }[]
}
// RETOURS-8 (R11) — `retention_jours` accompagne la liste pour le bandeau « conservées N jours ».
export const copiloteV2Missions = () => j<{ missions: CopiloteMission[]; retention_jours: number }>('/api/copilote-v2/missions')
export const copiloteV2Mission = (id: number) => j<CopiloteConversation>(`/api/copilote-v2/missions/${id}`)

// §2e — le héros : phrase (pourquoi cette parcelle gagne, faiblesses comprises) avec verrou
// anti-invention côté serveur (tout nombre ∈ JSON parcelle, sinon gabarit).
export const copiloteV2Heros = (parcelle: Record<string, unknown>, budget_max_eur?: number | null) =>
  j<{ phrase: string; gabarit: boolean }>('/api/copilote-v2/heros', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ parcelle, budget_max_eur }) })

// §2f — feedback 👍/👎 (le 👎 ouvre un champ libre optionnel).

// §4 — veilles : l'écran minimal (liste + suppression). M85 : les notifications produites vivent
// dans le centre unifié (cloche /events), plus dans un store parallèle.
export interface CopiloteVeille { id: number; type: string; commune: string | null }
// DENSIFIER-PLI (PISCINES-2 Lot B) — l'outil « Densifier l'existant » est plié dans le filtre Capacité
// (« Déjà bâti » + « SDP restante », run servi). Le calque `getRenouvGeojson` et la liste `getRenouvListe`
// (précalcul figé `parcel_renouvellement`) sont retirés : plus aucun écran ne les lit. Endpoints backend
// et table conservés en base (non servis à un écran).

// ── Prospection solaire (V1 restitution) — données PVGIS/SARAH3 servies, masque solaire non calculé ──
// A2 — type de propriétaire (PM nommée / particulier non nommé), même règle privacy que l'Assemblage.
export type SolaireProprio =
  | { type: 'personne_morale'; denomination: string; siren: string | null }
  | { type: 'particulier' }
export interface SolaireItem {
  idu: string; commune: string; productible: number | null
  azimut: number | null; azimut_confiance: string | null
  pente: number | null; toit_m2: number | null
  piscine: boolean; piscine_m2: number | null; abf: boolean; proba_occ: number | null
  tier_v2: string | null; etage0: boolean; classement: string; proprio: SolaireProprio
}
export interface ProspectionSolaireResp {
  total: number; n: number; cap: number; tronquee: boolean
  items: SolaireItem[]; source: string; maj: string; bandeau: string
}
export interface SolaireFiltres {
  commune?: string | null; potentielMin?: number; probaOccMin?: number
  piscine?: 'tous' | 'oui' | 'non'; piscineSurfMin?: number; sort?: 'potentiel' | 'toiture' | 'proba' | 'commune'
  // RETOURS-11F3 avenant — aligne le listing piscines sur le filtre confiance du compteur (agg).
  inclureIncertaines?: boolean
}
const solaireQs = (f: SolaireFiltres) => {
  const p: Record<string, string | number> = {}
  if (f.commune) p.commune = f.commune
  if (f.potentielMin) p.potentiel_min = f.potentielMin
  if (f.probaOccMin) p.proba_occ_min = f.probaOccMin
  if (f.piscine && f.piscine !== 'tous') p.piscine = f.piscine
  if (f.piscineSurfMin) p.piscine_surf_min = f.piscineSurfMin
  if (f.inclureIncertaines) p.inclure_incertaines = 'true'
  if (f.sort) p.sort = f.sort
  return qf(p)   // qf ajoute source=SOURCE (convention)
}
export const getProspectionSolaire = (f: SolaireFiltres) =>
  j<ProspectionSolaireResp>(`/modules/prospection-solaire?${solaireQs(f)}`)
// export CSV de démarchage — MÊMES colonnes que l'écran, mentions Sourcé/Estimé en en-tête (lien direct).
export const prospectionSolaireCsvUrl = (f: SolaireFiltres) =>
  `/modules/prospection-solaire?${solaireQs(f)}&fmt=csv`
// SOLAIRE (refonte) — mode Ensoleillement : la FICHE SOLEIL d'une parcelle (barre unique → IDU). Le
// profil mensuel (12 valeurs) + le mois optimal, non servis par la liste. Données gelées, lecture seule.
export interface SolaireFiche {
  ok: boolean; idu: string; message?: string; commune?: string
  productible?: number | null; prod_mensuel?: number[] | null; mois_optimal?: number | null
  azimut?: number | null; azimut_confiance?: string | null; pente?: number | null
  lon?: number | null; lat?: number | null   // RETOURS-12 O7 — centroïde parcelle (photo ortho du toit)
  toit_m2?: number | null; piscine?: boolean; piscine_m2?: number | null; abf?: boolean
  ombrage?: boolean; proba_occ?: number | null; classement?: string; millesime?: string
  // A6 — dimensionnement servi par le back (plus de calcul au front) : kWc = toit × kwc_par_m2 ;
  // production annuelle = kWc × productible. A1 — inclinaison = paramètre réel du calcul PVGIS.
  kwc?: number | null; prod_annuel?: number | null; kwc_par_m2?: number; inclinaison_deg?: number
  // RETOURS-13 R31 / RETOURS-14 S11 — nature de la toiture (Dérivé, LiDAR HD IGN), servie
  // seulement au-dessus du seuil de confiance ; « non déterminée (LiDAR) » sinon.
  toiture?: { verdict: string; libelle: string; libelle_court: string
              pente_mediane_deg: number | null; pans_orientation_deg: number[]
              confiance: number; seuil: number; statut: string; methode: string } | null
  // GEOPF-3 — filtre d'exclusion EnR au sol (loi APER) : parcelle dans une zone exclue (Parc national,
  // réserve naturelle) → projet AU SOL exclu, TOITURE possible. Zone nommée si exclue.
  enr_au_sol_exclu?: boolean; enr_sol_exclu_zone?: string | null
}
export const getSolaireFiche = (idu: string) =>
  j<SolaireFiche>(`/modules/prospection-solaire/parcelle/${idu}`)
// SOLAIRE (refonte) — mode Piscines : AGRÉGATS de la détection (île + par commune). Décomptes, jamais recalcul.
export interface PiscinesAgregat {
  total: number; communes: { commune: string; n: number }[]; source: string; maj: string
  // RETOURS-11F M12 — bandes de confiance + corrections « pas une piscine »
  confiance?: { haute: number; incertaines: number; seuil_haute: number; inclure_incertaines: boolean }
  corrigees?: number
}
export const getPiscinesAgregat = (commune?: string | null, surfMin = 0, inclureIncertaines = false) =>
  j<PiscinesAgregat>(`/modules/prospection-piscines?${qf({ ...(commune ? { commune } : {}), ...(surfMin ? { piscine_surf_min: surfMin } : {}), ...(inclureIncertaines ? { inclure_incertaines: 1 } : {}) })}`)
// LOT8b — TOUTES les piscines (île/commune) en points GeoJSON pour la carte (pas le listing capé à 500).
export const getPiscinesPoints = (commune?: string | null, surfMin = 0, inclureIncertaines = false) =>
  j<{ type: 'FeatureCollection'; features: unknown[] }>(`/modules/prospection-piscines/points?${qf({ ...(commune ? { commune } : {}), ...(surfMin ? { piscine_surf_min: surfMin } : {}), ...(inclureIncertaines ? { inclure_incertaines: 1 } : {}) })}`)
// RETOURS-11F M12 — « pas une piscine » : signal humain qui retire la parcelle du service (compteur, carte).
export const postPasUnePiscine = (idu: string, motif?: string) =>
  j<{ ok: boolean; idu: string; corrigees_total: number }>(`/modules/prospection-piscines/pas-une-piscine`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ idu, motif: motif ?? null }),
  })
// PISCINES-2 (A.3) — LISTE pisciniste : source unique `piscines` (idu · commune · surface bassin ·
// source · statut · propriétaire PM nommée / particulier). Aucune colonne « potentiel solaire ».
export interface PiscineItem {
  idu: string; commune: string; surface_m2: number | null
  source: 'flair' | 'cosia' | 'flair+cosia'; statut: 'servie' | 'a_confirmer' | 'ecartee'
  proprio: { type: 'personne_morale'; denomination: string; siren: string | null } | { type: 'particulier' }
}
export interface PiscinesListe { total: number; n: number; cap?: number; tronquee?: boolean; items: PiscineItem[]; maj: string; source: string }
export interface PiscinesFiltres { commune?: string | null; statut?: 'servie' | 'tous'; surfMin?: number; proprio?: 'tous' | 'pm' | 'pp' }
export const getPiscinesListe = (f: PiscinesFiltres) =>
  j<PiscinesListe>(`/modules/prospection-piscines/liste?${qf({
    ...(f.commune ? { commune: f.commune } : {}), ...(f.statut === 'tous' ? { statut: 'tous' } : {}),
    ...(f.surfMin ? { surf_min: f.surfMin } : {}), ...(f.proprio && f.proprio !== 'tous' ? { proprio: f.proprio } : {}) })}`)
// ── OUTILS-MUSCLER-1 Lot A — outil « Successions » (radar patrimonial Score V v1.3). Le signal est
// une succession PROBABLE (dirigeant ≥ 70 ans / SCI dormante), JAMAIS « en succession » (A0) ; le
// propriétaire est une PM nommée par construction (SIREN confirmé exigé par le critère).
export interface SuccessionItem {
  idu: string; commune: string; surface_m2: number | null; zone: string | null
  sdp_residuelle_m2: number | null   // Estimé — moteur de la fiche (p_model_ext_dataset)
  dirigeant_age: number | null; sci_dormante: boolean
  // DONNEES-1 lot 2.3 — dernier dépôt de comptes BODACC du propriétaire PM (null = aucun publié).
  depot_comptes: { annee: number | null; depuis_ans: number | null; muet?: boolean } | null
  proprio: SolaireProprio
}
export interface SuccessionsResp {
  total: number; n: number; items: SuccessionItem[]
  maj: string | null       // date du calcul Score V — le millésime du signal
  rne_sync: string | null  // date amont RNE (âges dirigeants)
  source: string; avertissement: string
}
export const SUCCESSIONS_PAGE = 200
export const getSuccessions = (communeNom?: string | null, sdpMin = 0, offset = 0) =>
  j<SuccessionsResp>(`/modules/successions?limit=${SUCCESSIONS_PAGE}${communeNom ? `&commune=${encodeURIComponent(communeNom)}` : ''}${sdpMin ? `&sdp_min=${sdpMin}` : ''}${offset ? `&offset=${offset}` : ''}`)

// OUTILS-MUSCLER-1 Lot B (B2) — voisines contiguës (1ᵉʳ anneau cadastral) proposées par l'Assemblage.
export interface VoisineItem {
  idu: string; surface_m2: number | null; zone: string | null
  sdp_residuelle_m2: number | null   // Estimé — même grandeur que la fiche
  meme_proprietaire: boolean         // égalité de SIREN avec la parcelle de départ (jamais par nom)
  proprio: SolaireProprio
}
export interface VoisinesResp {
  idu: string; n: number; n_meme_proprietaire: number
  depart_pm: boolean   // départ particulier → « même propriétaire » indécidable (dit à l'écran)
  items: VoisineItem[]
}
export const getAssemblageVoisines = (idu: string) =>
  j<VoisinesResp>(`/moteurs/assemblage/voisines?idu=${encodeURIComponent(idu)}`)

// ── OUTILS-MUSCLER-3 — outil « Blocs fonciers ». Les assiettes CONTIGUËS d'un même propriétaire
// personne morale (SIREN), sur toute l'île, servies depuis `parcel_blocs`. Le propriétaire est
// TOUJOURS une PM nommée (particuliers hors périmètre). SDP résiduelle agrégée = Estimé.
export interface BlocItem {
  bloc_id: number; siren: string; denomination: string | null
  n_parcelles: number; surface_totale_m2: number; communes: string[]
  sdp_residuelle_m2: number; sdp_couverture: number   // couverture = nb parcelles au résiduel connu
  zonages: string[]
  is_public: boolean        // propriétaire de droit public (classify_dgfip) — écarté par défaut
  idu_repr: string | null   // IDU représentatif (min) — résout le propriétaire pour le pont Courrier
}
export interface BlocsResp {
  total: number; n: number; items: BlocItem[]
  n_publics: number          // blocs publics écartés (mêmes filtres) — dit au bandeau
  inclure_publics: boolean
  maj: string | null; millesime: string | number | null
  source: string; avertissement: string
}
export interface BlocMembre {
  idu: string; surface_m2: number | null; commune: string | null
  zone: string | null; sdp_residuelle_m2: number | null
}
export interface BlocDetail extends BlocItem { membres: BlocMembre[] }
export const BLOCS_PAGE = 200
export const getBlocs = (communeNom?: string | null, surfaceMin = 0, sdpMin = 0, nMin = 2,
                         inclurePublics = false, offset = 0) =>
  j<BlocsResp>(`/modules/blocs?limit=${BLOCS_PAGE}&n_min=${nMin}`
    + `${communeNom ? `&commune=${encodeURIComponent(communeNom)}` : ''}`
    + `${surfaceMin ? `&surface_min=${surfaceMin}` : ''}${sdpMin ? `&sdp_min=${sdpMin}` : ''}`
    + `${inclurePublics ? '&inclure_publics=true' : ''}${offset ? `&offset=${offset}` : ''}`)
export const getBlocDetail = (blocId: number) => j<BlocDetail>(`/modules/blocs/${blocId}`)

// ── OUTILS-MUSCLER-2 — histoire de la parcelle (frise des faits sous le comparateur d'orthos).
// Des FAITS datés, jamais un récit (B2) ; chaque fait porte sa source et la MAILLE RÉELLE de sa
// date : 'jour' (ISO), 'annee' (« 2024 », jamais « 01/01/2024 »), 'millesime' (écart constaté
// entre deux situations au 1ᵉʳ janvier — propriétaire PM, jamais une date de vente).
export interface HistoireFait {
  famille: 'vente' | 'permis' | 'proprietaire' | 'decoupe'
  date: string | null                  // ISO jour, ou « YYYY » (maille annee), ou null (millesime)
  maille: 'jour' | 'annee' | 'millesime'
  annee: number | null                 // position sur la frise
  libelle: string
  chiffres: { prix_eur?: number | null; surface_bati_m2?: number | null; surface_terrain_m2?: number | null
    nb_logements?: number | null; surf_hab_m2?: number | null; statut: string }
  source: string
  // famille permis — pont « Permis sur ce permis »
  permit_id?: string; type_permis?: string
  // famille vente — E2 : la mutation portait sur la parcelle MÈRE (date antérieure à la découpe DFI)
  sur_parcelle_mere?: boolean
  // famille proprietaire — PM nommées (jamais un particulier), pont Scan patrimoine
  de_millesime?: number; a_millesime?: number
  avant?: { siren: string | null; denomination: string | null }
  apres?: { siren: string | null; denomination: string | null }
  non_identifiable?: boolean          // E3 : au moins un pseudo-siren « U… » → aucun changement affirmé
  // famille decoupe — liste bornée au cap (total toujours dit)
  parcelles_liees?: string[]; n_parcelles_liees?: number
}
export interface HistoireResp {
  idu: string; n: number; faits: HistoireFait[]
  cap_filiation: number
  sources: { cle: string; nom: string; maj: string | null }[]   // bandeau C6 (millésimes servis)
}
export const getHistoire = (idu: string) =>
  j<HistoireResp>(`/moteurs/histoire/${encodeURIComponent(idu)}`)

// REMONTER-TEMPS-2 Lot B — contour de la/les parcelle(s) MÈRE d'origine (cadastre d'époque),
// quand elle est captée dans cadastre_historique. `features` vide = pas de parcellaire d'époque.
export interface ParcellaireEpoque {
  idu: string; type: 'FeatureCollection'
  features: { type: 'Feature'; properties: { idu_mere: string; millesime: string }; geometry: unknown }[]
  millesimes: string[]; millesime: string | null; source: string
}
export const getParcellaireEpoque = (idu: string) =>
  j<ParcellaireEpoque>(`/moteurs/parcellaire-epoque/${encodeURIComponent(idu)}`)

export const pdfUrl = (idu: string, calc?: { cout_construction_m2: number; marge_frais_pct: number; prix_demande_eur: number | null } | null) => {
  const p = new URLSearchParams({ source: SOURCE })
  if (calc) {
    p.set('cout_construction_m2', String(calc.cout_construction_m2))
    p.set('marge_frais_pct', String(calc.marge_frais_pct))
    if (calc.prix_demande_eur != null) p.set('prix_demande_eur', String(calc.prix_demande_eur))
  }
  return `/parcels/${idu}/export.pdf?${p.toString()}`
}

// M54-EXPO — exports « document » orphelins branchés (URLs directes, ouvertes en onglet/téléchargées).
// M93 — one-pager retiré (onePagerUrl supprimé).
export const preDossierUrl = (idu: string) => `/pre-dossier/${idu}.zip`

// M54-EXPO-2 Volet C — statuts servis là où les boutons existent (dossier : dispo+quota ; courrier).
export interface DossierStatut { disponible: boolean; raison: string | null; plan: string; illimite: boolean; quota_mois: number | null; utilises_mois: number; restants: number | null }
export const getDossierStatut = () => j<DossierStatut>('/dossier/statut')
export interface CourrierStatut { disponible: boolean; provider: string; tarif: unknown; raison: string | null
  // OUTILS-FIX-4 D2 — plafond d'envoi quotidien (celui qui déclenche le 422) + ce qui reste.
  plafond_jour?: number; envoyes_jour?: number; reste_jour?: number
  // OUTILS-S2 Lot B — tarif unitaire TTC (prix client, impression+affranchissement+suivi), affiché à l'étape 3.
  tarif_unitaire_eur?: number }
// OUTILS-FIX-4 D1/D2 — état du service + plafond du jour, lus à l'ouverture de l'outil Courrier.
export const getCourrierStatut = () => j<CourrierStatut>('/courrier/statut')
export interface CourrierEnvoi { id: number; ts: string; idu: string | null; adresse: string | null; statut: string; provider: string; prix_eur: number | null; modele: string | null }

// M54-EXPO-2 A7 — shortlist : « sujets à traiter aujourd'hui » du run servi (top parcelles).
export interface ShortlistSujet { idu: string; commune?: string; surface_m2?: number; status?: string | null; tier_v2?: string | null; rang?: number | null; motif?: string | null }

// M54-EXPO-3 — veilles géographiques (zones dessinées + alertes DVF en zone). Le kind permis a été
// retiré (dédup cloche, EXPO-2) : ce canal ne porte plus que dvf_in_zone.
export interface WatchZone { id: number; name: string; commune: string; created_at: string | null; area_m2: number | null; n_alertes: number }
const _comm = () => (commune() ? `commune=${encodeURIComponent(commune()!)}` : '')
export const getWatchZones = () => j<WatchZone[]>(`/watch-zones${_comm() ? `?${_comm()}` : ''}`)
export const createWatchZone = (name: string, geometry: { type: 'Polygon'; coordinates: number[][][] }) =>
  j<{ zone: { id: number; name: string; commune: string }; detected: { dvf_in_zone: number; total: number } }>(
    '/watch-zones', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, geometry, ...(commune() ? { commune: commune() } : {}) }) })
export const renameWatchZone = (id: number, name: string) =>
  j<{ ok: boolean; name: string }>(`/watch-zones/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) })
export const deleteWatchZone = (id: number) => j<{ ok: boolean }>(`/watch-zones/${id}`, { method: 'DELETE' })
export interface Alerte { id: number; kind: string; label: string; payload: Record<string, unknown>; acknowledged: boolean; detected_at: string; zone_name: string | null; parcel_idu: string | null }
export const getAlertes = (onlyNew = false) => j<Alerte[]>(`/alertes?only_new=${onlyNew}${_comm() ? `&${_comm()}` : ''}`)
export const refreshAlertes = () => j<{ dvf_in_zone: number; total: number }>(`/alertes/refresh${_comm() ? `?${_comm()}` : ''}`, { method: 'POST' })
export const ackAlerte = (id?: number) =>
  j<{ ok: boolean; acknowledged: number }>('/alertes/ack', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(id != null ? { id } : (commune() ? { commune: commune() } : {})) })

// M54-EXPO-3 A8 — comparateur de parcelles (2 à 3 côte à côte).
export interface CompareRow {
  idu: string; commune?: string; surface_m2?: number | null
  // verdict SERVI (source _q_v2_fiche) — la puce dérive de tier_v2 + etage0 ; fraction + raison M135
  status?: string | null; tier_v2?: string | null; etage0?: boolean | null; rang_v2?: number | null
  label?: string | null; fraction?: string | null; raison?: string | null
  zone?: string | null; constructible?: boolean | null
  sdp_max_m2?: number | null; taux_emprise_pct?: number | null; sdp_residuelle_m2?: number | null; sous_densite?: boolean | null
  // COMPARER-2 §1 — CES PLU réelle (validée dans plu_destinations) ; null = zone sans CES → « non réglementée »
  emprise_ces_pct?: number | null; emprise_ces_source?: string | null
  charge_fonciere_m2?: number | null
  // COMPARER-2 §4 / SOURCES-FIX-2 lot B — Classement LABUSE du RUN SERVI (même source que l'Analyse et la fiche) : bande + Signal
  bande?: string | null; signal_niveau?: string | null
  terrain_zone_eur_m2?: number | null; contrainte_majeure?: string | null   // M82
  n_contraintes?: number; contraintes?: string[]
  // RETOURS-11F M13 (O9) — colonnes ajoutées, toutes de la fiche servie / du bilan servi.
  proprietaire?: string | null; bati_existant_pct?: number | null
  gabarit_niveaux_max?: number | null; logements_possibles?: number | null; logements_min?: number | null
  acces_reseaux?: string | null; assainissement?: string | null
  prix_secteur_bati_m2?: number | null
}
export const getCompare = (idus: string[]) =>
  j<{ count: number; parcels: CompareRow[] }>(`/compare?idus=${encodeURIComponent(idus.join(','))}`)

// M54-EXPO-2 A6 — marque blanche (logo + libellés) relue par GET, uploadée en body brut.
export interface Marque { raison_sociale: string; coordonnees: string; mention: string; has_logo: boolean; logo_data_uri?: string }
export const getMarque = () => j<Marque>('/moi/marque')
export const postLogo = (file: Blob) => j<{ ok: boolean; mime: string; octets: number }>(
  '/moi/logo', { method: 'POST', headers: { 'Content-Type': file.type || 'application/octet-stream' }, body: file })
export const deleteLogo = () => j<{ ok: boolean }>('/moi/logo', { method: 'DELETE' })
export const postMarque = (m: { raison_sociale: string; coordonnees: string; mention: string }) =>
  j<{ ok: boolean }>('/moi/marque', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(m) })

// M54-EXPO-2 — synthèse IA de la fiche (GET /parcels/{idu}/explain). Validée (available) OU repli
// stub déterministe (available=false, stub=true) — la couche 2 M-T garantit l'un ou l'autre.
export interface ExplainResult {
  available: boolean; explanation?: string; stub?: boolean; reason?: string
  message?: string; rules_summary?: string | string[]; model?: string
}
export const getExplain = (idu: string) => j<ExplainResult>(`/parcels/${idu}/explain`)

// M54-EXPO — retour promoteur par parcelle (POST /feedback : verdict + commentaire libre).
export type FeedbackVerdict = 'good_lead' | 'not_interested' | 'false_positive'
export const postFeedback = (idu: string, verdict: FeedbackVerdict, comment?: string) =>
  j<{ ok: boolean; id: number }>('/feedback', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ idu, verdict, ...(comment ? { comment } : {}) }),
  })

// ── Pipeline (CRM kanban) ──
export const getPipelineMeta = () => j<PipelineMeta>('/pipeline/meta')
export const getPipeline = () => j<PipelineEntry[]>('/pipeline')
export const getPipelineForParcel = (idu: string) =>
  j<{ in_pipeline: boolean; entry: PipelineEntry | null }>(`/pipeline/parcel/${idu}`)
// CONNEXIONS-2 Lot 3 (KO-8) — la colonne CRM choisie est transmise (défaut : 1re colonne côté back).
export const addToPipeline = (idu: string, status?: string) =>
  j<{ ok: boolean; already: boolean; entry: PipelineEntry }>('/pipeline', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(status ? { idu, status } : { idu }),
  })

// ── M9 lot 3 — Signaler une erreur (file de QA humaine, aucune action automatique) ──
export const postSignalement = (body: { idu: string; type_erreur: string; champ?: string; commentaire?: string }) =>
  j<{ ok: boolean; id: number; statut: string }>('/signalements', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  })
export const patchPipeline = (id: number, body: Record<string, unknown>) =>
  j<{ ok: boolean; entry: PipelineEntry }>(`/pipeline/${id}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  })
// M137 — plus de suppression DURE : DELETE archive (réversible). + restauration + liste des archivées.
export const archivePipeline = (id: number) => j<{ ok: boolean; archived: boolean }>(`/pipeline/${id}`, { method: 'DELETE' })
export const restorePipeline = (id: number) => j<{ ok: boolean; entry: PipelineEntry }>(`/pipeline/${id}/restore`, { method: 'POST' })
export const getArchivedPipeline = () => j<PipelineEntry[]>('/pipeline/archived')

// ── M12 LOT H — colonnes CRM personnalisables (par tenant) ──
const _jsonInit = (method: string, body?: unknown): RequestInit => ({
  method, headers: { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body),
})
export const createCrmColumn = (label: string, tone?: string | null) =>
  j<{ ok: boolean; columns: CrmColumn[] }>('/pipeline/columns', _jsonInit('POST', { label, tone: tone ?? null }))
export const renameCrmColumn = (id: number, label: string, tone?: string | null) =>
  j<{ ok: boolean; columns: CrmColumn[] }>(`/pipeline/columns/${id}`, _jsonInit('PATCH', { label, tone: tone ?? null }))
export const reorderCrmColumns = (order: number[]) =>
  j<{ ok: boolean; columns: CrmColumn[] }>('/pipeline/columns/reorder', _jsonInit('POST', { order }))
export const deleteCrmColumn = (id: number, moveTo?: number | null) =>
  j<{ ok: boolean; moved: number; columns: CrmColumn[] }>(`/pipeline/columns/${id}`, _jsonInit('DELETE', { move_to: moveTo ?? null }))
export const resetCrmColumns = () =>
  j<{ ok: boolean; columns: CrmColumn[]; note: string }>('/pipeline/columns/reset', _jsonInit('POST'))

// ── Sources ──
export const getSources = () => j<SourceInfo[]>('/sources')
// RETOURS-9 (Q11.5) — les chiffres de couverture client (parcelles · communes · DVF · Radar · dernière analyse).
export interface SourcesCouverture {
  parcelles: number | null; communes: number | null; communes_total: number
  // RETOURS-14 P6 — parcelles EXPLORABLES au filtre (surface ≥ 2 m², MIN_DISPLAY_SURFACE_M2) : le
  // filtre masque les micro-parcelles « sliver » < 2 m², d'où l'écart (légitime) avec `parcelles`
  // (total ingéré). La page Sources réconcilie les deux nombres.
  parcelles_filtrables: number | null
  dvf_transactions: number | null; radar_annonces: number | null
  analyse_label: string | null; analyse_date: string | null
}
export const getSourcesCouverture = () => j<SourcesCouverture>('/sources/couverture')
// COUCHES-REGISTRE-2 lot 3 — le sens inverse : par nom de source, les couches carte qu'elle alimente.
export type SourceCouche = { kind: string; nom: string }
export const getSourcesCouches = () => j<Record<string, SourceCouche[]>>('/sources/couches')
// CIRCUIT-SOURCES-1 lot 3 · DASHBOARD-4b lot 1 — par nom de source, SIX blocs distincts (le 7e,
// couches carte, = getSourcesCouches). Chaque ligne porte `rid` (id du robinet-élément) pour ouvrir
// son détail (sens inverse, lot 2). `rid` peut être null pour une section déclarée sans robinet dédié.
export type SourceRattLigne = { ligne: string; cible: string; rid: string | null }
export type SourceRattachements = {
  fiche_parcelle: SourceRattLigne[]
  fiche_commune: SourceRattLigne[]
  outils: SourceRattLigne[]
  documents: SourceRattLigne[]
  copilote: SourceRattLigne[]
  radar: SourceRattLigne[]
}
export const getSourcesRattachements = () => j<Record<string, SourceRattachements>>('/sources/rattachements')
// DASHBOARD-4b lot 2 — sens inverse : chaque élément (couche/section/carte commune/outil/document/
// copilote/radar) avec la liste de ses sources (réservoirs), pour la recherche de la page Données.
export type SourceElement = { id: string; nom: string; categorie: string; sources: string[] }
export const getSourcesParElement = () => j<{ elements: SourceElement[] }>('/sources/par-element')
// PLU-CALIBRAGE-1 lot 2 — par nom de source (réservoir GPU), ses lecteurs calibrage : un par
// commune dotée d'un PLU, avec l'état repris de destinations.etat_commune.
export type SourceCalibrage = {
  insee: string; commune: string
  etat: 'calibree' | 'a_relire' | 'non_calibree'
  etat_label: string; a_reverifier: boolean
  millesime: string | null; document_gpu: string | null; document_gpu_servi?: string | null
  lu_le: string | null; note?: string | null; n_zones: number; n_regles: number
}
export const getSourcesCalibrages = () => j<Record<string, SourceCalibrage[]>>('/sources/calibrages')

// ── Modules outils (Vague 1) ──
// M129-C (Vic 19/08/2026) : modDivision retiré — division hors produit (endpoint dormant).
export const modPatrimoineSearch = (q: string) => j<{ siren: string; nom: string; n: number }[]>(`/modules/patrimoine/search?q=${encodeURIComponent(q)}`)
// RETOURS-11 (T4) — liste PAGINÉE (limit/offset) : l'endpoint sert déjà des pages (géom calculée pour la
// page seulement) ; le front tranche par 200 via « Voir plus » (jamais de dump). Défauts = 1re page 200.
export const modPatrimoine = (siren: string, limit = 200, offset = 0) =>
  j<Record<string, unknown>>(`/modules/patrimoine?siren=${siren}&limit=${limit}&offset=${offset}`)
// GB-017/018 — export CSV du portefeuille d'une PM (raison sociale entière ; notice si plafond serveur).
export const modPatrimoineCsvUrl = (siren: string) => `/modules/patrimoine?siren=${encodeURIComponent(siren)}&fmt=csv`
const cq = () => (commune() ? `commune=${encodeURIComponent(commune()!)}` : '')
// RETOURS-17 W2 — `etat` (recent|acheve|autre) affine la fenêtre par ÉTAT DE CYCLE ; le dormant garde
// son endpoint /promesses (jointure parcelle+run). Sans `etat`, comportement d'avant (fenêtre `months`).
export const modPermis = (months: number, nature?: string | null, limit = 300, offset = 0, etat?: string | null) =>
  j<Record<string, unknown>>(`/modules/permis?${cq()}&months=${months}${nature ? `&nature=${nature}` : ''}${etat ? `&etat=${etat}` : ''}&limit=${limit}&offset=${offset}`)
// RETOURS-16 V4 — compteur seul (ni lignes ni carte) : le chip « Tous » dit le total EN BASE.
export const modPermisCount = (months: number, etat?: string | null) =>
  j<{ total: number; geocodes?: number; donnees_jusqu_au?: string }>(`/modules/permis?${cq()}&months=${months}${etat ? `&etat=${etat}` : ''}&count_only=true`)
export const modPermisFiche = (permitId: string) =>
  j<Record<string, unknown>>(`/modules/permis/${encodeURIComponent(permitId)}`)
export const modParcellePermis = (idu: string) =>
  j<Record<string, unknown>>(`/modules/parcelle-permis?idu=${encodeURIComponent(idu)}`)
// 1re page légère (1000), le reste en « voir plus » ; le total (COUNT ~4 s) arrive en PARALLÈLE.
export const modPromesses = (months: number, limit = 1000, offset = 0) =>
  j<Record<string, unknown>>(`/modules/promesses?${cq()}&months=${months}&limit=${limit}&offset=${offset}`)
export const modPromessesCount = (months: number) =>
  j<{ total: number }>(`/modules/promesses?${cq()}&months=${months}&count_only=true`)
export const modVelocite = (nature?: string | null) =>
  j<{ communes: Record<string, unknown>[]; [k: string]: unknown }>(`/modules/velocite${nature ? `?nature=${nature}` : ''}`)
// M137-Z — Rareté (horizon ZAN + stock foncier par commune), pour la fiche commune de l'outil Communes.
export const motRarete = () =>
  j<{ communes: Record<string, unknown>[]; caveat: string; [k: string]: unknown }>('/pipeline-rarete')
// M15-G — plus d'héritage du filtre commune global (cq) : le périmètre est choisi DANS l'outil.
export const modBailleur = (commune?: string | null) =>
  j<Record<string, unknown>>(`/modules/bailleur${commune ? `?commune=${encodeURIComponent(commune)}` : ''}`)
export const modFantome = (limit = 300, offset = 0, commune?: string | null) =>
  j<Record<string, unknown>>(`/modules/fantome?${commune ? `commune=${encodeURIComponent(commune)}&` : ''}limit=${limit}&offset=${offset}`)
export const getOrthoEquipements = (idu: string) => j<Record<string, unknown>>(`/ortho/equipements/${idu}`)
// M82 (option B) : le courrier généré est téléchargeable en PDF — le client l'envoie lui-même.
// CONNEXIONS-2 Lot 9.4 — commentaire périmé corrigé : « /courrier/demande » N'EST PAS retiré ; c'est
// le workflow COURRIER-SERVICE (postCourrierDemande, ci-dessous), bien wiré. Le PDF est une option EN PLUS.
export const courrierPdf = async (idu: string | null, motif: string, texte: string): Promise<void> => {
  const r = await fetch('/courrier/pdf', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ idu, motif, texte }) })
  if (!r.ok) throw new ApiError('/courrier/pdf', r.status)
  const url = URL.createObjectURL(await r.blob())
  const a = document.createElement('a')
  a.href = url; a.download = `courrier-${idu ?? 'parcelle'}.pdf`
  document.body.appendChild(a); a.click()
  // §1c — NE PAS révoquer l'object URL de façon synchrone après click() : selon le navigateur, le
  // téléchargement n'a pas encore lu le blob → « échoue » par intermittence. On diffère le nettoyage.
  setTimeout(() => { a.remove(); URL.revokeObjectURL(url) }, 4000)
}
// COURRIER-SERVICE (refonte 13 outils) — le client DEMANDE l'envoi ; LABUSE est notifié (cloche +
// Brevo), rappelle, confirme le tarif, fait avancer le statut. Aucun prix affiché côté client.
export interface CourrierDemande {
  id: number; ts: string; n: number; communes: string | null; modele: string | null
  statut: string; updated_at: string
  rang_compte?: number   // RECETTE-1 R13 — rang PROPRE AU COMPTE (affiché au client, pas le id PK global)
  // CONNEXIONS-2 Lot 4 (KO-6) — rattachement à la piste/projet d'origine
  pipeline_entry_id?: number | null; projet_id?: number | null
}
// CONNEXIONS-2 Lot 4 — la demande peut naître d'une piste (pipeline_entry_id) / d'un projet (sans ressaisie).
export const postCourrierDemande = (parcelles: string[], corps: string, modele: string | null, communes: string | null,
                                    rattach?: { pipeline_entry_id?: number | null; projet_id?: number | null }) =>
  j<{ ok: boolean; id: number; rang_compte?: number; ts: string; n: number; communes: string | null; statut: string }>('/courrier/demande', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ parcelles, corps, modele, communes, ...(rattach ?? {}) }) })
export const getCourrierDemandes = () => j<{ demandes: CourrierDemande[] }>('/courrier/demandes')
// COURRIER-2 Lot 2 — adressage (écran avant dépôt) : destinataire + adresse d'envoi + bien + motif de blocage.
export interface CourrierResolution {
  idu: string
  type: 'occupant' | 'siege' | null
  destinataire: string | null
  adresse_envoi: string | null
  mention: string | null
  bloque: boolean
  motif: string | null
  // OUTILS-S2 Lot B — code machine du blocage : 'nu'|'sans_adresse'|'sans_canal'|'inconnue' (aucun
  // occupant joignable → l'ajout est refusé, on renvoie au Courrier SPF) ; 'opposition' (traité au dépôt).
  code: 'nu' | 'sans_adresse' | 'sans_canal' | 'inconnue' | 'opposition' | null
  bien: { reference: string; adresse: string | null; commune: string | null }
}
export const postCourrierAdressage = (idus: string[]) =>
  j<{ resolutions: CourrierResolution[] }>('/courrier/adressage', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ idus }) })
// COURRIER-2 Lot 3 — aperçu COMPOSÉ (recto + verso), même source que le PDF (« ne pas reformuler »).
export interface CourrierApercu {
  recto: string; verso: string[]; ouverture: string; reference: string
  destinataire: string | null; adresse_envoi: string | null; bloque: boolean; motif: string | null
}
export const postCourrierComposer = (idu: string) =>
  j<CourrierApercu>('/courrier/composer', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ idu }) })
// CONNEXIONS-2 Lot 4 (KO-6) — la cliente saisit le RETOUR de sa demande (répondu / sans réponse).
export const postCourrierClientStatut = (id: number, statut: 'repondu' | 'sans_reponse') =>
  j<{ ok: boolean; statut: string }>(`/courrier/demandes/${id}/statut`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ statut }) })
// OUTILS-FIX-4 C1 — les seuils qui font le score, servis pour le tiroir « Comment ce score est calculé ».
// PIEGES-RISQUES-2 (Lot A) — « un lot » = union par contrainte, MÊME source/libellés/date que le
// mode « une parcelle ». Plus de score de risque ni de checklist cascade : l'outil ne lit plus l'ancien run.
export interface DiligenceContrainte {
  categorie: string; effet: string; source: string; date: string | null
  n_parcelles: number; parcelles: string[]
}
export interface DiligenceParcelle { idu: string; commune: string; surface_m2: number; n_contraintes: number }
export const modDueDiligence = (refs: string) =>
  j<{ n_demandes: number; n_trouvees: number; n_parcelles: number; parcelles: DiligenceParcelle[]
      contraintes: DiligenceContrainte[]; erreurs: string[]; non_couvert: string[] }>('/modules/duediligence', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refs }) })

// ── Copilote IA (Vague 2) — jamais d'accès base, filtres validés par schéma côté API ──
// M49 (Lot A, arbitrage Vic) : helpers iaSynthese/iaPourquoi RETIRÉS — 0 importeur (code mort front).
// Les routes serveur /ia/synthese, /ia/pourquoi restent listées « douteuses » (routes_inventaire.csv).

// M11 Surface A — barre de fiche : question libre → réponse SOURCÉE (grounding du socle IA)
export type Provenance = 'SOURCE' | 'ESTIME' | 'ABSENT'
export type AskResponse = {
  texte: string; sources: string[]; deeplinks?: Record<string, string>
  provenance?: Record<string, Provenance>; model?: string
  rejected?: boolean; cached?: boolean; absent?: boolean; quota_atteint?: boolean; degraded?: boolean
}
export const askParcel = (idu: string, question: string) =>
  j<AskResponse>(`/parcels/${idu}/ask`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question }) })

// ── Événements (Vague 3 : M11-M14) ──
export interface LabuseEvent { id: number; date: string; ts?: string | null; kind: string; idu: string | null; titre: string; detail: string | null; demo: boolean; lu: boolean; statut: string | null; source?: string | null; lien?: string | null; commune?: string | null }
// RETOURS-11 A5 (T4) — limite paginable (200 par défaut) : la cloche affiche 200, « Voir plus »
// remonte la limite. Le back paginant déjà (limit ≤ 1000), on grandit la fenêtre côté client.
export const getEvents = (limit = 200) => j<{ unread: number; items: LabuseEvent[] }>(`/events?limit=${limit}`)
// M87 P5 — libellés de l'en-tête de la cloche, dérivés du registre (jamais écrits à la main).
export const getEnteteCloche = () => j<{ libelles: string[] }>('/events/entete')
// M85 Phase 3 — le brief du matin (déterministe : veilles déclenchées + « depuis hier sur vos secteurs »).
export interface BriefGroupe { commune: string; n: number; ts_max: string | null; idus: string[] | null; sources: string[] | null }
export interface BriefMatin {
  genere_le: string
  veilles: { titre: string; detail: string | null; ts: string; lien: string | null; source: string | null }[]
  secteurs: { communes: string[]; permis_depuis_hier: number; derniere_donnee_permis: string | null; donnee_perimee: boolean }
  n: number                 // M87 P6 — compteur de la barre (0 → « rien de neuf depuis hier »)
  groupes: BriefGroupe[]    // M87 P6 — une ligne par commune pour le panneau latéral
  vide: boolean
  cause_vide: string | null
}
export const getBrief = () => j<BriefMatin>('/events/brief')
// M85-B — les parcelles suivies + date du dernier changement (null = jamais bougé).
export interface SuiviItem { idu: string; depuis: string; commune: string | null; dernier_changement: string | null
  // RADAR-2 (Lot 4) — enrichissements de l'écran Veille · le foncier.
  secteur?: string | null; dernier_evenement?: string | null; nouveau?: boolean }
export const getSuivis = () => j<{ suivis: SuiviItem[]; plafond: number }>('/events/suivis')
// M85 / M85-B — préférences par type (registre) et par canal (cloche / e-mail). `verrou` = non
// désactivable (maintenance : e-mail toujours actif, conséquences réelles).
// RETOURS-11F3 A5 — 3 canaux : cloche · brief (du matin) · e-mail. `brief_na` = brief non applicable
// (chaînes 3, envoi immédiat — la case est grisée). `verrou` = e-mail non désactivable (maintenance).
export interface NotifPref { key: string; label: string; cloche: boolean; email: boolean; brief: boolean; brief_na?: boolean; verrou?: boolean }
// VEILLE-FIX-2 (Lot C) — la FRÉQUENCE des mails, réglable par compte (grille config/veille.yaml).
export const getNotifPrefs = () => j<{ types: NotifPref[]; frequence: string; frequences: string[] }>('/events/prefs')
export const patchNotifPref = (p: { pref_type: string; cloche: boolean; email: boolean; brief?: boolean }) =>
  j<{ ok: boolean }>('/events/prefs', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(p) })
export const patchDigestFrequence = (frequence: string) =>
  j<{ ok: boolean; frequence: string }>('/events/prefs/frequence', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ frequence }) })
export const getEventsCount = () => j<{ unread: number; par_parcelle: Record<string, number> }>('/events/count')
export const markEventRead = (id: number) => j<{ ok: boolean }>(`/events/${id}/read`, { method: 'POST' })
export const markAllEventsRead = () => j<{ ok: boolean }>('/events/read-all', { method: 'POST' })
export const getWatch = (idu: string) => j<{ watched: boolean }>(`/events/watch/${idu}`)
export const toggleWatch = (idu: string) => j<{ watched: boolean }>(`/events/watch/${idu}`, { method: 'POST' })
export const getSavedSearches = () => j<{ id: number; nom: string; hash: string; date: string }[]>('/events/searches')
export const saveSearch = (nom: string, hash: string) =>
  j<{ ok: boolean }>('/events/searches', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nom, hash }) })
export const deleteSearch = (id: number) => j<{ ok: boolean }>(`/events/searches/${id}`, { method: 'DELETE' })
// CONNEXIONS-2 Lot 5 (KO-7) — ce qu'une veille de recherche VA surveiller (dimensions retenues +
// celles non évaluables), moteur partagé avec la carte. Affiché à la création.
export const getSearchApercu = (hash: string) =>
  j<{ surveille: string[]; non_retenu: string[] }>(`/events/searches/apercu?hash=${encodeURIComponent(hash)}`)
// M52 L5 — renommer une vue sauvegardée (compte-scopé).
// M17-B : veille en langage naturel — traduction réutilisée (schéma), garde-fou déclenchable côté back.
export const veilleNL = (text: string) =>
  j<{ ok: boolean; refus?: string; indeclenchable?: boolean; filters?: Record<string, unknown>; resume?: string; ignores?: string[] }>(
    '/events/veille-nl', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) })

// ── M16-C : menu compte (identité + statut réel). RETOURS-1 R1 : `mode` = 'compte' (session
// compte) ou 'local' (session dev sans compte, fail-open) ; email + plan réel du compte connecté,
// plan_eur_mois depuis offres.py (null pour 'interne' — jamais un prix sur un compte interne).
// postSuggestion (« Proposer une amélioration ») retiré : doublon du bouton Signaler (postRetour).
export interface Moi { mode: 'compte' | 'local'; plan: string; plan_label: string; plan_par_compte: boolean; role?: string; statut_compte?: string; email?: string | null; plan_eur_mois?: number | null;
  // RETOURS-11 A6 — nom du compte + échéance (« Intégral depuis le … » via `depuis`, « Essai jusqu'au … » via `essai_jusqu` ; dates ISO ou null).
  nom?: string | null; depuis?: string | null; essai_jusqu?: string | null }
export const getMoi = () => j<Moi>('/moi')
// DASHBOARD-V1 · D1 — bouton « Signaler » (en-tête) : bug/idée/question → table retours
// (statuts suivis au dashboard admin).
// COMPTE-2 (Lot 7) — « Signaler » global : le contexte (url/page/outil/idu/navigateur/écran) part avec.
export const postRetour = (body: {
  type: 'bug' | 'idee' | 'question' | 'donnee'; message: string
  idu?: string; section?: string; url?: string; page?: string; outil?: string; navigateur?: string; ecran?: string
}) =>
  j<{ ok: boolean; id: number }>('/retours', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

// ── DASHBOARD-V1 — Tour de contrôle (admin) ──
export interface StripeApercu {
  configure: boolean
  raison?: string
  erreur?: string
  mrr_eur?: number
  abonnements_actifs?: number
  paiements_en_echec?: number
  abonnements?: Array<{ subscription_id: string; customer_id: string; email: string | null; nom_stripe: string | null; statut: string; montant_eur_mois: number; depuis: number | null; periode_fin: number | null; prochaine_retentative: number | null }>
  ca_mois?: Record<string, number>
  rapprochement?: { comptes_sans_abo: Array<{ compte_id: number; nom: string; statut: string }>; abos_sans_compte: Array<{ customer_id: string; email: string | null; statut: string }>; indisponible?: boolean }
  maj?: string
}
export interface AdminPilotage {
  stripe: StripeApercu
  licences_actives: number
  actifs_24h: number
  mail_echecs_jour?: number   // DASHBOARD-2 (Lot 2) — échecs d'envoi du jour (mail_queue), jauge Système
  ia_mois: { cout_eur: number; appels: number }
  // RETOURS-8 (R10) — « non_configure » (répertoire absent) distinct d'« absent » (vide) ; + fichier/taille.
  backup: { etat: 'ok' | 'ambre' | 'rouge' | 'absent' | 'non_configure'; chemin: string; age_jours: number | null; mtime?: string; fichier?: string; taille_mo?: number }
  // DASHBOARD-2 (Lot 1) — LED rail : Horloge (jobs posés / attendus) et Verrous (ok / 16). null = « — ».
  horloge?: { poses: number | null; attendus: number | null }
  verrous?: { ok: number | null; sur: number | null }
  // CONNEXIONS-2 Lot 7.2 (N3) — `endpoints`/`endpoints_ok` = sonde RUNTIME métier (avec DB), en plus du heal boot.
  sante: { ok: boolean | null; total: number | null; en_echec: string[]; endpoints_ok?: boolean | null; endpoints?: Array<{ endpoint: string; ok: boolean; detail: string | null }> }
  // CONNEXIONS-2 Lot 4 — KPI courriers ; DASHBOARD-4 P1 — `deposables` (ce qui peut réellement partir,
  // ≠ a_deposer), `bloquees`/`incomplets` (retenus), `plus_ancien_ouvre_j` (seuil rouge = 5 j ouvrés).
  courrier: { a_deposer: number; en_cours: number; clos: number; deposables?: number; bloquees?: number; incomplets?: number; plus_ancien_ouvre_j?: number | null }
  // DASHBOARD-4 P3 — avance de main sur la prod (git + dernier deploy connu) ; rouge tant que avance > 0.
  deploiement?: { marqueur_present: boolean; sha: string | null; depuis: string | null; avance: number | null; branche: string }
  // DASHBOARD-4 P3 — sources vitrine sans contrôle récent (G8) ; la cause vraie = horloges non posées.
  sondes_muettes?: { n: number | null }
  // SCORING-3 (L5.3) — étiquettes de contact posées (7 j + cumul ; seuil TERRAIN-1 : 200)
  etiquettes_terrain?: { semaine: number; total: number }
  radar?: { compteurs: RadarCompteurs; ecart: FluxRadarEcart[] } | null   // FLUX-1 F3.5 — tuile « la donnée qui s'accumule »
  run: { label: string | null; carte_le: string | null }
  // ADMIN-1 (AD5) — rangée « À faire » (ambre) : un geste attendu par tuile.
  a_faire: { sources_nouvelle_version: number; essais_24h: number; signalements_ouverts: number; manuelles_retard: number }
  // RETOURS-11 A4 — retours « Signaler » ouverts, ventilés par type (bug/idee/question/donnee), clé SŒUR
  // de `a_faire` (qui reste 4 entiers). Clés absentes = 0.
  retours_par_type?: Record<string, number>
  // ADMIN-1 (AD5) — rangée « Santé · traction » (vert).
  traction: { mrr_eur: number | null; veilles_7j: number; coherence: { ok: boolean | null; n_surfaces: number | null; verifie_le: string | null } }
  fil: Array<{ id: number; ts: string | null; kind: string; source: string | null; titre: string; detail: string | null; lien: string | null }>
  gels: Array<{ sujet: string; motif: string | null; ts: string | null }>
}
export const getAdminPilotage = () => j<AdminPilotage>('/admin/pilotage')

// DESTINATIONS-1 (X5.3) — calibration destinations par commune (page admin « Destinations »).
export interface AdminDestinationsCommune {
  insee: string; commune: string
  etat: 'calibree' | 'a_relire' | 'rnu' | 'non_calibree'
  millesime: string | null; lu_le: string | null; document: string | null
  url?: string | null; note?: string | null; zones?: string[]
}
export interface AdminDestinations {
  communes: AdminDestinationsCommune[]
  compte: { calibree: number; a_relire: number; rnu: number; non_calibree: number }
  referentiel: string
}
export const getAdminDestinations = () => j<AdminDestinations>('/admin/destinations')
export const getAdminStripe = () => j<StripeApercu>('/admin/stripe')
export const postAdminDegeler = (sujet: string) =>
  j<{ ok: boolean; degele: boolean }>('/admin/degeler', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sujet }) })
// D4 — Licences
export interface AdminLicence {
  id: number; nom: string; email: string | null; plan: string; statut: string; created_at: string | null
  essai_expire_at: string | null
  est_test?: boolean   // COMPTE-2 (Lot 3) — compte de test/interne : masqué des chiffres client
  stripe: NonNullable<StripeApercu['abonnements']>[number] | null | undefined
  mails: Record<string, { statut: string; sent_at: string | null }>
  mail_echecs?: number   // VEILLE-FIX-2 (Lot D) — nb de mails en échec définitif → ligne rouge Comptes
  rappels: string[]
  partage: { sessions: number; ips: number; probable: boolean } | null   // A5 — sessions simultanées (informatif)
  kpi: { usage_7j_min: number; derniere_connexion: string | null; copilote_jour: number; copilote_quota: number
    // COMPTE-2 (Lot 3) — le plafond IA est en EUROS : dépense € du jour + budget € (corrige « 0 / 80 »).
    ia_depense_eur?: number; ia_budget_eur?: number }
}
export interface AdminLicences {
  licences: AdminLicence[]
  stripe_configure: boolean
  rapprochement?: StripeApercu['rapprochement']
  brevo: { api: boolean; templates: Record<string, boolean> }
  // ADMIN-1 (AD4) — libellés servis des mails (fini « Mail 1/2/3 »), source unique = brevo.LIBELLES.
  mail_libelles: Record<string, string>
  // COMPTE-2 (Lot 3) — compteurs SERVIS par le backend (source unique) : licences actives + masqués.
  compteurs?: { licences_actives: number; masques: number; visibles: number }
  partage_seuil: number
  // COMPTE-3 (Lot 2) — garde sur l'URL de base des liens de mails : bandeau rouge si non cliquable.
  mail_liens?: { base_url: string | null; ok: boolean; avert: string | null }
}
// ADMIN-1 (AD4) — aperçu du mail réel (template Brevo rendu avec les variables du compte) avant Envoyer.
export interface MailApercu {
  configure: boolean; key: string; libelle: string; params: Record<string, string>
  subject?: string; html?: string; raison?: string
}
export const getAdminMailApercu = (compteId: number, key: string) =>
  j<MailApercu>(`/admin/licences/${compteId}/mail/${encodeURIComponent(key)}/apercu`)
// E1 — offres servies par le serveur (source de vérité unique) : le front n'écrit AUCUN prix en dur.
export interface Offre { cle: string; label: string; eur_mois?: number; eur?: number; engagement?: boolean; periodicite: string; validite_lien_jours?: number }
export interface Offres { integral: Offre; flash: Offre }
export const getOffres = () => j<Offres>('/api/offres')

// KF1 (rattrapage KelFoncier) — FACETTES PROPRIÉTAIRE (DGFiP, non-nominatif au niveau PM).
// Valeurs RÉELLES avec comptes : formes juridiques, codes APE, couverture, drapeau âge dirigeant
// (RGPD, fermé par défaut). Le front n'écrit AUCUNE forme/APE en dur — tout vient d'ici.
export interface ProprietairesFacettes {
  millesime: string
  source: string
  formes: { code: string; label: string; n: number }[]
  apes: { code: string; label: string; n: number }[]
  couverture: { pm: number; total: number; couvert: boolean }
  age_dirigeant_actif: boolean
}
export const getProprietairesFacettes = (commune?: string | null) =>
  j<ProprietairesFacettes>(`/proprietaires/facettes${commune ? `?commune=${encodeURIComponent(commune)}` : ''}`)

// Autocomplétion de dénomination (2 caractères min). Renvoie les entités PM et leur volume parcellaire.
export interface ProprietairesAutocomplete {
  suggestions: { denomination: string; siren: string; n: number }[]
}
export const getProprietairesAutocomplete = (qy: string, commune?: string | null) => {
  const params = new URLSearchParams({ q: qy, ...(commune ? { commune } : {}) })
  return j<ProprietairesAutocomplete>(`/proprietaires/autocomplete?${params.toString()}`)
}

export const getAdminLicences = () => j<AdminLicences>('/admin/licences')
export const postAdminLicenceCreer = (body: { email: string; nom?: string }) =>
  j<{ ok: boolean; lien: string; compte_id: number; expire_at: string }>('/admin/licences/creer', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
// D9 — essai 48 h
export const postAdminLicenceCreerEssai = (body: { email: string; nom?: string; heures?: number }) =>
  j<{ ok: boolean; lien: string; compte_id: number; heures: number; essai_expire_at: string }>('/admin/licences/creer-essai', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
export const postAdminLicenceConvertir = (compteId: number) =>
  j<{ ok: boolean; detail: string }>(`/admin/licences/${compteId}/convertir`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) })
// COMPTE-3 (Lot 1) — prolonger un essai : la modale convertit la date de fin choisie en `heures` (1–720).
export const postAdminLicenceProlonger = (compteId: number, heures: number) =>
  j<{ ok: boolean; essai_expire_at: string; heures: number; detail: string }>(`/admin/licences/${compteId}/prolonger`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ heures }) })
export const postAdminSuspendre = (compteId: number) =>
  j<{ ok: boolean }>(`/admin/licences/${compteId}/suspendre`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) })
export const postAdminRetablir = (compteId: number) =>
  j<{ ok: boolean }>(`/admin/licences/${compteId}/retablir`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) })
// COMPTE-2 (Lot 4) — déconnexion à distance : ferme toutes les sessions du compte (poste partagé).
export const postAdminDeconnecter = (compteId: number) =>
  j<{ ok: boolean; sessions_fermees: number }>(`/admin/licences/${compteId}/deconnecter`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) })
export const postAdminLicenceMail = (compteId: number, key: string) =>
  j<{ ok: boolean; envoye: boolean; raison?: string }>(`/admin/licences/${compteId}/mail`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key }) })
// COMPTE-2 (Lot 2/3) — la file mail_queue d'un compte (onglet Activité / Facturation de la fiche).
export interface MailLigne {
  id: number; mail_key: string; template_nom: string | null; destinataire: string
  etat: string; etat_libelle: string; demandeur: string; tentatives: number
  message_id: string | null; erreur: string | null; cree_at: string | null; parti_at: string | null
  params: Record<string, unknown>
  // COMPTE-3 (Lot 2) — avertissement figé à l'enfilage (URL de base des liens non cliquable).
  avert?: string | null
}
export const getAdminMails = (compteId: number) =>
  j<{ lignes: MailLigne[]; compteurs: unknown }>(`/admin/mails?compte_id=${compteId}`)
// COMPTE-2 (Lot 6) — mémoire du compte : préférences de carte (fond + couches) en base (survivent au poste).
export const getPrefsCarte = () =>
  j<{ basemap: string | null; couches: Record<string, boolean> | null }>('/moi/prefs-carte')
export const postPrefsCarte = (body: { basemap?: string; couches?: Record<string, boolean> }) =>
  j<{ ok: boolean }>('/moi/prefs-carte', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
// D5 — IA
export interface AdminIa {
  mois: { cout_eur: number; appels: number; cout_moyen_question: number | null }
  // RETOURS-8 (R3) — coût unitaire d'UNE question (« 0,008 € / question »).
  cout_unitaire_question_eur: number
  projection_fin_mois_eur: number
  jours: Array<{ jour: string; cout: number; appels: number }>
  par_licence: Array<{ compte_id: number | null; nom: string; cout: number; appels: number }>
  // RETOURS-8 (R3) — le plafond par défaut est en EUROS/jour, éditable par licence.
  budget_defaut_eur: number
  // RETOURS-8 (R3) — par compte : budget €/jour, dépense du jour en €, équivalent « ≈ N questions »,
  // nombre d'appels du jour (mention secondaire).
  quotas: Array<{ id: number; nom: string; plan?: string | null; copilote_budget_eur: number | null; budget_eur: number
    depense_eur: number; equiv_questions: number | null; appels_aujourdhui: number }>
  // RETOURS-7 Z7 — quel modèle sert chaque surface IA (lu depuis la config, jamais un nom en dur)
  modeles_par_surface: Array<{ kind: string; label: string; model: string }>
  note: string
}
export const getAdminIa = () => j<AdminIa>('/admin/ia')
// CONNEXIONS-2 Lot 3 (KO-4) — file UNIQUE des signalements (fiche + annonce), traitée au dashboard
export interface Signalement {
  id: number; type: 'fiche' | 'annonce'; parcelle_id: string | null; bien_id: number | null
  type_erreur: string; champ: string | null; commentaire: string | null; utilisateur: string | null
  statut: 'nouveau' | 'traite'; created_at: string | null; traite_at: string | null
  compte_id: number | null; compte_nom: string | null
  compte_plan?: string | null   // DASHBOARD-2 (Lot 5) — 'interne' = compte de test, masqué par défaut
  fiche_lien: string | null   // RETOURS-11F M11 — lien cliquable vers la fiche d'origine (signalement fiche)
}
export const getAdminSignalements = (statut?: 'nouveau' | 'traite') =>
  j<{ signalements: Signalement[]; n_ouverts: number }>(`/admin/signalements${statut ? `?statut=${statut}` : ''}`)
export const postAdminSignalementStatut = (id: number, statut: 'nouveau' | 'traite') =>
  j<{ ok: boolean }>(`/admin/signalements/${id}/statut`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ statut }) })
// RETOURS-8 (R13) — traite en masse les signalements venus d'un compte interne/test (rien supprimé).
export const postAdminSignalementsTraiterInternes = () =>
  j<{ ok: boolean; traites: number }>('/admin/signalements/traiter-internes', { method: 'POST' })
// RETOURS-8 (R3) — le plafond s'édite en EUROS/jour (`budget_eur`, null = défaut config).
export const postAdminLicenceQuota = (compteId: number, budgetEur: number | null) =>
  j<{ ok: boolean }>(`/admin/licences/${compteId}/quota`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ budget_eur: budgetEur }) })
// D6 — Sources
// SENTINELLE-1 (W4) — état de veille amont d'une source (null si non surveillée = état normal).
export interface AdminSourceVeille {
  // SENTINELLE-3 (Y5.4) — nature de surveillance : version détectable (api/page) · changement détectable
  // (entete/temoin) · rappel manuel (Y4) · non surveillable (rien). `surveillee` = VRAIE sonde amont.
  nature: 'version' | 'changement' | 'rappel' | 'non_surveillable'
  surveillee: boolean
  actif: boolean | null
  methode: string | null            // api | page | entete | temoin | rappel
  statut: string | null             // ok | nouvelle_version | injoignable | illisible
  millesime_amont: string | null    // millésime constaté amont
  nouvelle_version: boolean
  passage_at: string | null
  message: string | null
  // SENTINELLE-2 (X5.2) — sondes en échec consécutives ; `echec_confirme` = ≥3 (à distinguer d'un aléa).
  // `raison` (X3.3) = pourquoi une source N'EST PAS surveillée (infobulle), null si surveillée.
  echecs: number
  echec_confirme: boolean
  raison: string | null
  // SENTINELLE-2 (X6) — `injectable` = une commande d'ingestion existe → bouton « Injecter cette version ».
  // Trace de la dernière injection déclenchée À LA MAIN par Vic (jamais la sentinelle) : suivi visible.
  injectable: boolean
  injection_lancee_at: string | null
  injection_vu: string | null
  // SENTINELLE-3 (Y4) — rappel de rafraîchissement des sources MANUELLES : cadence attendue, âge de la
  // dernière ingestion, échéance de convention si connue, et `rappel_retard` = donnée non rafraîchie à temps.
  cadence_attendue_jours: number | null
  convention_echeance: string | null
  jours_depuis_maj: number | null
  rappel_retard: boolean
  // SUITE-1 (S4.1) — alerte mail optionnelle PAR SOURCE (défaut off ; l'alerte in-app reste toujours).
  mail_alerte: boolean
}
// SUITE-1 (S2 bis) — colonne « Alimente » : moteurs + surfaces nourris, LUS de la matrice flux.py.
export interface AdminSourceAlimente {
  moteurs: Array<{ key: string; label: string }>
  surfaces: Array<{ key: string; label: string }>
  cable: boolean
}
// RETOURS-8 (R1) / RETOURS-9 (Q2) — l'état UNIQUE d'une source, calculé par l'arbitre backend.
// Cinq états qui partitionnent EXACTEMENT le catalogue (leur somme = le total).
export type SourceEtat = 'nouvelle_version' | 'a_rafraichir' | 'jamais_verifiee' | 'a_jour' | 'non_surveillee'
export interface AdminSource {
  id: number; name: string; category: string | null; millesime: string | null; horizon: string | null
  ingere_le: string | null; cadence: string | null; a_jour: boolean | null; relance: string | null
  // RETOURS-8 (R1) — état unique (arbitre serveur) + phrase honnête + projection client (2 états).
  etat: SourceEtat; etat_client: 'a_jour' | 'pas_a_jour'; etat_phrase: string; publie_le: string | null
  // CONNEXIONS-2 Lot 6.3 (M2) — désactivée au dashboard ⇒ hors vitrine + consommateurs coupés.
  affichage_desactive: boolean
  fournisseur: string | null    // SENTINELLE-2 (X4) — colonne/regroupement fournisseur du tableau de veille
  alimente: AdminSourceAlimente  // SUITE-1 (S2 bis) — ce que la source nourrit (matrice réelle)
  veille: AdminSourceVeille
}
export interface AdminSources {
  sources: AdminSource[]
  synthese: { a_mettre_a_jour: number; ok: number; sans_echeance: number; nouvelle_version: number; surveillees: number; sonde_echec: number; non_surveillees: number; version: number; changement: number; rappels: number; rappels_en_retard: number; etat_nouvelle_version: number; etat_a_rafraichir: number; etat_jamais_verifiee: number; etat_a_jour: number; etat_non_surveillee: number }
  cadences: string[]
  runs: Array<{ started_at: string | null; finished_at: string | null; status: string | null; parcels_count: number | null; name: string | null }>
}
export const getAdminSources = () => j<AdminSources>('/admin/sources')
export const postAdminSourceCadence = (id: number, cadence: string | null) =>
  j<{ ok: boolean }>(`/admin/sources/${id}/cadence`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ cadence }) })
export const postAdminSourceRelancer = (id: number) =>
  j<{ ok: boolean; label: string; log: string; millesime: string | null }>(`/admin/sources/${id}/relancer`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) })
// CONNEXIONS-2 Lot 6.3 (M2) — désactiver / réactiver une source depuis le dashboard.
export const postAdminSourceAffichage = (id: number, actif: boolean) =>
  j<{ ok: boolean; actif: boolean }>(`/admin/sources/${id}/affichage`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ actif }) })
// SENTINELLE-1 (W4) — veille amont : « Vérifier maintenant » (sonde en direct) + activer/désactiver la surveillance.
export const postAdminSourceVeilleVerifier = (id: number) =>
  j<{ ok: boolean; statut: string | null; millesime_amont: string | null; servi: string | null; message: string | null; notifs: number }>(`/admin/sources/${id}/veille/verifier`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) })
export const postAdminSourceVeilleActive = (id: number, actif: boolean) =>
  j<{ ok: boolean; actif: boolean }>(`/admin/sources/${id}/veille/active`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ actif }) })
// SUITE-1 (S4.1) — abonner/désabonner une source à l'alerte mail (l'alerte in-app reste toujours).
export const postAdminSourceVeilleMail = (id: number, mail_alerte: boolean) =>
  j<{ ok: boolean; mail_alerte: boolean }>(`/admin/sources/${id}/veille/mail`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ mail_alerte }) })
// SENTINELLE-2 (X6) — « Injecter cette version » : sur clic humain, lance le job d'ingestion EXISTANT.
export const postAdminSourceVeilleInjecter = (id: number) =>
  j<{ ok: boolean; label: string; log: string; millesime: string | null }>(`/admin/sources/${id}/veille/injecter`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) })
export const getHealthzCrons = () =>
  j<{ ok: boolean; crons: Record<string, { statut: string; note?: string; dernier_ok?: string | null; age_jours?: number }> }>('/healthz/crons')

// ── FLUX-1 — la page « Flux » (la donnée, de la source à l'écran) ──
export type FluxDot = 'ok' | 'warn' | 'err' | 'off'
export interface FluxSourceNode {
  id: number; name: string; fournisseur: string | null; categorie: string | null
  millesime: string | null; amont_vu: string | null; ingere_le: string | null
  dot: FluxDot; etat: string; nature: string; moteurs: string[]; message: string | null
  injectable: boolean; injection_lancee_at: string | null
}
export interface FluxMoteurNode { key: string; label: string; detail: string; run: string; dot: FluxDot; sources: number[] }
export interface FluxSurfaceNode { key: string; label: string; groupe: string; run: string; moteurs: string[]; dot: FluxDot }
export interface FluxRun {
  label: string; precedent: string; calcule_le: string | null; n_parcelles: number | null
  enregistre_sources: boolean
  source_millesimes: Array<{ source_id: number; name: string; fournisseur: string | null; millesime: string; horizon: string | null }>
}
export interface FluxFourmiliere {
  run: FluxRun
  sources: FluxSourceNode[]; moteurs: FluxMoteurNode[]; surfaces: FluxSurfaceNode[]
  comptes: { total: number; surveillees: number; nouvelle_version: number; plus_recentes_que_run: number; n_surfaces: number }
  plus_recentes: Array<{ id: number; name: string; millesime: string | null; amont: string | null }>
  genere_le: string
}
export interface RadarCompteurs {
  annonces: number; annonces_semaine: number; rattachees: number; rattachees_pct: number | null
  paires: number; paires_semaine: number; communes: number; communes_total: number; types: number
}
export interface FluxRadarEcart { type: string; n: number; ecart_pct: number | null; fragile: boolean }
export interface FluxRadar {
  compteurs: RadarCompteurs; ecart: FluxRadarEcart[]
  courbe: { points: Array<{ jour: string; paires: number; annonces: number; rattachees: number }>; depuis_le: string | null }
}
export interface CoherenceCheck { libelle: string; ok: boolean; detail: string | null }
export interface FluxCoherence { ok: boolean | null; run?: string; n_surfaces?: number; verifie_le?: string; checks: CoherenceCheck[]; erreur?: string }
// DONNEES-2 (B2/D3) — le STATUT d'un run : en_cours · termine · servi · retour_arriere · abandonne · ancien.
export type FluxRunStatut = 'en_cours' | 'termine' | 'servi' | 'retour_arriere' | 'abandonne' | 'ancien'
export interface FluxRunProgress { phase?: string | null; commune?: string | null; pct?: number | null; done?: number | null; total?: number | null }
export interface FluxRunTermine {
  label: string; servi: boolean; complet: boolean; motif: string; calcule_le: string | null; n_parcelles: number | null
  statut: FluxRunStatut
  ecart: { tiers_changes: number; promues_candidat: number; promues_servi: number; derive_promues_pct: number } | null
  // SCORING-3 (L1.3) — recette du run (m36 | q_v12) + note de version du candidat, lisible avant de basculer.
  modele?: string | null; recette?: string | null; note_de_version?: string | null
  // DONNEES-2 (B3) — progression d'un run en cours / abandonné (lue de l'état de progression).
  progress?: FluxRunProgress | null
}
// DONNEES-2 (B3) — l'état du run EN COURS (barre + % de l'étape 2), poll léger pendant un run.
export interface FluxRunEtat {
  label: string; recette?: string | null; statut: FluxRunStatut; pid?: number | null
  phase?: string | null; commune?: string | null; pct?: number | null; done?: number | null; total?: number | null
  started_at?: string | null; log?: string | null
}
export const getAdminFluxRunEtat = () => j<{ en_cours: FluxRunEtat | null }>('/admin/flux/run/etat')
export const postAdminFluxArreterRun = (label: string) =>
  j<{ ok: boolean; tue?: boolean }>('/admin/flux/run/arreter', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ label }) })
export interface FluxDerniereBascule { ts: string | null; ancien: string | null; nouveau: string; par: string | null; sens: string; caches_purges: string[] }
export interface AdminFlux {
  flux: FluxFourmiliere; radar: FluxRadar; coherence: FluxCoherence
  // RETOURS-9 (Q1) — les runs terminés (calcul d'écart coûteux, ~50 s en base réelle) ne sont
  // PLUS dans cette charge : le Circuit rend tout de suite, les runs arrivent via getAdminFluxRuns
  // (rendu progressif). `bascule` ne porte donc plus que la dernière bascule (rapide).
  bascule: { derniere: FluxDerniereBascule | null }
  // RETOURS-8 (R4.2) — briques qui ont lâché (repli servi) : la page rend quand même et le dit.
  erreurs?: string[] | null
}
export const getAdminFlux = () => j<AdminFlux>('/admin/flux')
export const getAdminFluxRuns = () => j<{ runs: FluxRunTermine[]; derniere: FluxDerniereBascule | null }>('/admin/flux/runs')
export const postAdminFluxLancerRun = (recette: 'm36' | 'q_v12' = 'm36') =>
  j<{ ok: boolean; label: string; estimation: string; log: string }>('/admin/flux/run/lancer', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ recette }) })
export const postAdminFluxBascule = (run: string) =>
  j<{ ok: boolean; ancien?: string; nouveau?: string; caches_purges?: string[]; coherence?: FluxCoherence; note?: string; motif?: string
      // DONNEES-2 (B1) — reconstruction détachée des tables servies run-scopées après la bascule.
      reconstruction?: { lancee: boolean; run?: string; log?: string; motif?: string } | null }>(
    '/admin/flux/bascule', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ run }) })
// D7 — Produit
export interface AdminProduit {
  usage: Array<{ outil: string; n: number }>
  retours: Array<{ id: number; ts: string | null; type: string; message: string; statut: string; compte: string | null; compte_plan?: string | null; idu?: string | null; section?: string | null; fiche_lien?: string | null }>
  jours?: number
}
// ADMIN-1 (AD7) — période au choix : 7 / 30 / 90 j (défaut 30).
export const getAdminProduit = (jours: 7 | 30 | 90 = 30) => j<AdminProduit>(`/admin/produit?jours=${jours}`)
export const postAdminRetourStatut = (id: number, statut: 'nouveau' | 'traite' | 'repondu') =>
  j<{ ok: boolean }>(`/admin/retours/${id}/statut`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ statut }) })
// D8 — Courrier (endpoints /courrier/admin/* EXISTANTS, consommés par la Tour de contrôle)
export interface AdminDemandeCourrier {
  id: number; ts: string | null; compte_id: number | null; n: number; communes: string | null
  modele: string | null; corps: string | null; statut: string; updated_at: string | null
  parcelles: string[] | null; client: string | null
  // ADMIN-1 (AD8) — lien vers la piste CRM d'origine (et le projet), nullable.
  pipeline_entry_id: number | null; projet_id: number | null
  // DASHBOARD-2 (Lot 3) — propriétaire = nombre de personnes morales (jamais un particulier) ;
  // compte_plan = 'interne' pour les comptes de test/pilote (masqués par défaut).
  proprietaire?: string | null; compte_plan?: string | null
  // COURRIER-2 Lot 5 — prix facturé SAISI par Vic (facturation manuelle), jamais calculé. Nullable.
  prix_eur?: number | null
}
// COURRIER-2 Lot 5 — coût prestataire : paramètre admin daté + saisie du prix par demande.
export interface CourrierConfig { cout_lettre_eur: number; marge: number; maj_at: string | null; maj_par: string | null }
export const getCourrierConfig = () => j<CourrierConfig>('/courrier/admin/config')
export const putCourrierConfig = (cout_lettre_eur: number) =>
  j<{ ok: boolean } & CourrierConfig>('/courrier/admin/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ cout_lettre_eur }) })
export const postAdminCourrierPrix = (id: number, prix_eur: number | null) =>
  j<{ ok: boolean; prix_eur: number | null }>(`/courrier/admin/demandes/${id}/prix`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prix_eur }) })
export const getAdminCourrierDemandes = () =>
  j<{ demandes: AdminDemandeCourrier[]; statuts: string[]; statut_libelles: Record<string, string> }>('/courrier/admin/demandes')
export const postAdminCourrierStatut = (id: number, statut: string) =>
  j<{ ok: boolean }>(`/courrier/admin/demandes/${id}/statut`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ statut }) })
// DASHBOARD-2 (Lot 3) — « Marquer les N déposés » en bloc.
export const postAdminCourrierDeposerTout = () =>
  j<{ ok: boolean; deposes: number; bloquees_opposition?: number }>('/courrier/admin/demandes/deposer-tout', { method: 'POST' })
export const urlCourrierPdf = '/courrier/pdf'

// COURRIER-2 Lot 1 — REGISTRE D'OPPOSITION (stop@labuse.immo). Saisie manuelle par Vic ; global.
export interface AdminOpposition {
  id: number; adresse_norm: string | null; idu: string | null; reference: string | null
  origine: string; note: string | null; cree_par: string | null; cree_at: string
}
export const getAdminOppositions = () =>
  j<{ oppositions: AdminOpposition[] }>('/courrier/admin/oppositions')
export const postAdminOpposition = (body: { adresse?: string; idu?: string; reference?: string; note?: string }) =>
  j<{ ok: boolean; opposition: AdminOpposition }>('/courrier/admin/oppositions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
export const deleteAdminOpposition = (id: number) =>
  j<{ ok: boolean }>(`/courrier/admin/oppositions/${id}`, { method: 'DELETE' })

// ── Moteurs (Vague 4) ──
// M137-Q — le périmètre du simulateur PLU est désormais un choix EXPLICITE dans l'outil (plus
// hérité muettement du filtre global). `commune === undefined` → repli sur le filtre global
// (compat) ; `null`/'' → toute l'île ; sinon la commune passée.
const communeQ = (c?: string | null) => c === undefined ? cq() : (c ? `commune=${encodeURIComponent(c)}` : '')
export const motSimulPluZones = (commune?: string | null) =>
  j<{ zone: string; n_ilots: number }[]>(`/moteurs/simulplu/zones?${communeQ(commune)}`)
// PLU Lot A (pagination) : `offset` pagine (cap par page) ; `signal` permet l'annulation effective
// du recalcul en cours (Lot B, UI de chargement honnête).
export const motSimulPlu = (zone: string, commune?: string | null, offset = 0, signal?: AbortSignal) =>
  j<Record<string, any>>(`/moteurs/simulplu?zone=${encodeURIComponent(zone)}&${communeQ(commune)}${offset ? `&offset=${offset}` : ''}`,
    signal ? { signal } : undefined)
export interface SimulPluProcedure {
  insee: string; commune: string; commune_radar: string; type: string
  stade: string | null; date_acte: string | null; etat: string | null; prochaine_etape: string | null
  source: string | null; source_url: string | null; date_constat: string | null; confiance: string | null
}
export const motSimulPluProcedures = () =>
  j<{ communes: SimulPluProcedure[]; source: string }>(`/moteurs/simulplu/procedures`)
export const motAssemblage = (idus: string[]) =>
  j<Record<string, any>>('/moteurs/assemblage', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ idus }) })
export const motZan = () => j<Record<string, any>>('/moteurs/zan')
export const zanParcelle = (idu: string) => j<Record<string, any>>(`/moteurs/zan/parcelle/${idu}`)
export const motBarometre = (insee?: string | null) =>
  j<Record<string, any>>(`/moteurs/barometre${insee ? `?insee=${encodeURIComponent(insee)}` : ''}`)
// M-U — bloc « Marché » par commune (9 lignes datées + market_signal DVF/Sitadel)
export const motMarcheCommune = (commune: string) =>
  j<Record<string, any>>(`/moteurs/marche/${encodeURIComponent(commune)}`)

// ── Vague 5 : matching + partage ──
export const getProfiles = () => j<Record<string, any>[]>('/partners/profiles')
export const addProfile = (p: Record<string, unknown>) =>
  j<{ ok: boolean }>('/partners/profiles', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(p) })
// M49 (Lot A, arbitrage Vic) : helpers runMatch/matchCompatibilite/listShares RETIRÉS — 0 importeur
// (vestiges M19, code mort front). Routes serveur correspondantes listées « douteuses » (non retirées).
export const promoteursActifs = (commune: string) => j<Record<string, any>>(`/partners/promoteurs-actifs?commune=${encodeURIComponent(commune)}`)
// M55-L point 3 : `createShare` retiré (0-caller après retrait de l'icône « partager » de la
// fiche). Endpoint back /partners/share intact — réexposable si le pack apporteur revient.

// ── M22 + Bilan (faisabilité bidirectionnelle) ──
export const getFaisabilite = (idu: string) => j<Record<string, any>>(`/modules/faisabilite/${idu}`)
// FAISABILITE-1 (lot D) — recalcule la capacité (11 étapes + fourchette) avec des hypothèses Estimé
// surchargées (« et si… »). UN SEUL moteur côté back (parcel_faisabilite) → aucune divergence.
export const postFaisabiliteRecalcul = (idu: string, overrides: Record<string, number>) =>
  j<Record<string, any>>(`/modules/faisabilite/${idu}/recalcul`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ overrides }),
  })
// FAISABILITE-3 (Vic 27/09) — UN SEUL appel sert le panneau (maquette validée) : scénario choisi
// (terrain_libere/bati_garde), hypothèses surchargées et projet à tester y entrent, verdict/étapes/
// section PLU/test en sortent. Aucun calcul dans le front — le moteur (parcel_faisabilite +
// compute_residuel) fait tout. `scenario` = null quand la parcelle est hors PLU.
export interface FaisaTest { n_logements?: number | null; surface_par_logement?: number | null }
export const postFaisabiliteScenario = (
  idu: string,
  body: { scenario: 'terrain_libere' | 'bati_garde'; overrides?: Record<string, number>; test?: FaisaTest | null },
) =>
  j<{ idu: string; scenario: Record<string, any> | null }>(`/modules/faisabilite/${idu}/scenario`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario: body.scenario, overrides: body.overrides ?? {}, test: body.test ?? null }),
  })

// M11 Surface C : explication IA de la dérivation du chiffrage (ancrée sur les steps, sur clic).
export const faisabiliteExplain = (idu: string) =>
  j<{ disponible: boolean; rejected?: boolean; degraded?: boolean; texte?: string; message?: string;
      sources?: string[]; provenance?: Record<string, string>; cached?: boolean }>(`/modules/faisabilite/${idu}/explain`)

// M-Q P1-16 — défauts d'hypothèses de la calculette servis par l'API (source unique côté serveur,
// dérivés du YAML). Le front ne grave plus 2500 : il seed ses champs depuis ici → calculette,
// Dossier banquier et Note de financement portent le même coût par défaut sur la même parcelle.
// VRD servie en défaut DIT (jamais un 0 silencieux) — la calculette la seed comme le coût/la marge.
export interface CalculetteDefaults { cout_construction_m2: number; marge_frais_pct: number; vrd_m2: number }
export const getCalculetteDefaults = () =>
  j<CalculetteDefaults>('/bilan/calculette-defaults')

// Calculette de charge foncière (mandat bilan-calculette) : LABUSE calcule le déterministe
// (SDP, prix DVF) ; le coût de construction, la marge ET la VRD sont les hypothèses SAISIES.
// M22-A : mode 'achat_max' = la même équation lue à l'envers (prix d'achat max admissible).
export interface ChargeIn { cout_construction_m2: number; marge_frais_pct: number; vrd_m2?: number; prix_demande_eur?: number | null; mode?: 'charge' | 'achat_max' }
export const postChargeFonciere = (idu: string, body: ChargeIn) =>
  j<Record<string, any>>(`/modules/faisabilite/${idu}/charge`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  })
// FAISABILITE-1 (lot C) — `postProgramme` (POST /modules/programme, ancien « Par critères ») RETIRÉ :
// « chercher des parcelles par capacité » passe désormais par le groupe Capacité du panneau Filtre
// (endpoint /filtre, compteur SQL exact). L'endpoint backend est retiré (aucun autre appelant).

// ── Projets (copilote-projet) — l'objet persistant de l'entretien de cadrage ──
// M120 — le CADRAGE d'un projet EST un jeu de filtres (le même objet que la carte). L'IDENTITÉ
// porte les infos indicatives (budget/type) qui n'alimentent AUCUN filtre. M120-B : date retirée.
export type Cadrage = Partial<Filters>
export interface Identite {
  budget_eur?: number | null          // indicatif — sans effet sur la sélection
  type_logement?: string | null       // indicatif (le moteur ne distingue pas par type)
}
export interface TypeLogement { cle: string; libelle: string }
export const getProjetTypes = () =>
  j<{ types: TypeLogement[]; informatif: boolean; note: string }>('/projets/types')
// contact proprio (PRIVACY : PM publique nommée OU particulier masqué) — partagé CRM ↔ projet
export type ProprietairePublic =
  | { type: 'personne_morale'; denomination: string; siren: string | null; groupe: string | null }
  | { type: 'particulier' }
export interface ProjetCounts { proposee: number; retenue: number; ecartee: number; a_analyser: number }
export interface Projet {
  id: number; nom: string; statut: 'actif' | 'archive'
  cadrage: Cadrage; identite: Identite; shortlist_perimee: boolean   // M120
  created_at: string | null; updated_at: string | null; derniere_execution_at: string | null
  counts?: ProjetCounts   // FIX-PROJETS : `proposee` = total VIF du cadrage − décidées (= l'ouverture) ; décidées depuis projet_parcelles
  proposee_at?: string | null   // fraîcheur du compte vif « à trier » (cache `cadrage_total`) — affichée « au JJ/MM »
}
// M120 — le diff d'un run (create/rejeu) : ce qui change, dit au client.
// M129-D P4 : ajoutees_refonte = entrées dues au nouveau vivier (refonte cascade), dites au rejeu.
// M120-B : + le vivier figeable (dénominateur honnête) + le cap (config) + `tronquee` (top-N vs tout le vivier).
export interface ShortlistDiff {
  ajoutees: number; ajoutees_refonte?: number; sorties: number; tris_conserves: number; n_shortlist: number
  vivier: number; cap: number; tronquee: boolean
}
// PROJETS-FIX F1 — le compteur du cadrage sort de LA MÊME requête que « À trier » du projet ouvert :
// `vivier` = le nombre EXACT que le projet servira (plus de `total` carte gonflé, source du mirage).
export interface CadrageCompteur { vivier: number; cap: number }
export const getCadrageCompteur = (cadrage: Cadrage, signal?: AbortSignal) =>
  j<CadrageCompteur>('/projets/compteur', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ cadrage }), signal })
// M120 — l'ancien entretien de cadrage IA (ProjetEntretien) a été retiré : un projet se cadre par
// ses facettes (ParcoursProjet → FiltreFacettes), plus par une fiche remplie par l'IA. Le client
// `/ia/entretien` et `/projets/reperes` est parti avec lui (endpoints backend conservés, non appelés).

export const getProjets = () => j<Projet[]>('/projets')
export const getProjet = (id: number) => j<Projet>(`/projets/${id}`)
export interface ProjetDerive { nom: string; cadrage: Cadrage; identite: Identite; sdp_besoin_m2: number | null }
// M120 — créer = FIGER la shortlist en une fois (le run part une fois ; plus de run à l'ouverture).
export const createProjet = (body: { cadrage: Cadrage; identite?: Identite; nom?: string; limit?: number; de_zero?: boolean }) =>
  // `existing: true` = dédup douce serveur (projet actif identique) → le front propose la reprise
  j<{ ok: boolean; existing?: boolean; projet: Projet; shortlist?: ShortlistDiff }>('/projets', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
export interface ApercuTop { idu: string; commune: string; statut: string | null; pourquoi: string[] }  // M139 bricole : q_score retiré (toujours None, non rendu)
export interface Apercu { nom: string; n: number; total: number; cap: number; sdp_besoin_m2: number | null; source: string; top: ApercuTop[] }
// PROJETS-CRM-FIX-1 (lot 2) — `projetPdfUrl` supprimé : /projets/{id}/export.pdf est retiré (410,
// remplacé par le document « Financier »). Plus aucun bouton n'y renvoie (export.csv reste, projetCsvUrl).
export const patchProjet = (id: number, body: { nom?: string; statut?: string; cadrage?: Cadrage; identite?: Identite }) =>
  j<{ ok: boolean; projet: Projet }>(`/projets/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
// M120 — rejouer À LA DEMANDE : rend le diff (entrées / sorties / tris conservés).
export const rejouerProjet = (id: number) =>
  j<{ ok: boolean; projet: Projet; shortlist: ShortlistDiff; counts: ProjetCounts }>(`/projets/${id}/rejouer`, { method: 'POST' })
// M139 Lot 1 (F1) — plus de suppression de projet côté front : l'archivage (patchProjet
// statut=archive/actif) est le SEUL chemin, réversible, et les cartes CRM suivent. Le wrapper
// deleteProjet (jamais appelé) est retiré ; l'API DELETE archive désormais aussi (défense).

// ── Parcours de sélection (Tinder) — statuts parcelle×projet ──
export type StatutParcelle = 'proposee' | 'retenue' | 'ecartee' | 'a_analyser'
export interface ParcoursCounts { proposee: number; retenue: number; ecartee: number; a_analyser: number }
// M120 · Phase 4 — la carte de tri : adresse + pourquoi COURT + signal marché/événement (servis
// batch par /parcelles, jamais un calcul client). Le q_score interne N'EST PLUS servi (mesuré :
// score de contraintes clampé 1-100, pas une « qualité » ni un rang de cadrage → ne se sert pas nu).
export interface ParcoursItem {
  idu: string; commune: string; statut: StatutParcelle; tier: string | null
  center: [number, number] | null; surface_m2?: number | null
  adresse?: string | null; pourquoi?: string[]; evenement?: boolean; marche_eur_m2?: number | null
  proprietaire_public?: ProprietairePublic | null; hors_criteres?: boolean; defisc?: boolean; caduc?: boolean
  etat_bien?: string | null   // M131 P3 : nu | bati_encore | bati_max (affichage)
  raison?: string | null      // OUTILS-5 (P1) : le signal dominant qui a classé la parcelle
  signaux?: { label: string; fort: boolean }[]   // PROJETS-V5 (E4) : ≤ 2 signaux de vie, fort = rouge
}
// M2 — fusion des doublons : union parcelles + statuts (statut le plus avancé gagne), conflits signalés.
export interface FusionResult { ok: boolean; cible: number; sources_archivees: number[]; n_parcelles: number; conflits: { parcel_id: number; statuts: string[]; retenu: string }[]; counts: ProjetCounts }
export const fusionnerProjets = (ids: number[]) => j<FusionResult>('/projets/fusionner', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ ids }) })
export interface ParcoursEtat {
  nom: string; sdp_besoin_m2: number | null; counts: ParcoursCounts
  // M139 Lot 2 (F2) — les deux dates : figeage du cadrage + run résiduel servi des valeurs.
  figee_le?: string | null; valeurs_run?: { label: string; seq: number; date: string | null } | null
  // M140 Lot A — les PROPOSÉES sont la liste COMPLÈTE des retenues, servie EN DIRECT et PAGINÉE :
  // `total_retenues` = N (dénominateur « X sur N »), `page` = la fenêtre courante. Décidées = complètes.
  total_retenues?: number | null
  page?: { offset: number; limit: number; returned: number; has_more: boolean }
  // PROJETS-V5 (E2) — le bandeau d'analyse : total du cadrage (= compteurs des filtres) + signalées par
  // tier (priorité = brûlante, à suivre = chaude). `signalees` = priorite + a_suivre.
  analyse?: { total: number; priorite: number; a_suivre: number; signalees: number } | null
  // RETOURS-3 R8 — le RESTANT à trier par tier (chips Tous/Priorité/À suivre) = total du cadrage par tier
  // moins les décidées du même tier. Le bandeau garde `analyse` (total) ; les chips lisent `restant`.
  restant?: { priorite: number; a_suivre: number; signalees: number } | null
  proposees: ParcoursItem[]; retenues: ParcoursItem[]; ecartees: ParcoursItem[]; a_analyser: ParcoursItem[]
}
export interface CarteDecision {
  idu: string; adresse: string | null; commune: string; surface_m2: number | null
  tier: string | null; statut: string | null; q_score: number | null; a_score: number | null
  completeness: number | null; center: [number, number] | null
  forces: { titre: string; detail: string }[]; attentions: { titre: string; detail: string }[]
}
// M140 Lot A — paginé : on feuillette la liste complète des retenues (offset/limit), jamais tout chargé.
// PROJETS-V5 (E5) — `sf` = sous-filtre du tiroir (JSON camelCase, mêmes clés que le wizard), fusionné
// côté serveur avec le cadrage du projet (une seule requête, aucun moteur parallèle).
export const getParcoursEtat = (id: number, offset = 0, limit = 60, tier?: string | null, sf?: Cadrage | null) =>
  j<ParcoursEtat>(`/projets/${id}/parcelles?offset=${offset}&limit=${limit}${tier ? `&tier=${tier}` : ''}${sf && Object.keys(sf).length ? `&sf=${encodeURIComponent(JSON.stringify(sf))}` : ''}`)
// M140 Lot B — export CSV de la liste COMPLÈTE des retenues (streamé, non stocké, zéro rang/score).
export const projetCsvUrl = (id: number) => `/projets/${id}/export.csv`
export const getCarteDecision = (id: number, idu: string) => j<CarteDecision>(`/projets/${id}/carte/${idu}`)
export const setStatutParcelle = (id: number, idu: string, statut: StatutParcelle) =>
  j<{ ok: boolean; idu: string; statut: StatutParcelle; counts: ParcoursCounts }>(
    `/projets/${id}/parcelle/${idu}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ statut }) })
// Phase 2 — chercher plus de parcelles (élargir / ajout manuel), dédupliqué côté serveur
export const ajouterParcelle = (id: number, idu: string) =>
  j<{ ok: boolean; added: boolean; already: boolean; idu: string; counts: ParcoursCounts }>(
    `/projets/${id}/ajouter`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ idu }) })
// F7 (M12) — projets ACTIFS du compte auxquels une parcelle est déjà rattachée (bouton « Projet » de la fiche).
export interface ProjetPourParcelle { id: number; nom: string; statut: StatutParcelle }
export const projetsPourParcelle = (idu: string) =>
  j<{ idu: string; projets: ProjetPourParcelle[] }>(`/projets/pour-parcelle/${idu}`)

// (Moteur de segments « Vues » retiré avec le spin-off — M12 Lot C-bis. Client, types et
//  routes /segments + /ia/segments-search partis avec la page. La recherche NL partagée de
//  la fiche reste `iaSearch` → /ia/search ci-dessus.)

// ── RADAR (pige) · P1 V3 — endpoints admin de la page Radar ──
export interface RadarProposition {
  statut: 'a_valider' | 'doublon_url' | 'rejet_commune' | 'echec_extraction'
  motif?: string; bien_id?: number; portail?: string; portail_inconnu?: boolean
  faits?: Record<string, unknown>; confiances?: Record<string, number>
  champs_a_verifier?: string[]; rattachement?: { niveau: string; idu: string | null; confiance: number | null; candidates: { idu: string; confiance: number }[] }
  fusion_proposee?: number | null; propose?: string; prix_ancien?: number | null; prix_nouveau?: number | null
}
export interface RadarBrouillon {
  bien_id: number; commune: string; type_bien: string | null; rattachement_niveau: string
  prix: number | null; surface_hab: number | null; surface_terrain: number | null
  dpe_classe: string | null; pieces: number | null; particulier_pro: string | null
  etiquettes: Record<string, string>; a_verifier: string[]
  portail: string; url_sortante: string; created_at: string | null
}
export interface RadarReverif {
  bien_id: number; commune: string; type_bien: string | null; statut: string; prix: number | null
  portail: string; url_sortante: string; date_derniere_confirmation: string | null
  date_publication: string | null; suivi_client: boolean; proche_longue: boolean
  // RETOURS-10 (T1) — non rattachée (idu NULL) + rattachement AUTOMATIQUE à confiance forte disponible :
  // un bouton « Rattacher » (1 clic) sur la ligne, dans la re-vérification. Faible → pas de bouton.
  non_rattachee?: boolean; rattachable_forte?: boolean; piste_idu?: string | null
}
export interface RadarCheck {
  cible_minutes: number; file_extraction: number; reverif_du_jour: number; signalements_en_attente: number
  // RETOURS-8 (R5) — les 4 chiffres de tête des onglets Radar.
  annonces_en_vie: number; a_rattacher: number; reverif_dues: number
  compteurs: { nouveautes: number; en_vente_longue: number; baisses: number }
  intake_vide_48h: boolean; derniere_saisie: string | null
  // RV2-V1 — état du répertoire de captures (écriture) : le défaut prod se voit AVANT le 1er dépôt.
  captures_dir_ok: boolean; captures_dir: string
  // DASHBOARD-2 (Lot 4) — bilan du dernier dépôt (persistant) + « Le flux ».
  dernier_depot: { date_depot: string | null; nom_fichier: string | null; nb_annonces: number | null
    nb_nouvelles: number | null; nb_maj: number | null; nb_a_qualifier: number | null } | null
  flux: { en_vie: number; biens: number; rattachees: number; paires: number; copros_non_servies: number }
  // RADAR-FIX-1 (3) — dernière capture AUTOMATIQUE de l'extension + drapeau « Déposer Radar » (> 26 h).
  capture_auto: { captured_at: string | null; pages: number; nouvelles: number } | null
  capture_auto_en_retard: boolean
}
export const radarDeposer = (lien: string, image_b64: string, media_type: string) =>
  j<RadarProposition>('/admin/radar/deposer', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ lien, image_b64, media_type }),
  })
// RADAR-HTML (Lot 1) — dépôt d'une page de résultats HTML (remplace la capture d'écran + vision).
export interface RadarDepotHtml {
  ok: boolean; erreur?: string; motif?: string
  depot_id?: number; nb_annonces?: number; nb_nouvelles?: number; nb_maj?: number
  nb_a_qualifier?: number; nb_hors_perimetre?: number; etats?: Record<string, number>; archive?: string
}
export const radarDeposerHtml = (html: string, nom_fichier: string | null) =>
  j<RadarDepotHtml>('/admin/radar/deposer-html', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ html, nom_fichier }),
  })
export const radarValider = (bien_id: number, faits: Record<string, unknown>) =>
  j<{ bien_id: number; statut: string; valide: boolean }>('/admin/radar/valider', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bien_id, faits }),
  })
// RADAR-VEILLE-1 (R3) — parcours DÉPÔT AGENCE (derrière drapeau, admin seulement)
export interface DepotRec { list_id?: number; url?: string; type?: string; prix?: number; surface_hab?: number; surface_terrain?: number; pieces?: number; commune?: string; description?: string; photos?: string[] }
export const getRadarDepotAgenceEtat = () => j<{ actif: boolean; admin?: boolean }>('/admin/radar/depot-agence/etat')
// CONNEXIONS-2 Lot 7.1 (N2) — l'admin ouvre/ferme le dépôt agence au dashboard (réglage base, relu à chaud).
export const postRadarDepotAgenceToggle = (actif: boolean) =>
  j<{ ok: boolean; actif: boolean }>('/admin/radar/depot-agence/toggle', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ actif }) })
// SECTEUR-2b (U2) — état PUBLIC du drapeau (lisible par tous) : l'écran Radar de l'app décide d'afficher
// le bouton « Publier une annonce » aux clients quand le drapeau est ouvert.
export const getRadarDepotOuvert = () => j<{ ouvert: boolean }>('/radar/depot-agence/ouvert')
export const radarDepotAgenceAnalyser = (html: string) =>
  j<{ ok: boolean; records?: DepotRec[]; motif?: string }>('/admin/radar/depot-agence/analyser', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ html }),
  })
export const radarDepotAgencePublier = (p: { rec: DepotRec; idu: string; lon?: number; lat?: number; adresse_exacte: string; agence_nom: string }) =>
  j<{ ok: boolean; bien_id?: number; commune?: string; idu?: string; motif?: string }>('/admin/radar/depot-agence/publier', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(p),
  })
export const radarInteresse = (bien_id: number) =>
  j<{ ok?: boolean; agence?: string; motif?: string }>('/radar/interesse', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ bien_id }),
  })
export const getRadarExtraction = () => j<{ file: RadarBrouillon[]; n: number }>('/admin/radar/extraction')
// RADAR-DEPOT-2 (D3) — file d'instruction ADMIN : biens en PISTE, non tranchés à la main.
export interface RadarAInstruire {
  bien_id: number; commune: string; type_bien: string | null; prix: number | null
  surface_terrain: number | null; surface_hab: number | null
  declaratif: RadarDeclaratif | null
  portail: string | null; url_sortante: string | null; n_candidates: number
  // RETOURS-8 (R5) — confiance (forte/faible) + pourquoi (critères convergents) + 1re candidate.
  rattachement_confiance: number | null; confiance: 'forte' | 'faible'
  rattachement_criteres: RadarCritere[] | null; rattachement_etat: string | null
  premiere_piste: RadarPiste | null
}
export const getRadarAInstruire = () => j<{ file: RadarAInstruire[]; n: number }>('/admin/radar/a-instruire')
export const getRadarReverif = () => j<{ file: RadarReverif[]; n: number }>('/admin/radar/reverif')
export const getRadarCheck = () => j<RadarCheck>('/admin/radar/check')
export const radarToujoursEnLigne = (bien_id: number) =>
  j<{ ok: boolean }>('/admin/radar/toujours-en-ligne', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ bien_id }) })
export const radarPrix = (bien_id: number, prix: number) =>
  j<{ ok: boolean }>('/admin/radar/prix', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ bien_id, prix }) })
export const radarRetiree = (bien_id: number) =>
  j<{ ok: boolean }>('/admin/radar/retiree', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ bien_id }) })

// ── RADAR (pige) · P3 C1 — écran CLIENT (faits + lien, jamais le contenu de l'annonce) ──
export interface RadarBienClient {
  bien_id: number; commune: string; type_bien: string | null; est_copro: boolean; statut: string
  // RADAR-RECETTE-1 D1c — bien incohérent : visible mais marqué, motifs consultables, jamais rattaché.
  a_qualifier: boolean; a_qualifier_motifs: string[]
  rattachement: { niveau: 'source' | 'estime' | 'absent'; idu: string | null; confiance: number | null; preuve?: 'certain' | 'probable' | 'quartier' }
  coords: [number, number] | null
  // RADAR-AUTO-1 (recette) — position servie : parcelle (rattaché) ou QUARTIER (position floutée du
  // portail, marqueur distinct sur la carte) ou absente. `quartier` = nom du quartier si approximatif.
  position_type: 'parcelle' | 'quartier' | 'absente'; quartier: string | null
  faits: { prix: number | null; pieces: number | null; surface_hab: number | null; surface_terrain: number | null; dpe_classe: string | null; dpe_conso: number | null; dpe_ges: number | null; particulier_pro: string | null }
  etiquettes: Record<string, string>; fraicheur_source: string | null
  date_publication: string | null; date_saisie: string | null; date_derniere_confirmation: string | null
  portail: string; url_sortante: string; annonce_id: number | null; baisse: boolean
  // RADAR-2 (Lot 2) — pastilles de la liste : ancien prix (barré) + % de la dernière baisse ; « de retour »
  // (annonce ré-activée après un retrait sans vente). Servis à plat par le back (jamais recalculés au front).
  ancien_prix: number | null; baisse_pct: number | null; de_retour: boolean
  // FRONT-CHIFFRES-2 (F14) — « nouveau » servi à plat (seuil back SEUIL_NOUVEAU_J) ; « en vente
  // longue » se lit sur `statut` (cycle back, seuil SEUIL_VENTE_LONGUE_J) — le front ne recalcule plus.
  nouveau: boolean
  // RADAR-DEPOT-2 D2 — faits DÉCLARÉS par le vendeur (zone PLU, drapeaux), « déclaré dans l'annonce ».
  declaratif: RadarDeclaratif | null; provenance: string | null
  // RADAR-DEPOT-2 D4 — badge « sous le marché » (null si non applicable/au-dessus du seuil).
  sous_le_marche: RadarSousMarche | null
  // RADAR-VEILLE-1 (R3) — annonce DÉPOSÉE par une agence : contenu confié affiché (photos/texte/adresse
  // abonnés-seuls). Le collecté a photos=[] / description=null (doctrine « faits + lien » intacte).
  depose_par_agence: boolean; agence_nom: string | null; adresse_exacte: string | null
  photos: string[]; description: string | null
}
export interface RadarDeclaratif {
  zone_plu: string[]
  cos_ces: { type: string; valeur: string } | null
  emprise_sol_pct: number | null
  drapeaux: { a_renover: boolean; a_demolir: boolean; succession: boolean; lotissement: boolean; lotissement_nom: string | null; viabilise: boolean }
}
export interface RadarSousMarche {
  // calculable: true = verdict rendu ; false = €/m² affiché mais pas de verdict (motif porté) ; null jamais servi
  calculable: boolean | null; affiche_eur_m2: number; referentiel_eur_m2?: number; n_referentiel?: number
  millesime_dvf?: string | null; zone?: string | null; perimetre?: string | null
  ecart_pct?: number; sous_le_marche?: boolean; sens?: string
  // RADAR-VEILLE-1 (R2) — référence du même type, garde biais terrain, formulation non ambiguë
  ecart_libelle?: string; meme_type_reference?: boolean; part_fonciere?: number | null; motif?: string
}
export interface RadarBienDetail extends RadarBienClient {
  historique_prix: { date: string | null; ancien: number | null; nouveau: number | null }[]
  // RADAR-HTML (Lot 3) — état de rattachement + candidates de PISTE (servis au détail seulement).
  rattachement_etat?: 'rattachee' | 'piste' | 'non_rattachee'
  pistes?: RadarPiste[]
  // RATTACHEMENT-V2 — critères convergents (pourquoi RATTACHÉE) + rattachement tranché à la main.
  rattachement_criteres?: RadarCritere[]
  rattachement_humain?: boolean
}
export interface RadarBiensRep { biens: RadarBienClient[]; n_total: number; n_servi: number; n_rattaches: number; n_carte: number; page: number; taille: number; plafond: number; tronquee: boolean; tri: string }
export interface RadarFiltres {
  commune?: string; type_bien?: string; prix_min?: number; prix_max?: number
  surface_hab_min?: number; surface_hab_max?: number; surface_terrain_min?: number; surface_terrain_max?: number
  particulier_pro?: string; statuts?: string[]; periode_debut?: string; periode_fin?: string
  rattache?: 'oui' | 'non'; sous_marche?: 'oui' | 'non'
}
export const getRadarBiens = (f: RadarFiltres, tri = 'recentes', page = 1, taille = 60) => {
  const p = new URLSearchParams()
  const set = (k: string, v: unknown) => { if (v !== undefined && v !== null && v !== '') p.set(k, String(v)) }
  set('commune', f.commune); set('type_bien', f.type_bien); set('prix_min', f.prix_min); set('prix_max', f.prix_max)
  set('surface_hab_min', f.surface_hab_min); set('surface_hab_max', f.surface_hab_max)
  set('surface_terrain_min', f.surface_terrain_min); set('surface_terrain_max', f.surface_terrain_max)
  set('particulier_pro', f.particulier_pro); set('rattache', f.rattache); set('sous_marche', f.sous_marche)
  set('periode_debut', f.periode_debut); set('periode_fin', f.periode_fin)
  if (f.statuts?.length) set('statuts', f.statuts.join(','))
  set('tri', tri); set('page', page); set('taille', taille)
  return j<RadarBiensRep>(`/radar/biens?${p.toString()}`)
}
export const getRadarBienDetail = (bienId: number) => j<RadarBienDetail>(`/radar/biens/${bienId}`)
export const radarClic = (bien_id: number, annonce_id?: number | null) =>
  j<{ ok: boolean; clic_id: number }>('/radar/clic', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ bien_id, annonce_id: annonce_id ?? null }) })
export const radarSignaler = (bien_id: number, motif = '') =>
  j<{ ok: boolean; event_id: number }>('/radar/signaler', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ bien_id, motif }) })
// RADAR-HTML (Lot 3) + V2 (Lot 2) — « Instruire » : candidates ENRICHIES (ortho + critères par candidate).
export interface RadarCritere { critere: string; valeur: string; converge?: boolean }
// RETOURS-9 (Q7) — les faits de la candidate, lus tels quels de la fiche parcelle (aucun calcul neuf).
export interface RadarCandidateFiche {
  surface_cadastrale: number | null; surface_bati: number | null; n_batiments: number | null
  zone_plu: string | null; adresse_ban: string | null
}
export interface RadarPiste {
  idu: string; distance_m?: number | null; n_criteres?: number
  criteres?: RadarCritere[]                 // critères convergents (cascade)
  criteres_detail?: RadarCritere[]          // chaque critère applicable : converge (✓) ou diverge (✗)
  ortho_url?: string | null                 // vignette BD ORTHO 20 cm de la candidate
  fiche?: RadarCandidateFiche | null        // RETOURS-9 (Q7) — faits candidate pour trancher côte à côte
}
// RADAR-DEPOT-2 (D3) — l'Instruire et le rattachement humain sont ADMIN SEULEMENT (endpoints /admin/…).
export const radarInstruire = (bien_id: number) =>
  j<{ ok: boolean; bien_id: number; etat: string; humain?: boolean; candidates: RadarPiste[]; criteres?: RadarCritere[]; motif?: string | null }>(
    '/admin/radar/instruire', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ bien_id }) })
export const radarRattacherHumain = (bien_id: number, idu: string) =>
  j<{ ok: boolean; bien_id: number; idu: string; etat: string; humain: boolean; motif?: string }>(
    '/admin/radar/rattacher-humain', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ bien_id, idu }) })

// ── RADAR (pige) · P6 D3 — onglet Marché (stats par commune, honnêteté statistique) ──
export interface RadarMesure { valeur: number | null; n: number; insuffisant: boolean }
export interface RadarMarcheLigne {
  commune: string; actives: number; nouvelles_30j: number; retirees_30j: number; vendues_90j: number
  prix_m2_terrain: RadarMesure; prix_m2_bati: RadarMesure; delai_median_j: RadarMesure
  taux_echec_pct: RadarMesure; part_particuliers_pct: RadarMesure
}
export interface RadarMarche { communes: RadarMarcheLigne[]; ile: RadarMarcheLigne; seuil_n: number; corpus_total: number; corpus_actif: number; corpus_jeune: boolean }
export const getRadarMarche = () => j<RadarMarche>('/radar/marche')
// RADAR-HTML (Lot 4) — signaux croisés d'une commune (écart demandé/acté + annonces actives).
export interface RadarEcart {
  calculable: boolean; demande_eur_m2: number | null; n_demande: number
  acte_eur_m2: number | null; n_acte: number; millesime_dvf: string | null
  ecart_pct?: number; sens?: string; motif?: string
}
export interface RadarSignaux {
  commune: string; actives: number
  // RADAR-DEPOT-2 D5 — chaque famille DIT son périmètre (bâti = maisons + appartements).
  perimetre_terrain?: string; perimetre_bati?: string
  prix_m2_terrain: RadarMesure & { perimetre?: string }; prix_m2_bati: RadarMesure & { perimetre?: string }
  ecart_demande_acte: { commune: string; perimetre_terrain?: string; perimetre_bati?: string; terrain: RadarEcart; bati: RadarEcart }
}
export const getRadarSignaux = (commune: string) => j<RadarSignaux>(`/radar/signaux/${encodeURIComponent(commune)}`)

// veille Radar (P4)
export interface RadarVeille { id: number; nom: string | null; commune: string | null; criteria: Record<string, unknown>; created_at: string | null }
export const getRadarVeilles = () => j<{ veilles: RadarVeille[] }>('/radar/veille')
export const creerRadarVeille = (criteria: Record<string, unknown>) =>
  j<{ ok: boolean; veille_id: number }>('/radar/veille', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(criteria) })
export const supprimerRadarVeille = (id: number) =>
  j<{ ok: boolean }>(`/radar/veille/${id}`, { method: 'DELETE' })
// RETOURS-11 A7 — renommer une veille Radar (nom vide = retour au résumé des critères).
export const renommerRadarVeille = (id: number, nom: string) =>
  j<{ ok: boolean }>(`/radar/veille/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nom }) })

// ── RADAR-2 — le hub (deux portes) + les alertes (pause / nouveaux depuis hier) ──
export interface RadarApercu {
  biens_en_vente: number; derniere_capture_at: string | null
  suivis_n: number; alertes_n: number; nouveaux_total: number
}
export const getRadarApercu = () => j<RadarApercu>('/radar/apercu')
export interface RadarAlerte {
  id: number; nom: string | null; commune: string | null; criteria: Record<string, unknown>
  created_at: string | null; en_pause: boolean; paused_at: string | null; nouveaux: number
}
export const getRadarAlertes = () => j<{ alertes: RadarAlerte[]; nouveaux_total: number }>('/radar/alertes')
export const pauseRadarVeille = (id: number, en_pause: boolean) =>
  j<{ ok: boolean; en_pause: boolean }>(`/radar/veille/${id}/pause`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ en_pause }) })

// ── RADAR-2 (Lot 3) — le marché (colonne de droite) : 4 chiffres + table par type + 30 j + écart/commune ──
export interface RadarMarcheChiffre { valeur: number | null; n: number; sous_seuil: boolean; periode?: string | null }
// RADAR-FIX-3 — palier d'un écart : 'normal' ≥30 annonces · 'indicatif' 5–29 (gris) · 'insuffisant' <5.
export type EcartNiveau = 'normal' | 'indicatif' | 'insuffisant'
export interface RadarMarcheTypeLigne {
  type: 'terrain' | 'maison' | 'appartement'; en_vente: number
  demande_eur_m2: number | null; acte_eur_m2: number | null
  ecart_pct: number | null; ecart_niveau: EcartNiveau; ecart_sous_seuil: boolean; ecart_n: number
  sup_90j: number; baisses_30j: number
}
export interface RadarMarcheEcartCommune { commune: string; ecart_pct: number; niveau: EcartNiveau; n: number }
export interface RadarMarcheTableau {
  scope: string; commune: string | null
  prix_demande_median_eur_m2: RadarMarcheChiffre      // maisons
  prix_acte_median_eur_m2: RadarMarcheChiffre         // maisons, DVF (moteur fiche commune)
  ecart_demande_acte_pct: number | null; ecart_sous_seuil: boolean; ecart_niveau: EcartNiveau; ecart_n: number
  biens_en_vente: number; biens_sup_90j: number
  par_type: RadarMarcheTypeLigne[]
  bouge_30j: { nouvelles: number; baisses: number; retirees: number; de_retour: number }
  ecart_par_commune: RadarMarcheEcartCommune[]
  seuil_ecart_n: number; seuil_indicatif_n: number; millesime_dvf: string | null; derniere_capture_at: string | null
}
export const getRadarMarcheTableau = (commune?: string) =>
  j<RadarMarcheTableau>(`/radar/marche-tableau${commune ? `?commune=${encodeURIComponent(commune)}` : ''}`)

// RADAR-2 (recette) — « Ce bien face à son marché » (colonne de droite quand une annonce est sélectionnée)
export interface RadarBienCmp { median: number | null; n: number; ecart_pct: number | null; niveau: EcartNiveau; sous_seuil: boolean }
export interface RadarBienVsMarche {
  bien_id: number; commune: string; type_bien: string | null; prix: number | null; eur_m2: number | null
  demande: RadarBienCmp; acte: RadarBienCmp
  anciennete_j: number | null; anciennete_mediane_j: number | null; anciennete_n: number; anciennete_sous_seuil: boolean
  historique_prix: { date: string | null; ancien: number | null; nouveau: number | null }[]
  url_sortante: string; portail: string; seuil_n: number; introuvable?: boolean
}
export const getRadarBienVsMarche = (bienId: number) => j<RadarBienVsMarche>(`/radar/biens/${bienId}/vs-marche`)

// CRON-2 (K7) — la page CRON de l'admin (état des jobs planifiés)
export interface CronJob {
  nom: string; titre: string; cadence: string; cron_utc: string; heure_reunion: string
  timeout_s: number; envoie_mail: boolean
  prochaine_utc: string | null; prochaine_reunion: string | null
  dernier: { statut: string | null; fin: string | null; duree_s: number | null; dry_run: boolean | null; compteurs: Record<string, unknown> | null; erreur: string | null }
}
export interface Mairie { insee: string | null; commune: string; nom: string | null; adresse: string | null; code_postal: string | null; telephone: string | null; email: string | null; site_officiel: string | null; url_annuaire: string | null; source: string; date_import: string | null; contacts?: CommuneContact[] }
export interface Epci { code: string; nom: string | null; communes: string[] }
export interface AutreContact { type: string; nom: string; adresse: string; telephone: string; site: string }
export interface ContactsInstitutionnels { mairies: Mairie[]; epci: Epci[]; autres: AutreContact[]; note: string }
export const getContactsInstitutionnels = () => j<ContactsInstitutionnels>('/admin/contacts-institutionnels')

// ADMIN-1 (AD10) — carnet des contacts NOMMÉS d'une commune (au-delà du standard officiel).
export interface CommuneContact {
  id: number; insee: string; commune_nom: string | null; nom: string; role: string | null
  telephone: string | null; email: string | null; note: string | null; cree_le: string | null; cree_par: string | null
}
export interface CommuneContactIn {
  insee: string; commune_nom?: string | null; nom: string; role?: string | null
  telephone?: string | null; email?: string | null; note?: string | null
}
// Lecture OUVERTE (fiche commune, tous comptes) : contacts d'une commune par INSEE.
export const getCommuneContacts = (insee: string) =>
  j<{ contacts: CommuneContact[] }>(`/communes/${encodeURIComponent(insee)}/contacts`)
// ADMIN — tous les contacts groupés par commune (page Contacts).
export const getAdminCommuneContacts = () =>
  j<{ communes: Array<{ insee: string; commune_nom: string | null; contacts: CommuneContact[] }> }>('/admin/commune-contacts')
export const postCommuneContact = (body: CommuneContactIn) =>
  j<{ ok: boolean; contact: CommuneContact }>('/admin/commune-contacts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
export const patchCommuneContact = (id: number, body: Partial<CommuneContactIn>) =>
  j<{ ok: boolean; contact: CommuneContact }>(`/admin/commune-contacts/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
export const deleteCommuneContact = (id: number) =>
  j<{ ok: boolean }>(`/admin/commune-contacts/${id}`, { method: 'DELETE' })

// SECTEUR-2b (U1) — panneau de détail d'une commune de la couche VEFA (clic carte).
export interface VefaDetail {
  insee: string; commune: string | null; peinte: boolean
  mediane_eur_m2: number | null; n_ventes: number; fenetre_mois: number; seuil: number
  tendance_12m: { pct: number; n_12m: number; sens: string } | null
  repartition: { appartements: number; maisons: number }
  par_taille: { disponible: boolean; motif: string }
  offre_engagee: { logements: number | null; permis: number | null; mois: number; libelle: string }
  millesime: string; source: string
}
export const getVefaDetail = (ref: string) => j<VefaDetail>(`/outils/vefa-neuf/${encodeURIComponent(ref)}`)

export const getAdminCron = () => j<{ jobs: CronJob[]; note: string }>('/admin/cron')
export const getAdminCronLog = (nom: string) => j<{ nom: string; lignes: string[]; note?: string }>(`/admin/cron/${encodeURIComponent(nom)}/log`)
export const postAdminCronRun = (nom: string) =>
  j<{ ok: boolean; nom?: string; note?: string; motif?: string }>(`/admin/cron/${encodeURIComponent(nom)}/run`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })

// ── CIRCUIT-1 lot 5 — la page Circuit (un appel) + ses gestes ──────────────────────────────
export const getAdminCircuit = () => j<any>('/admin/circuit')
// COHERENCE-FIX-1 (lot A) — fraîcheur des caches (clé attendue / clé réelle / périmé), page Données.
export interface CacheFraicheur {
  cache: string; porte_sur?: string; cle_attendue?: string; cle_reelle?: string | null
  perime: boolean; detail?: string; remede?: string; erreur?: string
}
export const getSanteFraicheur = () =>
  j<{ empreinte_attendue: string; perimes: string[]; caches: CacheFraicheur[] }>('/sante/fraicheur')
// COHERENCE-FIX-1 (lot G) — les passages du banc de cohérence (onglet Cohérence, page Données).
export const getAdminCoherence = () => j<any>('/admin/coherence')
export const postAdminCircuitVerifier = () => j<any>('/admin/circuit/verifier', { method: 'POST' })
// CIRCUIT-P2 (lot 3.2/3.3) / CIRCUIT-P7 — tâches longues : lancer l'agent LLM (une source via
// `sourceId`, ou une portée « sans_amont » (défaut) / « g8 » / « tous » depuis la carte Agents).
export const postAdminCircuitAgents = (opts?: { sourceId?: number; portee?: 'sans_amont' | 'g8' | 'tous' }) => {
  const p = new URLSearchParams()
  if (opts?.sourceId != null) p.set('source_id', String(opts.sourceId))
  if (opts?.portee) p.set('portee', opts.portee)
  const s = p.toString()
  return j<any>(`/admin/circuit/agents${s ? '?' + s : ''}`, { method: 'POST' })
}
// CIRCUIT-P7 (lot 1) — « Sonder maintenant » : un passage de la sentinelle (toutes les sources, ou une).
export const postAdminCircuitSonder = (sourceId?: number) =>
  j<any>(`/admin/circuit/sonder${sourceId != null ? `?source_id=${sourceId}` : ''}`, { method: 'POST' })
// DASHBOARD-4 (D2) — rejouer « labuse circuit verrous » à la demande depuis le Résumé (tâche détachée).
export const postAdminCircuitVerrous = () => j<any>('/admin/circuit/verrous', { method: 'POST' })
export const getAdminCircuitTaches = () => j<any>('/admin/circuit/taches')
export const postAdminCircuitPurger = () => j<any>('/admin/circuit/purger-runs', { method: 'POST' })
export const postAdminCircuitRevenir = () => j<any>('/admin/circuit/revenir', { method: 'POST' })
export const getAdminCircuitNoteVersion = (candidat: string) =>
  j<any>(`/admin/circuit/note-version?candidat=${encodeURIComponent(candidat)}`)
// CIRCUIT-3 lot 5.2 — gestes du filtre : servir quand même une quarantaine, revenir à la précédente.
export const postAdminCircuitFiltreServir = (source: string, motif = '') =>
  j<any>(`/admin/circuit/filtre/servir-quand-meme?source=${encodeURIComponent(source)}&motif=${encodeURIComponent(motif)}`, { method: 'POST' })
export const postAdminCircuitFiltreRevenir = (source: string) =>
  j<any>(`/admin/circuit/filtre/revenir?source=${encodeURIComponent(source)}`, { method: 'POST' })
// CIRCUIT-P — journal filtrable/paginé + pages de détail (un appel chacun).
export const getAdminCircuitJournal = (p: { type?: string; depuis?: string; page?: number; taille?: number } = {}) => {
  const q = new URLSearchParams()
  if (p.type) q.set('type', p.type)
  if (p.depuis) q.set('depuis', p.depuis)
  if (p.page) q.set('page', String(p.page))
  if (p.taille) q.set('taille', String(p.taille))
  const s = q.toString()
  return j<any>(`/admin/circuit/journal${s ? '?' + s : ''}`)
}
// CIRCUIT-P2 (lot 2.2) — la page de détail du compteur de réservoirs (68 par état + non servies).
export const getAdminCircuitCompteur = () => j<any>('/admin/circuit/compteur')
export const getAdminCircuitReservoir = (id: number) => j<any>(`/admin/circuit/reservoir/${id}`)
export const getAdminCircuitRobinet = (id: string) => j<any>(`/admin/circuit/robinet/${encodeURIComponent(id)}`)
export const getAdminCircuitPompe = () => j<any>('/admin/circuit/pompe')

// EXPORTS-2 lot 4 — le questionnaire du Financier (4 écrans, saisies persistées par compte+IDU).
export interface QChampPrefill { valeur: unknown; source: string }
export interface QChamp {
  id: string; libelle: string; unite: string; type: string
  domaine: string[] | null; obligatoire: boolean; prefill: QChampPrefill | null
  aide?: string | null   // RECETTE-5 (V19) — le « i » : ce qu'on attend comme valeur
  tri?: 'garder' | 'affiner' | 'supprimer'   // RECETTE-10 T2b — tri des questions
}
export interface QEcran { titre: string; champs: QChamp[] }
// RECETTE-6 (E5) — écran 0 « Que voulez-vous chiffrer ? ». Seul `construction` est servi ; les autres
// usages sont grisés avec leur `raison` (pas de moteur inventé).
export interface QUsage { key: string; label: string; servi: boolean; sous?: string; raison?: string }
// RECETTE-9 T1 — d'où vient la surface vendable du bilan : chiffrée par le potentiel (rien à saisir)
// ou à décrire par le porteur (logements + typologie deviennent indispensables).
export interface QProgramme { auto: boolean; source: 'potentiel' | 'saisie'; message: string }
export interface QuestionnaireFinancier {
  idu: string; reponses: Record<string, unknown>; complet: boolean; existe: boolean
  ecrans: QEcran[]; usages?: QUsage[]; tva_explication: string; champs_obligatoires: string[]
  // RECETTE-8 W13bis (C3) — les écrans PAR usage : le front sert le questionnaire du parcours choisi.
  ecrans_par_usage?: Record<string, QEcran[]>; champs_obligatoires_revente?: string[]
  programme?: QProgramme   // RECETTE-9 T1 — programme constructible : potentiel vs à saisir
  // FRONT-CHIFFRES-2 (F04) — bornes du garde « hors marché » servies depuis la source unique
  // (faisabilite/engine.py) : le front ne code plus 20000/8000/12000, il les lit.
  hors_marche_bornes?: { prix_sortie_saisi_eur_m2: number; cout_construction_saisi_eur_m2: number; prix_vente_bailleur_saisi_eur_m2: number }
}
export const getFinancierQuestionnaire = (idu: string) =>
  j<QuestionnaireFinancier>(`/financier/${encodeURIComponent(idu)}/questionnaire`)
export const putFinancierQuestionnaire = (
  idu: string, reponses: Record<string, unknown>, projet_id?: number | null,
) =>
  j<{ idu: string; reponses: Record<string, unknown>; complet: boolean; existe: boolean }>(
    `/financier/${encodeURIComponent(idu)}/questionnaire`,
    { method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reponses, ...(projet_id != null ? { projet_id } : {}) }) })

// RECETTE-11 B2 — le garde du questionnaire : une saisie hors marché (prix > borne, ou bailleur >
// prix libre) est refusée AVANT tout document, avec l'écran/le champ/l'accordéon à ouvrir.
export interface QHorsMarche {
  champ_id: string | null; champ_libelle: string; ecran: number; affiner: boolean
  valeur: number; borne: number; message: string
}
export const validerFinancierQuestionnaire = (idu: string, reponses: Record<string, unknown>) =>
  j<{ idu: string; hors_marche: QHorsMarche | null }>(
    `/financier/${encodeURIComponent(idu)}/questionnaire/valider`,
    { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reponses }) })
