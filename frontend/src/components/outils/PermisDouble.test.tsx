import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useApp } from '../../store/useApp'
import { M03 } from './ModulePanel'

// Mandat PERMIS — deux entrées franches (compteurs réels), lignes enrichies (commune + badges),
// survol d'une ligne = le point s'allume sur la carte (permitHover).
const GEOM = { type: 'Point', coordinates: [55.4, -20.9] }
const RADAR = {
  total: 5613, geocodes: 5037, sans_localisation: 576, pct_geocode: 90, donnees_jusqu_au: '2026-06-30',
  has_more: false, carte: [{ permit_id: 'PC1', type: 'PC', date: '2026-06-30', geom: GEOM }],
  items: [
    { permit_id: 'PC1', type: 'PC', date: '2026-06-30', commune: 'Saint-Denis', etat: 'en cours', nb_lgt: 68, delai_mois: 5, geom: GEOM },
    { permit_id: 'PC2', type: 'PC', date: '2026-06-29', commune: 'Sainte-Marie', etat: 'en cours', nb_lgt: 2, delai_mois: null, geom: null },
  ],
}
const PROMESSES = {
  has_more: false,
  items: [{ permit_id: 'PC9', type: 'PC', date: '2023-11-14', commune: 'Le Tampon', etat: '3', surface_m2: 800, nb_lgt: 12, geom: GEOM, tier_v2: 'neutre', etage0: false, statut: null }],
}

function mockFetch() {
  global.fetch = vi.fn(async (url: string) => {
    const u = String(url)
    if (u.includes('count_only')) return { ok: true, json: async () => ({ total: 412 }) }
    if (u.includes('/modules/promesses')) return { ok: true, json: async () => PROMESSES }
    if (u.includes('/modules/permis')) return { ok: true, json: async () => RADAR }
    return { ok: true, json: async () => ({}) }
  }) as unknown as typeof fetch
}
function renderM03() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><M03 /></QueryClientProvider>)
}

describe('PERMIS — double entrée + densité', () => {
  beforeEach(() => { mockFetch(); useApp.setState({ module: 'permis', commune: null, zone: null, permitHover: null, permitToOpen: null }) })
  afterEach(() => { vi.restoreAllMocks(); useApp.setState({ module: null, permitHover: null }) })

  it('deux entrées avec compteurs RÉELS (radar 5 613 / point mort 412)', async () => {
    renderM03()
    await waitFor(() => expect(document.querySelector('[data-permis-entree="cours"]')?.textContent).toContain('613'))
    expect(document.querySelector('[data-permis-entree="mort"]')?.textContent).toContain('412')
  })

  it('lignes enrichies : commune + badge « non géocodé »', async () => {
    const { container } = renderM03()
    await waitFor(() => expect(document.querySelectorAll('[data-permis-row]').length).toBe(2))
    expect(container.textContent).toContain('Saint-Denis')
    expect(container.textContent).toContain('Sainte-Marie')
    expect(document.querySelector('[data-permis-badge-nongeo]')).toBeTruthy()   // le PC2 non géocodé
  })

  it('survol d\'une ligne allume le point (permitHover), sortie l\'éteint', async () => {
    renderM03()
    await waitFor(() => expect(document.querySelectorAll('[data-permis-row]').length).toBe(2))
    const row = document.querySelector('[data-permis-row]') as HTMLElement
    fireEvent.mouseEnter(row)
    expect(useApp.getState().permitHover).toEqual(GEOM)
    fireEvent.mouseLeave(row)
    expect(useApp.getState().permitHover).toBeNull()
  })

  it('basculer sur « Accordés jamais réalisés » → liste point mort (badge)', async () => {
    renderM03()
    await waitFor(() => expect(document.querySelectorAll('[data-permis-row]').length).toBe(2))
    fireEvent.click(document.querySelector('[data-permis-entree="mort"]')!)
    await waitFor(() => expect(document.querySelector('[data-permis-badge-mort]')).toBeTruthy())
  })
})
