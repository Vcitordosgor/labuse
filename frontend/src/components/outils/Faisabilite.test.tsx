import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useApp } from '../../store/useApp'
import { M22 } from './M22Programme'
import { FaisabiliteTab } from '../fiche/Fiche'

// Mandat FAISABILITE — pagination SOCLE (par critères) + programme épinglé + étape 12 (SHAB vendable
// retenue) dans la trace par parcelle.
const CAP = 2, N = 5
function progPage(offset: number) {
  const n = Math.min(CAP, N - offset)
  return {
    criteres: { unites: 24, sdp_min_m2: 1728, calcul: '24 × 60 × 1,2', hauteur_min_m: 9, hauteur_regle: 'R+2 → gabarit' },
    bandeau: 'Estimation.', n: N, cap: CAP, offset,
    items: Array.from({ length: Math.max(0, n) }, (_, k) => ({
      idu: `97415000DK${String(1000 + offset + k)}`, commune: 'Saint-Paul', sdp: 281159 - offset - k, zone: 'AU2h',
      hauteur_verifiee: true, hauteur_plu_m: 13, capacite_estimee: false, marge_capacite: 162.7 - offset - k,
      statut: 'neutre', tier_v2: 'neutre', etage0: false, geom: null,
    })),
  }
}
const BILAN = {
  idu: '97411000BZ1065',
  capacite: {
    verdict: 'R+1 · ~2 logts', calibree: true, bandeau: 'Estimé.',
    fourchette: { niveaux: 'R+1', niveaux_max: 2, hauteur_m: 6, surface_plancher_m2: 219, shab_vendable_m2: 123, logements_au_sol: [1, 2] },
    steps: [
      { label: 'Surface habitable (rendement)', valeur: '~175 m²', source: 'SDP × 0,8', prov: 'derive' },
      { label: 'Logements retenus au sol', valeur: '~1 à 2', source: 'plafond densité', prov: 'derive' },
    ],
  },
  marche: null, bilan: null, fiscal: null, rtaa: null,
}

function mockFetch() {
  global.fetch = vi.fn(async (url: string, init?: RequestInit) => {
    const u = String(url)
    if (u.includes('/modules/faisabilite/')) return { ok: true, json: async () => BILAN }
    if (u.includes('/modules/programme')) { const off = JSON.parse(String(init?.body ?? '{}')).offset ?? 0; return { ok: true, json: async () => progPage(off) } }
    if (u.includes('/communes')) return { ok: true, json: async () => [] }   // CommuneScope
    return { ok: true, json: async () => ({}) }
  }) as unknown as typeof fetch
}
const qc = () => new QueryClient({ defaultOptions: { queries: { retry: false } } })

describe('FAISABILITE — pagination + programme épinglé', () => {
  beforeEach(() => { mockFetch(); useApp.setState({ m22Prefill: null, parcelPrefill: null }) })
  afterEach(() => vi.restoreAllMocks())

  it('par critères : « Trouver » → recap épinglé (total) + pagination « voir N de plus »', async () => {
    render(<QueryClientProvider client={qc()}><M22 /></QueryClientProvider>)
    fireEvent.click(screen.getByText('Trouver les parcelles'))
    await waitFor(() => expect(document.querySelectorAll('[data-prog-item]').length).toBe(CAP))
    // recap épinglé : le VRAI total (5) + les critères (24 unités)
    const recap = document.querySelector('[data-prog-count]') as HTMLElement
    expect(recap.className).toContain('sticky')
    expect(recap.textContent).toContain('5')
    expect(recap.textContent).toContain('24')
    // pagination
    expect(document.querySelector('[data-pagination-count]')?.textContent).toContain('2 / 5')
    ;(document.querySelector('[data-pagination-more]') as HTMLElement).click()
    await waitFor(() => expect(document.querySelectorAll('[data-prog-item]').length).toBe(4))
    expect(document.querySelector('[data-prog-csv]')).toBeTruthy()
  })
})

describe('FAISABILITE — étape 12 (SHAB vendable retenue)', () => {
  beforeEach(mockFetch)
  afterEach(() => vi.restoreAllMocks())

  it('la trace par parcelle gagne l\'étape « SHAB vendable retenue » (~123 m²)', async () => {
    render(<QueryClientProvider client={qc()}><FaisabiliteTab idu="97411000BZ1065" /></QueryClientProvider>)
    const ol = await waitFor(() => { const o = document.querySelector('[data-faisa-steps]'); if (!o) throw new Error('no steps'); return o as HTMLElement })
    // 2 étapes moteur + 1 étape ajoutée = 3
    expect(ol.querySelectorAll('li').length).toBe(3)
    const last = ol.querySelectorAll('li')[2]
    expect(last.textContent).toContain('SHAB vendable retenue')
    expect(last.textContent).toContain('123')
  })
})
