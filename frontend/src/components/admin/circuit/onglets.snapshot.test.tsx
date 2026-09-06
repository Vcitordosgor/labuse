// CIRCUIT-P (lot 6.2) — snapshot de chaque onglet : Résumé, Circuit (diagramme), Journal. Capture
// de régression du rendu une fois l'ancien rendu retiré.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const getJournal = vi.fn()
vi.mock('../../../lib/api', () => ({ getAdminCircuitJournal: (...a: any[]) => getJournal(...a) }))

// eslint-disable-next-line import/first
import { CircuitDiagram } from './CircuitDiagram'
// eslint-disable-next-line import/first
import { Journal } from './Journal'
// eslint-disable-next-line import/first
import { Resume } from './Resume'

const data = {
  run_servi: 'q_v11_m137', candidat: null, manifeste: { scoring_run: 'q_v11_m137' },
  dernier_controle: { ts: '2026-09-06T07:15:00Z' },
  reservoirs: [
    { id: 1, nom: 'Cadastre', producteur: 'IGN', etat: ['mint', 'à jour'], slug: 'cadastre', taps: ['fiche_parcelle'], millesime: 'PCI', dernier_controle: null, cadence_jours: null },
    { id: 2, nom: 'SITADEL', producteur: 'DGFiP', etat: ['ambre', 'nouvelle version à injecter'], slug: 'sitadel', taps: ['outil_marche'], millesime: '2026-07', dernier_controle: null, cadence_jours: 180 },
  ],
  robinets: [
    { id: 'fiche_parcelle', nom: 'Fiche parcelle', categorie: 'fiche', chiffres: ['a'], etat: ['mint', 'cohérent'], parent: null },
    { id: 'outil_marche', nom: 'Marché', categorie: 'outil', chiffres: ['b'], etat: ['ambre', '1 hors moteur'], parent: null },
  ],
  familles: [{ nom: 'Parcelles et propriété', ids: [1] }, { nom: 'Marché, logement, permis', ids: [2] }],
  categories: [{ slug: 'fiche', nom: 'Fiches', ids: ['fiche_parcelle'] }, { slug: 'outil', nom: 'Outils', ids: ['outil_marche'] }],
  chiffres: { a: { moteur: 'x', calcul: 'moteur' }, b: { moteur: 'y', calcul: 'passe_plat' } },
  compteurs: { chiffres: 2, reservoirs: 2, a_jour: 1, a_regarder: 1, vides: 0, robinets: 2, robinets_a_regarder: 1, robinets_coherents: 1 },
  residuel: { changees: false }, fuites: [],
  resume: {
    total: 1, reste: { reservoirs: 2, robinets: 2, chiffres: 2 },
    kpis: [
      { valeur: 1, sur: 2, libelle: 'réservoirs à jour et vérifiés' },
      { valeur: 1, sur: 2, libelle: 'robinets sans rien à signaler' },
      { valeur: 2, libelle: 'chiffres définis une fois' },
      { valeur: 'q_v11_m137', candidat: null, libelle: 'run servi' },
    ],
    groupes: [
      { titre: 'À faire, un geste de toi', lignes: [
        { n: 1, couleur: 'ambre', titre: 'réservoir plein, à injecter', phrase: 'SITADEL', verbe: 'Injecter', cible: { type: 'reservoir', ids: [2] } }] },
      { titre: 'À corriger, un mandat pour CC', lignes: [] },
      { titre: 'À décider, quand tu veux', lignes: [] },
    ],
  },
} as any

describe('snapshots des onglets', () => {
  beforeEach(() => getJournal.mockResolvedValue({
    entrees: [{ gk: 'row:1', n: 1, categorie: 'cron', categorie_label: 'cron', geste: 'job',
      cible: 'coherence-robinets', cible_nom: 'coherence-robinets', par_nom: 'système',
      ts: '2026-09-06T07:15:00Z', resultat: 'ok', verdicts: {}, resultats: { ok: 1 }, membres: [] }],
    page: 1, taille: 50, total: 1, aujourdhui: 1,
    categories: [{ slug: 'vanne', label: 'vanne' }, { slug: 'cron', label: 'cron' }],
  }))

  it('Résumé', () => {
    const { container } = render(<Resume data={data} onCible={() => {}} />)
    expect(container.firstChild).toMatchSnapshot()
  })

  it('Circuit (diagramme)', () => {
    const { container } = render(<CircuitDiagram data={data} groupe={null} onOpen={() => {}} />)
    expect(container.firstChild).toMatchSnapshot()
  })

  it('Journal', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const { container, getByText } = render(
      <QueryClientProvider client={qc}><Journal data={data} onOpen={() => {}} /></QueryClientProvider>)
    await waitFor(() => expect(getByText('coherence-robinets')).toBeInTheDocument())
    expect(container.firstChild).toMatchSnapshot()
  })
})
