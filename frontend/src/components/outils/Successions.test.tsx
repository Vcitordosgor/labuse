import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { useApp } from '../../store/useApp'
import { Successions } from './Successions'

afterEach(() => vi.restoreAllMocks())

it('distingue les dates, le motif SCI, le lien entreprise et la fiche parcelle', async () => {
  const scope = useApp.getState()
  const focus = vi.spyOn(scope, 'focusParcelle').mockImplementation(() => {})
  const meta = { maj: '06/10/2026', rne_sync: '05/07/2026', n_age_ecarte: 0, avertissement: 'Veille patrimoniale.' }
  const item = { idu: 'TEST', commune: 'Saint-Denis', sci_dormante: true, sdp_residuelle_m2: null,
    proprio: { type: 'personne_morale', denomination: 'SCI Test', siren: '111222333' },
    depot_comptes: { muet: true, annee: 2018, annee_parution: 2020, depuis_ans: 6 } }
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
    const path = String(url)
    const body = path.includes('/successions')
      ? path.includes('commune=') ? { ...meta, total: 0, items: [] } : { ...meta, total: 1, items: [item] }
      : [{ commune: 'Saint-Denis' }]
    return new Response(JSON.stringify(body))
  })
  render(<QueryClientProvider client={new QueryClient()}><Successions /></QueryClientProvider>)
  expect(await screen.findByText(/SCI ancienne/)).toBeTruthy()
  expect(screen.getByText(/BODACC en 2020/)).toBeTruthy()
  expect(screen.queryByText('Estimé')).toBeNull()
  for (const date of [meta.maj, meta.rne_sync]) expect(screen.getByText(date)).toBeTruthy()
  fireEvent.click(screen.getByRole('link', { name: '111222333' }))
  expect(focus).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Ouvrir la fiche de TEST' }))
  expect(focus).toHaveBeenCalledWith('TEST', { fiche: true })
  fireEvent.change(screen.getByRole('combobox'), { target: { value: 'Saint-Denis' } })
  expect(await screen.findByText(/Aucune parcelle correspondant/)).toBeTruthy()
  expect(screen.getByText(meta.maj)).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: 'Réinitialiser les filtres' }))
  expect(await screen.findByText(/SCI ancienne/)).toBeTruthy()
})
