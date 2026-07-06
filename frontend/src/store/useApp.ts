import { create } from 'zustand'
import type { MapMode, Statut } from '../lib/types'

export interface LayerToggles {
  zonage: boolean
  parcelles: boolean
  ppr: boolean
  vue_mer: boolean
  parc: boolean
}

// Filtres actifs — appliqués EN MÊME TEMPS à la carte, la liste et les compteurs.
export interface Filters {
  statut: Statut | 'all' // piloté par les chips de statut du panneau gauche + chip omnibox
  scoreMin: number | null // Q ≥ N
  surfaceMin: number | null // surface ≥ N m²
}

const EMPTY: Filters = { statut: 'all', scoreMin: null, surfaceMin: null }

interface AppState {
  selectedIdu: string | null
  select: (idu: string | null) => void
  mode: MapMode
  setMode: (m: MapMode) => void
  layers: LayerToggles
  toggleLayer: (k: keyof LayerToggles) => void
  query: string
  setQuery: (q: string) => void
  filters: Filters
  setFilter: <K extends keyof Filters>(k: K, v: Filters[K]) => void
  clearFilter: (k: keyof Filters) => void
}

export const useApp = create<AppState>((set) => ({
  selectedIdu: null,
  select: (idu) => set({ selectedIdu: idu }),
  mode: 'verdict',
  setMode: (mode) => set({ mode }),
  layers: { zonage: true, parcelles: true, ppr: false, vue_mer: true, parc: false },
  toggleLayer: (k) => set((s) => ({ layers: { ...s.layers, [k]: !s.layers[k] } })),
  query: '',
  setQuery: (query) => set({ query }),
  filters: EMPTY,
  setFilter: (k, v) => set((s) => ({ filters: { ...s.filters, [k]: v } })),
  clearFilter: (k) => set((s) => ({ filters: { ...s.filters, [k]: EMPTY[k] } })),
}))
