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
// RECETTE-1 H13.3 — la carte montre des PARCELLES COLORÉES (polygones), plus des points/gouttes.
const PARCELLES = { type: 'FeatureCollection', features: [{ type: 'Feature', geometry: { type: 'Polygon', coordinates: [[[55.3, -21], [55.31, -21], [55.31, -21.01], [55.3, -21]]] }, properties: { kind: 'piscine-parcelle', idu: '97411000AP0000', statut: 'servie' } }] }
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
    if (u.includes('/prospection-piscines/parcelles')) return { ok: true, json: async () => PARCELLES }
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

  it('écran d\'entrée : deux cartes (Piscines / Ensoleillement), sans pied de sources', () => {
    renderTool()
    expect(document.querySelector('[data-solaire-mode="piscines"]')).toBeTruthy()
    expect(document.querySelector('[data-solaire-mode="ensoleillement"]')).toBeTruthy()
    // RECETTE-3 (D13) — le pied « Détection FLAIR … PVGIS … » est retiré de l'écran d'entrée.
    expect(screen.queryByText(/PVGIS v5\.3 SARAH3/)).toBeNull()
  })

  it('H13.3 — étape 1 Périmètre : toute l\'île + les communes avec leurs comptes (pas de liste encore)', async () => {
    renderTool()
    fireEvent.click(document.querySelector('[data-solaire-mode="piscines"]')!)
    // étape 1 : choix du périmètre (toute l'île OU une commune), compte à côté ; aucune liste pour l'instant.
    await waitFor(() => expect(document.querySelector('[data-piscines-perim="ile"]')).toBeTruthy())
    expect(document.body.textContent).toContain('Toute l’île')
    expect(screen.getByText('Saint-Pierre')).toBeTruthy()            // les communes sont listées
    expect(document.querySelector('[data-piscines-row]')).toBeNull() // pas de listing à l'étape périmètre
    // RECETTE-PROD-1 (9c/9d + #9 précision Vic) — l'étape « Statut » est SUPPRIMÉE : cliquer un
    // périmètre mène DIRECTEMENT au résultat. UNE SEULE catégorie « Piscines » : un compteur, aucune
    // notion de statut (ni « confirmées » ni « à confirmer »).
    fireEvent.click(document.querySelector('[data-piscines-perim="ile"]')!)
    await waitFor(() => expect(document.querySelectorAll('[data-piscines-row]').length).toBe(2))
    expect(document.querySelector('[data-piscines-statut="servie"]')).toBeNull()   // plus d'étape statut
    expect(document.querySelector('[data-piscines-total]')?.textContent).toContain('980')  // 12 480 + 500 (total unique)
    expect(document.body.textContent).toContain('piscines à La Réunion')
    expect(document.body.textContent ?? '').not.toMatch(/confirmée|à confirmer/i)   // aucune notion de statut
    // RECETTE-PROD-1 (9b) — la phrase « la carte montre tout le périmètre » est retirée.
    expect(document.body.textContent ?? '').not.toContain('la carte montre')
  })

  // CHASSE-DONNEES-FIX-1 (E-80) — l'année codée en dur « 2025 » a été retirée du pied de source : la
  // source renvoie désormais au millésime SERVI (page Sources), source unique de vérité du millésime.
  it('H13.3 — source « IGN FLAIR et CoSIA (millésime servi en page Sources) », aucun potentiel solaire dans le chemin Piscines', async () => {
    renderTool()
    fireEvent.click(document.querySelector('[data-solaire-mode="piscines"]')!)
    await waitFor(() => expect(document.querySelector('[data-piscines-perim="ile"]')).toBeTruthy())
    expect(document.querySelector('[data-piscines-source]')?.textContent).toContain('IGN FLAIR et CoSIA (millésime servi en page Sources)')
    expect(document.body.textContent ?? '').not.toContain('précision ≥ 85 %')
    fireEvent.click(document.querySelector('[data-piscines-perim="ile"]')!)
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

  it('RECETTE-4 — les deux paragraphes sous le graphe mensuel sont RETIRÉS (plus de « Productible estimé… » ni « En clair… »)', async () => {
    // Décision Vic : les deux paragraphes d'explication sous le graphe mensuel sont supprimés. L'ancien
    // verrou « A1 » (inclinaison 15° affichée dans « En clair… ») est donc obsolète : on verrouille le RETRAIT.
    useApp.setState({ solairePrefill: '97411000AP0000' })
    renderTool()
    await screen.findByText(/Profil mensuel/)
    const fiche = document.querySelector('[data-solaire-fiche]')!
    expect(fiche.textContent).not.toContain('Productible estimé à la')
    expect(fiche.textContent).not.toContain('En clair : le potentiel')
    expect(fiche.textContent).not.toContain('inclinés à')
  })

  it('A6 — puissance installable + production servies par le back, ratio kWc/m² écrit', async () => {
    useApp.setState({ solairePrefill: '97411000AP0000' })
    renderTool()
    await screen.findByText(/Profil mensuel/)
    const fiche = document.querySelector('[data-solaire-fiche]')!
    expect(fiche.textContent).toContain('28')          // kWc servi (pas recalculé au front)
    expect(document.querySelector('[data-solaire-kwc-hyp]')?.textContent).toContain('0,2 kWc/m²')
  })

  it('D14b — liste IDU · commune (plus de colonne source ni croix « pas une piscine ») ; clic ligne → fiche', async () => {
    renderTool()
    fireEvent.click(document.querySelector('[data-solaire-mode="piscines"]')!)
    await waitFor(() => expect(document.querySelector('[data-piscines-perim="ile"]')).toBeTruthy())
    fireEvent.click(document.querySelector('[data-piscines-perim="ile"]')!)
    await waitFor(() => expect(document.querySelectorAll('[data-piscines-row]').length).toBe(2))
    const body = document.body.textContent ?? ''
    // plus de propriétaire dans la liste, plus de section Courrier ni de cases de sélection.
    expect(body).not.toContain('SCI SOLEIL')
    expect(document.querySelector('[data-piscines-courrier]')).toBeNull()
    expect(document.querySelectorAll('[data-piscines-sel]').length).toBe(0)
    // RECETTE-2 (D14b) — IDU · commune affichés ; colonne SOURCE (CoSIA/FLAIR) et croix « pas une
    // piscine » RETIRÉES de chaque ligne.
    expect(body).toContain('Saint-Paul')
    expect(document.querySelectorAll('[data-piscines-pas]').length).toBe(0)
    expect(body).not.toContain('FLAIR+CoSIA')   // la colonne source par ligne (FLAIR+CoSIA) est retirée
    // clic sur une ligne → focusParcelle(fiche) : la fiche s'ouvre (selectedIdu posé).
    fireEvent.click(document.querySelector('[data-piscines-row]')!)
    expect(useApp.getState().selectedIdu).toBe('97411000AP0000')
  })
})
