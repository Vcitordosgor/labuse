import { create } from 'zustand'
import type { MapMode } from '../lib/types'

export interface LayerToggles {
  zonage: boolean
  parcelles: boolean
  ppr: boolean
  vue_mer: boolean
  parc: boolean
}

interface AppState {
  selectedIdu: string | null
  select: (idu: string | null) => void
  mode: MapMode
  setMode: (m: MapMode) => void
  layers: LayerToggles
  toggleLayer: (k: keyof LayerToggles) => void
  query: string
  setQuery: (q: string) => void
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
}))
