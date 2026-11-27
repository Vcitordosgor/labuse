import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import * as api from '../../lib/api'
import { ProjetsPanel } from './ProjetsPanel'

afterEach(() => vi.restoreAllMocks())

it('distingue une lecture en échec d’une liste vide et permet de réessayer', async () => {
  const lecture = vi.spyOn(api, 'getProjets')
    .mockRejectedValueOnce(new Error('503'))
    .mockResolvedValueOnce([])
  vi.spyOn(api, 'getCourrierDemandes').mockResolvedValue({ demandes: [] })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={client}><ProjetsPanel /></QueryClientProvider>)

  expect(await screen.findByRole('alert')).toHaveTextContent('Impossible de charger les projets.')
  expect(screen.queryByText(/Aucun projet/)).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: 'Réessayer' }))
  expect(await screen.findByText("Aucun projet pour l'instant")).toBeVisible()
  expect(screen.queryByRole('alert')).toBeNull()
  expect(lecture).toHaveBeenCalledTimes(2)
})
