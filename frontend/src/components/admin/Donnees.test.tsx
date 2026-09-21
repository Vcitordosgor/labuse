// CIRCUIT-P2 (lot 1.4) · DASHBOARD-2 (Lot 7) — la page « Données » = le Circuit + UN lien vers le
// détail du réservoir plu_destinations (calibration des destinations, qui a quitté le rail). Pas
// d'enrobage legacy (bandeau « Mes données sont-elles à jour ? », onglet Catalogue, « Qui fait quoi »).
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

vi.mock('../../lib/api', () => ({
  getAdminCircuit: () => new Promise(() => {}),       // reste en « chargement » (rendu déterministe)
  postAdminCircuitVerifier: vi.fn(),
  postAdminCircuitAgents: vi.fn(),
  getAdminCircuitTaches: () => Promise.resolve({ verifier: null, agents: null, verrous: null }),
  postAdminCircuitVerrous: vi.fn(),   // DASHBOARD-4 (D2)
  getAdminCircuitJournal: vi.fn(),
}))

// eslint-disable-next-line import/first
import { DonneesSection } from './Donnees'

describe('CIRCUIT-P2 lot 1 — la page Données EST le Circuit', () => {
  const wrap = () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    return render(<QueryClientProvider client={qc}><DonneesSection /></QueryClientProvider>)
  }

  it('le Circuit (.cxp) + le lien Destinations, sans enrobage legacy', () => {
    const { container } = wrap()
    // le conteneur du Circuit est présent (rien n'a remplacé le Circuit)
    expect(container.querySelector('.cxp')).toBeTruthy()
    const txt = container.textContent || ''
    // DASHBOARD-2 Lot 7 · DASHBOARD-4 D6 — le lien vers le détail du réservoir plu_destinations
    // (renommé « Destinations PLU », déplacé en bas du Circuit).
    expect(txt).toContain('Destinations PLU')
    // plus d'enrobage legacy
    expect(txt).not.toContain('Mes données sont-elles à jour')
    expect(txt).not.toContain('Qui fait quoi')
  })

  it('snapshot', () => {
    const { container } = wrap()
    expect(container.firstChild).toMatchSnapshot()
  })
})
