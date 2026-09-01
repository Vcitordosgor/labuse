import { describe, expect, it } from 'vitest'
import { render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { VeillePanel } from './Sources'
import type { AdminSource } from '../../lib/api'

// SENTINELLE-1 (W4.3) — le panneau « Agent de veille des sources » n'est plus grisé : il liste les
// sources SURVEILLÉES (une ligne source_veille), montre millésime servi vs amont, et met en avant
// une nouvelle version. Les sources non surveillées n'y apparaissent pas (état normal).

const src = (over: Partial<AdminSource> & { id: number; name: string }): AdminSource => ({
  category: null, millesime: '2025-S2', horizon: null, ingere_le: null, cadence: null,
  a_jour: true, relance: null, affichage_desactive: false,
  veille: { surveillee: false, actif: null, methode: null, statut: null, millesime_amont: null,
    nouvelle_version: false, passage_at: null, message: null },
  ...over,
})

const renderPanel = (sources: AdminSource[]) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><VeillePanel sources={sources} /></QueryClientProvider>)
}

describe('SENTINELLE-1 — panneau de veille des sources', () => {
  it('liste les sources surveillées et masque les non surveillées', () => {
    const sources = [
      src({ id: 1, name: 'DVF surveillée', veille: { surveillee: true, actif: true, methode: 'page',
        statut: 'nouvelle_version', millesime_amont: '2026-S1', nouvelle_version: true, passage_at: null, message: null } }),
      src({ id: 2, name: 'Source non surveillée' }),
    ]
    const { getByText, queryByText } = renderPanel(sources)
    expect(getByText('DVF surveillée')).toBeTruthy()
    expect(getByText('2026-S1')).toBeTruthy()               // millésime amont mis en avant
    expect(queryByText('Source non surveillée')).toBeNull() // non surveillée → absente du panneau
  })

  it('affiche un vide honnête quand aucune source n\'est surveillée', () => {
    const { getByText } = renderPanel([src({ id: 3, name: 'X' })])
    expect(getByText(/Aucune source surveillée/)).toBeTruthy()
  })

  it('propose les deux actions par source surveillée (Vérifier maintenant + suspendre)', () => {
    const sources = [src({ id: 1, name: 'A', veille: { surveillee: true, actif: true, methode: 'entete',
      statut: 'ok', millesime_amont: null, nouvelle_version: false, passage_at: null, message: null } })]
    const { getByText } = renderPanel(sources)
    expect(getByText('Vérifier maintenant')).toBeTruthy()
    expect(getByText('Suspendre la veille')).toBeTruthy()
  })
})
