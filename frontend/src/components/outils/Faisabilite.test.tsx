import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useApp } from '../../store/useApp'
import { M22 } from './M22Programme'
import { FaisabiliteTab } from '../fiche/Fiche'

// FAISABILITE-3 (Vic 27/09) — LE panneau de la maquette validée, partagé fiche + outil (une
// implémentation). Le front ne calcule rien : tout vient d'UN appel (POST …/scenario). On vérifie :
// les deux cartes de scénario + la bascule, le verdict + « ce qui limite » + badges, la section PLU
// (article/page cliquable), les 3 hypothèses éditables, les 8 étapes, « tester un projet », et
// (M22) l'ouverture sur la saisie de parcelle + le lien discret vers le filtre Capacité.
const SCEN = (scenario: 'terrain_libere' | 'bati_garde', test: any = null) => ({
  idu: '97411000BZ1065',
  zone: 'Uh', commune: 'Saint-Denis', surface_m2: 1625, calibree: true, a_cheval: false,
  portion_constructible_m2: null, portion_zone: null,
  scenario, bati_present: true, bati_libelle: '193 m² bâtis · 3 niveau(x) (lidar)',
  constructible: true, cause: null, logement_autorise: true,
  verdict: scenario === 'bati_garde'
    ? 'Presque saturée : 26 m² de plancher encore possibles.'
    : "Jusqu'à 245 m² de plancher · 2–3 logement(s).",
  ce_qui_limite: 'emprise au sol 30 % · hauteur 7 m (R+1)',
  sdp_possible_m2: scenario === 'bati_garde' ? 26 : 245,
  logements: scenario === 'bati_garde' ? [0, 1] : [2, 3],
  stationnement_places: 3, surface_a_demolir_m2: scenario === 'bati_garde' ? null : 219,
  badges: { regles_sourcees: true, plancher_estime: true, plu_approuve_le: '05/08/2026' },
  bandeau: 'Pré-faisabilité sur règlement public, pas un certificat d’urbanisme.',
  plu: { zone: 'Uh', regles_valeurs: [
    { cle: 'hauteur', libelle: 'Hauteur max', valeur: '7 m au faîtage', etat: 'chiffre',
      reference: 'Art. Uh.10 · p.73', url: 'plu.pdf#page=73' },
    { cle: 'mixite', libelle: 'Mixité sociale', valeur: 'non modélisée pour cette zone',
      etat: 'non_modelisee', reference: null, url: null } ] },
  hypotheses_modifiables: [
    { key: 'coef_occupation', label: 'Occupation du gabarit', valeur: 50, unite: '%', min: 10, max: 100 },
    { key: 'coef_rendement', label: 'Rendement SDP → habitable', valeur: 80, unite: '%', min: 50, max: 100 },
    { key: 'logement_m2', label: 'Surface moyenne / logement', valeur: 72, unite: 'm²', min: 20, max: 200 },
  ],
  etapes: Array.from({ length: 8 }, (_, i) => ({
    n: i + 1, label: `Étape ${i + 1}`, valeur: `~${(i + 1) * 100} m²`, source: 'src', prov: 'derive' })),
  test,
})

function mockFetch() {
  global.fetch = vi.fn(async (url: string, opts?: any) => {
    const u = String(url)
    if (u.includes('/scenario')) {
      const body = opts?.body ? JSON.parse(opts.body) : {}
      const sc = body.scenario ?? 'terrain_libere'
      let test = null
      if (body.test) {
        const n = body.test.n_logements, s = body.test.surface_par_logement
        if (!n || !s) test = { statut: 'a_completer', message: 'indiquez…' }
        else test = (n * s) <= (sc === 'bati_garde' ? 26 : 245)
          ? { statut: 'tient', besoin_m2: n * s, possible_m2: sc === 'bati_garde' ? 26 : 245, places: n }
          : { statut: 'ne_tient_pas', besoin_m2: n * s, possible_m2: sc === 'bati_garde' ? 26 : 245, manque_m2: n * s - (sc === 'bati_garde' ? 26 : 245), places: n }
      }
      return { ok: true, json: async () => ({ idu: '97411000BZ1065', scenario: SCEN(sc, test) }) }
    }
    if (u.includes('/pipeline/parcel/')) return { ok: true, json: async () => ({ in_pipeline: false, entry: null }) }
    if (u.includes('/communes')) return { ok: true, json: async () => [] }
    return { ok: true, json: async () => ({}) }
  }) as unknown as typeof fetch
}
const qc = () => new QueryClient({ defaultOptions: { queries: { retry: false } } })
const renderTab = () => render(<QueryClientProvider client={qc()}><FaisabiliteTab idu="97411000BZ1065" /></QueryClientProvider>)

describe('FAISABILITE-3 — l\'outil ouvre sur la saisie de parcelle + lien vers le filtre Capacité', () => {
  beforeEach(() => { mockFetch(); useApp.setState({ parcelPrefill: null }) })
  afterEach(() => vi.restoreAllMocks())

  it('sous-titre présent, PAS de sélecteur de mode « Par critères »', () => {
    render(<QueryClientProvider client={qc()}><M22 /></QueryClientProvider>)
    expect(screen.getByText(/Ce que le PLU laisse construire sur cette parcelle/)).toBeTruthy()
    expect(document.querySelector('[data-faisa-mode]')).toBeFalsy()
    expect(screen.queryByText('Par critères')).toBeFalsy()
  })

  it('le lien « Chercher des parcelles par capacité → » ouvre la carte sur le panneau Filtre', () => {
    render(<QueryClientProvider client={qc()}><M22 /></QueryClientProvider>)
    const lien = document.querySelector('[data-chercher-capacite]') as HTMLElement
    fireEvent.click(lien)
    const st = useApp.getState()
    expect(st.view).toBe('cartes')
    expect(st.panneauSection).toBe('filtres')
    expect(st.module).toBeNull()
  })
})

describe('FAISABILITE-3 — le panneau (verdict, PLU, hypothèses, étapes)', () => {
  beforeEach(mockFetch)
  afterEach(() => vi.restoreAllMocks())

  it('rend le verdict, « ce qui limite » et les badges', async () => {
    renderTab()
    const v = await waitFor(() => { const e = document.querySelector('[data-faisa-verdict-phrase]'); if (!e) throw new Error('no verdict'); return e as HTMLElement })
    expect(v.textContent).toContain('245')
    expect(screen.getByText('Ce qui limite')).toBeTruthy()
    expect(screen.getByText('Règles sourcées')).toBeTruthy()
    expect(screen.getByText('Plancher estimé')).toBeTruthy()
  })

  it('la section PLU affiche une règle avec article/page cliquable + mixité « non modélisée »', async () => {
    renderTab()
    const plu = await waitFor(() => { const e = document.querySelector('[data-faisa-plu]'); if (!e) throw new Error('no plu'); return e as HTMLElement })
    const lien = plu.querySelector('a.f-ref') as HTMLAnchorElement
    expect(lien).toBeTruthy()
    expect(lien.getAttribute('href')).toContain('page=73')
    expect(plu.textContent).toContain('non modélisée')
  })

  it('rend 3 hypothèses éditables ; éditer fait apparaître « Revenir aux valeurs LABUSE »', async () => {
    renderTab()
    const bloc = await waitFor(() => { const b = document.querySelector('[data-faisa-hypotheses]'); if (!b) throw new Error('no hyp'); return b as HTMLElement })
    const inputs = bloc.querySelectorAll('input[type="number"]')
    expect(inputs.length).toBe(3)
    expect(document.querySelector('[data-faisa-hyp-reset]')).toBeFalsy()
    fireEvent.change(inputs[0], { target: { value: '60' } })
    await waitFor(() => expect(document.querySelector('[data-faisa-hyp-reset]')).toBeTruthy())
    fireEvent.click(document.querySelector('[data-faisa-hyp-reset]') as HTMLElement)
    await waitFor(() => expect(document.querySelector('[data-faisa-hyp-reset]')).toBeFalsy())
  })

  it('les 8 étapes sont repliées par défaut, dépliables', async () => {
    renderTab()
    await waitFor(() => { if (!document.querySelector('[data-faisa-steps-wrap]')) throw new Error('no wrap') })
    expect(document.querySelector('[data-faisa-steps]')).toBeFalsy()   // replié
    fireEvent.click(screen.getByText(/Le calcul, étape par étape/))
    const ol = await waitFor(() => { const o = document.querySelector('[data-faisa-steps]'); if (!o) throw new Error('no steps'); return o as HTMLElement })
    expect(ol.querySelectorAll('li').length).toBe(8)
  })

  it('bascule de scénario : cliquer « En gardant le bâti » recharge le verdict bâti gardé', async () => {
    renderTab()
    await waitFor(() => { if (!document.querySelector('[data-sc="bati_garde"]')) throw new Error('no card') })
    fireEvent.click(document.querySelector('[data-sc="bati_garde"]') as HTMLElement)
    await waitFor(() => expect(document.querySelector('[data-faisa-verdict-phrase]')!.textContent).toContain('26'))
  })

  it('tester un projet : champs remplis → « Ne tient pas » par le moteur', async () => {
    renderTab()
    const bloc = await waitFor(() => { const b = document.querySelector('[data-faisa-test]'); if (!b) throw new Error('no test'); return b as HTMLElement })
    const inputs = bloc.querySelectorAll('input[type="number"]')
    fireEvent.change(inputs[0], { target: { value: '2' } })
    fireEvent.change(inputs[1], { target: { value: '90' } })   // 180 > 245 ? non → tient ; forçons ne tient pas
    fireEvent.change(inputs[0], { target: { value: '3' } })
    fireEvent.change(inputs[1], { target: { value: '90' } })   // 270 > 245 → ne tient pas
    await waitFor(() => expect(document.querySelector('[data-faisa-test-result]')?.textContent).toContain('Ne tient pas'))
  })

  it('aucun bouton IA « Expliquer » (fiche ni outil)', async () => {
    renderTab()
    await waitFor(() => { if (!document.querySelector('[data-faisa-panneau]')) throw new Error('no panneau') })
    expect(document.querySelector('[data-faisa-explain]')).toBeFalsy()
    expect(document.querySelector('[data-faisa-explain-btn]')).toBeFalsy()
  })
})
