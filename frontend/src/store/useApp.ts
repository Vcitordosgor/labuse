import { create } from 'zustand'
import type { MapMode, Statut } from '../lib/types'

export type View = 'ia' | 'cartes' | 'crm' | 'sources'

export interface LayerToggles {
  zonage: boolean
  parcelles: boolean
  ppr: boolean
  vue_mer: boolean
  parc: boolean
}

// Filtres actifs — appliqués EN MÊME TEMPS à la carte, la liste et les compteurs.
export interface Filters {
  statut: Statut | 'all'
  scoreMin: number | null
  surfaceMin: number | null
}

const EMPTY: Filters = { statut: 'all', scoreMin: null, surfaceMin: null }

interface AppState {
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
  clearFilter: (k: keyof Filters) => void
  sourcesFocus: string | null // nom de source à surligner sur la page Sources
  openSources: (focus?: string | null) => void
}

export const useApp = create<AppState>((set) => ({
  view: 'cartes',
  setView: (view) => set({ view, outilsOpen: false }),
  outilsOpen: false,
  toggleOutils: () => set((s) => ({ outilsOpen: !s.outilsOpen })),
  selectedIdu: null,
  select: (idu) => set({ selectedIdu: idu }),
  mode: 'verdict',
  setMode: (mode) => set({ mode }),
  layers: { zonage: false, parcelles: true, ppr: false, vue_mer: false, parc: false },
  toggleLayer: (k) => set((s) => ({ layers: { ...s.layers, [k]: !s.layers[k] } })),
  panelOpen: true,
  togglePanel: () => set((s) => ({ panelOpen: !s.panelOpen })),
  query: '',
  setQuery: (query) => set({ query }),
  filters: EMPTY,
  setFilter: (k, v) => set((s) => ({ filters: { ...s.filters, [k]: v } })),
  clearFilter: (k) => set((s) => ({ filters: { ...s.filters, [k]: EMPTY[k] } })),
  sourcesFocus: null,
  openSources: (focus = null) => set({ view: 'sources', sourcesFocus: focus }),
}))
