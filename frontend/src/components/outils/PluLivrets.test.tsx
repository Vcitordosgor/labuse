import { fireEvent, render, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { it, expect, vi } from 'vitest'
import { PluAnnuaire } from './PluAnnuaire'
import { useApp } from '../../store/useApp'

vi.mock('../../lib/api', () => ({
  pluAnnuaireCommunes: async () => ({ communes: [{ insee: '97415', commune: 'Saint-Paul', statut: 'servable' }] }),
  pluAnnuaireSearch: async () => ({ n: 1, n_total: 1, resultats: [{ commune: 'Saint-Paul', zone: 'USDU',
    article_ref: 'Article 12-', page_pdf: 139, pdf_url: 'https://data.geopf.fr/reglement.pdf',
    texte_verbatim: 'Stationnement', livrets: [139, 200, 246, 306].map((p, i) => ({ livret: 'Livret ' + (i + 1), page_pdf: p })),
  }] }),
}))

it('permet d’ouvrir la page de chaque livret de Saint-Paul', async () => {
  useApp.setState({ pluPrefill: { insee: '97415', zone: 'Usdu' } })
  const { container } = render(<QueryClientProvider client={new QueryClient()}><PluAnnuaire /></QueryClientProvider>)
  const q = await waitFor(() => {
    const el = container.querySelector('input[data-plu-q]')
    expect(el).toBeTruthy()
    return el!
  })
  fireEvent.change(q, { target: { value: 'stationnement' } })
  fireEvent.keyDown(q, { key: 'Enter' })
  await waitFor(() => expect(container.querySelector('[data-plu-carte]')).toBeTruthy())
  for (const n of [139, 200, 246, 306]) {
    const a = Array.from(container.querySelectorAll('a')).find(l => l.textContent?.includes('Livret') && l.href.endsWith('#page=' + n))
    expect(a).toBeTruthy()
  }
})
