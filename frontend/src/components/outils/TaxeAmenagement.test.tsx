import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { useApp } from '../../store/useApp'
import { TaxeAmenagement } from './TaxeAmenagement'

afterEach(() => { cleanup(); vi.unstubAllGlobals(); useApp.setState({ selectedIdu: null }) })

it('préserve la virgule, accepte le forfait seul et efface le projet au changement de parcelle', async () => {
  const requests: URL[] = []
  vi.stubGlobal('fetch', vi.fn(async (input: string) => {
    const url = new URL(input, 'https://test.local')
    let data: object = {}
    if (url.pathname.endsWith('/config')) data = {
      meta: { annee: 2026 }, valeur_forfaitaire_m2: { hors_idf: 892 },
      taux: {}, abattement: { taux_pct: 50, plafond_m2_residence_principale: 100 },
      forfaits: { piscine_m2: 251, stationnement_ext_place: 2928, stationnement_ext_place_max_delib: 5857,
        panneau_pv_sol_m2: 10, eolienne_mat: 3000 },
    }
    else if (url.pathname.includes('/prefill')) data = { taux_communal_pct: null }
    else if (url.pathname.endsWith('/taxe-amenagement')) {
      requests.push(url)
      data = { lignes: [], assiette_eur: 3137.50, total_eur: null, taux_communal_manquant: true }
    }
    return { ok: true, json: async () => data }
  }))
  useApp.setState({ selectedIdu: '97411000BZ1065' })
  render(<QueryClientProvider client={new QueryClient()}><TaxeAmenagement /></QueryClientProvider>)
  const piscine = await screen.findByLabelText('Piscine')
  fireEvent.change(piscine, { target: { value: '12,5' } })
  await waitFor(() => expect(requests.at(-1)?.searchParams.get('piscine_m2')).toBe('12.5'))
  expect(requests.at(-1)?.searchParams.get('surface_taxable_m2')).toBe('0')
  fireEvent.change(await screen.findByLabelText('Taux communal de la délibération'), { target: { value: '0' } })
  await waitFor(() => expect(requests.at(-1)?.searchParams.get('taux_communal_pct')).toBe('0'))
  fireEvent.change(piscine, { target: { value: '-12' } })
  expect(piscine.getAttribute('aria-invalid')).toBe('true')
  expect(document.querySelector('[data-taxe-resultat]')).toBeNull()
  act(() => useApp.setState({ selectedIdu: '97415000EV0324' }))
  expect((await screen.findByLabelText('Piscine') as HTMLInputElement).value).toBe('')
})
