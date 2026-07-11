import type { Fiche, ParcelResult, PipelineEntry, PipelineMeta, SourceInfo, Stats } from './types'

export interface ParcelFeatureCollection {
  type: 'FeatureCollection'
  features: Array<{ type: 'Feature'; geometry: unknown; properties: Record<string, unknown> }>
}

import { useApp, type Filters } from '../store/useApp'
import { vSignalCodes } from './filters'

// SOURCE DE VÉRITÉ : run de référence q_v3_datagap (bascule 10/07/2026 — data-gap +
// règle « le signal de zone ne bascule jamais seul »). Doit rester aligné sur Q_A_RUN_LABEL.
// JAMAIS parcel_evaluations (éval historique). Cf. brief « NOTE SOURCE DE VÉRITÉ ».
export const SOURCE = 'q_v3_datagap'
/** Commune active — depuis le store (null = « Toute l'île »). L'ancienne constante Saint-Paul
 *  est devenue un état : TOUTE requête commune-scopée passe par ici. */
export const commune = () => useApp.getState().commune

async function j<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init)
  if (!r.ok) throw new Error(`${url} → HTTP ${r.status}`)
  return r.json() as Promise<T>
}

const q = (extra: Record<string, string | number> = {}) => {
  const c = commune()
  return new URLSearchParams({
    source: SOURCE, ...(c ? { commune: c } : {}),
    ...Object.fromEntries(Object.entries(extra).map(([k, v]) => [k, String(v)])),
  }).toString()
}

/** Filtres chips → query params serveur (mode île : la liste et les compteurs sont SQL). */
export const filterParams = (f: Filters): Record<string, string | number> => ({
  ...(f.statuts.length ? { statuts: f.statuts.join(',') } : {}),
  ...(f.scoreMin != null ? { score_min: f.scoreMin } : {}),
  ...(f.surfaceMin != null ? { surface_min: f.surfaceMin } : {}),
  ...(f.surfaceMax != null ? { surface_max: f.surfaceMax } : {}),
  ...(f.sdpMin != null ? { sdp_min: f.sdpMin } : {}),
  ...(f.evenement ? { evenement: 'true' } : {}),
  ...(f.vueMer ? { vue_mer: 'true' } : {}),
  ...(f.flags.length ? { flags: f.flags.join(',') } : {}),
  ...(f.flagsExclus.length ? { flags_exclus: f.flagsExclus.join(',') } : {}),
  ...(f.communes.length ? { communes: f.communes.join(',') } : {}),
  ...(f.vBands.length ? { v_bands: f.vBands.join(',') } : {}),
  ...(f.vSignals.length ? { v_signal: vSignalCodes(f.vSignals).join(',') } : {}),
  ...(f.brulantes ? { brulantes: 'true' } : {}),
})

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
export interface Entonnoir { commune: string | null; analysees: number; opportunites: number; motifs: { motif: string; n: number }[]; note: string }
export const getEntonnoir = () => {
  const c = commune()
  return j<Entonnoir>(`/stats/entonnoir${c ? `?commune=${encodeURIComponent(c)}` : ''}`)
}
export const getContexteCommune = (commune: string) =>
  j<ContexteCommune>(`/communes/${encodeURIComponent(commune)}/contexte`)
export const parcelAt = (lon: number, lat: number) =>
  j<{ idu: string | null }>(`/parcels/at?lon=${lon}&lat=${lat}`)
export const searchParcels = (needle: string) =>
  j<{ idu: string; commune: string; status: string | null; q_score: number | null }[]>(
    `/parcels/search?q=${encodeURIComponent(needle)}${commune() ? `&commune=${encodeURIComponent(commune()!)}` : ''}`)

export const getStats = (f?: Filters) => j<Stats>(`/stats?${q(f ? filterParams(f) : {})}`)
export const getResults = (f?: Filters, limit = 500, sortV = false) =>
  j<ParcelResult[]>(`/parcels?${q({ limit, ...(sortV ? { sort: 'v' } : {}), ...(f ? filterParams(f) : {}) })}`)
/** Export CSV de la liste courante (mêmes filtres) — colonnes v_score / v_band / top_signaux. */
export const csvExportUrl = (f?: Filters, sortV = false) =>
  `/parcels/export.csv?${q({ limit: 5000, ...(sortV ? { sort: 'v' } : {}), ...(f ? filterParams(f) : {}) })}`
export const getParcelsGeojson = () =>
  j<ParcelFeatureCollection>(`/map/parcels.geojson?${q({ limit: 60000 })}`)
export const getFiche = (idu: string) => j<Fiche>(`/parcels/${idu}?source=${SOURCE}`)
export const getMapLayer = (kind: string) => {
  const c = commune()
  return j<ParcelFeatureCollection>(`/map/layers.geojson?kind=${kind}${c ? `&commune=${encodeURIComponent(c)}` : ''}`)
}
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
export const modPermis = (months: number) => j<Record<string, unknown>>(`/modules/permis?${cq()}&months=${months}`)
export const modPromesses = (months: number) => j<Record<string, unknown>>(`/modules/promesses?${cq()}&months=${months}`)
export const modVelocite = () => j<{ note: string; communes: Record<string, unknown>[] }>('/modules/velocite')
export const modBailleur = () => j<Record<string, unknown>>(`/modules/bailleur?${cq()}`)
export const modFantome = () => j<Record<string, unknown>>(`/modules/fantome?${cq()}`)
// Habitat Solaire (mandat habitat-solaire)
export const getSolaireFiche = (idu: string) => j<Record<string, unknown>>(`/solaire/fiche/${idu}`)
export const modSolaireParkings = (tranche?: string | null) =>
  j<Record<string, unknown>>(`/solaire/parkings${tranche ? `?tranche=${tranche}` : ''}`)
export const modSolaireTertiaire = () => j<Record<string, unknown>>('/solaire/tertiaire')
export const getOrthoEquipements = (idu: string) => j<Record<string, unknown>>(`/ortho/equipements/${idu}`)
export const modCourriers = (idus: string[], contexte: string) =>
  j<{ n: number; courriers: { idu: string; texte?: string; erreur?: string }[]; rappel_identite: string }>('/modules/courriers', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ idus, contexte }) })
export const modDueDiligence = (refs: string) =>
  j<{ n_demandes: number; n_trouvees: number; items: Record<string, unknown>[] }>('/modules/duediligence', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refs }) })

// ── Copilote IA (Vague 2) — jamais d'accès base, filtres validés par schéma côté API ──
export const iaStatus = () => j<{ provider: string; raison: string | null }>('/ia/status')
export const iaSearch = (body: { text: string; history?: { role: string; content: string }[] }) =>
  j<{ stub: boolean; filters?: Record<string, unknown>; cadrage?: Record<string, unknown>; explanation?: string; out_of_scope?: string }>('/ia/search', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
export const iaSynthese = (idu: string) =>
  j<{ stub: boolean; texte: string; mention: string }>(`/ia/synthese/${idu}`, { method: 'POST' })
export const iaPourquoi = (idu: string) =>
  j<{ stub: boolean; texte: string; mention: string }>(`/ia/pourquoi/${idu}`, { method: 'POST' })

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
export const motBarometre = () => j<Record<string, any>>('/moteurs/barometre')

// ── Vague 5 : matching + partage ──
export const getProfiles = () => j<Record<string, any>[]>('/partners/profiles')
export const addProfile = (p: Record<string, unknown>) =>
  j<{ ok: boolean }>('/partners/profiles', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(p) })
export const runMatch = () => j<{ matches: number }>('/partners/match/run', { method: 'POST' })
export const createShare = (idu: string) => j<{ token: string; url: string }>(`/partners/share/${idu}`, { method: 'POST' })
export const listShares = (idu: string) => j<{ token: string; date: string; views: number }[]>(`/partners/share/${idu}/list`)

// ── M22 + Bilan (faisabilité bidirectionnelle) ──
export const getFaisabilite = (idu: string) => j<Record<string, any>>(`/modules/faisabilite/${idu}`)

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
export interface Projet {
  id: number; nom: string; statut: 'actif' | 'archive'
  fiche: FicheProjet; filtres: Record<string, unknown>; programme: Record<string, unknown> | null
  created_at: string | null; updated_at: string | null; derniere_execution_at: string | null
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
export interface ProjetDerive { nom: string; fiche: FicheProjet; filtres: Record<string, unknown>; programme: Record<string, unknown> | null; sdp_besoin_m2: number | null }
export const deriveProjet = (body: { fiche: FicheProjet; nom?: string }) =>
  j<ProjetDerive>('/projets/derive', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
export const createProjet = (body: { fiche: FicheProjet; nom?: string; filtres_extra?: Record<string, unknown> }) =>
  j<{ ok: boolean; projet: Projet }>('/projets', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
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
