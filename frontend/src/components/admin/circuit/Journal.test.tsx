// CIRCUIT-P (lot 5) — le journal : tableau, filtre « tous » à gauche, ligne cliquable vers le
// détail quand la cible existe, compteur du jour remonté.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const getJournal = vi.fn()
vi.mock('../../../lib/api', () => ({ getAdminCircuitJournal: (...a: any[]) => getJournal(...a) }))

// eslint-disable-next-line import/first
import { Journal } from './Journal'

const data = {
  reservoirs: [{ id: 42, nom: 'SITADEL', slug: 'sitadel', etat: ['mint', 'à jour'] }],
  robinets: [{ id: 'fiche_parcelle', nom: 'Fiche parcelle', etat: ['mint', 'cohérent'] }],
} as any

const reponse = {
  entrees: [
    { ts: '2026-09-06T07:15:00Z', geste: 'job', cible: 'coherence-robinets', par: 'cron', resultat: 'ok' },
    { ts: '2026-09-05T18:30:00Z', geste: 'bascule', cible: 'SITADEL', par: 'Vic', resultat: 'ok' },
  ],
  page: 1, taille: 50, total: 2, aujourdhui: 1, gestes: ['job', 'bascule', 'filtre'],
}

describe('Journal', () => {
  beforeEach(() => { vi.clearAllMocks(); getJournal.mockResolvedValue(reponse) })
  const wrap = (ui: React.ReactElement) => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
  }

  it('rend le tableau, « tous » en premier, remonte le compteur du jour', async () => {
    const onJour = vi.fn()
    const { getByText, getAllByText } = wrap(<Journal data={data} onOpen={() => {}} onAujourdhui={onJour} />)
    await waitFor(() => expect(getByText('SITADEL')).toBeInTheDocument())
    // le premier filtre est « tous »
    const filtres = getAllByText(/^(tous|job|bascule|filtre)$/)
    expect(filtres[0].textContent).toBe('tous')
    expect(getByText('quand')).toBeInTheDocument()
    expect(onJour).toHaveBeenCalledWith(1)   // aujourd'hui = 1
  })

  it('une ligne dont la cible existe navigue vers le détail', async () => {
    const onOpen = vi.fn()
    const { getByText } = wrap(<Journal data={data} onOpen={onOpen} onAujourdhui={() => {}} />)
    await waitFor(() => expect(getByText('SITADEL')).toBeInTheDocument())
    fireEvent.click(getByText('SITADEL'))
    expect(onOpen).toHaveBeenCalledWith('reservoir', 42)
  })

  it('filtrer par geste relance la requête', async () => {
    const { getByText, getByRole } = wrap(<Journal data={data} onOpen={() => {}} />)
    await waitFor(() => expect(getByText('SITADEL')).toBeInTheDocument())
    fireEvent.click(getByRole('button', { name: 'bascule' }))   // le bouton de filtre (nom exact)
    await waitFor(() => expect(getJournal).toHaveBeenCalledWith(expect.objectContaining({ type: 'bascule' })))
  })
})
