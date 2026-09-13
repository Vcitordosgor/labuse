// EXPORTS-2 lot 4 — le questionnaire du Financier : les 3 règles Vic, côté écran.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const Q = {
  idu: 'IDU1', reponses: {}, complet: false, existe: false,
  tva_explication: 'Le régime de TVA décide si le bilan travaille HT ou TTC. À confirmer avec votre expert-comptable.',
  champs_obligatoires: ['regime_tva_saisi'],
  // RECETTE-6 (E5) — écran 0 « Que voulez-vous chiffrer ? » : construction servie, les autres grisés.
  usages: [
    { key: 'construction', label: 'Construction neuve', servi: true, sous: 'Le bilan à rebours.' },
    { key: 'revente', label: 'Revente en l\'état', servi: false, raison: 'Pas encore servi.' },
  ],
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

// RECETTE-6 (E5) — l'écran 0 précède les 4 écrans : on choisit « Construction neuve » (le seul servi)
// pour atteindre le questionnaire. Les autres usages restent grisés (non testés ici).
const entrerConstruction = async () => {
  await waitFor(() => screen.getByText('Que voulez-vous chiffrer ?'))
  fireEvent.click(screen.getByText('Construction neuve'))
  await waitFor(() => screen.getByText('Logements visés (logements)'))
}

describe('FinancierQuestionnaire (les 3 règles)', () => {
  beforeEach(() => vi.clearAllMocks())

  it('E5 — écran 0 : construction servie, les autres usages grisés', async () => {
    rend()
    await waitFor(() => screen.getByText('Que voulez-vous chiffrer ?'))
    const revente = screen.getByText('Revente en l\'état').closest('button') as HTMLButtonElement
    expect(revente.disabled).toBe(true)
    expect(screen.getByText('Pas encore servi.')).toBeTruthy()
    const construction = screen.getByText('Construction neuve').closest('button') as HTMLButtonElement
    expect(construction.disabled).toBe(false)
  })

  it('règle 1 — un champ pré-rempli affiche sa source sous le champ', async () => {
    rend()
    await entrerConstruction()
    expect(screen.getByText(/Source : fourchette du potentiel LABUSE/)).toBeTruthy()
  })

  it('règle 2 — un champ vidé annonce « non chiffré » (jamais un retour au défaut)', async () => {
    const { container } = rend()
    await entrerConstruction()
    const input = container.querySelector('input[type="number"]') as HTMLInputElement
    expect(input.value).toBe('8')                       // pré-rempli
    fireEvent.change(input, { target: { value: '' } })  // le client vide
    expect(screen.getByText(/Laissé vide.*non chiffré/)).toBeTruthy()
  })

  it('règle 3 — le régime de TVA porte son explication + renvoi expert-comptable', async () => {
    rend()
    await entrerConstruction()
    fireEvent.click(screen.getByText('Continuer →'))
    await waitFor(() => screen.getByText('Régime de TVA'))
    expect(screen.getByText(/expert-comptable/)).toBeTruthy()
    // RECETTE-5 (V19) — le marqueur « obligatoire » devient « indispensable » (les autres « facultatif »).
    expect(screen.getByText(/indispensable/)).toBeTruthy()
  })
})

// RECETTE-10 T2a/T2b — questionnaire au propre : le bandeau programme et le tri des questions.
const Q2 = {
  ...Q,
  programme: { auto: false, source: 'saisie', message: 'Renseignez le nombre de logements visés et la typologie.' },
  ecrans: [
    { titre: 'Votre projet', champs: [
      { id: 'logements_vises_saisi', libelle: 'Logements visés', unite: 'logements', type: 'nombre',
        domaine: null, obligatoire: true, prefill: null, tri: 'garder' },
      { id: 'part_sociale_saisi_pct', libelle: 'Part sociale', unite: '%', type: 'nombre',
        domaine: null, obligatoire: false, prefill: null, tri: 'affiner' },
      { id: 'scenario_saisi', libelle: 'Scénario', unite: 'texte', type: 'texte',
        domaine: null, obligatoire: false, prefill: { valeur: 'reconstruction', source: 'x' }, tri: 'supprimer' },
    ] },
  ],
}

describe('FinancierQuestionnaire — RECETTE-10 T2 (bandeau + tri)', () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    const api = await import('../../lib/api')
    ;(api.getFinancierQuestionnaire as ReturnType<typeof vi.fn>).mockResolvedValue(Q2)
  })

  const entrer = async () => {
    await waitFor(() => screen.getByText('Que voulez-vous chiffrer ?'))
    fireEvent.click(screen.getByText('Construction neuve'))
    await waitFor(() => screen.getByText('Logements visés (logements)'))
  }

  it('T2a — le bandeau programme s\'affiche à l\'écran du champ, puis disparaît une fois rempli', async () => {
    const { container } = rend()
    await entrer()
    expect(container.querySelector('[data-financier-programme]')).toBeTruthy()   // affiché : champ vide
    const input = container.querySelector('input[type="number"]') as HTMLInputElement
    fireEvent.change(input, { target: { value: '8' } })                          // on répond
    expect(container.querySelector('[data-financier-programme]')).toBeNull()     // disparaît
  })

  it('T2b — « garder » visible, « affiner » replié, « supprimer » jamais rendu', async () => {
    const { container } = rend()
    await entrer()
    expect(screen.getByText('Logements visés (logements)')).toBeTruthy()          // garder : direct
    expect(screen.queryByText('Part sociale (%)')).toBeNull()                     // affiner : replié
    expect(screen.queryByText('Scénario')).toBeNull()                            // supprimer : absent
    const toggle = container.querySelector('[data-financier-affiner-toggle]') as HTMLButtonElement
    expect(toggle).toBeTruthy()
    fireEvent.click(toggle)                                                       // on déplie
    expect(screen.getByText('Part sociale (%)')).toBeTruthy()
    expect(screen.queryByText('Scénario')).toBeNull()                            // toujours absent
  })
})
