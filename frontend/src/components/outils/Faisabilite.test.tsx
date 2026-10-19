import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
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
  // LOGEMENTS-SOURCE-UNIQUE — le panneau ne sert plus `logements`/`stationnement_places` (ancien
  // calcul de capacité) : verdict sans fourchette + renvoi vers l'Étude + mention volet D.
  verdict: scenario === 'bati_garde'
    ? 'Presque saturée : 26 m² de plancher encore possibles.'
    : "Jusqu'à 245 m² de plancher.",
  ce_qui_limite: 'emprise au sol 30 % · hauteur 7 m (R+1)',
  sdp_possible_m2: scenario === 'bati_garde' ? 26 : 245,
  capacite_mention: 'maximum réglementaire — les permis réels en utilisent ~½ en médiane (volet D)',
  logements_renvoi: "voir l'Étude de faisabilité",
  surface_a_demolir_m2: scenario === 'bati_garde' ? null : 219,
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

// IMPLANTATION-2 — l'OUTIL « Étude de faisabilité » (M22) a été refondu : il n'ouvre plus l'ancien
// panneau faisabilité mais le moteur d'implantation (cf. Etude.test.tsx). Ce fichier ne garde que
// les tests du composant partagé FaisabiliteTab (encore rendu par l'ancien chemin / tests de non-
// régression du panneau servi par /modules/faisabilite/.../scenario).
describe('FAISABILITE-3 — le panneau (verdict, PLU, hypothèses, étapes)', () => {
  beforeEach(mockFetch)
  afterEach(() => vi.restoreAllMocks())

  it('ouvre par défaut sur « bâti gardé » (résiduel servi) : verdict, « ce qui limite », badges', async () => {
    // ALGO-FIX-1 (point 3, suite) — parcelle BÂTIE : l'onglet s'ouvre sur bati_garde = le résiduel
    // servi (26 dans le mock), plus l'enveloppe démolition (245). Même chiffre que fiche/Dossier.
    renderTab()
    const v = await waitFor(() => { const e = document.querySelector('[data-faisa-verdict-phrase]'); if (!e) throw new Error('no verdict'); return e as HTMLElement })
    expect(v.textContent).toContain('26')
    expect(screen.getByText('Ce qui limite')).toBeTruthy()
    expect(screen.getByText('Règles sourcées')).toBeTruthy()
    expect(screen.getByText('Plancher estimé')).toBeTruthy()
  })

  it('la section PLU affiche une règle avec article/page cliquable + mixité « non modélisée »', async () => {
    renderTab()
    // FICHE-FIX-5 (reste 2) — « Ce que le PLU permet » est désormais dans un Repli « Règles du PLU »
    // (doublon des tuiles §Urbanisme) : on l'ouvre avant de vérifier son contenu.
    const toggle = await waitFor(() => {
      const t = [...document.querySelectorAll('[data-repli-toggle]')].find((b) => /Règles du PLU/.test(b.textContent ?? ''))
      if (!t) throw new Error('no repli')
      return t as HTMLElement
    })
    toggle.click()
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

  it('bascule de scénario : défaut « bâti gardé » (26), cliquer « Terrain libéré » → enveloppe pleine (245)', async () => {
    renderTab()
    // défaut = bâti gardé = résiduel servi (ALGO-FIX-1)
    await waitFor(() => expect(document.querySelector('[data-faisa-verdict-phrase]')!.textContent).toContain('26'))
    await waitFor(() => { if (!document.querySelector('[data-sc="terrain_libere"]')) throw new Error('no card') })
    fireEvent.click(document.querySelector('[data-sc="terrain_libere"]') as HTMLElement)
    await waitFor(() => expect(document.querySelector('[data-faisa-verdict-phrase]')!.textContent).toContain('245'))
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
