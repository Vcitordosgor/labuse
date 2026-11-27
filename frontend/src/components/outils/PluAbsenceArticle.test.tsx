import { fireEvent, render, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { expect, it, vi } from 'vitest'
import { PluAnnuaire } from './PluAnnuaire'
import { useApp } from '../../store/useApp'

const texte = 'Le chapitre de la zone A ne comporte pas d’article propre au stationnement.'
vi.mock('../../lib/api', () => ({
  pluAnnuaireCommunes: async () => ({ communes: [{ insee: '97410', commune: 'Saint-Benoît', statut: 'servable' }] }),
  pluAnnuaireSearch: async (_q: string, _insee: string, zone: string) => ({ n: 0, n_total: 0, resultats: [], absence_article: {
    ...(zone === 'Nta53' ? { complement: { texte: 'Accès piéton depuis le parking.', page: 86, url: 'https://data.geopf.fr/reglement.pdf#page=86' } } : {}),
    texte, page_debut: 32, page_fin: 39, url: 'https://data.geopf.fr/reglement.pdf#page=32',
  } }),
}))

it('affiche une carte documentaire paginée pour le stationnement en A', async () => {
  useApp.setState({ pluPrefill: { insee: '97410', zone: 'A' } })
  const page = render(<QueryClientProvider client={new QueryClient()}><PluAnnuaire /></QueryClientProvider>)
  const q = await waitFor(() => {
    const input = page.container.querySelector('input[data-plu-q]')
    expect(input).toBeTruthy()
    return input!
  })
  fireEvent.change(q, { target: { value: 'stationnement' } })
  fireEvent.keyDown(q, { key: 'Enter' })
  await page.findByText(texte)
  expect(page.getByRole('link', { name: /32.*39/ }).getAttribute('href')).toMatch(/#page=32$/)
  expect(page.container.querySelector('[data-plu-aucun]')).toBeNull()
})

it('relie la fiche du secteur à sa page du règlement', async () => {
  useApp.setState({ pluPrefill: { insee: '97410', zone: 'Nta53' } })
  const page = render(<QueryClientProvider client={new QueryClient()}><PluAnnuaire /></QueryClientProvider>)
  const q = await waitFor(() => {
    const input = page.container.querySelector('input[data-plu-q]')
    expect(input).toBeTruthy()
    return input!
  })
  fireEvent.change(q, { target: { value: 'stationnement' } })
  fireEvent.keyDown(q, { key: 'Enter' })
  expect((await page.findByRole('link', { name: /fiche.*86/i })).getAttribute('href')).toMatch(/#page=86$/)
  expect(page.getByText('Accès piéton depuis le parking.')).toBeTruthy()
})
