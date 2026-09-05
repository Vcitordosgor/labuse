import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fmtInt } from '../../lib/format'
import { useApp } from '../../store/useApp'
import { EtudierBien } from './EtudierBien'

// RETOURS-12 O2 — refonte « Étudier un bien » en DEUX niveaux : premier niveau DESCRIPTIF (ce que
// porte la parcelle + repères de marché, AUCUN nombre négatif, AUCUN verdict d'opération), et le
// raisonnement d'opération (bilan, charge, marge) derrière un geste explicite. Le prix demandé est
// COMPARÉ à ce qu'une opération pourrait payer (plancher 0), jamais additionné à une charge négative.
// Ancré sur BZ 1065 (charge calibrée −219 375 € = le cas de la capture de Vic).
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

describe('ETUDIER — refonte O2 deux niveaux (BZ 1065)', () => {
  beforeEach(() => {
    mockFetch()
    useApp.setState({ calcPrefill: '97411000BZ1065' })   // porte fiche → résout le constat au montage
  })
  afterEach(() => { vi.restoreAllMocks(); useApp.setState({ calcPrefill: null }) })

  it('PREMIER niveau descriptif : « ce que porte la parcelle », AUCUN verdict/charge à l\'accueil', async () => {
    renderEtudier()
    const porte = await screen.findByText(/Ce que porte la parcelle/)
    const box = porte.closest('[data-etudier-porte]') as HTMLElement
    expect(norm(box.textContent ?? '')).toContain('Surface habitable constructible')
    expect(norm(box.textContent ?? '')).toContain(`${fmtInt(123)} m²`)
    expect(document.querySelector('[data-etudier-verdict]')).toBeNull()   // pas de charge à l'accueil
    expect(document.querySelector('[data-etudier-analyser]')).toBeTruthy()   // le geste explicite
  })

  it('SECOND niveau (sur geste) : charge NÉGATIVE présentée « 0 € », jamais un nombre négatif de tête', async () => {
    renderEtudier()
    await screen.findByText(/Ce que porte la parcelle/)
    fireEvent.click(document.querySelector('[data-etudier-analyser]') as HTMLElement)
    const chargeEl = await screen.findByText('0 €', { selector: '[data-etudier-charge]' })
    expect(chargeEl).toBeTruthy()
    expect(document.querySelector('[data-etudier-verdict]')).toBeTruthy()
    expect(norm(document.querySelector('[data-etudier-verdict]')!.textContent ?? ''))
      .toContain('ne dégage rien pour le terrain')
  })

  it('prix demandé COMPARÉ, jamais additionné : « écart » = prix, pas un déficit cumulé', async () => {
    renderEtudier()
    await screen.findByText(/Ce que porte la parcelle/)
    fireEvent.click(document.querySelector('[data-etudier-analyser]') as HTMLElement)
    await screen.findByText('0 €', { selector: '[data-etudier-charge]' })
    fireEvent.change(document.querySelector('[data-etudier-prix]') as HTMLElement, { target: { value: '500000' } })
    const t = norm((document.querySelector('[data-etudier-ecart]') as HTMLElement).textContent ?? '')
    expect(t).toContain('écart')
    expect(t).toContain('une opération pourrait en payer')
    expect(t).not.toContain('719')   // plus jamais le déficit cumulé charge − prix (−219 − 500 = −719)
  })

  it('bascule [Calibrées LABUSE | Vos hypothèses] présente dans l\'analyse d\'opération', async () => {
    renderEtudier()
    await screen.findByText(/Ce que porte la parcelle/)
    fireEvent.click(document.querySelector('[data-etudier-analyser]') as HTMLElement)
    await screen.findByText('0 €', { selector: '[data-etudier-charge]' })
    expect(document.querySelector('[data-etudier-mode="calibree"]')).toBeTruthy()
    expect(document.querySelector('[data-etudier-mode="hypotheses"]')).toBeTruthy()
    expect(document.querySelectorAll('[data-etudier-verdict]')).toHaveLength(1)
  })

  it('alerte de cohérence résiduel (26 m²) reliée à Pièges & risques', async () => {
    renderEtudier()
    await screen.findByText(/Ce que porte la parcelle/)
    const alerte = await screen.findByText(/Bâti existant/)   // attend la résolution de la fiche (async)
    const box = alerte.closest('[data-etudier-residuel]') as HTMLElement
    expect(box).toBeTruthy()
    expect(norm(box.textContent ?? '')).toContain(`${fmtInt(26)} m²`)
    expect(box.querySelector('[data-etudier-residuel-lien]')).toBeTruthy()
  })
})
