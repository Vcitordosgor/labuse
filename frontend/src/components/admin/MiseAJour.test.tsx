import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import fixture from './__fixtures__/adminFluxReal.json'

// DONNEES-2 — l'onglet « Mise à jour » (trois étapes verticales) rendu sur la RÉPONSE RÉELLE capturée
// (la même fixture que le Circuit, RETOURS-9 Q1) : une action = un endroit, un chiffre = une liste.
// On vérifie que les trois étapes portent leurs infos et leurs boutons, que l'étape 3 distingue le
// run recommandé du retour arrière (run précédent), et qu'on n'invente rien (l'écart et la garde
// lus tels quels). Injecter/Lancer/Basculer/Vérifier appellent bien les mutations.

const injecter = vi.fn((_id: number) => {})
const lancer = vi.fn((_r: string) => Promise.resolve({ ok: true, label: 'q_v12_20260903_1810', estimation: '~2 h 05', log: '/tmp/x.log' }))
const bascule = vi.fn((_r: string) => Promise.resolve({ ok: true, ancien: 'q_v11_m137', nouveau: 'q_v10_m129', caches_purges: ['a', 'b'] }))
const cronRun = vi.fn((_n: string) => Promise.resolve({ ok: true }))

vi.mock('../../lib/api', async (importOriginal) => {
  const real = await importOriginal<typeof import('../../lib/api')>()
  return {
    ...real,
    getAdminFlux: vi.fn(async () => fixture.flux),
    getAdminFluxRuns: vi.fn(async () => fixture.runs),
    postAdminSourceVeilleInjecter: (id: number) => { injecter(id); return Promise.resolve({ ok: true, label: 'x', log: 'y', millesime: null }) }, // eslint-disable-line
    postAdminFluxLancerRun: (r: string) => lancer(r),
    postAdminFluxBascule: (r: string) => bascule(r),
    postAdminCronRun: (n: string) => cronRun(n),
  }
})

const renderMaj = async () => {
  const { MiseAJour } = await import('./MiseAJour')
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><MiseAJour /></QueryClientProvider>)
}

describe('DONNEES-2 — onglet Mise à jour (3 étapes verticales, réponse réelle)', () => {
  it('rend les trois étapes avec leurs titres', async () => {
    await renderMaj()
    await waitFor(() => expect(screen.getByText('Injecter')).toBeTruthy())
    expect(screen.getByText('Calculer')).toBeTruthy()
    expect(screen.getByText('Basculer')).toBeTruthy()
  })

  it('étape 1 — rien à injecter (aucune source warn) + bouton « Vérifier toutes les sources »', async () => {
    const { container } = await renderMaj()
    await waitFor(() => expect(screen.getByText(/Rien à injecter/)).toBeTruthy())
    const btn = container.querySelector('[data-verifier-toutes]') as HTMLButtonElement
    expect(btn).toBeTruthy()
    fireEvent.click(btn)
    await waitFor(() => expect(cronRun).toHaveBeenCalledWith('sentinelle-sources'))
  })

  it('étape 2 — run servi nommé + Lancer un run appelle la recette m36', async () => {
    await renderMaj()
    await waitFor(() => expect(screen.getAllByText(/q_v11_m137/).length).toBeGreaterThan(0))
    fireEvent.click(screen.getByText('Lancer un run →'))
    await waitFor(() => expect(lancer).toHaveBeenCalledWith('m36'))
    // le run lancé apparaît « en cours » (session), honnêtement sans % ni arrêt
    await waitFor(() => expect(screen.getByText(/En cours/)).toBeTruthy())
    expect(screen.getByText(/ne peut pas être interrompu/)).toBeTruthy()
    expect(screen.queryByText('Arrêter')).toBeNull()
  })

  it('étape 3 — recommandé vs retour arrière (run précédent), écart lu tel quel, garde 6/6', async () => {
    await renderMaj()
    // le run précédent (q_v10_m129) est le RETOUR ARRIÈRE (pas le recommandé)
    await waitFor(() => expect(screen.getByText('ancien run servi')).toBeTruthy())
    expect(screen.getByText('recommandé')).toBeTruthy()
    // écart réel du rollback : 220 parcelles changent, Priorité 1 478 → 1 607
    expect(screen.getByText(/220/)).toBeTruthy()
    // la garde de cohérence (6 checks du fixture) est affichée
    expect(screen.getByText(/Tier identique fiche/)).toBeTruthy()
  })

  it('basculer appelle l\'endpoint avec le label du run', async () => {
    await renderMaj()
    await waitFor(() => expect(screen.getByText('ancien run servi')).toBeTruthy())
    fireEvent.click(screen.getByText('Revenir à ce run →'))
    await waitFor(() => expect(bascule).toHaveBeenCalledWith('q_v10_m129'))
  })
})
