import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ProspectionSolaire } from './ProspectionSolaire'
import { useApp } from '../../store/useApp'

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
    // A2 — type de propriétaire : i=0 PM nommée, i=1 particulier non nommé
    proprio: i === 0 ? { type: 'personne_morale', denomination: 'SCI SOLEIL', siren: '123456789' } : { type: 'particulier' },
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
  // A6 — dimensionnement servi par le back ; A1 — inclinaison réelle du calcul PVGIS (config, 15°).
  kwc: 28, prod_annuel: 44744, kwc_par_m2: 0.2, inclinaison_deg: 15,
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
    // A1 — les sources restent affichées, mais plus de date « gelée » en dur (millésime servi ailleurs).
    expect(screen.getByText(/PVGIS v5\.3 SARAH3/)).toBeTruthy()
    expect(screen.queryByText(/gelées 11\/07\/2026/)).toBeNull()
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
    // RETOURS-11 O13 — l'onglet « Top parcelles » (et ses lignes data-ens-row) est RETIRÉ : la fiche
    // soleil s'ouvre via la barre unique « Ma parcelle » (prefill IDU → mode ensoleillement).
    useApp.setState({ solairePrefill: '97411000AP0000' })
    renderTool()
    await screen.findByText(/Profil mensuel/)
    expect(document.querySelectorAll('[data-solaire-bar]')).toHaveLength(12)          // profil mensuel
    expect(document.querySelector('[data-solaire-fiche]')?.textContent).toContain('kWh/kWc/an')  // potentiel AVEC unité
  })

  it('A1 — le pied dit l\'inclinaison RÉELLE du calcul PVGIS (15°), jamais « 65 » en dur', async () => {
    useApp.setState({ solairePrefill: '97411000AP0000' })
    renderTool()
    await screen.findByText(/Profil mensuel/)
    const fiche = document.querySelector('[data-solaire-fiche]')!
    expect(fiche.textContent).toContain('inclinés à 15°')
    expect(fiche.textContent).not.toContain('65°')
    // A1 — plus de date « gelée » en dur dans le pied de page
    expect(fiche.textContent).not.toContain('gelées 11/07/2026')
  })

  it('A6 — puissance installable + production servies par le back, ratio kWc/m² écrit', async () => {
    useApp.setState({ solairePrefill: '97411000AP0000' })
    renderTool()
    await screen.findByText(/Profil mensuel/)
    const fiche = document.querySelector('[data-solaire-fiche]')!
    expect(fiche.textContent).toContain('28')          // kWc servi (pas recalculé au front)
    expect(document.querySelector('[data-solaire-kwc-hyp]')?.textContent).toContain('0,2 kWc/m²')
  })

  it('A2/A5 — liste Piscines : potentiel, type propriétaire, pont Courrier (CSV retiré FIX-3 E)', async () => {
    renderTool()
    fireEvent.click(document.querySelector('[data-solaire-mode="piscines"]')!)
    await waitFor(() => expect(document.querySelectorAll('[data-piscines-row]').length).toBe(2))
    const body = document.body.textContent ?? ''
    expect(body).toContain('SCI SOLEIL')                 // A2 — PM nommée
    expect(body).toContain('particulier — non nommé')    // A2 — particulier jamais nommé
    expect(body.replace(/\s/g, '')).toContain('1598')    // A2 — potentiel servi (fmtInt insère une espace)
    expect(document.querySelector('[data-piscines-csv]')).toBeFalsy()        // OUTILS-FIX-3 E — export CSV retiré
    // A5 — sélectionner une ligne active le pont Courrier
    const cb = document.querySelector('[data-piscines-sel]') as HTMLInputElement
    fireEvent.click(cb)
    const courrier = document.querySelector('[data-piscines-courrier]') as HTMLButtonElement
    expect(courrier.disabled).toBe(false)
    expect(courrier.textContent).toContain('(1)')
  })
})
