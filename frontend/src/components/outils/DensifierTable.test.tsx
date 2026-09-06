import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useApp } from '../../store/useApp'
import { DensifierTablePanel } from './Renouvellement'

// Mandat DENSIFIER — grand tableau plein écran : pagination SOCLE par offset (400 par 400 → épuisement),
// compteur exact « n / total », colonnes complètes, export CSV. Le back sert des pages capées (offset).
const TOTAL = 7
const CAP = 3   // pages de 3 pour un test léger (l'écran réel = 400)

function mkItem(i: number) {
  return {
    idu: `9740400000AZ${String(i).padStart(4, '0')}`, commune_nom: 'Saint-Paul', commune_insee: '97411',
    renouv_score: 100 - i, comp_potentiel: 40, comp_assiette: 20, comp_marche: 10,
    code_bati_origine: i % 2 === 0 ? 'deja_bati' : 'ensemble_bati',
    sdp_residuelle_m2: 3000 - i, surface_m2: 5000 - i, zone_plu: 'U3',
    rang_segment: i + 1, rang_commune: i + 1, tier_v2: 'neutre', etage0: false,
  }
}
function page(offset: number) {
  const n = Math.min(CAP, TOTAL - offset)
  return {
    total: TOTAL, n, cap: CAP, tronquee: TOTAL > n, source: 'Analyse LABUSE', run_label: 'r', maj: '2026-08-20',
    libelle: '', composantes_libelles: {}, avertissement: '',
    items: Array.from({ length: Math.max(0, n) }, (_, k) => mkItem(offset + k)),
  }
}

function renderPanel() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><DensifierTablePanel /></QueryClientProvider>)
}

describe('DENSIFIER — DensifierTablePanel (grand tableau)', () => {
  beforeEach(() => {
    global.fetch = vi.fn(async (url: string) => {
      const m = /offset=(\d+)/.exec(String(url))
      const offset = m ? Number(m[1]) : 0
      return { ok: true, json: async () => page(offset) }
    }) as unknown as typeof fetch
    useApp.setState({ module: 'renouvellement', densifierTableOpen: true, commune: null })
  })
  afterEach(() => { vi.restoreAllMocks(); useApp.setState({ module: null, densifierTableOpen: false }) })

  it('page 1 : compteur exact + colonnes attendues, la première page est servie', async () => {
    renderPanel()
    await screen.findByText('9740400000AZ0000')
    // compteur SOCLE « 3 / 7 »
    expect(document.querySelector('[data-pagination-count]')?.textContent).toContain('3 / 7')
    expect(document.querySelectorAll('[data-densifier-row]')).toHaveLength(CAP)
    // colonnes du mandat, dont « Bâti existant » (certains libellés existent aussi en chip de tri → getAll).
    // OUTILS-FIX-1 C1 : la colonne « Surélévation » est RETIRÉE (batch débranché, valeur périmée).
    for (const h of ['Parcelle', 'Classement', 'SDP nette', 'Surface', 'Bâti existant', 'Zone', 'Rang commune'])
      expect(screen.getAllByText(h).length).toBeGreaterThan(0)
    expect(screen.queryByText('Surélévation')).toBeNull()
  })

  it('« Bâti existant » sert le TYPE d\'occupation (jamais un m² inventé)', async () => {
    renderPanel()
    await screen.findByText('9740400000AZ0000')
    // item 0 = deja_bati → « déjà bâtie » ; aucune valeur m² dans cette colonne
    expect(screen.getAllByText('déjà bâtie').length).toBeGreaterThan(0)
  })

  it('pagination par offset : « Voir de plus » accumule jusqu\'à épuisement', async () => {
    renderPanel()
    await screen.findByText('9740400000AZ0000')
    ;(document.querySelector('[data-pagination-more]') as HTMLElement).click()
    await waitFor(() => expect(document.querySelectorAll('[data-densifier-row]')).toHaveLength(6))
    expect(document.querySelector('[data-pagination-count]')?.textContent).toContain('6 / 7')
    // dernière page (partielle) : 1 restante
    ;(document.querySelector('[data-pagination-more]') as HTMLElement).click()
    await waitFor(() => expect(document.querySelectorAll('[data-densifier-row]')).toHaveLength(7))
    expect(document.querySelector('[data-pagination-more]')).toBeNull()   // épuisé : plus de bouton
  })

  it('OUTILS-1 B7 — export CSV RETIRÉ (consultation illimitée, extraction non)', async () => {
    renderPanel()
    await screen.findByText('9740400000AZ0000')
    // Le bouton d'export CSV n'existe plus ; la liste reste consultable en entier.
    expect(document.querySelector('[data-densifier-csv]')).toBeNull()
  })
})
