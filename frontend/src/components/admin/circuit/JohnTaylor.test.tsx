// JOHN-TAYLOR-2 — la page « John Taylor » en conversation : liste des conversations à gauche, fil au
// centre (accueil qui parle + réponses sourcées), volet repliable à droite (résumé/veille/carnet/coût).
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

const chatSpy = vi.fn((_message: string) => Promise.resolve({
  conversation_id: 7, texte: 'Les **42** jobs tournent, aucun en échec.',
  sources: [{ label: 'Jobs', heure: '14:30' }], boutons: [{ ecran: 'cron', label: 'Voir les jobs' }],
}))

vi.mock('../../../lib/api', () => ({
  getAdminJohn: () => Promise.resolve({
    actif: true,
    accueil: { attentes: 2, phrase: "Bonjour Vic. Deux choses t'attendent.", items: [],
      suggestions: ['Tout est à jour ?', 'Qu’est-ce qui a changé depuis hier ?', 'Où en est q_v21 ?'] },
    cout: { plafond_eur: 50, depense_eur: 1.23, reste_eur: 48.77, appels: 4, en_pause: false },
    resume_matin: { ts: '2026-11-03T03:30:00+04:00', urgent: false, sujet: '[INFO] Rien à signaler',
      corps: 'Rien n’attend votre décision.', par: 'john' },
    veille: [{ ts: '2026-11-03T03:00:00+04:00', axe: 'concurrence', titre: 'KelFoncier bouge',
      source: 'kelfoncier.com', date_vue: '2026-10-20', libelle: 'concurrence', url: null, extrait: null }],
    carnet: [{ cle: 'dec-bdnb-retiree', type: 'decision', titre: 'BDNB retirée', corps: '…', par: 'mémoire' }],
    carnet_propositions: [],
    actions: [], journal: [],
  }),
  getJohnConversations: () => Promise.resolve({
    conversations: [{ id: 3, titre: 'Les sources sont fraîches ?', maj_at: '2026-11-04T08:00:00+04:00', cree_at: '2026-11-04T08:00:00+04:00' }],
    retention_jours: 90,
  }),
  getJohnConversation: vi.fn(),
  deleteJohnConversation: vi.fn(() => Promise.resolve({ ok: true })),
  postJohnChat: (msg: string) => chatSpy(msg),
  postJohnEnquete: vi.fn(),
  postJohnCarnetValider: vi.fn(),
  postJohnCarnetRejeter: vi.fn(),
}))

// eslint-disable-next-line import/first
import { JohnTaylor } from './JohnTaylor'

const wrap = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><JohnTaylor /></QueryClientProvider>)
}

describe('JOHN-TAYLOR-2 — la page conversationnelle', () => {
  it('ouvre sur un accueil qui parle, la liste des conversations et le volet (coût/résumé/veille/carnet)', async () => {
    const { container } = wrap()
    await waitFor(() => expect(container.textContent).toContain("Deux choses t'attendent"))
    const txt = container.textContent || ''
    expect(txt).toContain('+ Nouvelle conversation')            // colonne gauche
    expect(txt).toContain('Les sources sont fraîches ?')        // une conversation listée
    expect(txt).toContain('Conservées 90 jours')                // bandeau de rétention
    expect(txt).toContain('Coût du mois')
    expect(txt).toContain('1.23')
    expect(txt).toContain('Rien à signaler')                    // résumé du matin
    expect(txt).toContain('KelFoncier bouge')                   // veille
    expect(txt).toContain('BDNB retirée')                       // carnet de bord
    // trois suggestions sur l'accueil
    expect(container.querySelectorAll('[data-jt-suggestion]').length).toBe(3)
  })

  it('le chat envoie la question et rend une réponse lisible : chiffre en gras, source datée, bouton', async () => {
    const { container } = wrap()
    await waitFor(() => screen.getByPlaceholderText(/comme à un collègue/))
    const input = screen.getByPlaceholderText(/comme à un collègue/) as HTMLTextAreaElement
    fireEvent.change(input, { target: { value: 'Est-ce que tout tourne ?' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    await waitFor(() => expect(chatSpy).toHaveBeenCalledWith('Est-ce que tout tourne ?'))
    await waitFor(() => expect(screen.getByText(/jobs tournent/)).toBeTruthy())
    // la question de Vic reste affichée à droite dans le fil (bulle utilisateur).
    expect(container.querySelector('.jt-q')?.textContent).toBe('Est-ce que tout tourne ?')
    // chiffre en gras
    const gras = Array.from(container.querySelectorAll('[data-jt-reponse] b')).map((b) => b.textContent)
    expect(gras).toContain('42')
    // source en étiquette datée + bouton vers l'écran concerné
    const chip = container.querySelector('[data-jt-chip]')
    expect(chip?.textContent).toContain('Jobs')
    expect(chip?.textContent).toContain('14:30')
    expect(container.querySelector('[data-jt-lien]')?.textContent).toContain('Voir les jobs')
  })

  it('« + Nouvelle conversation » remet l’accueil', async () => {
    const { container } = wrap()
    await waitFor(() => screen.getByPlaceholderText(/comme à un collègue/))
    const input = screen.getByPlaceholderText(/comme à un collègue/) as HTMLTextAreaElement
    fireEvent.change(input, { target: { value: 'Une question' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    await waitFor(() => expect(screen.getByText(/jobs tournent/)).toBeTruthy())
    fireEvent.click(screen.getByText('+ Nouvelle conversation'))
    await waitFor(() => expect(container.querySelector('[data-jt-accueil]')).toBeTruthy())
  })
})
