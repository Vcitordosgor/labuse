// EXPORTS-2 lot 4 — le questionnaire du Financier : les 3 règles Vic, côté écran.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const Q = {
  idu: 'IDU1', reponses: {}, complet: false, existe: false,
  tva_explication: 'Le régime de TVA décide si le bilan travaille HT ou TTC. À confirmer avec votre expert-comptable.',
  champs_obligatoires: ['regime_tva_saisi'],
  ecrans: [
    { titre: 'Votre projet', champs: [
      { id: 'logements_vises_saisi', libelle: 'Logements visés', unite: 'logements', type: 'nombre',
        domaine: null, obligatoire: false, prefill: { valeur: 8, source: 'fourchette du potentiel LABUSE' } },
    ] },
    { titre: 'Vos conditions', champs: [
      { id: 'regime_tva_saisi', libelle: 'Régime de TVA', unite: 'classe', type: 'classe',
        domaine: ['assujetti_recuperation', 'tva_marge', 'autre'], obligatoire: true, prefill: null },
    ] },
  ],
}

vi.mock('../../lib/api', () => ({
  getFinancierQuestionnaire: vi.fn(() => Promise.resolve(Q)),
  putFinancierQuestionnaire: vi.fn(() => Promise.resolve({ idu: 'IDU1', reponses: {}, complet: true, existe: true })),
}))

import { FinancierQuestionnaire } from './FinancierQuestionnaire'

const rend = () => {
  const qc = new QueryClient()
  return render(<QueryClientProvider client={qc}><FinancierQuestionnaire idu="IDU1" onClose={() => {}} /></QueryClientProvider>)
}

describe('FinancierQuestionnaire (les 3 règles)', () => {
  beforeEach(() => vi.clearAllMocks())

  it('règle 1 — un champ pré-rempli affiche sa source sous le champ', async () => {
    rend()
    await waitFor(() => expect(screen.getByText('Logements visés (logements)')).toBeTruthy())
    expect(screen.getByText(/Source : fourchette du potentiel LABUSE/)).toBeTruthy()
  })

  it('règle 2 — un champ vidé annonce « non chiffré » (jamais un retour au défaut)', async () => {
    const { container } = rend()
    await waitFor(() => screen.getByText('Logements visés (logements)'))
    const input = container.querySelector('input[type="number"]') as HTMLInputElement
    expect(input.value).toBe('8')                       // pré-rempli
    fireEvent.change(input, { target: { value: '' } })  // le client vide
    expect(screen.getByText(/Laissé vide.*non chiffré/)).toBeTruthy()
  })

  it('règle 3 — le régime de TVA porte son explication + renvoi expert-comptable', async () => {
    rend()
    await waitFor(() => screen.getByText('Logements visés (logements)'))
    fireEvent.click(screen.getByText('Continuer →'))
    await waitFor(() => screen.getByText('Régime de TVA'))
    expect(screen.getByText(/expert-comptable/)).toBeTruthy()
    expect(screen.getByText(/obligatoire/)).toBeTruthy()
  })
})
