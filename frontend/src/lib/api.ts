import type { Fiche, ParcelResult, PipelineEntry, PipelineMeta, SourceInfo, Stats } from './types'

export interface ParcelFeatureCollection {
  type: 'FeatureCollection'
  features: Array<{ type: 'Feature'; geometry: unknown; properties: Record<string, unknown> }>
}

import { useApp, type Filters } from '../store/useApp'
import { vSignalCodes } from './filters'

// SOURCE DE VÉRITÉ : run servi, CONFIGURABLE (fin du hard-code, clôture A-1). Défaut = q_v7_defisc
// (BASCULE cycle 1 : composante V « fenêtre de sortie de défisc » ; modèle P m8 inchangé, V module le
// seul rang). Override au build : VITE_RUN_LABEL (rollback → 'q_v6_m8', cf. A1_BASCULE_ROLLBACK.md).
// Doit rester aligné sur le backend Q_A_RUN_LABEL (test_run_serving_coherence). JAMAIS parcel_evaluations.
export const SOURCE = import.meta.env.VITE_RUN_LABEL ?? 'q_v7_defisc'
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

const q = (extra: Record<string, string | number> = {}) => {
  const c = commune()
  return new URLSearchParams({
    source: SOURCE, ...(c ? { commune: c } : {}),
    ...Object.fromEntries(Object.entries(extra).map(([k, v]) => [k, String(v)])),
  }).toString()
}

/** Filtres chips → query params serveur (mode île : la liste et les compteurs sont SQL).
 *  M5.1 : `tiers` (v2) pilote — plus jamais `statuts` (matrice) ni `brulantes` (v1.3). */
export const filterParams = (f: Filters): Record<string, string | number> => ({
  ...(f.tiers.length ? { tiers: f.tiers.join(',') } : {}),
  ...(f.scoreMin != null ? { score_min: f.scoreMin } : {}),
  ...(f.surfaceMin != null ? { surface_min: f.surfaceMin } : {}),
  ...(f.surfaceMax != null ? { surface_max: f.surfaceMax } : {}),
  ...(f.sdpMin != null ? { sdp_min: f.sdpMin } : {}),
  ...(f.evenement ? { evenement: 'true' } : {}),
  ...(f.veille ? { veille: 'true' } : {}),
  ...(f.horsCopro ? { hors_copro: 'true' } : {}),
  ...(f.flags.length ? { flags: f.flags.join(',') } : {}),
  ...(f.flagsExclus.length ? { flags_exclus: f.flagsExclus.join(',') } : {}),
  ...(f.communes.length ? { communes: f.communes.join(',') } : {}),
  ...(f.vSignals.length ? { v_signal: vSignalCodes(f.vSignals).join(',') } : {}),
  ...(f.personneMorale ? { personne_morale: 'true' } : {}),        // M11 B2 : propriétaire personne morale
  ...(f.zonagePlu.length ? { zonage: f.zonagePlu.join(',') } : {}), // M11 B2 : zonage PLU (familles U/AU/A/N)
})

/** Tris de la liste (M5.1) : rang P par défaut ; ×N, surface, commune en options. */
export type SortKey = 'rang' | 'mult' | 'surface' | 'commune'

export interface CommuneInfo { commune: string; insee: string; parcelles: number; chaudes: number; evaluees: number; bbox: [number, number, number, number]; note: string | null }
export const getCommunes = () => j<CommuneInfo[]>('/communes')
export interface ContexteCommune {
  commune: string; epci: string | null; epci_nom: string | null
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

export const getStats = (f?: Filters) => j<Stats>(`/stats?${q(f ? filterParams(f) : {})}`)
// E3 (M12) : `offset` exposé — le back le supporte déjà (LIMIT/OFFSET en SQL, top-N sur index).
// Permet la pagination « Charger plus » au lieu du plafond dur de 500.
export const getResults = (f?: Filters, limit = 200, sort: SortKey = 'rang', offset = 0) =>
  j<ParcelResult[]>(`/parcels?${q({ limit, offset, sort, ...(f ? filterParams(f) : {}) })}`)
/** Export CSV de la liste courante (mêmes filtres, même tri) — tier v2 en premier. */
export const csvExportUrl = (f?: Filters, sort: SortKey = 'rang') =>
  `/parcels/export.csv?${q({ limit: 5000, sort, ...(f ? filterParams(f) : {}) })}`
export const getParcelsGeojson = () =>
  j<ParcelFeatureCollection>(`/map/parcels.geojson?${q({ limit: 60000 })}`)
export const getFiche = (idu: string) => j<Fiche>(`/parcels/${idu}?source=${SOURCE}`)

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
export const scoreurAdresse = (adresse: string, prixDemandeEur: number | null) =>
  j<ScoreurResult>('/scoreur-adresse', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ q: adresse, prix_demande_eur: prixDemandeEur }),
  })

// O3 · anti-fiche « pourquoi pas » : motifs d'écartement hiérarchisés, sourcés (cascade servie).
export interface AntiFicheMotif { couche: string; motif: string; source: string }
export interface AntiFiche {
  idu: string; tier: string | null; cadre: string; synthese: string
  redhibitoire: AntiFicheMotif[]; vigilance: AntiFicheMotif[]
  n_redhibitoire: number; n_vigilance: number; avertissement: string
}
export const getAntiFiche = (idu: string) => j<AntiFiche>(`/anti-fiche/${idu}`)

export const getMapLayer = (kind: string) => {
  const c = commune()
  return j<ParcelFeatureCollection>(`/map/layers.geojson?kind=${kind}${c ? `&commune=${encodeURIComponent(c)}` : ''}`)
}
// M6.1 : capacités des tuiles île — `zonage_parcelle` dit si mvt_parcels embarque zone_fam
// (sinon la couche « Zonage PLU (parcelles) » est grisée en mode île jusqu'au prochain build).
export const getTilesMeta = () => j<{ run_label: string | null; zonage_parcelle: boolean }>('/map/tiles/meta')
export const pdfUrl = (idu: string, calc?: { cout_construction_m2: number; marge_frais_pct: number; prix_demande_eur: number | null } | null) => {
  const p = new URLSearchParams({ source: SOURCE })
  if (calc) {
    p.set('cout_construction_m2', String(calc.cout_construction_m2))
    p.set('marge_frais_pct', String(calc.marge_frais_pct))
    if (calc.prix_demande_eur != null) p.set('prix_demande_eur', String(calc.prix_demande_eur))
  }
  return `/parcels/${idu}/export.pdf?${p.toString()}`
}

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

// ── Sources ──
export const getSources = () => j<SourceInfo[]>('/sources')

// ── Modules outils (Vague 1) ──
export const modDivision = (minScore = 0) => j<{ total: number; items: Record<string, unknown>[] }>(`/modules/division?min_score=${minScore}&limit=300&${cq()}`)
export const modPatrimoineSearch = (q: string) => j<{ siren: string; nom: string; n: number }[]>(`/modules/patrimoine/search?q=${encodeURIComponent(q)}`)
export const modPatrimoine = (siren: string) => j<Record<string, unknown>>(`/modules/patrimoine?siren=${siren}`)
const cq = () => (commune() ? `commune=${encodeURIComponent(commune()!)}` : '')
export const modPermis = (months: number, nature?: string | null) =>
  j<Record<string, unknown>>(`/modules/permis?${cq()}&months=${months}${nature ? `&nature=${nature}` : ''}`)
export const modPermisFiche = (permitId: string) =>
  j<Record<string, unknown>>(`/modules/permis/${encodeURIComponent(permitId)}`)
export const modParcellePermis = (idu: string) =>
  j<Record<string, unknown>>(`/modules/parcelle-permis?idu=${encodeURIComponent(idu)}`)
export const modPromesses = (months: number) => j<Record<string, unknown>>(`/modules/promesses?${cq()}&months=${months}`)
export const modVelocite = (nature?: string | null) =>
  j<{ communes: Record<string, unknown>[]; [k: string]: unknown }>(`/modules/velocite${nature ? `?nature=${nature}` : ''}`)
export const modBailleur = () => j<Record<string, unknown>>(`/modules/bailleur?${cq()}`)
export const modFantome = () => j<Record<string, unknown>>(`/modules/fantome?${cq()}`)
export const getOrthoEquipements = (idu: string) => j<Record<string, unknown>>(`/ortho/equipements/${idu}`)
export const modCourriers = (idus: string[], contexte: string) =>
  j<{ n: number; courriers: { idu: string; texte?: string; erreur?: string }[]; rappel_identite: string }>('/modules/courriers', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ idus, contexte }) })
export const courrierDemande = (body: { idu: string | null; motif: string; texte: string }) =>
  j<{ ok: boolean; message: string }>('/courrier/demande', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
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
export const iaSynthese = (idu: string) =>
  j<{ stub: boolean; texte: string; mention: string }>(`/ia/synthese/${idu}`, { method: 'POST' })
export const iaPourquoi = (idu: string) =>
  j<{ stub: boolean; texte: string; mention: string }>(`/ia/pourquoi/${idu}`, { method: 'POST' })

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
export interface LabuseEvent { id: number; date: string; kind: string; idu: string | null; titre: string; detail: string | null; demo: boolean; lu: boolean; statut: string | null }
export const getEvents = () => j<{ unread: number; items: LabuseEvent[] }>('/events?limit=100')
export const getEventsCount = () => j<{ unread: number; par_parcelle: Record<string, number> }>('/events/count')
export const markEventRead = (id: number) => j<{ ok: boolean }>(`/events/${id}/read`, { method: 'POST' })
export const markAllEventsRead = () => j<{ ok: boolean }>('/events/read-all', { method: 'POST' })
export const getWatch = (idu: string) => j<{ watched: boolean }>(`/events/watch/${idu}`)
export const toggleWatch = (idu: string) => j<{ watched: boolean }>(`/events/watch/${idu}`, { method: 'POST' })
export const getSavedSearches = () => j<{ id: number; nom: string; hash: string; date: string }[]>('/events/searches')
export const saveSearch = (nom: string, hash: string) =>
  j<{ ok: boolean }>('/events/searches', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nom, hash }) })
export const deleteSearch = (id: number) => j<{ ok: boolean }>(`/events/searches/${id}`, { method: 'DELETE' })

// ── Moteurs (Vague 4) ──
export const motSimulPluZones = () => j<{ zone: string; n_ilots: number }[]>(`/moteurs/simulplu/zones?${cq()}`)
export const motSimulPlu = (zone: string) => j<Record<string, any>>(`/moteurs/simulplu?zone=${encodeURIComponent(zone)}&${cq()}`)
export const motAssemblage = (idus: string[]) =>
  j<Record<string, any>>('/moteurs/assemblage', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ idus }) })
export const motZan = () => j<Record<string, any>>('/moteurs/zan')
export const zanParcelle = (idu: string) => j<Record<string, any>>(`/moteurs/zan/parcelle/${idu}`)
export const motBarometre = () => j<Record<string, any>>('/moteurs/barometre')

// ── Vague 5 : matching + partage ──
export const getProfiles = () => j<Record<string, any>[]>('/partners/profiles')
export const addProfile = (p: Record<string, unknown>) =>
  j<{ ok: boolean }>('/partners/profiles', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(p) })
export const runMatch = () => j<{ matches: number }>('/partners/match/run', { method: 'POST' })
export const matchCompatibilite = (idu: string) => j<Record<string, any>>(`/partners/match/compatibilite/${idu}`)
export const promoteursActifs = (commune: string) => j<Record<string, any>>(`/partners/promoteurs-actifs?commune=${encodeURIComponent(commune)}`)
export const createShare = (idu: string) => j<{ token: string; url: string }>(`/partners/share/${idu}`, { method: 'POST' })
export const listShares = (idu: string) => j<{ token: string; date: string; views: number }[]>(`/partners/share/${idu}/list`)

// ── M22 + Bilan (faisabilité bidirectionnelle) ──
export const getFaisabilite = (idu: string) => j<Record<string, any>>(`/modules/faisabilite/${idu}`)
// M11 Surface C : explication IA de la dérivation du chiffrage (ancrée sur les steps, sur clic).
export const faisabiliteExplain = (idu: string) =>
  j<{ disponible: boolean; rejected?: boolean; degraded?: boolean; texte?: string; message?: string;
      sources?: string[]; provenance?: Record<string, string>; cached?: boolean }>(`/modules/faisabilite/${idu}/explain`)

// Calculette de charge foncière (mandat bilan-calculette) : LABUSE calcule le déterministe
// (SDP, prix DVF) ; le coût de construction et la marge sont les hypothèses SAISIES.
export interface ChargeIn { cout_construction_m2: number; marge_frais_pct: number; prix_demande_eur?: number | null }
export const postChargeFonciere = (idu: string, body: ChargeIn) =>
  j<Record<string, any>>(`/modules/faisabilite/${idu}/charge`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  })
export const postProgramme = (body: Record<string, unknown>) =>
  j<Record<string, any>>('/modules/programme', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

// ── Projets (copilote-projet) — l'objet persistant de l'entretien de cadrage ──
export interface FicheProjet {
  type_programme?: 'logements' | 'etudiant' | 'bureaux' | 'autre'
  ampleur?: { logements?: number; sdp_m2?: number; niveaux?: number }
  perimetre?: { mode: 'ile' | 'secteur' | 'communes'; secteur?: string; communes?: string[] }
  contraintes?: string[]
  budget_foncier_eur?: number
  criteres_libres?: string
}
// contact proprio (PRIVACY : PM publique nommée OU particulier masqué) — partagé CRM ↔ projet
export type ProprietairePublic =
  | { type: 'personne_morale'; denomination: string; siren: string | null; groupe: string | null }
  | { type: 'particulier' }
export interface ProjetCounts { proposee: number; retenue: number; ecartee: number; a_analyser: number }
export interface Projet {
  id: number; nom: string; statut: 'actif' | 'archive'
  fiche: FicheProjet; filtres: Record<string, unknown>; programme: Record<string, unknown> | null
  created_at: string | null; updated_at: string | null; derniere_execution_at: string | null
  counts?: ProjetCounts   // Lot 4 : mini-compteurs de tri (fiche projet) — depuis projet_parcelles
}
// L'entretien de cadrage (réel uniquement — fallback si stub)
export interface EntretienChip { label: string; value?: string }
export interface EntretienQuestion { id: string; texte: string; dimension?: 'secteur' | 'commune'; defaut?: string; chips: EntretienChip[] }
export interface EntretienRep {
  stub: boolean; fallback?: boolean; message?: string
  reformulation?: string; fiche?: FicheProjet; nom?: string; pret?: boolean
  questions?: EntretienQuestion[]; doctrine_neutralise?: boolean
}
export const iaEntretien = (body: { text: string; fiche?: FicheProjet; history?: { role: string; content: string }[] }) =>
  j<EntretienRep>('/ia/entretien', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

export interface RepereOption { key: string; label: string; nb_opportunites: number; dvf_median_eur_m2: number | null; communes_carencees: string[] }
export const getReperes = (dimension: 'secteur' | 'commune') =>
  j<{ dimension: string; options: RepereOption[]; note: string }>(`/projets/reperes?dimension=${dimension}`)

export const getProjets = () => j<Projet[]>('/projets')
export const getProjet = (id: number) => j<Projet>(`/projets/${id}`)
export interface ProjetDerive { nom: string; fiche: FicheProjet; filtres: Record<string, unknown>; programme: Record<string, unknown> | null; sdp_besoin_m2: number | null }
export const deriveProjet = (body: { fiche: FicheProjet; nom?: string }) =>
  j<ProjetDerive>('/projets/derive', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
export const createProjet = (body: { fiche: FicheProjet; nom?: string; filtres_extra?: Record<string, unknown> }) =>
  // `existing: true` = dédup douce serveur (projet actif identique) → le front propose la reprise
  j<{ ok: boolean; existing?: boolean; projet: Projet }>('/projets', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
export interface ApercuTop { idu: string; commune: string; statut: string | null; q_score: number | null; pourquoi: string[] }
export interface Apercu { nom: string; n: number; sdp_besoin_m2: number | null; programme_defini: boolean; source: string; top: ApercuTop[] }
export const getApercu = (fiche: FicheProjet, limit = 5) =>
  j<Apercu>('/projets/apercu', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ fiche, limit }) })
export const projetPdfUrl = (id: number) => `/projets/${id}/export.pdf`
export const patchProjet = (id: number, body: { nom?: string; statut?: string; fiche?: FicheProjet }) =>
  j<{ ok: boolean; projet: Projet }>(`/projets/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
export const rejouerProjet = (id: number) =>
  j<{ ok: boolean; projet: Projet }>(`/projets/${id}/rejouer`, { method: 'POST' })
export const deleteProjet = (id: number) => j<{ ok: boolean }>(`/projets/${id}`, { method: 'DELETE' })

// ── Parcours de sélection (Tinder) — statuts parcelle×projet ──
export type StatutParcelle = 'proposee' | 'retenue' | 'ecartee' | 'a_analyser'
export interface ParcoursCounts { proposee: number; retenue: number; ecartee: number; a_analyser: number }
export interface ParcoursItem { idu: string; commune: string; statut: StatutParcelle; q_score: number | null; tier: string | null; center: [number, number] | null; proprietaire_public?: ProprietairePublic | null; surface_m2?: number | null; hors_criteres?: boolean; defisc?: boolean; caduc?: boolean }
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

// ── Moteur de segments Habitat (mandat segments) ──
export interface SegmentFiltreDef {
  cle: string; libelle: string; type: 'range' | 'bool' | 'enum'; unite: string | null
  groupe: string; enum_values: string[]; description: string
  disponible: boolean; raison: string | null; mandat: string | null
}
export interface SegmentFiltre { cle?: string; min?: number; max?: number; value?: boolean; values?: string[]; optionnel?: boolean; ou?: SegmentFiltre[] }
export interface SegmentPreset {
  slug: string; nom: string; categorie: string; description: string | null; argumentaire: string | null
  filtres: SegmentFiltre[]; colonnes_export: string[]; tri_defaut: string | null
  boost_catnat: boolean; actif: boolean; ordre: number; created_by: string | null; updated_at: string | null
  disponibilite: 'complet' | 'partiel'; filtres_inactifs: { cle: string; libelle: string; raison: string | null; mandat: string | null }[]
  count: number | null; count_at: string | null
  // Mention informative sourcée (mandat ANC & Végétation) — références Légifrance
  // vérifiées, formulation factuelle : JAMAIS un conseil juridique.
  mention_legale?: {
    texte: string; liens: { texte: string; url: string }[]; sources_donnees: string
  } | null
}
export interface SegmentsHome {
  categories: Record<string, string>
  presets: SegmentPreset[]
  filtres: SegmentFiltreDef[]
  tris: { cle: string; libelle: string }[]
  colonnes_export: { cle: string; libelle: string }[]
  catnat: { fenetre_mois: number; communes: { commune: string; dernier_arrete: string | null; perils: string }[] }
  libelle_residuel: string
}
export const getSegments = () => j<SegmentsHome>('/segments')
export interface SegmentQueryBody {
  slug?: string; filtres?: SegmentFiltre[]; tri?: string | null
  colonnes_export?: string[]; limit?: number; offset?: number; geojson?: boolean
}
export interface SegmentQueryRep {
  count: number; items: Record<string, unknown>[]; tri: string
  filtres_actifs: SegmentFiltre[]; filtres_inactifs: { cle: string; libelle: string; raison: string | null; mandat: string | null }[]
  colonnes: { cle: string; libelle: string }[]
  limit: number; offset: number
  geojson?: { type: 'FeatureCollection'; features: unknown[] }
}
export const querySegment = (body: SegmentQueryBody) =>
  j<SegmentQueryRep>('/segments/query', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
export const exportSegmentCsv = async (body: SegmentQueryBody, filename: string) => {
  const r = await fetch('/segments/export', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  if (!r.ok) throw new Error(`export → HTTP ${r.status}`)
  const blob = await r.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename
  document.body.appendChild(a); a.click(); a.remove()
  URL.revokeObjectURL(url)
}
// Publipostage (wave-adresses Lot 2A) : ZIP = CSV normalisé « À l'occupant » + planches
// d'étiquettes PDF + gabarit de lettre du métier. Adresse BAN exigée côté serveur.
export const exportPublipostage = async (body: SegmentQueryBody, filename: string) => {
  const r = await fetch('/segments/publipostage', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  if (!r.ok) throw new Error((await r.json().catch(() => null))?.detail ?? `publipostage → HTTP ${r.status}`)
  const blob = await r.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename
  document.body.appendChild(a); a.click(); a.remove()
  URL.revokeObjectURL(url)
}
export const getGabarits = () =>
  j<{ gabarits: Record<string, { titre: string; corps: string }>; avertissement: string }>('/segments/gabarits')

export const createSegmentPreset = (body: Record<string, unknown>) =>
  j<SegmentPreset>('/segments/presets', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
export const updateSegmentPreset = (slug: string, body: Record<string, unknown>) =>
  j<SegmentPreset>(`/segments/presets/${slug}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
export const deleteSegmentPreset = (slug: string) =>
  j<{ supprime: string }>(`/segments/presets/${slug}`, { method: 'DELETE' })
export const refreshSegmentCounts = () =>
  j<{ recalcules: Record<string, number> }>('/segments/refresh-counts?stale_hours=0', { method: 'POST' })

// Recherche en langage naturel → filtres du registry (wave-adresses Lot 6). Le serveur
// valide CHAQUE clé contre le registry — jamais de SQL, jamais de champ inconnu exécuté.
export interface NlSegmentsRep {
  stub: boolean
  filtres?: SegmentFiltre[]
  filtres_rejetes?: { filtre: unknown; raison: string }[]
  filtres_gates?: (SegmentFiltre & { plan_requis?: string; raison?: string; cta?: string })[]
  explication?: string
  out_of_scope?: string; message?: string; groupes_disponibles?: string[]; quota?: boolean
}
export const nlSegmentsSearch = (text: string) =>
  j<NlSegmentsRep>('/ia/segments-search', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) })
