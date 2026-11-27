import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, waitFor } from '@testing-library/react'
import { it, expect, vi } from 'vitest'
import { useApp } from '../../store/useApp'
import { PluAnnuaire } from './PluAnnuaire'

vi.mock('../../lib/api', () => ({
  pluAnnuaireCommunes: async () => ({ communes: [{
    insee: '97423', commune: 'Les Trois-Bassins', statut: 'servable', idurba: '97423_PLU_20220602',
    date_approbation: '2017-02-21', derniere_modification_couverture: '2022-06-02',
    modifications: [{ type: 'mise en compatibilité', date: '2026-08-27', source: 'Conseil municipal, p. 2',
      url: 'https://docs.trois-bassins.re/conseil.pdf#page=2' }],
  }] }),
  pluAnnuaireSearch: async () => ({ n: 2, n_total: 2, resultats: [
    { article_ref: 'Article N6', mention_rattachement: 'règle de la zone mère', texte_verbatim: 'Recul des bâtiments' },
    { article_ref: 'Article N7', mention_rattachement: 'rattachement non établi dans le règlement écrit, à vérifier', texte_verbatim: 'Limites séparatives' },
  ] }),
}))

function ouvrir() {
  useApp.setState({ pluPrefill: { insee: '97423', zone: 'Nto1' } })
  return render(<QueryClientProvider client={new QueryClient()}><PluAnnuaire /></QueryClientProvider>)
}

it('affiche la provenance dans chacune des cartes concernées', async () => {
  const page = ouvrir()
  const q = await waitFor(() => {
    const input = page.container.querySelector('input[data-plu-q]')
    expect(input).toBeTruthy()
    return input!
  })
  fireEvent.change(q, { target: { value: 'implantation' } })
  fireEvent.keyDown(q, { key: 'Enter' })
  await waitFor(() => expect(page.container.querySelectorAll('[data-plu-carte]')).toHaveLength(2))
  const cartes = Array.from(page.container.querySelectorAll('[data-plu-carte]'))
  expect(cartes[0].textContent).toContain('règle de la zone mère')
  expect(cartes[1].textContent).toContain('rattachement non établi')
})

it('qualifie la date de modification en couverture', async () => {
  expect(await ouvrir().findByText(/Dernière modification en couverture le 02\/06\/2022/)).toBeTruthy()
})

it('ouvre la page du vote des Zattes depuis l’avertissement', async () => {
  const lien = await ouvrir().findByRole('link', { name: 'Conseil municipal, p. 2' })
  expect(lien.getAttribute('href')).toBe('https://docs.trois-bassins.re/conseil.pdf#page=2')
})
