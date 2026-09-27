import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useApp } from '../../store/useApp'
import { M02 } from './ModulePanel'

// Mandat SCAN — deux retraits : plus aucun bouton d'envoi de courrier ; l'outil observe, il ne démarche pas.
// KELFONCIER-FIX-2 (Lot B) — les deux actions « Préparer les courriers » et « Comparer » (barre de
// sélection multiple) sont retirées, avec les cases de sélection qui ne servaient qu'à elles.
// RECETTE-1 R8 — le scoring (pastille de palier) ne s'affiche QUE dans « Demander à LABUSE » et la fiche :
// le Scan patrimoine n'affiche PLUS aucun classement (ni « Sans signal », ni « Priorité »…).
const PAT = {
  nom: 'SCI TEST', siren: '123456789', n_parcelles: 3, n_actionnables: 2, sdp_residuelle_m2: 500,
  valorisation_nu_eur: 100000, bodacc: null, inpi_sans_dirigeant: false, assiette_contigue: [],
  // a_creuser = classement canonique « Neutre » (brulante serait « Priorité » — même vocabulaire que l'app).
  items: [{ idu: '97411000BZ1065', commune: 'Saint-Denis', surface_m2: 1625, sdp: 217, tier_v2: 'a_creuser', etage0: false }],
}

function mockFetch() {
  global.fetch = vi.fn(async (url: string) => {
    if (String(url).includes('/patrimoine')) return { ok: true, json: async () => PAT }
    return { ok: true, json: async () => ({}) }
  }) as unknown as typeof fetch
}
function renderM02() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><M02 /></QueryClientProvider>)
}

describe('SCAN — deux retraits', () => {
  beforeEach(() => { mockFetch(); useApp.setState({ m02Prefill: '123456789', module: 'patrimoine' }) })
  afterEach(() => { vi.restoreAllMocks(); useApp.setState({ m02Prefill: null, module: null }) })

  it('plus AUCUN bouton d\'envoi de courrier', async () => {
    const { container } = renderM02()
    await screen.findByText('SCI TEST')
    expect(container.querySelector('[data-m02-courrier]')).toBeNull()
    expect(container.querySelector('[data-scan-courrier]')).toBeNull()
    expect(container.textContent).not.toContain('✉')
  })

  it('KELFONCIER-FIX-2 Lot B — plus d\'action « Comparer » ni de sélection multiple', async () => {
    const { container } = renderM02()
    await screen.findByText('SCI TEST')                 // la liste (1 parcelle) est rendue…
    expect(container.querySelector('[data-scan-comparer]')).toBeNull()   // …sans bouton Comparer
    expect(container.querySelector('[data-scan-parc-sel]')).toBeNull()   // …sans case de sélection
    expect((container.textContent ?? '').toLowerCase()).not.toContain('comparer')
  })

  it('RECETTE-1 R8 — aucune pastille de palier (le scoring ne sort pas de « Demander à LABUSE »/fiche)', async () => {
    const { container } = renderM02()
    await screen.findByText('SCI TEST')                 // la liste est rendue…
    const txt = (container.textContent ?? '').toLowerCase()
    for (const label of ['priorité', 'à suivre', 'sans signal', 'écartée'])   // …sans aucun label de palier
      expect(txt).not.toContain(label)
  })
})
