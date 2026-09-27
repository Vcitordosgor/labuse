import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ProspectionSolaire } from './ProspectionSolaire'
import { useApp } from '../../store/useApp'

// Mandat SOLAIRE — deux modes : Piscines (stat d'abord = agrégat) / Ensoleillement (barre unique →
// fiche soleil avec profil mensuel). Écartées masquées par défaut. Potentiel avec unité kWh/kWc/an.
// PISCINES-2 — agrégat de la source unique : `confiance` porte les bandes par STATUT (servie / à confirmer).
const AGG = {
  total: 12480,
  communes: [{ commune: 'Saint-Paul', n: 2913 }, { commune: 'Saint-Pierre', n: 1842 }],
  confiance: { haute: 12480, incertaines: 500, seuil_haute: 0.8, inclure_incertaines: false },
  corrigees: 0,
  source: 'Source unique fusionnée FLAIR ∪ CoSIA, dédoublonnée à 5 m ; statut servie (précision ≥ 85 %) par défaut', maj: '2026-09-25',
}
// PISCINES-2 — LISTE pisciniste : idu · commune · surface · source · statut · propriétaire (pas de potentiel).
const PISC_LIST = {
  total: 2, n: 2, maj: '2026-09-25', source: 'Source unique FLAIR ∪ CoSIA',
  items: [
    { idu: '97411000AP0000', commune: 'Saint-Paul', surface_m2: 42, source: 'flair+cosia', statut: 'servie',
      proprio: { type: 'personne_morale', denomination: 'SCI SOLEIL', siren: '123456789' } },
    { idu: '97411000AP0001', commune: 'Saint-Paul', surface_m2: 28, source: 'cosia', statut: 'a_confirmer',
      proprio: { type: 'particulier' } },
  ],
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
    if (u.includes('/prospection-piscines/liste')) return { ok: true, json: async () => PISC_LIST }
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

  it('RETOURS-15 C6 : encart « N piscines détectées à La Réunion », « Voir les piscines » ouvre la liste', async () => {
    renderTool()
    fireEvent.click(document.querySelector('[data-solaire-mode="piscines"]')!)
    // (1) encart total + (2) par commune apparaissent d'emblée ; (3) « Voir les piscines » ouvre la liste.
    await waitFor(() => expect(document.querySelector('[data-piscines-total]')?.textContent).toContain('480'))
    expect(document.body.textContent).toContain('piscines détectées à La Réunion')   // C6 — encart
    expect(document.body.textContent).not.toContain('à équiper')                     // sous-texte retiré
    expect(screen.getByText('Saint-Pierre')).toBeTruthy()       // filtre par commune
    expect(document.querySelector('[data-piscines-row]')).toBeNull()   // pas encore de listing
    expect(document.querySelector('[data-piscines-voir]')?.textContent).toContain('Voir les piscines')
    fireEvent.click(document.querySelector('[data-piscines-voir]')!)
    await waitFor(() => expect(document.querySelectorAll('[data-piscines-row]').length).toBe(2))
    expect(document.querySelector('[data-piscines-voir]')).toBeNull()  // le bouton a disparu
  })

  it('PISCINES-2 : source fusionnée (statut) + bascule « à confirmer » ; aucun « potentiel »', async () => {
    renderTool()
    fireEvent.click(document.querySelector('[data-solaire-mode="piscines"]')!)
    await waitFor(() => expect(document.querySelector('[data-piscines-source]')?.textContent).toContain('fusionnée'))
    expect(document.querySelector('[data-piscines-toggle-aconfirmer]')).toBeTruthy()   // statut, plus de « incertaines » confiance
    fireEvent.click(document.querySelector('[data-piscines-voir]')!)   // ouvre le listing
    await waitFor(() => expect(document.querySelectorAll('[data-piscines-row]').length).toBe(2))
    expect((document.body.textContent ?? '').replace(/\s/g, '')).not.toContain('kWh/kWc')  // aucun potentiel solaire
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

  it('RETOURS-15 C6 — liste IDU · commune · surface ; clic ligne → fiche ; sans courrier/propriétaire/sélection', async () => {
    renderTool()
    fireEvent.click(document.querySelector('[data-solaire-mode="piscines"]')!)
    await waitFor(() => expect(document.querySelector('[data-piscines-voir]')).toBeTruthy())
    fireEvent.click(document.querySelector('[data-piscines-voir]')!)   // « Voir les piscines »
    await waitFor(() => expect(document.querySelectorAll('[data-piscines-row]').length).toBe(2))
    const body = document.body.textContent ?? ''
    // C6 — plus de propriétaire dans la liste, plus de section Courrier ni de cases de sélection.
    expect(body).not.toContain('SCI SOLEIL')
    expect(document.querySelector('[data-piscines-courrier]')).toBeNull()
    expect(document.querySelectorAll('[data-piscines-sel]').length).toBe(0)
    // IDU · commune · surface affichés ; « pas une piscine » (correction) conservé.
    expect(body).toContain('Saint-Paul')
    expect(document.querySelectorAll('[data-piscines-pas]').length).toBe(2)
    // clic sur une ligne → focusParcelle(fiche) : la fiche s'ouvre (selectedIdu posé).
    fireEvent.click(document.querySelector('[data-piscines-row]')!)
    expect(useApp.getState().selectedIdu).toBe('97411000AP0000')
  })
})
