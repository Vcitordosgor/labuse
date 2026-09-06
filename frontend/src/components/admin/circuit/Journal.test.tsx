// CIRCUIT-P (lot 5) / CIRCUIT-P2 (lot 4) — le journal : filtres de catégorie (« tous » d'abord,
// ordre fixe, présents même vides), ligne cliquable vers le détail (par NOM), passage GROUPÉ sur
// une ligne dépliable, « par » qui dit un nom, compteur du jour remonté.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const getJournal = vi.fn()
vi.mock('../../../lib/api', () => ({ getAdminCircuitJournal: (...a: any[]) => getJournal(...a) }))

// eslint-disable-next-line import/first
import { Journal } from './Journal'

const data = {
  reservoirs: [
    { id: 42, nom: 'SITADEL', slug: 'sitadel', etat: ['mint', 'à jour'] },
    { id: 7, nom: 'Géorisques — mouvements de terrain', slug: 'georisques_mvt', etat: ['ambre', 'en quarantaine'] },
  ],
  robinets: [{ id: 'fiche_parcelle', nom: 'Fiche parcelle', etat: ['mint', 'cohérent'] }],
} as any

const CATS = [
  { slug: 'vanne', label: 'vanne' }, { slug: 'calcul', label: 'calcul' },
  { slug: 'bascule', label: 'bascule' }, { slug: 'filtre', label: 'filtre' },
]

const reponse = {
  entrees: [
    // un passage GROUPÉ de filtres : une ligne, dépliable
    { gk: 'lot:abc', n: 2, categorie: 'filtre', categorie_label: 'filtre', geste: 'filtre',
      par_nom: 'système', ts: '2026-09-06T07:15:00Z', resultat: 'ok', cible: null, cible_nom: null,
      verdicts: { ok: 1, quarantaine: 1 }, resultats: { ok: 1, refuse: 1 },
      membres: [
        { ts: '2026-09-06T07:15:00Z', cible: 'sitadel', cible_nom: 'SITADEL', par_nom: 'système', resultat: 'ok', details: { verdict: 'ok' } },
        { ts: '2026-09-06T07:15:00Z', cible: 'georisques_mvt', cible_nom: 'Géorisques — mouvements de terrain', par_nom: 'système', resultat: 'refuse', details: { verdict: 'quarantaine' } },
      ] },
    // un geste isolé
    { gk: 'row:9', n: 1, categorie: 'bascule', categorie_label: 'bascule', geste: 'basculer',
      par_nom: 'Vic', ts: '2026-09-05T18:30:00Z', resultat: 'ok', cible: 'SITADEL', cible_nom: 'SITADEL',
      verdicts: {}, resultats: { ok: 1 }, membres: [] },
  ],
  page: 1, taille: 50, total: 2, aujourdhui: 1, categories: CATS,
}

describe('Journal', () => {
  beforeEach(() => { vi.clearAllMocks(); getJournal.mockResolvedValue(reponse) })
  const wrap = (ui: React.ReactElement) => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
  }

  it('filtres de catégorie « tous » d\'abord, ordre fixe ; compteur du jour remonté', async () => {
    const onJour = vi.fn()
    const { getByText, getAllByText } = wrap(<Journal data={data} onOpen={() => {}} onAujourdhui={onJour} />)
    await waitFor(() => expect(getByText('SITADEL')).toBeInTheDocument())
    const filtres = getAllByText(/^(tous|vanne|calcul|bascule|filtre)$/)
    expect(filtres[0].textContent).toBe('tous')
    expect(getByText('quand')).toBeInTheDocument()
    expect(onJour).toHaveBeenCalledWith(1)
  })

  it('un passage groupé tient sur une ligne, dépliable source par source (par nom)', async () => {
    const { getByText, queryByText } = wrap(<Journal data={data} onOpen={() => {}} onAujourdhui={() => {}} />)
    await waitFor(() => expect(getByText('SITADEL')).toBeInTheDocument())
    // la ligne groupée : « 2 cibles » et la répartition par verdict, sur UNE ligne
    expect(getByText('cibles', { exact: false })).toBeInTheDocument()
    expect(getByText('1 ok, 1 quarantaine')).toBeInTheDocument()
    // le détail par source est masqué avant dépliage
    expect(queryByText('Géorisques — mouvements de terrain')).toBeNull()
    fireEvent.click(getByText('cibles', { exact: false }))
    await waitFor(() => expect(getByText('Géorisques — mouvements de terrain')).toBeInTheDocument())
  })

  it('une cible mène au détail (par son nom)', async () => {
    const onOpen = vi.fn()
    const { getByText } = wrap(<Journal data={data} onOpen={onOpen} onAujourdhui={() => {}} />)
    await waitFor(() => expect(getByText('SITADEL')).toBeInTheDocument())
    fireEvent.click(getByText('SITADEL'))   // la ligne isolée « basculer » sur SITADEL
    expect(onOpen).toHaveBeenCalledWith('reservoir', 42)
  })

  it('filtrer par catégorie relance la requête', async () => {
    const { getByText, getByRole } = wrap(<Journal data={data} onOpen={() => {}} />)
    await waitFor(() => expect(getByText('SITADEL')).toBeInTheDocument())
    fireEvent.click(getByRole('button', { name: 'bascule' }))
    await waitFor(() => expect(getJournal).toHaveBeenCalledWith(expect.objectContaining({ type: 'bascule' })))
  })
})
