// CIRCUIT-P (lot 4) — le deep-link (hash) et la page de détail : rendu, retour, chips navigables.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ecrireCx, parseCx } from './hash'

vi.mock('../../../lib/api', () => ({
  getAdminCircuitReservoir: vi.fn(() => Promise.resolve({
    reservoir: { id: 42, nom: 'SITADEL', producteur: 'DGFiP', mode: 'one_shot', cadence_jours: 180,
      cadence_statut: 'validee', millesime: '2026-08', ingere_le: null, dernier_controle: null,
      etat: ['ambre', 'nouvelle version à injecter'], veille: { statut: 'nouvelle_version' },
      vanne: { type: 'injecter', label: 'sitadel' }, filtre: { source: 'sitadel', verdict: 'avertissements', controles: [] } },
    alimente: { n_chiffres: 2, n_robinets: 1, robinets: [{ id: 'fiche_parcelle', nom: 'Fiche parcelle' }] },
    chiffres: [{ id: 'n_permis', libelle: 'Permis à proximité', robinets: 1 }],
    rapport_agent: null,
  })),
  getAdminCircuitRobinet: vi.fn(), getAdminCircuitPompe: vi.fn(), getAdminCircuitNoteVersion: vi.fn(),
  postAdminSourceVeilleInjecter: vi.fn(), postAdminCircuitFiltreServir: vi.fn(),
  postAdminCircuitFiltreRevenir: vi.fn(), postAdminCircuitRevenir: vi.fn(),
  postAdminFluxBascule: vi.fn(), postAdminFluxLancerRun: vi.fn(),
}))

// eslint-disable-next-line import/first
import { Detail } from './Detail'

const data = { reservoirs: [], robinets: [{ id: 'fiche_parcelle', nom: 'Fiche parcelle', etat: ['mint', 'cohérent'] }] } as any

describe('hash deep-link', () => {
  it('parse et écrit cx sans écraser les autres paramètres', () => {
    expect(parseCx('#cx=reservoir:42')).toEqual({ type: 'reservoir', id: 42 })
    expect(parseCx('#m=donnees&cx=robinet:fiche_parcelle')).toEqual({ type: 'robinet', id: 'fiche_parcelle' })
    expect(parseCx('#cx=pompe')).toEqual({ type: 'pompe', id: 'pompe' })
    expect(parseCx('#m=donnees')).toBeNull()
    // fusion : le paramètre existant survit
    const h = ecrireCx('#m=donnees', { type: 'reservoir', id: 42 })
    expect(h).toContain('m=donnees'); expect(h).toContain('cx=reservoir%3A42')
    // fermeture : cx retiré, le reste garde
    expect(ecrireCx('#m=donnees&cx=pompe', null)).toBe('#m=donnees')
  })
})

describe('Detail réservoir', () => {
  beforeEach(() => vi.clearAllMocks())
  const wrap = (ui: React.ReactElement) => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
  }

  it('rend le nom, l\'état, une chip « alimente » et le bouton vanne ; Échap ferme', async () => {
    const onClose = vi.fn(); const onOpen = vi.fn()
    const { getByText, findByText } = wrap(
      <Detail type="reservoir" id={42} data={data} onClose={onClose} onOpen={onOpen} />)
    expect(await findByText('SITADEL')).toBeInTheDocument()
    expect(getByText('nouvelle version à injecter')).toBeInTheDocument()
    expect(getByText('Ouvrir la vanne, injecter')).toBeInTheDocument()
    fireEvent.click(getByText('Fiche parcelle'))          // chip alimente → navigue
    expect(onOpen).toHaveBeenCalledWith('robinet', 'fiche_parcelle')
    fireEvent.click(getByText('← Retour au circuit'))
    expect(onClose).toHaveBeenCalled()
  })

  it('Échap ferme le détail', async () => {
    const onClose = vi.fn()
    wrap(<Detail type="reservoir" id={42} data={data} onClose={onClose} onOpen={() => {}} />)
    await waitFor(() => {})
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).toHaveBeenCalled()
  })
})
