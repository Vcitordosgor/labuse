import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import * as api from '../../../lib/api'
import { CopiloteView } from '../CopiloteView'

vi.mock('../../../lib/api', async (original) => ({
  ...await original<typeof api>(),
  copiloteV2Ask: vi.fn(), copiloteV2Mission: vi.fn(),
  copiloteV2Missions: vi.fn(), copiloteV2MissionSupprimer: vi.fn(),
}))

const mission: api.CopiloteMission = {
  id: 7, titre: 'Conversation A', updated_at: new Date().toISOString(),
  n_messages: 2, statut: 'active', run_id: null,
}
const conversation: api.CopiloteConversation = {
  ...mission, created_at: mission.updated_at,
  messages: [
    { role: 'client', texte: 'Question passée', intent: null, ts: mission.updated_at },
    { role: 'copilote', texte: 'Résultat passé', intent: 'QUESTION', ts: mission.updated_at,
      reponse: { sources: ['cadastre'], porte: 'communes' } },
  ],
}
beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn()
  vi.mocked(api.copiloteV2Missions).mockResolvedValue({ missions: [mission], retention_jours: 30 })
  vi.mocked(api.copiloteV2Mission).mockResolvedValue(conversation)
})
afterEach(() => { cleanup(); vi.resetAllMocks(); vi.useRealTimers() })

function envoyer(question: string) {
  fireEvent.change(screen.getByRole('textbox'), { target: { value: question } })
  fireEvent.click(screen.getByRole('button', { name: 'Envoyer' }))
}

it('ignore une réponse qui arrive après Nouvelle conversation', async () => {
  let terminer!: (rep: api.CopiloteV2Reponse) => void
  vi.mocked(api.copiloteV2Ask).mockReturnValue(new Promise(resolve => { terminer = resolve }))
  render(<CopiloteView />)
  envoyer('Question tardive')
  fireEvent.click(screen.getByText('+ Nouvelle conversation'))
  await act(async () => terminer({ conversation_id: 7, text: 'Réponse tardive', intent: 'QUESTION' }))
  expect(screen.queryByText('Réponse tardive')).toBeNull()
  expect(screen.getByText('Sur quoi on travaille ?')).toBeTruthy()
})

it('affiche la nouvelle parcelle sans les attributs de la précédente', async () => {
  const a = '97415000CV1186', b = '97415000BY0083'
  vi.mocked(api.copiloteV2Ask).mockResolvedValueOnce({ text: 'Première réponse', intent: 'QUESTION',
    resume_fiche: { idu: a, commune: 'Saint-Paul', tuiles: [], sections: [], source: '', millesime: null } })
    .mockResolvedValueOnce({ text: 'Seconde réponse', intent: 'OUTIL', prefill_idu: b })
  const { container } = render(<CopiloteView />)
  envoyer(a)
  await screen.findByText('Première réponse')
  envoyer(b)
  await screen.findByText('Seconde réponse')
  expect(container.querySelector('[data-fil-contexte]')?.textContent).toBe(b)
})

it('restaure les sources et les actions des tours enregistrés', async () => {
  render(<CopiloteView />)
  fireEvent.click(await screen.findByText(mission.titre))
  expect(await screen.findByText('cadastre')).toBeTruthy()
  expect(screen.getByRole('button', { name: /ouvrir l.outil/i })).toBeTruthy()
})

it('annonce l’expiration du contexte pendant la lecture du fil', async () => {
  vi.useFakeTimers()
  vi.mocked(api.copiloteV2Ask).mockResolvedValue({ intent: 'QUESTION', text: 'Résultat', contexte_ttl_minutes: 1 })
  render(<CopiloteView />)
  await act(async () => envoyer('Question'))
  expect(screen.queryByText(/contexte de cette conversation a expiré/)).toBeNull()
  act(() => vi.advanceTimersByTime(60000))
  expect(screen.getByText(/contexte de cette conversation a expiré/)).toBeTruthy()
})

it('signale aussi un contexte déjà expiré à la réouverture', async () => {
  vi.mocked(api.copiloteV2Mission).mockResolvedValue({ ...conversation, updated_at: '2020-01-01T00:00:00Z', contexte_ttl_minutes: 10 })
  render(<CopiloteView />)
  fireEvent.click(await screen.findByText(mission.titre))
  expect(await screen.findByText(/contexte de cette conversation a expiré/)).toBeTruthy()
})

it.each(['refus', 'réseau'])('préserve le fil et le brouillon si la suppression échoue (%s)', async (cas) => {
  if (cas === 'refus') vi.mocked(api.copiloteV2MissionSupprimer).mockResolvedValue({ ok: false })
  else vi.mocked(api.copiloteV2MissionSupprimer).mockRejectedValue(new Error())
  render(<CopiloteView />)
  fireEvent.click(await screen.findByText(mission.titre))
  await screen.findByText('Résultat passé')
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Mon brouillon' } })
  fireEvent.click(screen.getByRole('button', { name: /Supprimer la conversation/ }))
  fireEvent.click(screen.getByText('Oui'))
  expect(await screen.findByRole('alert')).toBeTruthy()
  expect(screen.getByDisplayValue('Mon brouillon')).toBeTruthy()
  expect(screen.getByText('Résultat passé')).toBeTruthy()
})

it('distingue liste en erreur et liste vide, puis relance le chargement', async () => {
  vi.mocked(api.copiloteV2Missions).mockRejectedValueOnce(new Error())
  render(<CopiloteView />)
  await screen.findByRole('alert')
  expect(screen.queryByText(/Aucune conversation/)).toBeNull()
  fireEvent.click(screen.getByText('Réessayer'))
  await waitFor(() => expect(screen.getByText(mission.titre)).toBeTruthy())
  expect(screen.queryByRole('alert')).toBeNull()
})

it('signale un échec à l’ouverture du fil', async () => {
  vi.mocked(api.copiloteV2Mission).mockRejectedValue(new Error())
  render(<CopiloteView />)
  fireEvent.click(await screen.findByText(mission.titre))
  expect(await screen.findByText(/Impossible d’ouvrir cette conversation/)).toBeTruthy()
})

it('réessaie la même demande sans dupliquer le tour ni effacer le brouillon', async () => {
  vi.mocked(api.copiloteV2Ask).mockRejectedValueOnce(new Error('504'))
    .mockResolvedValueOnce({ text: 'Réponse récupérée', intent: 'QUESTION', conversation_id: 7 })
  const { container } = render(<CopiloteView />)
  envoyer('Question à reprendre')
  const retry = await screen.findByText('Réessayer')
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Mon prochain tour' } })
  fireEvent.click(retry)
  await screen.findByText('Réponse récupérée')
  expect(vi.mocked(api.copiloteV2Ask).mock.calls[1]).toEqual(vi.mocked(api.copiloteV2Ask).mock.calls[0])
  expect(container.querySelectorAll('[data-fil-question]')).toHaveLength(1)
  fireEvent.click(await screen.findByText(mission.titre))
  expect(screen.getByDisplayValue('Mon prochain tour')).toBeTruthy()
})

it('charge la page de conversations suivante en conservant la première', async () => {
  vi.mocked(api.copiloteV2Missions)
    .mockResolvedValueOnce({ missions: [mission], retention_jours: 30, suite: true })
    .mockResolvedValueOnce({ missions: [{ ...mission, titre: 'Ancien fil', id: 2 }], retention_jours: 30 })
  render(<CopiloteView />)
  fireEvent.click(await screen.findByText('Conversations précédentes'))
  await screen.findByText('Ancien fil')
  expect(screen.getByText(mission.titre)).toBeTruthy()
  expect(vi.mocked(api.copiloteV2Missions).mock.calls[1]).toEqual([mission])
})

it('rend la saisie au clavier après le premier envoi par Entrée', async () => {
  vi.mocked(api.copiloteV2Ask).mockResolvedValue({ intent: 'QUESTION', text: 'Surface calculée' })
  render(<CopiloteView />)
  const champ = screen.getByRole('textbox')
  champ.focus()
  fireEvent.change(champ, { target: { value: 'Question' } })
  fireEvent.keyDown(champ, { key: 'Enter' })
  await screen.findByText('Surface calculée')
  expect(document.activeElement).toBe(screen.getByRole('textbox'))
})
