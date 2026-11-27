import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { useApp } from '../../store/useApp'
import { EtudeZone } from './EtudeZone'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  useApp.setState({ selectedIdu: null })
})

it('efface le cercle au changement de rayon et permet de relancer une lecture en erreur', async () => {
  let echec = false
  const rayons: number[] = []
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    if (url.endsWith('/outils/etude-zone')) {
      rayons.push(JSON.parse(String(init?.body)).rayon_km)
      if (echec) return Response.json({ detail: { message: 'Parcelle introuvable' } }, { status: 404 })
      return Response.json({
        zone_disponible: true, entree: 'rayon', origine: { lon: 55.3, lat: -21 },
        geom: { type: 'Polygon', coordinates: [] }, emplois_couverture: 'servie',
        emplois: { postes_min: 10000, postes_max: 0, postes_max_ouvert: true,
          n_etablissements: 1, n_avec_tranche: 1, n_sans_tranche: 0 },
      })
    }
    return Response.json({})
  }))
  useApp.setState({ selectedIdu: '97411000BZ1281' })
  render(<QueryClientProvider client={new QueryClient()}><EtudeZone /></QueryClientProvider>)
  const lire = () => fireEvent.click(screen.getByRole('button', { name: 'Lire la zone' }))
  lire()
  fireEvent.click(await screen.findByRole('button', { name: 'Économie' }))
  expect(screen.getByText(/Au moins 10\s000/)).toBeTruthy()
  expect(useApp.getState().moduleMap.extra).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '2 km' }))
  await waitFor(() => expect(useApp.getState().moduleMap.extra).toBeNull())
  echec = true
  lire()
  expect((await screen.findByRole('alert')).textContent).toContain('Parcelle introuvable')
  echec = false
  lire()
  await screen.findByRole('button', { name: 'Exporter en PDF' })
  expect(rayons).toEqual([1, 2, 2])
})
