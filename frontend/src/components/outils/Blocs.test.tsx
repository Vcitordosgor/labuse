import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { useApp } from '../../store/useApp'
import { Blocs } from './Blocs'

afterEach(() => {
  vi.unstubAllGlobals()
  useApp.setState({ module: null, mselPrefill: null, outilRetour: [] })
})

it('distingue une estimation absente et transmet uniquement les parcelles choisies', async () => {
  const bloc = {
    bloc_id: 7, denomination: 'Titulaire test', siren: '123456789', communes: ['Petite-Île', 'Saint-Pierre'],
    n_parcelles: 3, surface_totale_m2: 1200, sdp_couverture: 0, sdp_residuelle_m2: 0, zonages: [],
  }
  const membres = ['A', 'B', 'C'].map((idu) => ({ idu, surface_m2: 400, sdp_residuelle_m2: null }))
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    if (url.includes('/modules/blocs?')) return Response.json({ total: 1, items: [bloc] })
    if (url.includes('/modules/blocs/7')) return Response.json({ ...bloc, membres })
    if (url.includes('/moteurs/config')) return Response.json({ assemblage_max_ecran: 2 })
    return Response.json([])
  }))
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={qc}><Blocs /></QueryClientProvider>)
  const ouvrir = await screen.findByRole('button', { name: 'Titulaire test' })
  expect(screen.getByText('Non renseigné')).toBeTruthy()
  expect(screen.getByText(/Petite-Île, Saint-Pierre/)).toBeTruthy()
  fireEvent.click(ouvrir)
  const choisir = await screen.findAllByRole('checkbox', { name: /dans l’assemblage/ })
  fireEvent.click(choisir[2])
  fireEvent.click(choisir[0])
  expect((choisir[1] as HTMLInputElement).disabled).toBe(true)
  const carte = ouvrir.closest('[data-bloc-row]') as HTMLElement
  fireEvent.click(within(carte).getByRole('button', { name: /Assembler la sélection/ }))
  expect(useApp.getState().mselPrefill).toEqual(['C', 'A'])
  expect(useApp.getState().module).toBe('assemblage')
})
