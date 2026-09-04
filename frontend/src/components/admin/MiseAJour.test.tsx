import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import fixture from './__fixtures__/adminFluxReal.json'

// DONNEES-2 — l'onglet « Mise à jour » (trois étapes verticales) : une action = un endroit, un chiffre
// = une liste. On rejoue le flux réel capturé (fixture) pour l'en-tête/garde, et une charge de RUNS
// portant leur STATUT (D3 : termine · servi · retour_arriere · ancien · abandonne) pour vérifier que
// l'étape 3 range chaque run au bon endroit, et que l'étape 2 (progression réelle + Arrêter) marche.

const injecter = vi.fn((_id: number) => {})
const lancer = vi.fn((_r: string) => Promise.resolve({ ok: true, label: 'q_v12_20260903_1810', estimation: '~2 h 05', log: '/tmp/x.log' }))
const bascule = vi.fn((_r: string) => Promise.resolve({ ok: true, ancien: 'q_v11_m137', nouveau: 'q_v10_m129', caches_purges: ['a', 'b'], reconstruction: { lancee: true, run: 'q_v10_m129' } }))
const arreter = vi.fn((_l: string) => Promise.resolve({ ok: true, tue: true }))
const cronRun = vi.fn((_n: string) => Promise.resolve({ ok: true }))
const etat = vi.fn(async () => ({ en_cours: null as unknown }))

// runs avec STATUT (D3) : q_v12 recommandé, q_v11 servi, q_v10 retour arrière, q_v8 ancien, un abandonné.
const RUNS = {
  runs: [
    { label: 'q_v12', servi: false, complet: true, statut: 'termine', motif: 'run complet',
      calcule_le: '2026-09-03T18:59:29+04:00', n_parcelles: 431663, recette: 'q_v12',
      note_de_version: 'Candidat q_v12 — gains sûrs de SCORING-2.',
      ecart: { tiers_changes: 4688, promues_candidat: 1225, promues_servi: 1478, derive_promues_pct: -17.1 } },
    { label: 'q_v11_m137', servi: true, complet: true, statut: 'servi', motif: 'run complet',
      calcule_le: '2026-08-27T15:02:01+04:00', n_parcelles: 431663, ecart: null },
    { label: 'q_v10_m129', servi: false, complet: true, statut: 'retour_arriere', motif: 'run complet',
      calcule_le: '2026-08-19T18:38:08+04:00', n_parcelles: 431663,
      ecart: { tiers_changes: 220, promues_candidat: 1607, promues_servi: 1478, derive_promues_pct: 8.7 } },
    { label: 'q_v8_calibre', servi: false, complet: true, statut: 'ancien', motif: 'run complet',
      calcule_le: '2026-08-07T00:17:13+04:00', n_parcelles: 431663, ecart: null },
    { label: 'q_v12_20260903_1550', servi: false, complet: false, statut: 'abandonne',
      motif: 'run abandonné', calcule_le: '2026-09-03T17:50:00+04:00', n_parcelles: null, ecart: null,
      progress: { phase: 'abandonné', commune: null, pct: null } },
  ],
  derniere: null,
}

vi.mock('../../lib/api', async (importOriginal) => {
  const real = await importOriginal<typeof import('../../lib/api')>()
  return {
    ...real,
    getAdminFlux: vi.fn(async () => fixture.flux),
    getAdminFluxRuns: vi.fn(async () => RUNS),
    getAdminFluxRunEtat: () => etat(),
    postAdminSourceVeilleInjecter: (id: number) => { injecter(id); return Promise.resolve({ ok: true, label: 'x', log: 'y', millesime: null }) }, // eslint-disable-line
    postAdminFluxLancerRun: (r: string) => lancer(r),
    postAdminFluxBascule: (r: string) => bascule(r),
    postAdminFluxArreterRun: (l: string) => arreter(l),
    postAdminCronRun: (n: string) => cronRun(n),
  }
})

const renderMaj = async () => {
  const { MiseAJour } = await import('./MiseAJour')
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><MiseAJour /></QueryClientProvider>)
}

beforeEach(() => { etat.mockResolvedValue({ en_cours: null }) })

describe('DONNEES-2 — onglet Mise à jour (3 étapes, statut des runs)', () => {
  it('rend les trois étapes', async () => {
    await renderMaj()
    await waitFor(() => expect(screen.getByText('Injecter')).toBeTruthy())
    expect(screen.getByText('Calculer')).toBeTruthy()
    expect(screen.getByText('Basculer')).toBeTruthy()
  })

  it('étape 1 — rien à injecter + « Vérifier toutes les sources » appelle le job sentinelle', async () => {
    const { container } = await renderMaj()
    await waitFor(() => expect(screen.getByText(/Rien à injecter/)).toBeTruthy())
    fireEvent.click(container.querySelector('[data-verifier-toutes]') as HTMLButtonElement)
    await waitFor(() => expect(cronRun).toHaveBeenCalledWith('sentinelle-sources'))
  })

  it('étape 2 — run servi nommé + « Lancer un run » appelle la recette m36', async () => {
    await renderMaj()
    await waitFor(() => expect(screen.getAllByText(/q_v11_m137/).length).toBeGreaterThan(0))
    fireEvent.click(screen.getByText('Lancer un run →'))
    await waitFor(() => expect(lancer).toHaveBeenCalledWith('m36'))
  })

  it('étape 2 — un run EN COURS montre la progression réelle (%) et le bouton Arrêter (pas de faux %)', async () => {
    etat.mockResolvedValue({ en_cours: { label: 'q_v12_20260903_1810', statut: 'en_cours', phase: 'cascade', commune: 'Saint-Paul', pct: 42, done: 10, total: 25 } })
    await renderMaj()
    await waitFor(() => expect(screen.getByText(/En cours/)).toBeTruthy())
    expect(screen.getByText(/Saint-Paul/)).toBeTruthy()
    expect(screen.getByText(/42%/)).toBeTruthy()
    // Lancer est désactivé pendant qu'un run tourne
    expect((screen.getByText('Lancer un run →') as HTMLButtonElement).disabled).toBe(true)
    fireEvent.click(screen.getByText('Arrêter'))
    await waitFor(() => expect(arreter).toHaveBeenCalledWith('q_v12_20260903_1810'))
  })

  it('étape 3 — statut : recommandé=termine, retour arrière=retour_arriere, abandonné masqué', async () => {
    await renderMaj()
    await waitFor(() => expect(screen.getByText('recommandé')).toBeTruthy())
    // recommandé = q_v12 (termine), écart réel lu tel quel
    expect(screen.getByText(/4 688/)).toBeTruthy()
    // retour arrière = q_v10_m129
    expect(screen.getByText('ancien run servi')).toBeTruthy()
    // le run abandonné (et l'ancien) sont dans le repli « anciens ou abandonnés »
    expect(screen.getByText(/runs? anciens? ou abandonné/)).toBeTruthy()
    // la garde de cohérence (6 checks du fixture) est affichée
    expect(screen.getByText(/Tier identique fiche/)).toBeTruthy()
  })

  it('basculer vers le recommandé appelle l\'endpoint et annonce la reconstruction', async () => {
    await renderMaj()
    await waitFor(() => expect(screen.getByText('recommandé')).toBeTruthy())
    fireEvent.click(screen.getByText('Basculer vers q_v12 →'))
    await waitFor(() => expect(bascule).toHaveBeenCalledWith('q_v12'))
  })
})
