import type { CrmColumn, Fiche, ParcelResult, PipelineEntry, PipelineMeta, SourceInfo, Stats } from './types'

export interface ParcelFeatureCollection {
  type: 'FeatureCollection'
  features: Array<{ type: 'Feature'; geometry: unknown; properties: Record<string, unknown> }>
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
export const SOURCE = import.meta.env.VITE_RUN_LABEL ?? ''
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
  ...(f.zonePlu.length ? { zone_plu: f.zonePlu.join(',') } : {}),
  // M45 (P2d) — tiroirs éco / mutation / propriété / veille
  ...(f.sousDensite ? { sous_densite: 'true' } : {}),
  ...(f.multMin != null ? { mult_min: f.multMin } : {}),
  ...(f.rangMax != null ? { rang_max: f.rangMax } : {}),
  ...(f.renouvellement ? { renouvellement: 'true' } : {}),
  ...(f.divisionOr ? { division_or: 'true' } : {}),
  ...(f.proprietaireType.length ? { proprietaire_type: f.proprietaireType.join(',') } : {}),
  ...(f.etatSociete.length ? { etat_societe: f.etatSociete.join(',') } : {}),
  ...(f.copro.length ? { copro: f.copro.join(',') } : {}),
  ...(f.npnru ? { npnru: 'true' } : {}),
  ...(f.adresseAbsente ? { adresse_absente: 'true' } : {}),
  // M45-B (L1) — tiroir Économie
  ...(f.budgetMax != null ? { budget_max: f.budgetMax } : {}),
  ...(f.chargeMin != null ? { charge_min: f.chargeMin } : {}),
  ...(f.chargeMax != null ? { charge_max: f.chargeMax } : {}),
  ...(f.prixMarcheMin != null ? { prix_marche_min: f.prixMarcheMin } : {}),
  ...(f.prixMarcheMax != null ? { prix_marche_max: f.prixMarcheMax } : {}),
  ...(f.marcheFiable ? { marche_fiable: 'true' } : {}),
  // M55-D stage 6 — Signaux de vie (OU dans le groupe, ET avec le reste)
  ...(f.signaux.length ? { signaux: f.signaux.join(',') } : {}),
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
  'brulante', 'chaude', 'reserve_fonciere', 'a_creuser',
  'declasse_bati_sature', 'declasse_non_constructible', 'declasse_bati_revele',
  'declasse_zone_fermee', 'declasse_au_statut_inconnu', 'declasse_au_fermee',
]
const tiersParam = (f: Filters): Record<string, string> =>
  f.analyseLabuse
    ? { tiers: (f.tiers.length ? f.tiers : TIERS_ANALYSE).join(',') }   // l'analyse retient (hors exclusions dures)
    : { tiers: [...TIERS_ANALYSE, 'ecartee'].join(',') }               // toute la trame (le cadastre analysé)

export interface FiltreReponse {
  compte: number
  total: number
  tiers: { brulante: number; chaude: number; reserve_fonciere: number; a_creuser: number; ecartee: number }
  opportunites: number
  opportunites_evenement: number
  dossiers_opportunites: number
  opportunites_avec_dossier: number
  opportunites_sans_identite: number
  page: ParcelResult[]
  limit: number; offset: number; sort: string
}
/** Endpoint UNIFIÉ M45 (« théâtre ») : compte exact + ventilation tier + page en un appel. */
export const getFiltre = (f: Filters, limit = 20, sort: SortKey = 'rang', offset = 0, groupes = false) => {
  const { tiers: _t, ...rest } = filterParams(f)   // le tier passe par l'interrupteur (tiersParam)
  return j<FiltreReponse>(`/filtre?${qf({ limit, offset, sort, ...(groupes ? { groupes: 1 } : {}), ...rest, ...tiersParam(f) })}`)
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
export type SortKey = 'rang' | 'mult' | 'surface' | 'surface_asc' | 'commune'

export interface CommuneInfo { commune: string; insee: string; parcelles: number; chaudes: number; evaluees: number; bbox: [number, number, number, number]; note: string | null }
export const getCommunes = () => j<CommuneInfo[]>('/communes')
export interface ContexteCommune {
  commune: string; epci: string | null; epci_nom: string | null
  // M55-C : bandeau RNU générique (null hors commune au règlement national d'urbanisme)
  rnu: { libelle: string; detail: string } | null
  // M83 C1 — le foncier de la commune (points de calcul existants réutilisés)
  foncier: {
    n_parcelles: number; surface_ha: number | null
    repartition_zonage: { U: number; AU: number; A: number; N: number; total: number } | null
    classement: { evaluees: number; sans_zonage: number; raison_sans_zonage: string }
    prix_terrain_nu: { par_zone: Record<string, { median_eur_m2: number | null; n: number | null; calculable: boolean }> | null; calculable: boolean; motif: string | null; seuil_n: number; etiquette: string | null }
    mutations_12m: number
    permis_12m: { n: number; reserve: string }
  } | null
  // M36 Lot D : le compteur du tier haut EN DUR (même point de calcul que /communes)
  classement: { tiers_hauts: number; dossiers: number; libelle: string; source: string } | null
  sru: { taux_lls: number; objectif_pct: number; statut: string; prelevement_eur: number; millesime: string; detail: { nb_lls?: number }; source_nom: string; source_url: string } | null
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
export const getEntonnoir = () => {
  const c = commune()
  return j<Entonnoir>(`/stats/entonnoir${c ? `?commune=${encodeURIComponent(c)}` : ''}`)
}
export const getContexteCommune = (commune: string) =>
  j<ContexteCommune>(`/communes/${encodeURIComponent(commune)}/contexte`)
export const parcelAt = (lon: number, lat: number) =>
  j<{ idu: string | null }>(`/parcels/at?lon=${lon}&lat=${lat}`)
export const searchParcels = (needle: string, opts?: { ileEntiere?: boolean }) =>
  j<{ idu: string; commune: string; status: string | null; q_score: number | null;
      tier_v2: string | null; rang_v2: number | null; etage0: boolean;
      adresse?: string | null }[]>(
    `/parcels/search?q=${encodeURIComponent(needle)}${!opts?.ileEntiere && commune() ? `&commune=${encodeURIComponent(commune()!)}` : ''}`)

// M45-B (L3) — UNIFICATION : compteur/cartouches ET liste passent par /filtre (FiltreCriteres),
// donc portent EXACTEMENT les mêmes facettes que le compteur du panneau. Plus jamais un compteur
// filtré et une liste qui ignore les filtres. `f` absent = univers par défaut (analyse active).
export const getStats = (f?: Filters) => getFiltre(f ?? EMPTY_FILTERS, 0).then((r) => r as unknown as Stats)
// E3 (M12) : `offset` exposé — pagination « Charger plus ». La page vient de /filtre (mêmes facettes).
// M55-H point 5 : `groupes` = liste groupée par tier (mode analyse), tri secondaire dedans
export const getResults = (f?: Filters, limit = 200, sort: SortKey = 'rang', offset = 0, groupes = false) =>
  getFiltre(f ?? EMPTY_FILTERS, limit, sort, offset, groupes).then((r) => r.page)
/** Export CSV de la liste courante — M46 (Lot D) : EXACTEMENT les mêmes facettes + interrupteur
 *  que la liste/compteur (même construction que getFiltre : facettes hors tiers + tiersParam).
 *  Plus jamais un export qui ignore un filtre actif. */
export const csvExportUrl = (f?: Filters, sort: SortKey = 'rang') => {
  const ff = f ?? EMPTY_FILTERS
  const { tiers: _t, ...rest } = filterParams(ff)
  return `/parcels/export.csv?${qf({ limit: 5000, sort, ...rest, ...tiersParam(ff) })}`
}
export const getParcelsGeojson = () =>
  j<ParcelFeatureCollection>(`/map/parcels.geojson?${q({ limit: 60000 })}`)
export const getFiche = (idu: string) => j<Fiche>(`/parcels/${idu}?source=${SOURCE}`)

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
}
export const pluAnnuaireSearch = (qy: string, insee?: string, zone?: string) =>
  j<PluSearch>(`/modules/plu-annuaire/search?q=${encodeURIComponent(qy)}${insee ? `&insee=${insee}` : ''}${zone ? `&zone=${encodeURIComponent(zone)}` : ''}`)
export const pluAnnuaireCommunes = () =>
  j<{ n_communes: number; servables: number; communes: PluCommune[] }>(`/modules/plu-annuaire/communes`)

// M33 — recalcul mode B avec le paramètre CLIENT travaux (état UI seulement, rien persisté)
export const getModeB = (idu: string, travauxM2?: number) =>
  j<import('./types').ModeB>(`/parcels/${idu}/mode-b${travauxM2 != null ? `?travaux_m2=${travauxM2}` : ''}`)

// ── R5 (reliquats front) — UI des outils O2/O3 ────────────────────────────────────────────
// O2 · scoreur d'adresse inversé : adresse → parcelle déjà scorée → verdict compact ;
// prix demandé SAISI À LA MAIN (jamais scrapé), confronté à la charge foncière (Score É V2).
export interface ScoreurResult {
  ok: boolean
  adresse: string
  message?: string
  idu?: string
  commune?: string
  surface_m2?: number
  verdict?: { tier: string | null; libelle: string; rang: number | null; percentile: number | null }
  score_e?: { estimable: boolean; marge_estimee: number | null; charge_supportable: number | null
              prix_probable: number | null; niveau_prix: string | null; libelle_court: string } | null
  prix?: { prix_demande_eur: number; prix_demande_m2_terrain?: number; marge_a_ce_prix_eur?: number
           verdict: string; message: string; avertissement: string }
}
export const scoreurAdresse = (adresse: string, prixDemandeEur: number | null, idu?: string | null) =>
  j<ScoreurResult>('/scoreur-adresse', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ q: adresse, prix_demande_eur: prixDemandeEur, idu: idu ?? null }),
  })

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

// O3 · anti-fiche « pourquoi pas » : motifs d'écartement hiérarchisés, sourcés (cascade servie).
export interface AntiFicheMotif { couche: string; motif: string; source: string }
export interface AntiFiche {
  idu: string; tier: string | null; cadre: string; synthese: string
  redhibitoire: AntiFicheMotif[]; vigilance: AntiFicheMotif[]
  n_redhibitoire: number; n_vigilance: number; avertissement: string
}
export const getAntiFiche = (idu: string) => j<AntiFiche>(`/anti-fiche/${idu}`)

// M55-E : `limit` exposé — la couche ÉQUIPEMENTS (15 214 objets) dépassait le LIMIT 6000 par
// défaut de l'endpoint → 61 % des marqueurs silencieusement absents en mode île (centre de
// Saint-Denis VIDE alors que la base est pleine). Le payload complet pèse 271 Ko gzippé.
export const getMapLayer = (kind: string, limit?: number) => {
  const c = commune()
  return j<ParcelFeatureCollection>(`/map/layers.geojson?kind=${kind}${c ? `&commune=${encodeURIComponent(c)}` : ''}${limit ? `&limit=${limit}` : ''}`)
}
// M6.1 : capacités des tuiles île — `zonage_parcelle` dit si mvt_parcels embarque zone_fam
// (sinon la couche « Zonage PLU (parcelles) » est grisée en mode île jusqu'au prochain build).
export const getTilesMeta = () => j<{ run_label: string | null; zonage_parcelle: boolean }>('/map/tiles/meta')
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

// M83 B4 — « CETTE SEMAINE » : trois signaux mesurés, avec fraîcheur (un zéro n'est pas une absence).
export interface AccueilCetteSemaine {
  permis: { n_7j: number; frais: boolean; derniere: string | null }
  ventes: { n_7j: number; frais: boolean; dernier_trimestre: string | null; sans_date_publication: boolean }
  communes_procedure_plu: number | null
}
export const getAccueilCetteSemaine = () => j<AccueilCetteSemaine>('/accueil/cette-semaine')

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
  partiel?: boolean
  sources?: string[]
  clarification?: boolean
  degraded?: boolean
  erreur?: boolean          // M102 garde générale /ask — incident serveur (gabarit erreur M117)
  en_construction?: boolean
  web?: boolean                          // M78-ter — réponse issue du web (marquage distinct)
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
}
export const copiloteV2Ask = (message: string, opts?: {
  history?: { role: string; content: string }[]; contexte?: Record<string, unknown>
  conversation_id?: number | null; confirme?: boolean; scenario?: string | null }) =>
  j<CopiloteV2Reponse>('/api/copilote-v2/ask', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, ...opts }) })

// M113 · Phase 2 — les chips de contexte, servis par le serveur (jamais en dur au front).
export interface CopiloteScenario { cle: string; libelle: string; sub: string; placeholder: string }
export const getScenarios = () =>
  j<{ scenarios: CopiloteScenario[] }>('/api/copilote-v2/scenarios').then((r) => r.scenarios)

// §2b — l'historique : missions passées du compte + reprise d'une conversation.
export interface CopiloteMission {
  id: number; titre: string; statut: string; run_id: string | null
  updated_at: string; n_messages: number
}
export interface CopiloteConversation extends CopiloteMission {
  created_at: string
  messages: { role: 'client' | 'copilote'; texte: string; intent: string | null; ts: string }[]
}
export const copiloteV2Missions = () => j<{ missions: CopiloteMission[] }>('/api/copilote-v2/missions')
export const copiloteV2Mission = (id: number) => j<CopiloteConversation>(`/api/copilote-v2/missions/${id}`)

// §2e — le héros : phrase (pourquoi cette parcelle gagne, faiblesses comprises) avec verrou
// anti-invention côté serveur (tout nombre ∈ JSON parcelle, sinon gabarit).
export const copiloteV2Heros = (parcelle: Record<string, unknown>, budget_max_eur?: number | null) =>
  j<{ phrase: string; gabarit: boolean }>('/api/copilote-v2/heros', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ parcelle, budget_max_eur }) })

// §2f — feedback 👍/👎 (le 👎 ouvre un champ libre optionnel).
export const copiloteV2Feedback = (conversation_id: number | null, pouce: 'haut' | 'bas', commentaire?: string) =>
  j<{ ok: boolean }>('/api/copilote-v2/feedback', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ conversation_id, pouce, commentaire }) })

// §4 — veilles : l'écran minimal (liste + suppression). M85 : les notifications produites vivent
// dans le centre unifié (cloche /events), plus dans un store parallèle.
export interface CopiloteVeille { id: number; type: string; commune: string | null }
export const copiloteV2Veilles = () => j<{ veilles: CopiloteVeille[] }>('/api/copilote-v2/veilles')
export const copiloteV2VeilleSupprimer = (id: number) =>
  j<{ ok: boolean }>(`/api/copilote-v2/veilles/${id}`, { method: 'DELETE' })
// M-RENOUV : calque du segment Renouvellement (occupées, potentiel). `total`/`servis`
// voyagent — la légende dit la troncature, jamais un « tout » silencieux.
export type RenouvFC = ParcelFeatureCollection & {
  total: number; servis: number; source: string; run_label: string; maj: string | null
}
export const getRenouvGeojson = () => {
  const c = commune()
  return j<RenouvFC>(`/map/renouvellement.geojson${c ? `?commune=${encodeURIComponent(c)}` : ''}`)
}
export interface RenouvItem {
  idu: string; commune_nom: string; commune_insee: string; renouv_score: number
  comp_potentiel: number; comp_assiette: number; comp_marche: number; comp_divisibilite: number
  code_bati_origine: string; sdp_residuelle_m2: number | null; surface_m2: number | null
  zone_plu: string | null; rang_segment: number; rang_commune: number
}
export interface RenouvListe {
  total: number; n: number; items: RenouvItem[]
  source: string; run_label: string; maj: string | null
  libelle: string; composantes_libelles: Record<string, string>; avertissement: string
}
export const getRenouvListe = (sort: string, communeNom?: string | null) =>
  j<RenouvListe>(`/renouvellement/liste?sort=${sort}&limit=300${communeNom ? `&commune=${encodeURIComponent(communeNom)}` : ''}`)
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
export const spfLetterUrl = (idu: string) => `/parcels/${idu}/spf-letter`

// M54-EXPO-2 Volet C — statuts servis là où les boutons existent (dossier : dispo+quota ; courrier).
export interface DossierStatut { disponible: boolean; raison: string | null; plan: string; illimite: boolean; quota_mois: number | null; utilises_mois: number; restants: number | null }
export const getDossierStatut = () => j<DossierStatut>('/dossier/statut')
export interface CourrierStatut { disponible: boolean; provider: string; tarif: unknown; raison: string | null }
export const getCourrierStatut = () => j<CourrierStatut>('/courrier/statut')
export interface CourrierEnvoi { id: number; ts: string; idu: string | null; adresse: string | null; statut: string; provider: string; prix_eur: number | null; modele: string | null }
export const getCourrierEnvois = () => j<{ envois: CourrierEnvoi[]; n: number }>('/courrier/envois')

// M54-EXPO-2 A7 — shortlist : « sujets à traiter aujourd'hui » du run servi (top parcelles).
export interface ShortlistSujet { idu: string; commune?: string; surface_m2?: number; status?: string | null; tier_v2?: string | null; rang?: number | null; motif?: string | null }
export const getShortlist = (limit = 8) =>
  j<{ commune: string; count: number; candidates_total: number; sujets: ShortlistSujet[] }>(
    `/shortlist?limit=${limit}${commune() ? `&commune=${encodeURIComponent(commune()!)}` : ''}`)

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
  idu: string; commune?: string; section?: string; numero?: string; surface_m2?: number | null
  status?: string | null; tier_v2?: string | null; etage0?: boolean | null; rang_v2?: number | null
  zone?: string | null; constructible?: boolean | null; capacite?: string | null
  sdp_max_m2?: number | null; taux_emprise_pct?: number | null; sdp_residuelle_m2?: number | null; sous_densite?: boolean | null
  ca_bas?: number | null; ca_haut?: number | null; charge_fonciere_m2?: number | null
  terrain_zone_eur_m2?: number | null; contrainte_majeure?: string | null   // M82
  n_contraintes?: number; contraintes?: string[]; synthese?: string | null
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
export const addToPipeline = (idu: string) =>
  j<{ ok: boolean; already: boolean; entry: PipelineEntry }>('/pipeline', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ idu }),
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
export const deletePipeline = (id: number) => j<{ ok: boolean }>(`/pipeline/${id}`, { method: 'DELETE' })

// ── M12 LOT H — colonnes CRM personnalisables (par tenant) ──
const _jsonInit = (method: string, body?: unknown): RequestInit => ({
  method, headers: { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body),
})
export const getCrmColumns = () => j<{ columns: CrmColumn[] }>('/pipeline/columns')
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

// ── Modules outils (Vague 1) ──
export const modDivision = (minScore = 0) => j<{ total: number; items: Record<string, unknown>[] }>(`/modules/division?min_score=${minScore}&limit=300&${cq()}`)
export const modPatrimoineSearch = (q: string) => j<{ siren: string; nom: string; n: number }[]>(`/modules/patrimoine/search?q=${encodeURIComponent(q)}`)
export const modPatrimoine = (siren: string) => j<Record<string, unknown>>(`/modules/patrimoine?siren=${siren}`)
const cq = () => (commune() ? `commune=${encodeURIComponent(commune()!)}` : '')
export const modPermis = (months: number, nature?: string | null, limit = 300, offset = 0) =>
  j<Record<string, unknown>>(`/modules/permis?${cq()}&months=${months}${nature ? `&nature=${nature}` : ''}&limit=${limit}&offset=${offset}`)
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
// M15-G — plus d'héritage du filtre commune global (cq) : le périmètre est choisi DANS l'outil.
export const modBailleur = (commune?: string | null) =>
  j<Record<string, unknown>>(`/modules/bailleur${commune ? `?commune=${encodeURIComponent(commune)}` : ''}`)
export const modFantome = (limit = 300, offset = 0, commune?: string | null) =>
  j<Record<string, unknown>>(`/modules/fantome?${commune ? `commune=${encodeURIComponent(commune)}&` : ''}limit=${limit}&offset=${offset}`)
export const getOrthoEquipements = (idu: string) => j<Record<string, unknown>>(`/ortho/equipements/${idu}`)
export const modCourriers = (idus: string[], contexte: string) =>
  j<{ n: number; courriers: { idu: string; texte?: string; erreur?: string }[]; rappel_identite: string }>('/modules/courriers', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ idus, contexte }) })
// M82 (option B) : « /courrier/demande » retiré (aucune promesse d'envoi). Le courrier généré est
// téléchargeable en PDF — le client l'envoie lui-même.
export const courrierPdf = async (idu: string | null, motif: string, texte: string): Promise<void> => {
  const r = await fetch('/courrier/pdf', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ idu, motif, texte }) })
  if (!r.ok) throw new ApiError('/courrier/pdf', r.status)
  const url = URL.createObjectURL(await r.blob())
  const a = document.createElement('a')
  a.href = url; a.download = `courrier-${idu ?? 'parcelle'}.pdf`
  document.body.appendChild(a); a.click(); a.remove()
  URL.revokeObjectURL(url)
}
export const modDueDiligence = (refs: string) =>
  j<{ n_demandes: number; n_trouvees: number; items: Record<string, unknown>[] }>('/modules/duediligence', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refs }) })

// ── Copilote IA (Vague 2) — jamais d'accès base, filtres validés par schéma côté API ──
export const iaStatus = () => j<{ provider: string; raison: string | null }>('/ia/status')
export const iaSearch = (body: { text: string; history?: { role: string; content: string }[] }) =>
  j<{ stub: boolean; filters?: Record<string, unknown>; cadrage?: Record<string, unknown>; explanation?: string; out_of_scope?: string; criteres_non_appliques?: string[];
      // M11 B2 : réponse AGRÉGÉE (compte/classement) — chiffre SQL-sourcé, pas une liste de parcelles
      aggregate?: boolean; texte?: string; sources?: string[]; provenance?: Record<string, string>; rejected?: boolean;
      data?: { kind: 'count' | 'superlative' | 'distribution'; commune?: string; tier?: string; nombre?: number; classement?: { commune: string; nombre: number }[] } }>('/ia/search', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
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
export const getEvents = () => j<{ unread: number; items: LabuseEvent[] }>('/events?limit=100')
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
export interface SuiviItem { idu: string; depuis: string; commune: string | null; dernier_changement: string | null }
export const getSuivis = () => j<{ suivis: SuiviItem[]; plafond: number }>('/events/suivis')
// M85 / M85-B — préférences par type (registre) et par canal (cloche / e-mail). `verrou` = non
// désactivable (maintenance : e-mail toujours actif, conséquences réelles).
export interface NotifPref { key: string; label: string; cloche: boolean; email: boolean; verrou?: boolean }
export const getNotifPrefs = () => j<{ types: NotifPref[] }>('/events/prefs')
export const patchNotifPref = (p: { pref_type: string; cloche: boolean; email: boolean }) =>
  j<{ ok: boolean }>('/events/prefs', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(p) })
export const getEventsCount = () => j<{ unread: number; par_parcelle: Record<string, number> }>('/events/count')
export const markEventRead = (id: number) => j<{ ok: boolean }>(`/events/${id}/read`, { method: 'POST' })
export const markAllEventsRead = () => j<{ ok: boolean }>('/events/read-all', { method: 'POST' })
export const getWatch = (idu: string) => j<{ watched: boolean }>(`/events/watch/${idu}`)
export const toggleWatch = (idu: string) => j<{ watched: boolean }>(`/events/watch/${idu}`, { method: 'POST' })
export const getSavedSearches = () => j<{ id: number; nom: string; hash: string; date: string }[]>('/events/searches')
export const saveSearch = (nom: string, hash: string) =>
  j<{ ok: boolean }>('/events/searches', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nom, hash }) })
export const deleteSearch = (id: number) => j<{ ok: boolean }>(`/events/searches/${id}`, { method: 'DELETE' })
// M52 L5 — renommer une vue sauvegardée (compte-scopé).
export const renameSearch = (id: number, nom: string) =>
  j<{ ok: boolean }>(`/events/searches/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nom }) })
// M17-B : veille en langage naturel — traduction réutilisée (schéma), garde-fou déclenchable côté back.
export const veilleNL = (text: string) =>
  j<{ ok: boolean; refus?: string; indeclenchable?: boolean; filters?: Record<string, unknown>; resume?: string; ignores?: string[] }>(
    '/events/veille-nl', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) })

// ── M16-C : menu compte (identité + palier RÉEL) + « proposer une amélioration » ──
export interface Moi { mode: 'pilote' | 'compte'; plan: string; plan_label: string; plan_par_compte: boolean; role?: string; statut_compte?: string }
export const getMoi = () => j<Moi>('/moi')
export const postSuggestion = (body: { categorie: string; texte: string; contexte?: string }) =>
  j<{ ok: boolean }>('/suggestions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

// ── Moteurs (Vague 4) ──
export const motSimulPluZones = () => j<{ zone: string; n_ilots: number }[]>(`/moteurs/simulplu/zones?${cq()}`)
export const motSimulPlu = (zone: string) => j<Record<string, any>>(`/moteurs/simulplu?zone=${encodeURIComponent(zone)}&${cq()}`)
export const motAssemblage = (idus: string[]) =>
  j<Record<string, any>>('/moteurs/assemblage', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ idus }) })
export const motZan = () => j<Record<string, any>>('/moteurs/zan')
export const zanParcelle = (idu: string) => j<Record<string, any>>(`/moteurs/zan/parcelle/${idu}`)
export const motBarometre = () => j<Record<string, any>>('/moteurs/barometre')
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
// M11 Surface C : explication IA de la dérivation du chiffrage (ancrée sur les steps, sur clic).
export const faisabiliteExplain = (idu: string) =>
  j<{ disponible: boolean; rejected?: boolean; degraded?: boolean; texte?: string; message?: string;
      sources?: string[]; provenance?: Record<string, string>; cached?: boolean }>(`/modules/faisabilite/${idu}/explain`)

// M-Q P1-16 — défauts d'hypothèses de la calculette servis par l'API (source unique côté serveur,
// dérivés du YAML). Le front ne grave plus 2500 : il seed ses champs depuis ici → calculette,
// Dossier banquier et Note de financement portent le même coût par défaut sur la même parcelle.
export interface CalculetteDefaults { cout_construction_m2: number; marge_frais_pct: number }
export const getCalculetteDefaults = () =>
  j<CalculetteDefaults>('/bilan/calculette-defaults')

// Calculette de charge foncière (mandat bilan-calculette) : LABUSE calcule le déterministe
// (SDP, prix DVF) ; le coût de construction et la marge sont les hypothèses SAISIES.
// M22-A : mode 'achat_max' = la même équation lue à l'envers (prix d'achat max admissible).
export interface ChargeIn { cout_construction_m2: number; marge_frais_pct: number; prix_demande_eur?: number | null; mode?: 'charge' | 'achat_max' }
export const postChargeFonciere = (idu: string, body: ChargeIn) =>
  j<Record<string, any>>(`/modules/faisabilite/${idu}/charge`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  })
export const postProgramme = (body: Record<string, unknown>) =>
  j<Record<string, any>>('/modules/programme', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

// ── Projets (copilote-projet) — l'objet persistant de l'entretien de cadrage ──
// M120 — le CADRAGE d'un projet EST un jeu de filtres (le même objet que la carte). L'IDENTITÉ
// porte les infos indicatives (budget/type/date) qui n'alimentent AUCUN filtre.
export type Cadrage = Partial<Filters>
export interface Identite {
  budget_eur?: number | null          // indicatif — sans effet sur la sélection
  type_logement?: string | null       // indicatif (le moteur ne distingue pas par type)
  date_livraison?: string | null      // indicatif
}
export interface TypeLogement { cle: string; libelle: string }
export const getProjetTypes = () =>
  j<{ types: TypeLogement[]; informatif: boolean; note: string }>('/projets/types')
// contact proprio (PRIVACY : PM publique nommée OU particulier masqué) — partagé CRM ↔ projet
export type ProprietairePublic =
  | { type: 'personne_morale'; denomination: string; siren: string | null; groupe: string | null }
  | { type: 'particulier' }
export interface ProjetCounts { proposee: number; retenue: number; ecartee: number; a_analyser: number }
// M114 — la vignette d'emprise : centroïdes des parcelles normalisés 0–1 + drapeau retenue (aplat
// mint) ; `commune` sert l'état vide (initiale) quand `points` est vide. Live depuis projet_parcelles.
export interface ProjetVignette { commune: string | null; points: { x: number; y: number; r: boolean }[] }
export interface Projet {
  id: number; nom: string; statut: 'actif' | 'archive'
  cadrage: Cadrage; identite: Identite; shortlist_perimee: boolean   // M120
  created_at: string | null; updated_at: string | null; derniere_execution_at: string | null
  counts?: ProjetCounts   // Lot 4 : mini-compteurs de tri (fiche projet) — depuis projet_parcelles
  vignette?: ProjetVignette   // M114 — schéma d'emprise (64/52 px)
}
// M120 — le diff d'un run (create/rejeu) : ce qui change, dit au client.
export interface ShortlistDiff { ajoutees: number; sorties: number; tris_conserves: number; n_shortlist: number }
// M120 — l'ancien entretien de cadrage IA (ProjetEntretien) a été retiré : un projet se cadre par
// ses facettes (ParcoursProjet → FiltreFacettes), plus par une fiche remplie par l'IA. Le client
// `/ia/entretien` et `/projets/reperes` est parti avec lui (endpoints backend conservés, non appelés).

export const getProjets = () => j<Projet[]>('/projets')
export const getProjet = (id: number) => j<Projet>(`/projets/${id}`)
export interface ProjetDerive { nom: string; cadrage: Cadrage; identite: Identite; sdp_besoin_m2: number | null }
export const deriveProjet = (body: { cadrage: Cadrage; identite?: Identite; nom?: string }) =>
  j<ProjetDerive>('/projets/derive', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
// M120 — créer = FIGER la shortlist en une fois (le run part une fois ; plus de run à l'ouverture).
export const createProjet = (body: { cadrage: Cadrage; identite?: Identite; nom?: string; limit?: number }) =>
  // `existing: true` = dédup douce serveur (projet actif identique) → le front propose la reprise
  j<{ ok: boolean; existing?: boolean; projet: Projet; shortlist?: ShortlistDiff }>('/projets', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
export interface ApercuTop { idu: string; commune: string; statut: string | null; q_score: number | null; pourquoi: string[] }
export interface Apercu { nom: string; n: number; sdp_besoin_m2: number | null; source: string; top: ApercuTop[] }
export const getApercu = (cadrage: Cadrage, identite: Identite = {}, limit = 5) =>
  j<Apercu>('/projets/apercu', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ cadrage, identite, limit }) })
export const projetPdfUrl = (id: number) => `/projets/${id}/export.pdf`
export const patchProjet = (id: number, body: { nom?: string; statut?: string; cadrage?: Cadrage; identite?: Identite }) =>
  j<{ ok: boolean; projet: Projet }>(`/projets/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
// M120 — rejouer À LA DEMANDE : rend le diff (entrées / sorties / tris conservés).
export const rejouerProjet = (id: number) =>
  j<{ ok: boolean; projet: Projet; shortlist: ShortlistDiff; counts: ProjetCounts }>(`/projets/${id}/rejouer`, { method: 'POST' })
export const deleteProjet = (id: number) => j<{ ok: boolean }>(`/projets/${id}`, { method: 'DELETE' })

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
}
// M2 — fusion des doublons : union parcelles + statuts (statut le plus avancé gagne), conflits signalés.
export interface FusionResult { ok: boolean; cible: number; sources_archivees: number[]; n_parcelles: number; conflits: { parcel_id: number; statuts: string[]; retenu: string }[]; counts: ProjetCounts }
export const fusionnerProjets = (ids: number[]) => j<FusionResult>('/projets/fusionner', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ ids }) })
export interface ParcoursEtat {
  nom: string; sdp_besoin_m2: number | null; counts: ParcoursCounts
  proposees: ParcoursItem[]; retenues: ParcoursItem[]; ecartees: ParcoursItem[]; a_analyser: ParcoursItem[]
}
export interface CarteDecision {
  idu: string; adresse: string | null; commune: string; surface_m2: number | null
  tier: string | null; statut: string | null; q_score: number | null; a_score: number | null
  completeness: number | null; center: [number, number] | null
  forces: { titre: string; detail: string }[]; attentions: { titre: string; detail: string }[]
}
export const proposerProjet = (id: number, limit = 24) =>
  j<{ ok: boolean; propose: number; sdp_besoin_m2: number | null; counts: ParcoursCounts }>(
    `/projets/${id}/proposer`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ limit }) })
export const getParcoursEtat = (id: number) => j<ParcoursEtat>(`/projets/${id}/parcelles`)
export const getCarteDecision = (id: number, idu: string) => j<CarteDecision>(`/projets/${id}/carte/${idu}`)
export const setStatutParcelle = (id: number, idu: string, statut: StatutParcelle) =>
  j<{ ok: boolean; idu: string; statut: StatutParcelle; counts: ParcoursCounts }>(
    `/projets/${id}/parcelle/${idu}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ statut }) })
// Phase 2 — chercher plus de parcelles (élargir / ajout manuel), dédupliqué côté serveur
export const chercherPlus = (id: number, body: { limit?: number; surface_min?: number | null; ile?: boolean }) =>
  j<{ ok: boolean; n_added: number; n_search: number; elargi: boolean; counts: ParcoursCounts }>(
    `/projets/${id}/chercher-plus`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
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
