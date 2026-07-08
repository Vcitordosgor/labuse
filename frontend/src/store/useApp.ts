import { create } from 'zustand'
import type { FicheLine, MapMode, Statut } from '../lib/types'

export type View = 'ia' | 'cartes' | 'crm' | 'sources' | 'projets'

export interface LayerToggles {
  zonage: boolean
  parcelles: boolean
  ppr: boolean
  vue_mer: boolean
  parc: boolean
  limites: boolean
  anru: boolean
  equipements: boolean
}

// Filtres actifs — appliqués EN MÊME TEMPS à la carte, la liste et les compteurs, et
// SÉRIALISÉS DANS L'URL (#f=…) : une recherche = un lien partageable.
export interface Filters {
  statuts: Statut[]          // vide = tous
  scoreMin: number | null
  surfaceMin: number | null
  surfaceMax: number | null
  sdpMin: number | null      // SDP résiduelle minimale (m²)
  evenement: boolean         // seulement les parcelles à événement (BODACC rouge)
  vueMer: boolean            // seulement vue mer dégagée
  flags: string[]            // flags actifs requis (au moins un)
  flagsExclus: string[]      // copilote-projet : contraintes RÉDHIBITOIRES (aucun de ces flags)
  communes: string[]         // R2 : secteur du cadreur (multi-communes, mode île)
}

export const EMPTY_FILTERS: Filters = {
  statuts: [], scoreMin: null, surfaceMin: null, surfaceMax: null, sdpMin: null,
  evenement: false, vueMer: false, flags: [], flagsExclus: [], communes: [],
}

// brouillon d'un projet issu de l'entretien : la fiche + la dérivation moteur (filtres, SDP
// besoin) — porté jusqu'à la restitution où « Enregistrer ce projet » le persiste (V3).
export interface ProjetBrouillon {
  fiche: Record<string, unknown>
  nom: string
  filtres: Record<string, unknown>
  sdp_besoin_m2: number | null
}

export type Basemap = 'dark' | 'plan' | 'ortho'
export type OrthoYear = 'now' | '2000' | '1950'
export type MapTool = 'distance' | 'surface' | 'alti' | 'zone'

interface AppState {
  // Commune active — null = « Toute l'île » (défaut). Pilote carte, compteurs, liste, modules,
  // et vit dans l'URL (#…&c=…). Sélecteur dans le header.
  commune: string | null
  setCommune: (c: string | null) => void
  // volet CONTEXTE COMMUNE (SRU/ANRU/PLH/marché) — ouvert depuis le sélecteur ou le header
  contexteCommune: string | null
  setContexteCommune: (c: string | null) => void
  // toast produit (C6) : une action utilisateur ne tombe JAMAIS dans le vide
  toast: string | null
  setToast: (t: string | null) => void
  // R1 (revue Vic n°2) : le VERDICT est un GESTE — la carte s'ouvre en cadastre neutre,
  // « LABUSE a trié pour vous » allume couleurs + entonnoir + liste. URL : v=1.
  verdict: boolean
  setVerdict: (v: boolean) => void
  // R2 : restitution chorégraphiée du copilote (compteur animé + top 3 cliquables)
  iaRestitution: { n: number; phrase: string; top: { idu: string; commune: string; q_score: number }[] } | null
  setIaRestitution: (r: { n: number; phrase: string; top: { idu: string; commune: string; q_score: number }[] } | null) => void
  // copilote-projet : brouillon issu de l'entretien (« Lancer la recherche ») → « Enregistrer ce projet » (V3)
  projetBrouillon: ProjetBrouillon | null
  setProjetBrouillon: (b: ProjetBrouillon | null) => void
  view: View
  setView: (v: View) => void
  outilsOpen: boolean
  toggleOutils: () => void
  selectedIdu: string | null
  select: (idu: string | null) => void
  mode: MapMode
  setMode: (m: MapMode) => void
  layers: LayerToggles
  toggleLayer: (k: keyof LayerToggles) => void
  panelOpen: boolean
  togglePanel: () => void
  query: string
  setQuery: (q: string) => void
  filters: Filters
  setFilter: <K extends keyof Filters>(k: K, v: Filters[K]) => void
  setFilters: (f: Filters) => void
  resetFilters: () => void
  sourcesFocus: string | null // nom de source à surligner sur la page Sources
  openSources: (focus?: string | null) => void
  // Drawer source (depuis une ligne de fiche) : jamais un cul-de-sac, la fiche reste ouverte dessous.
  sourceLine: FicheLine | null
  openSourceDrawer: (line: FicheLine) => void
  closeSourceDrawer: () => void
  // Carto : fond de plan, ortho historique, relief 3D, outil de mesure, zone dessinée (filtre).
  basemap: Basemap
  setBasemap: (b: Basemap) => void
  orthoYear: OrthoYear
  setOrthoYear: (y: OrthoYear) => void
  terrain3d: boolean
  toggleTerrain: () => void
  tool: MapTool | null
  setTool: (t: MapTool | null) => void
  zone: [number, number][] | null // polygone [lng,lat] dessiné → filtre les résultats
  setZone: (z: [number, number][] | null) => void
  // ── Modules outils (filtres savants, accent violet) ──
  module: string | null
  setModule: (m: string | null) => void
  // ce que le module affiche sur la carte : parcelles surlignées (idus) + géométries propres (lots, permis)
  moduleMap: { idus: string[]; extra: unknown | null }
  setModuleMap: (m: { idus: string[]; extra: unknown | null }) => void
  // bloc module en tête de fiche : idu → lignes [libellé, valeur]
  moduleFiche: Record<string, { module: string; lines: [string, string][] }>
  setModuleFiche: (f: Record<string, { module: string; lines: [string, string][] }>) => void
  flyTo: { center: [number, number]; zoom: number } | null
  setFlyTo: (f: { center: [number, number]; zoom: number } | null) => void
  msel: string[] // sélection multi-parcelles (module assemblage M16)
  setMsel: (m: string[]) => void
  m22Prefill: Record<string, unknown> | null // copilote → formulaire programme (M22)
  setM22Prefill: (p: Record<string, unknown> | null) => void
  m02Prefill: string | null // fiche → scan patrimoine du propriétaire (SIREN)
  setM02Prefill: (s: string | null) => void
}

export const useApp = create<AppState>((set) => ({
  commune: null,
  // changer de commune remet la zone dessinée à zéro (elle appartenait à l'ancienne emprise)
  setCommune: (commune) => set({ commune, zone: null }),
  contexteCommune: null,
  setContexteCommune: (contexteCommune) => set({ contexteCommune }),
  toast: null,
  setToast: (toast) => set({ toast }),
  verdict: false,
  setVerdict: (verdict) => set({ verdict }),
  iaRestitution: null,
  setIaRestitution: (iaRestitution) => set({ iaRestitution }),
  projetBrouillon: null,
  setProjetBrouillon: (projetBrouillon) => set({ projetBrouillon }),
  view: 'cartes',
  setView: (view) => set({ view, outilsOpen: false }),
  outilsOpen: false,
  toggleOutils: () => set((s) => ({ outilsOpen: !s.outilsOpen })),
  selectedIdu: null,
  select: (idu) => set({ selectedIdu: idu }),
  mode: 'verdict',
  setMode: (mode) => set({ mode }),
  layers: { zonage: false, parcelles: true, ppr: false, vue_mer: false, parc: false, limites: true, anru: false, equipements: false },
  toggleLayer: (k) => set((s) => ({ layers: { ...s.layers, [k]: !s.layers[k] } })),
  panelOpen: true,
  togglePanel: () => set((s) => ({ panelOpen: !s.panelOpen })),
  query: '',
  setQuery: (query) => set({ query }),
  filters: EMPTY_FILTERS,
  setFilter: (k, v) => set((s) => ({ filters: { ...s.filters, [k]: v } })),
  setFilters: (filters) => set({ filters }),
  resetFilters: () => set({ filters: EMPTY_FILTERS, zone: null }),
  sourcesFocus: null,
  openSources: (focus = null) => set({ view: 'sources', sourcesFocus: focus }),
  sourceLine: null,
  openSourceDrawer: (line) => set({ sourceLine: line }),
  closeSourceDrawer: () => set({ sourceLine: null }),
  basemap: 'dark',
  setBasemap: (basemap) => set({ basemap }),
  orthoYear: 'now',
  setOrthoYear: (orthoYear) => set({ orthoYear, basemap: 'ortho' }),
  terrain3d: false,
  toggleTerrain: () => set((s) => ({ terrain3d: !s.terrain3d })),
  tool: null,
  setTool: (tool) => set({ tool }),
  zone: null,
  setZone: (zone) => set({ zone }),
  module: null,
  setModule: (module) => set({ module, view: 'cartes', outilsOpen: false, moduleMap: { idus: [], extra: null }, moduleFiche: {} }),
  moduleMap: { idus: [], extra: null },
  setModuleMap: (moduleMap) => set({ moduleMap }),
  moduleFiche: {},
  setModuleFiche: (moduleFiche) => set({ moduleFiche }),
  flyTo: null,
  setFlyTo: (flyTo) => set({ flyTo }),
  msel: [],
  setMsel: (msel) => set({ msel }),
  m22Prefill: null,
  setM22Prefill: (m22Prefill) => set({ m22Prefill }),
  m02Prefill: null,
  setM02Prefill: (m02Prefill) => set({ m02Prefill }),
}))
