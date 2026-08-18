// M120 — LE SEAU DES FACETTES : un binding {filters, setFilter} que les contrôles de filtre lisent,
// LOCAL (fourni par un provider — le cadrage projet) ou, à défaut, LE STORE de la carte. Un seul jeu
// de contrôles sert les deux surfaces (carte ET cadrage projet) — jamais une copie. La carte
// n'enveloppe rien : sans provider, `useFiltre()` retombe sur le store, comportement inchangé.
import { createContext, useContext, type ReactNode } from 'react'
import { useApp, type Filters } from '../../store/useApp'

export interface FiltreBinding {
  filters: Filters
  setFilter: <K extends keyof Filters>(k: K, v: Filters[K]) => void
}

const FiltreCtx = createContext<FiltreBinding | null>(null)

/** Le binding courant. Les DEUX hooks sont appelés inconditionnellement (règle des hooks) ;
 *  le provider local prime, sinon on lit/écrit le store de la carte. */
export function useFiltre(): FiltreBinding {
  const local = useContext(FiltreCtx)
  const filters = useApp((s) => s.filters)
  const setFilter = useApp((s) => s.setFilter)
  return local ?? { filters, setFilter }
}

export function FiltreProvider({ value, children }: { value: FiltreBinding; children: ReactNode }) {
  return <FiltreCtx.Provider value={value}>{children}</FiltreCtx.Provider>
}
