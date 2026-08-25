import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ProspectionSolaire } from './ProspectionSolaire'

// Mandat SOLAIRE — deux modes : Piscines (stat d'abord = agrégat) / Ensoleillement (barre unique →
// fiche soleil avec profil mensuel). Écartées masquées par défaut. Potentiel avec unité kWh/kWc/an.
const AGG = {
  total: 12480,
  communes: [{ commune: 'Saint-Paul', n: 2913 }, { commune: 'Saint-Pierre', n: 1842 }],
  source: 'Détection FLAIR sur BD ORTHO — retenues au seuil de confiance (juge FLAIR ≥ 0,30 × probe ≥ 0,50)', maj: '2026-07-11',
}
const POINTS = { type: 'FeatureCollection', features: [{ type: 'Feature', geometry: { type: 'Point', coordinates: [55.3, -21] }, properties: { kind: 'piscine', idu: '97411000AP0000' } }] }
function mkItem(i: number, ecartee = false) {
  return {
    idu: `97411000AP${String(i).padStart(4, '0')}`, commune: 'Saint-Paul', productible: 1598 - i,   // IDU 14 car.
    azimut: 12, azimut_confiance: 'basse', pente: 5, toit_m2: 140, piscine: true, piscine_m2: 32,
    abf: false, proba_occ: 60, tier_v2: ecartee ? null : 'neutre', etage0: ecartee,
    classement: ecartee ? 'Écartée' : 'Neutre',
  }
}
const LIST = {
  total: 2, n: 2, cap: 400, tronquee: false, source: 's', maj: '2026-07-11', bandeau: 'b',
  items: [mkItem(0, false), mkItem(1, true)],   // une normale + une écartée
}
const FICHE = {
  ok: true, idu: '97411000AP0000', commune: 'Saint-Paul', productible: 1598,
  prod_mensuel: [88, 84, 78, 64, 52, 46, 48, 56, 68, 78, 84, 90], mois_optimal: 12,
  azimut: 12, azimut_confiance: 'basse', pente: 5, toit_m2: 140, piscine: true, piscine_m2: 32,
  abf: false, ombrage: false, proba_occ: 60, classement: 'Neutre', millesime: 'PVGIS v5.3 SARAH3',
}

function mockFetch() {
  global.fetch = vi.fn(async (url: string) => {
    const u = String(url)
    if (u.includes('/prospection-piscines/points')) return { ok: true, json: async () => POINTS }
    if (u.includes('/prospection-piscines')) return { ok: true, json: async () => AGG }
    if (u.includes('/prospection-solaire/parcelle/')) return { ok: true, json: async () => FICHE }
    if (u.includes('/prospection-solaire')) return { ok: true, json: async () => LIST }
    if (u.includes('/communes')) return { ok: true, json: async () => [] }
    return { ok: true, json: async () => ({}) }
  }) as unknown as typeof fetch
}
function renderTool() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><ProspectionSolaire /></QueryClientProvider>)
}

describe('SOLAIRE — deux modes', () => {
  beforeEach(mockFetch)
  afterEach(() => vi.restoreAllMocks())

  it('écran d\'entrée : deux cartes (Piscines / Ensoleillement) + sources', () => {
    renderTool()
    expect(document.querySelector('[data-solaire-mode="piscines"]')).toBeTruthy()
    expect(document.querySelector('[data-solaire-mode="ensoleillement"]')).toBeTruthy()
    expect(screen.getByText(/données gelées 11\/07\/2026/)).toBeTruthy()
  })

  it('mode Piscines : la STAT d\'abord (compteur agrégat île + par commune)', async () => {
    renderTool()
    fireEvent.click(document.querySelector('[data-solaire-mode="piscines"]')!)
    await waitFor(() => expect(document.querySelector('[data-piscines-total]')?.textContent).toContain('480'))
    expect(screen.getByText('Saint-Pierre')).toBeTruthy()       // ligne par commune
  })

  it('mode Piscines (LOT8) : TOUTES les piscines listées (classement ignoré, pas de pied « écartées ») + seuil écrit', async () => {
    renderTool()
    fireEvent.click(document.querySelector('[data-solaire-mode="piscines"]')!)
    // les 2 lignes (dont l'« écartée ») s'affichent : le pisciniste veut toutes les piscines.
    await waitFor(() => expect(document.querySelectorAll('[data-piscines-row]').length).toBe(2))
    expect(document.querySelector('[data-solaire-ecartees]')).toBeNull()          // plus de pied « écartées masquées »
    // LOT8a — le seuil de rétention est écrit à l'écran ; LOT8c — pas de colonne Classement.
    expect(document.querySelector('[data-piscines-source]')?.textContent).toContain('seuil')
    expect(screen.queryByText('Classement')).toBeNull()
  })

  it('mode Ensoleillement : fiche soleil (profil mensuel 12 barres + unité kWh/kWc/an)', async () => {
    renderTool()
    fireEvent.click(document.querySelector('[data-solaire-mode="ensoleillement"]')!)
    // la fiche s'ouvre par setFicheIdu (même chemin que la barre unique SOCLE) — ici via une ligne.
    await waitFor(() => expect(document.querySelector('[data-ens-row]')).toBeTruthy())
    fireEvent.click(document.querySelector('[data-ens-row]')!)
    await screen.findByText(/Profil mensuel/)
    expect(document.querySelectorAll('[data-solaire-bar]')).toHaveLength(12)          // profil mensuel
    expect(document.querySelector('[data-solaire-fiche]')?.textContent).toContain('kWh/kWc/an')  // potentiel AVEC unité
  })
})
