import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useApp } from '../../store/useApp'
import { M22 } from './M22Programme'

// IMPLANTATION-2 (LOT B) — l'écran « Étude de faisabilité » : config → scénarios, servi par UN appel
// POST /modules/etude. VERROU « aucun calcul dans le front » : l'écran n'affiche QUE les valeurs du
// payload (ici mockées) et filtre le GeoJSON par couche cochée ; aucun chiffre n'est recalculé côté UI.

const FEAT = (kind: string) => ({
  type: 'Feature', properties: { kind },
  geometry: { type: 'Polygon', coordinates: [[[55.3, -21.2], [55.3001, -21.2], [55.3001, -21.2001], [55.3, -21.2]]] },
})
const SCN = (ref: string, forme: string, niveaux: number, statut: string, logements: number, places: number, sdp: number) => ({
  ref, forme, niveaux, niveaux_label: `R+${niveaux - 1}`, statut_etude: statut,
  resume: { logements, places, sdp_m2: sdp },
  controles_compte: { reussi: 6, echoue: 0, non_effectue: 1, non_applicable: 4 },
  programme: { par_type: { T2: logements - 4, T3: 4 }, shab_par_type_m2: {}, shab_estimee_m2: 1100,
               ratio_shab_sdp: 0.61, mixite_applicable: true, logements_aides_imposes: 6, sdp_aidee_imposee_m2: 360 },
  distribution_niveaux: [{ niveau: 0, par_type: { T2: 4 }, sdp_m2: 450 }],
  stationnement: { places, places_imposees: places, details_places: {}, m2_par_place: 18,
                   surface_stationnement_m2: 600, note: { allee_unique: true, deux_cotes: true, raison: 'deux côtés' }, acces: null },
  surfaces_mesurees_m2: {}, emprise_sol_m2: 500, pleine_terre_m2: 590,
  controles: [
    { nom: 'Emprise au sol', regle: '≤ 1 222 m²', mesure: '505 m²', resultat: 'Réussi', citation: 'PLU UA · p.22', detail: null },
    { nom: 'Distance entre constructions', regle: 'non modélisée', mesure: '—', resultat: 'Non effectué', citation: null, detail: null },
  ],
  checks_geometriques: [],
  geojson: { type: 'FeatureCollection', features: [FEAT('assiette'), FEAT('batiment_emprise'), FEAT('place'), FEAT('module')] },
})
const PAYLOAD = (scenarios: any[], extra: Partial<Record<string, any>> = {}) => ({
  moteur: { livrable: 'IMPLANTATION-2', version_conventions: 'implantation-conventions-1', etiquette: 'Estimé', crs_dessin: 'EPSG:2975', crs_carte: 'EPSG:4326' },
  entrees: { idus: ['97404000AW0099'], commune: "L'Étang-Salé", insee: '97404', zone: 'UA', type_projet: 'collectif', objectif: 'equilibre', programme_mode: 'propose', stationnement: 'aerien', terrain: 'libere' },
  regles: { zone: 'UA', insee: '97404', lignes: [] },
  terrain: { contenance_totale_m2: 1746, aire_dessin_m2: 1744, zone_implantation_m2: 1155, has_voie: true, note_limites: null, contraintes: {}, ppr_rouge_m2: 0, ppr_bleue_m2: 0, pente_lidar: null, parcelles: [] },
  hypotheses: { profondeur_m: 13, coef_plancher_habitable: 0.8, surfaces: { T2: 50, T3: 65, T4: 80 }, largeur_coursive_m: 1.4, hauteur_etage_m: 3, place_m: [2.5, 5], allee_largeur_m: 5, etiquette: 'Estimé' },
  programme_saisi: null, statut_global: scenarios[0]?.statut_etude ?? 'simulation impossible', message: null, scenarios,
  ...extra,
})

function mockFetch(payload: any) {
  global.fetch = vi.fn(async (url: string) => {
    const u = String(url)
    if (u.includes('/modules/etude')) return { ok: true, json: async () => payload }
    if (u.includes('/moteurs/config')) return { ok: true, json: async () => ({ assemblage_max_ecran: 8 }) }
    return { ok: true, json: async () => ({}) }
  }) as unknown as typeof fetch
}
const qc = () => new QueryClient({ defaultOptions: { queries: { retry: false } } })
const renderOutil = () => render(<QueryClientProvider client={qc()}><M22 /></QueryClientProvider>)

describe('IMPLANTATION-2 — écran Étude de faisabilité', () => {
  beforeEach(() => { useApp.setState({ msel: ['97404000AW0099'], parcelPrefill: null, module: 'programme' }) })
  afterEach(() => { vi.restoreAllMocks(); useApp.setState({ msel: [] }) })

  it('état 1 : l\'assiette + le bouton Générer ; génère puis affiche les cartes de scénario', async () => {
    mockFetch(PAYLOAD([SCN('A', 'barre', 4, 'exploitable en pré-faisabilité', 28, 34, 1800),
                       SCN('B', 'deux_barres', 4, 'à compléter', 24, 30, 1600)]))
    renderOutil()
    const gen = await waitFor(() => { const b = document.querySelector('[data-etude-generer]'); if (!b) throw new Error('no btn'); return b as HTMLElement })
    fireEvent.click(gen)
    const cartes = await waitFor(() => { const c = document.querySelectorAll('[data-etude-carte]'); if (c.length < 2) throw new Error('cards'); return c })
    expect(cartes.length).toBe(2)
    // AUCUN CALCUL FRONT : les chiffres affichés = ceux du payload, tels quels.
    expect(cartes[0].textContent).toContain('28 logements')
    expect(cartes[0].textContent).toContain('34 places')
    expect(screen.getByText('Exploitable')).toBeTruthy()
    expect(screen.getByText('À compléter')).toBeTruthy()
  })

  it('3 chiffres clés = valeurs du payload ; bascule d\'onglet A→B sans recalcul', async () => {
    mockFetch(PAYLOAD([SCN('A', 'barre', 4, 'exploitable en pré-faisabilité', 28, 34, 1800),
                       SCN('B', 'deux_barres', 3, 'à compléter', 24, 30, 1600)]))
    renderOutil()
    fireEvent.click(await waitFor(() => document.querySelector('[data-etude-generer]') as HTMLElement))
    await waitFor(() => { if (!document.querySelectorAll('[data-etude-carte]').length) throw new Error('x') })
    // onglet A actif par défaut : SDP 1 800
    await waitFor(() => expect(document.body.textContent).toContain('1 800'))
    // bascule sur B (2e carte) → 1 600, pris du payload (pas recalculé)
    fireEvent.click(document.querySelectorAll('[data-etude-carte]')[1] as HTMLElement)
    await waitFor(() => expect(document.body.textContent).toContain('1 600'))
  })

  it('couche décochée ne change AUCUN chiffre (filtre d\'affichage, pas un calcul)', async () => {
    mockFetch(PAYLOAD([SCN('A', 'barre', 4, 'exploitable en pré-faisabilité', 28, 34, 1800)]))
    renderOutil()
    fireEvent.click(await waitFor(() => document.querySelector('[data-etude-generer]') as HTMLElement))
    await waitFor(() => { if (!document.querySelectorAll('[data-etude-carte]').length) throw new Error('x') })
    const avant = document.querySelector('[data-etude-carte]')!.textContent
    const bati = await waitFor(() => { const c = [...document.querySelectorAll('input[type="checkbox"]')]; if (!c.length) throw new Error('no cb'); return c[0] as HTMLInputElement })
    fireEvent.click(bati)   // décoche « Bâtiments »
    expect(document.querySelector('[data-etude-carte]')!.textContent).toBe(avant)
  })

  it('aucun scénario → message « ne tient pas » servi, zéro carte', async () => {
    mockFetch(PAYLOAD([], { statut_global: 'ne tient pas', message: 'ne tient pas : T4 : 300 demandés, 20 au mieux. Ce qui plafonne la capacité : la largeur de la zone.' }))
    renderOutil()
    fireEvent.click(await waitFor(() => document.querySelector('[data-etude-generer]') as HTMLElement))
    await waitFor(() => expect(document.body.textContent).toContain('ne tient pas'))
    expect(document.querySelectorAll('[data-etude-carte]').length).toBe(0)
  })

  it('Nouvelle étude réinitialise l\'assiette et revient à la configuration', async () => {
    mockFetch(PAYLOAD([SCN('A', 'barre', 4, 'exploitable en pré-faisabilité', 28, 34, 1800)]))
    renderOutil()
    fireEvent.click(await waitFor(() => document.querySelector('[data-etude-generer]') as HTMLElement))
    await waitFor(() => { if (!document.querySelectorAll('[data-etude-carte]').length) throw new Error('x') })
    fireEvent.click(document.querySelector('[data-reinitialiser]') as HTMLElement)
    await waitFor(() => expect(document.querySelectorAll('[data-etude-carte]').length).toBe(0))
    expect(useApp.getState().msel.length).toBe(0)
  })
})
