// CIRCUIT-P2 (lot 1.4) — la page « Données » n'a plus qu'UN composant racine : le Circuit. Ce test
// garde la régression du ménage — plus d'enrobage (bandeau « Mes données sont-elles à jour ? »,
// onglet Catalogue, paragraphes « Qui fait quoi »), juste le conteneur `.cxp` du Circuit.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

vi.mock('../../lib/api', () => ({
  getAdminCircuit: () => new Promise(() => {}),       // reste en « chargement » (rendu déterministe)
  postAdminCircuitVerifier: vi.fn(),
  postAdminCircuitAgents: vi.fn(),
  getAdminCircuitTaches: () => Promise.resolve({ verifier: null, agents: null }),
  getAdminCircuitJournal: vi.fn(),
}))

// eslint-disable-next-line import/first
import { DonneesSection } from './Donnees'

describe('CIRCUIT-P2 lot 1 — la page Données EST le Circuit', () => {
  const wrap = () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    return render(<QueryClientProvider client={qc}><DonneesSection /></QueryClientProvider>)
  }

  it('un seul composant racine, le Circuit (.cxp), sans enrobage', () => {
    const { container } = wrap()
    const root = container.firstChild as HTMLElement
    expect(root).toBeTruthy()
    expect(root.className).toContain('cxp')       // le conteneur du Circuit, rien d'autre
    const txt = container.textContent || ''
    expect(txt).not.toContain('Mes données sont-elles à jour')
    expect(txt).not.toContain('Catalogue')
    expect(txt).not.toContain('Qui fait quoi')
  })

  it('snapshot', () => {
    const { container } = wrap()
    expect(container.firstChild).toMatchSnapshot()
  })
})
