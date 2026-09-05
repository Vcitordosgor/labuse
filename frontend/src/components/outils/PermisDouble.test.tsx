import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useApp } from '../../store/useApp'
import { M03 } from './ModulePanel'

// Mandat PERMIS (OUTILS-2 O2-1) — segment [En cours N | Point mort N | Tous] (compteurs réels),
// lignes sur deux lignes (commune + badges), survol = le point s'allume sur la carte (permitHover).
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
    if (u.includes('/communes')) return { ok: true, json: async () => [] }   // RETOURS-18 — bloc Affiner rend CommunePermisSelect
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

  // RETOURS-18 X1 — la liste vit dans le bloc d'accordéon « Voir les permis », replié par défaut :
  // on l'ouvre avant d'attendre des lignes.
  const ouvrirListe = () => fireEvent.click(document.querySelector('[data-permis-bloc-toggle="liste"]')!)

  it('segment avec compteurs RÉELS (en cours 5 613 / point mort 412)', async () => {
    renderM03()
    // le bloc « Filtrer par état » est ouvert d'emblée : les compteurs sont visibles sans rien ouvrir.
    await waitFor(() => expect(document.querySelector('[data-permis-seg="cours"]')?.textContent).toContain('613'))
    expect(document.querySelector('[data-permis-seg="mort"]')?.textContent).toContain('412')
  })

  it('lignes enrichies : commune + badge « non géocodé » (après ouverture du bloc liste)', async () => {
    const { container } = renderM03()
    ouvrirListe()
    await waitFor(() => expect(document.querySelectorAll('[data-permis-row]').length).toBe(2))
    expect(container.textContent).toContain('Saint-Denis')
    expect(container.textContent).toContain('Sainte-Marie')
    expect(document.querySelector('[data-permis-badge-nongeo]')).toBeTruthy()   // le PC2 non géocodé
  })

  it('la liste ne s\'affiche PAS d\'emblée (accordéon replié)', async () => {
    renderM03()
    // compteurs présents (bloc état ouvert) mais aucune ligne tant que « Voir les permis » est replié
    await waitFor(() => expect(document.querySelector('[data-permis-seg="cours"]')).toBeTruthy())
    expect(document.querySelectorAll('[data-permis-row]').length).toBe(0)
    ouvrirListe()
    await waitFor(() => expect(document.querySelectorAll('[data-permis-row]').length).toBe(2))
  })

  it('survol d\'une ligne allume le point (permitHover), sortie l\'éteint', async () => {
    renderM03()
    ouvrirListe()
    await waitFor(() => expect(document.querySelectorAll('[data-permis-row]').length).toBe(2))
    const row = document.querySelector('[data-permis-row]') as HTMLElement
    fireEvent.mouseEnter(row)
    expect(useApp.getState().permitHover).toEqual(GEOM)
    fireEvent.mouseLeave(row)
    expect(useApp.getState().permitHover).toBeNull()
  })

  it('segment « Point mort » → liste point mort (badge « Sans DAACT · X ans »)', async () => {
    renderM03()
    fireEvent.click(document.querySelector('[data-permis-seg="mort"]')!)
    ouvrirListe()
    await waitFor(() => expect(document.querySelector('[data-permis-badge-mort]')).toBeTruthy())
    // ancienneté calculée depuis la date d'autorisation (2023 → « · N ans »)
    expect(document.querySelector('[data-permis-badge-mort]')?.textContent).toContain('Sans DAACT')
  })

  // RETOURS-18 X1 — accordéon : un seul bloc ouvert à la fois ; les barres repliées disent leur contenu.
  it('accordéon : un seul bloc ouvert (ouvrir Affiner referme Filtrer par état)', async () => {
    renderM03()
    // état ouvert d'emblée : ses lignes sont là, ni le corps Affiner ni la liste
    await waitFor(() => expect(document.querySelector('[data-permis-segment]')).toBeTruthy())
    expect(document.querySelector('[data-permis-geo="geo"]')).toBeNull()       // Affiner replié
    expect(document.querySelector('[data-permis-pied]')).toBeNull()            // liste repliée
    // ouvrir Affiner → Filtrer par état se referme
    fireEvent.click(document.querySelector('[data-permis-bloc-toggle="affiner"]')!)
    await waitFor(() => expect(document.querySelector('[data-permis-geo="geo"]')).toBeTruthy())
    expect(document.querySelector('[data-permis-segment]')).toBeNull()         // état refermé
    // la barre repliée « Filtrer par état » DIT son état actif + compte (défaut permis = Récent)
    const barreEtat = document.querySelector('[data-permis-bloc-toggle="etat"]')?.textContent
    expect(barreEtat).toContain('Récent')
    expect(barreEtat).toContain('613')
  })

  it('accordéon : Échap referme le bloc ouvert', async () => {
    renderM03()
    ouvrirListe()
    await waitFor(() => expect(document.querySelector('[data-permis-pied]')).toBeTruthy())
    fireEvent.keyDown(document.querySelector('[data-permis-bloc-toggle="liste"]')!, { key: 'Escape' })
    await waitFor(() => expect(document.querySelector('[data-permis-pied]')).toBeNull())
  })
})
