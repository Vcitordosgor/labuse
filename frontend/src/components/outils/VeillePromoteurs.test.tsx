import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useApp } from '../../store/useApp'
import { VeillePromoteurs } from './VeillePromoteurs'

// RETOURS-12 O6 — UN PROPRIÉTAIRE MORAL = UNE CARTE. Le listing servait une carte par OPÉRATION : un
// promoteur à plusieurs opérations (CBO TERRITORIA : 33 permis/115 lgt ET 8 permis/8 lgt) apparaissait
// deux fois. On regroupe par SIREN → une seule carte, compteurs = somme de ses opérations.
const OP = (over: Record<string, unknown>) => ({
  siren: '452038805', denomination: 'CBO TERRITORIA', categorie: 'promoteur', commune: 'Saint-Denis',
  nb_logements: 0, n_permis: 0, date_min: null, date_max: '2025-01-01', annee: 2025, etat: null,
  lon: 55.4, lat: -20.9, idus: ['97411000AB0001'], libelle: '', radar_bien_id: null, radar_cite: false,
  programme: null, ...over,
})
const DATA = {
  n_total: 3, n_servi: 3, tronquee: false, plafond: 200, n_logements_total: 173,
  categories: [], millesime: '2025-01-01',
  regle: { contiguite_m: 150, periode_mois: 18, phrase: 'règle' },
  operations: [
    OP({ nb_logements: 115, n_permis: 33 }),                        // CBO opération 1
    OP({ nb_logements: 8, n_permis: 8, idus: ['97411000AB0002'] }), // CBO opération 2 (même SIREN)
    OP({ siren: '999999999', denomination: 'AUTRE PROMOTEUR', nb_logements: 50, n_permis: 5 }),
  ],
  note: '',
}

function mockFetch() {
  global.fetch = vi.fn(async (url: string) => {
    const u = String(url)
    if (u.includes('/outils/veille-promoteurs')) return { ok: true, json: async () => DATA }
    if (u.includes('/moi')) return { ok: true, json: async () => ({ mode: 'local' }) }
    return { ok: true, json: async () => ({}) }
  }) as unknown as typeof fetch
}

function renderVP() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><VeillePromoteurs /></QueryClientProvider>)
}

describe('VeillePromoteurs — anti-doublon O6', () => {
  beforeEach(() => { mockFetch(); useApp.setState({ commune: '', veilleFocusSiren: null }) })
  afterEach(() => vi.restoreAllMocks())

  it('un propriétaire moral = UNE carte (CBO regroupé, plus deux)', async () => {
    renderVP()
    await screen.findByText('CBO TERRITORIA')
    // 2 promoteurs distincts → 2 cartes (pas 3 opérations)
    expect(document.querySelectorAll('[data-vp-promoteur]')).toHaveLength(2)
    expect(document.querySelectorAll('[data-vp-siren="452038805"]')).toHaveLength(1)   // CBO une seule fois
  })

  it('les compteurs de la carte = somme de ses opérations (même périmètre que la frise)', async () => {
    renderVP()
    await screen.findByText('CBO TERRITORIA')
    const carte = document.querySelector('[data-vp-siren="452038805"]') as HTMLElement
    const t = (carte.textContent ?? '').replace(/\s/g, ' ')
    expect(t).toContain('2 opérations')          // ses deux opérations regroupées
    expect(t).toContain('41 permis')             // 33 + 8
    expect(t).toContain('123 logements')         // 115 + 8
    // ses deux opérations restent listées dessous (détail, une fois chacune)
    expect(carte.querySelectorAll('[data-vp-operation]')).toHaveLength(2)
  })
})
