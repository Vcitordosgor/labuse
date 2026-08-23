import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fmtEurCompact, fmtInt } from '../../lib/format'
import { useApp } from '../../store/useApp'
import { EtudierBien } from './EtudierBien'

// Mandat ETUDIER — sur BZ 1065 : charge NÉGATIVE affichée (plus de « 0 € » écrêté), verdict UNIQUE à
// bascule, libellé « SHAB vendable » (pas « SDP »), alerte de cohérence résiduel-bâti (26 < 123).
const CONSTAT = {
  ok: true, adresse: 'BZ 1065', idu: '97411000BZ1065', commune: 'Saint-Denis', surface_m2: 1625,
  verdict: { tier: 'neutre', libelle: 'Neutre', rang: null, percentile: null },
  constat: {
    charge_calibree: { central: -219375, par_m2_terrain: -135, ca_central: 525825 },
    sourced: { shab_vendable_m2: 123, sdp_plancher_m2: 154, coef_rendement: 0.8, terrain_m2: 1625, prix_sortie_median: 4275, prix_neuf_label: null },
    terrain_zone: { eur_m2: 485, fiabilite: 'moyenne', n: 12 },
    motif: null,
  },
}
const FICHE = { potentiel_transformation: { sdp_residuelle_m2: 26 } }

function mockFetch() {
  global.fetch = vi.fn(async (url: string) => {
    const u = String(url)
    if (u.includes('/scoreur-adresse')) return { ok: true, json: async () => CONSTAT }
    if (u.includes('/parcels/')) return { ok: true, json: async () => FICHE }
    return { ok: true, json: async () => ({}) }
  }) as unknown as typeof fetch
}

function renderEtudier() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><EtudierBien /></QueryClientProvider>)
}

const norm = (s: string) => s.replace(/\s/g, ' ')

describe('ETUDIER — « Étudier un bien » (BZ 1065)', () => {
  beforeEach(() => {
    mockFetch()
    useApp.setState({ calcPrefill: '97411000BZ1065' })   // porte fiche → résout le constat au montage
  })
  afterEach(() => { vi.restoreAllMocks(); useApp.setState({ calcPrefill: null }) })

  it('la charge NÉGATIVE s\'affiche en négatif (jamais « 0 € »), en rouge', async () => {
    renderEtudier()
    await screen.findByText(/SHAB vendable/)
    const chargeEl = document.querySelector('[data-etudier-charge]') as HTMLElement
    expect(chargeEl).toBeTruthy()
    expect(norm(chargeEl.textContent ?? '')).toBe(norm(fmtEurCompact(-219375)))   // « −219 k€ », pas « 0 € »
    expect(chargeEl.textContent).not.toBe('0 €')
    expect(chargeEl.className).toContain('text-st-ecartee')                        // rouge
  })

  it('libellé « SHAB vendable » — plus jamais « SDP vendable »', async () => {
    renderEtudier()
    await screen.findByText(/SHAB vendable/)
    expect(screen.queryByText(/SDP vendable/)).toBeNull()
  })

  it('verdict UNIQUE à bascule [Calibrées LABUSE | Vos hypothèses]', async () => {
    renderEtudier()
    await screen.findByText(/SHAB vendable/)
    expect(document.querySelector('[data-etudier-mode="calibree"]')).toBeTruthy()
    expect(document.querySelector('[data-etudier-mode="hypotheses"]')).toBeTruthy()
    // un SEUL bloc-verdict
    expect(document.querySelectorAll('[data-etudier-verdict]')).toHaveLength(1)
  })

  it('alerte de cohérence résiduel (26 m²) reliée à Pièges & risques', async () => {
    renderEtudier()
    const alerte = await screen.findByText(/Résiduel net du bâti/)
    const box = alerte.closest('[data-etudier-residuel]') as HTMLElement
    expect(norm(box.textContent ?? '')).toContain(`${fmtInt(26)} m²`)
    expect(box.querySelector('[data-etudier-residuel-lien]')).toBeTruthy()
  })
})
