import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactElement } from 'react'
import { useApp } from '../../store/useApp'

// MINI-CORRECTIONS-2 (pt 24) — RÉGRESSION Vic : avec 3 parcelles, « Comparer (3/3) » n'affichait que
// la barre de titre, sans tableau. Cause : le rendu du tableau ne traitait QUE trois cas (0 parcelle ·
// requête en cours · parcels>0) ; si la requête ÉCHOUE ou RÉPOND SANS parcelle exploitable, plus rien
// ne s'affichait sous le titre. Ces tests verrouillent les DEUX états de repli ajoutés + le cas nominal.
const { getCompareMock } = vi.hoisted(() => ({ getCompareMock: vi.fn() }))
vi.mock('../../lib/api', async (orig) => {
  const actual = (await orig()) as Record<string, unknown>
  return { ...actual, getCompare: getCompareMock }
})

const { ComparePanel } = await import('./ComparePanel')

const renderQC = (ui: ReactElement) =>
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>{ui}</QueryClientProvider>)

const IDUS = ['97411000BZ0824', '97411000BZ0381', '97411000BZ1065']

beforeEach(() => { getCompareMock.mockReset(); useApp.setState({ compareIdus: IDUS, compareOpen: true }) })
afterEach(() => useApp.setState({ compareIdus: [], compareOpen: false }))

describe('COMPARER — le tableau ne se réduit jamais à la barre de titre (MINI-CORRECTIONS-2 pt 24)', () => {
  it('réponse AVEC parcelles → le TABLEAU s\'affiche (la régression de Vic est levée)', async () => {
    getCompareMock.mockResolvedValue({ count: 3, parcels: IDUS.map((idu) => ({ idu, commune: 'Saint-Denis', surface_m2: 589, zone: 'Uh' })) })
    const { container } = renderQC(<ComparePanel />)
    await waitFor(() => expect(container.querySelector('table')).toBeTruthy())
    expect(container.querySelectorAll('[data-compare-col]')).toHaveLength(3)
    expect(container.querySelector('[data-compare-aucune]')).toBeNull()
  })

  it('réponse SANS parcelle exploitable → repli « aucune donnée » (plus jamais un titre nu)', async () => {
    getCompareMock.mockResolvedValue({ count: 0, parcels: [] })
    const { container } = renderQC(<ComparePanel />)
    await waitFor(() => expect(container.querySelector('[data-compare-aucune]')).toBeTruthy())
    expect(container.querySelector('table')).toBeNull()
  })

  it('requête en ÉCHEC → état d\'erreur avec réessai (plus jamais un titre nu)', async () => {
    getCompareMock.mockRejectedValue(new Error('boom'))
    const { container } = renderQC(<ComparePanel />)
    await waitFor(() => expect(container.querySelector('[data-compare-erreur]')).toBeTruthy())
    expect(container.querySelector('table')).toBeNull()
  })
})
