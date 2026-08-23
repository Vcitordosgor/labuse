import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { M15 } from './moteurs'

// Mandat PLU Lot A — le recalcul à blanc AU→U se PAGINE (SOCLE) : « Voir N de plus » jusqu'à
// épuisement, compteur exact, TOTAUX stables (servis par le back, pas la somme de la page).
const CAP = 3
const TOTAL = 7
function mkItem(i: number) {
  return { idu: `97415000AB${String(i).padStart(4, '0')}`, surface_m2: 1000 - i, statut_actuel: 'a_creuser',
    tier_v2: 'a_creuser', rang_v2: i, etage0: false, sdp_estimee_m2: 400 - i, bascule_potentielle: true,
    geom: { type: 'Point', coordinates: [0, 0] } }
}
function page(offset: number) {
  const n = Math.min(CAP, TOTAL - offset)
  return {
    zone: 'AUs', commune: 'Saint-Paul', ratio_analogie: 0.318, methode: '',
    n_parcelles: n, n_total: TOTAL, cap: CAP, offset, tronquee: TOTAL > offset + n,
    bascules_potentielles: TOTAL, sdp_totale_estimee_m2: 2_799_683,   // TOTAL stable
    items: Array.from({ length: Math.max(0, n) }, (_, k) => mkItem(offset + k)),
  }
}

function mockFetch() {
  global.fetch = vi.fn(async (url: string) => {
    const u = String(url)
    if (u.includes('/simulplu/zones')) return { ok: true, json: async () => [{ zone: 'AUs', n_ilots: 10 }] }
    if (u.includes('/simulplu')) { const m = /offset=(\d+)/.exec(u); return { ok: true, json: async () => page(m ? Number(m[1]) : 0) } }
    return { ok: true, json: async () => ({}) }
  }) as unknown as typeof fetch
}
function renderM15() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><M15 communeOverride="Saint-Paul" /></QueryClientProvider>)
}

describe('PLU Lot A — pagination du recalcul à blanc', () => {
  beforeEach(mockFetch)
  afterEach(() => vi.restoreAllMocks())

  it('choisir une zone → page 1 : compteur exact + totaux stables', async () => {
    renderM15()
    const chip = await screen.findByText('AUs → U')
    fireEvent.click(chip)
    await waitFor(() => expect(document.querySelectorAll('[data-m15-item]').length).toBe(CAP))
    expect(document.querySelector('[data-pagination-count]')?.textContent).toContain('3 / 7')
    // total (7) et SDP totale servis par le back — pas la somme de la page
    expect(screen.getByText(/parcelles en AUs/).textContent).toContain('7')
  })

  it('« Voir N de plus » pagine par offset jusqu\'à épuisement', async () => {
    renderM15()
    fireEvent.click(await screen.findByText('AUs → U'))
    await waitFor(() => expect(document.querySelectorAll('[data-m15-item]').length).toBe(3))
    ;(document.querySelector('[data-pagination-more]') as HTMLElement).click()
    await waitFor(() => expect(document.querySelectorAll('[data-m15-item]').length).toBe(6))
    expect(document.querySelector('[data-pagination-count]')?.textContent).toContain('6 / 7')
    ;(document.querySelector('[data-pagination-more]') as HTMLElement).click()
    await waitFor(() => expect(document.querySelectorAll('[data-m15-item]').length).toBe(7))
    expect(document.querySelector('[data-pagination-more]')).toBeNull()   // épuisé
  })
})
