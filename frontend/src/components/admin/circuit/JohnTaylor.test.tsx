// JOHN-TAYLOR-1 — l'onglet « John Taylor » : chat à gauche, résumé/veille/carnet/coût à droite.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

const chatSpy = vi.fn(() =>
  Promise.resolve({ conversation_id: 7, texte: 'Tous les jobs tournent, aucun en échec.', sources: [] }))

vi.mock('../../../lib/api', () => ({
  getAdminJohn: () => Promise.resolve({
    actif: true,
    cout: { plafond_eur: 50, depense_eur: 1.23, reste_eur: 48.77, appels: 4, en_pause: false },
    resume_matin: { ts: '2026-11-03T03:30:00+04:00', urgent: false, sujet: '[INFO] Rien à signaler',
      corps: 'Rien n’attend votre décision.', par: 'john' },
    veille: [{ ts: '2026-11-03T03:00:00+04:00', axe: 'concurrence', titre: 'KelFoncier bouge',
      source: 'kelfoncier.com', date_vue: '2026-10-20', libelle: 'concurrence', url: null, extrait: null }],
    carnet: [{ cle: 'dec-bdnb-retiree', type: 'decision', titre: 'BDNB retirée', corps: '…', par: 'mémoire' }],
    carnet_propositions: [],
    actions: [], journal: [],
  }),
  postJohnChat: (msg: string) => chatSpy(msg),
  postJohnEnquete: vi.fn(),
  postJohnCarnetValider: vi.fn(),
  postJohnCarnetRejeter: vi.fn(),
}))

// eslint-disable-next-line import/first
import { JohnTaylor } from './JohnTaylor'

const wrap = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<div className="cxp"><QueryClientProvider client={qc}><JohnTaylor /></QueryClientProvider></div>)
}

describe('JOHN-TAYLOR-1 — l’onglet', () => {
  it('affiche le coût du mois, le résumé, la veille et le carnet', async () => {
    const { container } = wrap()
    await waitFor(() => expect(container.textContent).toContain('Coût du mois'))
    const txt = container.textContent || ''
    expect(txt).toContain('1.23') && expect(txt).toContain('/ 50')
    expect(txt).toContain('Rien à signaler')          // résumé du matin
    expect(txt).toContain('KelFoncier bouge')         // veille
    expect(txt).toContain('BDNB retirée')             // carnet de bord
  })

  it('le chat envoie la question et affiche la réponse de John', async () => {
    wrap()
    await waitFor(() => screen.getByPlaceholderText(/Pose ta question/))
    const input = screen.getByPlaceholderText(/Pose ta question/) as HTMLInputElement
    fireEvent.change(input, { target: { value: 'Est-ce que tout tourne ?' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    await waitFor(() => expect(chatSpy).toHaveBeenCalledWith('Est-ce que tout tourne ?'))
    await waitFor(() => expect(screen.getByText(/Tous les jobs tournent/)).toBeTruthy())
    // la question de Vic reste affichée dans le fil.
    expect(screen.getByText('Est-ce que tout tourne ?')).toBeTruthy()
  })
})
