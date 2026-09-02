import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import fixture from './__fixtures__/adminFluxReal.json'

// RETOURS-9 (Q1) — le Circuit restait bloqué sur « Chargement… » chez Vic. Cause exacte prouvée en
// base réelle : /admin/flux mettait ~55 s (le calcul d'écart des runs, `comparer()` + COUNT self-join
// sur parcel_p_score_v2 3 M lignes). Fix = rendu progressif : /admin/flux rend le Circuit tout de
// suite, les runs arrivent via /admin/flux/runs. Ce test rejoue la RÉPONSE RÉELLE capturée (fixture,
// pas fabriquée) et vérifie que la page rend — jamais bloquée — et que Q4 (une seule phrase surfaces)
// est bien la MÊME au bandeau et à la colonne.

vi.mock('../../lib/api', async (importOriginal) => {
  const real = await importOriginal<typeof import('../../lib/api')>()
  return {
    ...real,
    getAdminFlux: vi.fn(async () => fixture.flux),
    getAdminFluxRuns: vi.fn(async () => fixture.runs),
    postAdminFluxLancerRun: vi.fn(),
    postAdminFluxBascule: vi.fn(),
    postAdminSourceVeilleInjecter: vi.fn(),
  }
})

const renderFlux = async () => {
  const { FluxSection } = await import('./Flux')
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><FluxSection /></QueryClientProvider>)
}

describe('RETOURS-9 Q1 — Circuit rend sur la réponse RÉELLE (plus de « Chargement… »)', () => {
  it('rend la fourmilière avec la réponse réelle capturée', async () => {
    await renderFlux()
    // la page rend (n'est PAS restée sur « Chargement… »)
    await waitFor(() => expect(screen.getByText(/La donnée, de la source à l'écran/)).toBeTruthy())
    // le run réel est affiché
    expect(screen.getAllByText(/q_v11_m137/).length).toBeGreaterThan(0)
  })

  it('Q4 — UNE phrase surfaces exacte, identique au bandeau et à la colonne (21 · 20 · 1 vivante)', async () => {
    await renderFlux()
    await waitFor(() => expect(screen.getByText(/La donnée, de la source à l'écran/)).toBeTruthy())
    const phrase = '21 surfaces · 20 sur q_v11_m137 · 1 vivante (hors run)'
    const occ = screen.getAllByText(phrase)
    // bandeau (data-flux-surfaces-phrase) ET note de colonne Surfaces = 2 fois la MÊME chaîne
    expect(occ.length).toBeGreaterThanOrEqual(2)
  })

  it('Q5 — ligne d\'aide + bouton « Tout désélectionner »', async () => {
    await renderFlux()
    await waitFor(() => expect(screen.getByText(/La donnée, de la source à l'écran/)).toBeTruthy())
    expect(screen.getByText(/tout ce qui est relié s'allume/)).toBeTruthy()
    expect(screen.getByText('Tout désélectionner')).toBeTruthy()
  })
})
