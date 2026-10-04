import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useApp } from '../../store/useApp'
import { M16 } from './moteurs'

// RECETTE-1 (H5) — refonte en étapes. Étape 1 « Choisir les parcelles » (EntreeParcelle + liste, 8 max,
// « Vérifier l'assemblage »). Étape 2 : CONTIGU → en-tête + bilan (2 KPI, ×1,03, charge négative rouge) ;
// NON contigu → « pas d'assemblage possible » + parcelles isolées, RIEN D'AUTRE. Plus de bouton Courrier,
// plus de section « parcelles voisines ».
const IDUS = ['97415000CT1917', '97415000CT2565', '97415000CT3327']
const STUDY_OK = {
  n: 3, contigu: true, isolees: [], surface_totale_m2: 14111, sdp_combinee_m2: 11065, sdp_max_seule_m2: 10726,
  gain_ratio: 1.03, gain_pct: 3, logements_combine: [78, 89], n_proprietaires: 3, n_personnes_morales: 1, n_particuliers: 2,
  tous_personnes_morales: false, proprietaires_pm: [], sans_potentiel: false, n_chiffrables: 3,
  ca: { central: 5000000 }, charge_fonciere: { central: -1879117, par_m2_terrain: -133 },
  terrain_zone_eur_m2: 479, terrain_zone_fiabilite: 'moyenne', zones_mixtes: false, note_sdp: 'Indicatif.',
  items: IDUS.map((idu, k) => ({ idu, surface_m2: [619, 250, 13242][k], sdp_m2: [217, 122, 10726][k],
    tier_v2: 'neutre', etage0: false, proprio: { type: k === 0 ? 'personne_morale' : 'particulier', denomination: 'SEDRE', siren: '1' } })),
}
// NON contigu : le backend sert contigu=false + la liste des parcelles isolées (hors du bloc d'un seul tenant).
const STUDY_KO = { ...STUDY_OK, contigu: false, isolees: ['97415000CT3327'] }

let current: Record<string, any> = STUDY_OK
function mockFetch() {
  global.fetch = vi.fn(async (url: string) => {
    if (String(url).includes('/moteurs/assemblage')) return { ok: true, json: async () => current }
    return { ok: true, json: async () => ({}) }
  }) as unknown as typeof fetch
}
function renderM16() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><M16 /></QueryClientProvider>)
}
async function verifier(attendu: string) {
  const [btn] = [...document.querySelectorAll('button')].filter((b) => /Vérifier l'assemblage/.test(b.textContent ?? ''))
  fireEvent.click(btn!)
  await waitFor(() => expect(document.querySelector(attendu)).toBeTruthy())
}

describe('ASSEMBLAGE (H5) — étapes, contiguïté, isolées, plus de Courrier', () => {
  beforeEach(() => { current = STUDY_OK; mockFetch(); useApp.setState({ msel: IDUS, parcelPrefill: null, module: 'assemblage' }) })
  afterEach(() => { vi.restoreAllMocks(); useApp.setState({ msel: [], module: null }) })

  it('contigu : en-tête « N contiguës · surface totale » + 2 KPI distincts (14 111 / 11 065)', async () => {
    renderM16(); await verifier('[data-asm-charge]')
    expect(document.querySelector('[data-asm-contigu]')?.textContent).toContain('111')   // surface totale 14 111
    expect(document.querySelector('[data-asm-kpi="surface"]')?.textContent).toContain('111')
    expect(document.querySelector('[data-asm-kpi="sdp"]')?.textContent).toContain('065')  // 11 065
  })

  it('contigu : ×gain à 2 décimales ×1,03 (+3 %) + charge négative ROUGE + réf marché', async () => {
    renderM16(); await verifier('[data-asm-charge]')
    const kpi = document.querySelector('[data-asm-kpi="ratio"]')?.textContent ?? ''
    expect(kpi).toContain('1,03'); expect(kpi).toContain('3')
    const bloc = document.querySelector('[data-asm-charge]') as HTMLElement
    expect(bloc.getAttribute('data-neg')).toBe('1')
    expect(bloc.textContent).toContain('ne dégage rien pour le terrain')
    expect(bloc.textContent).toContain('479')
  })

  it('NON contigu : « pas d\'assemblage possible » + parcelles isolées, PAS de bilan', async () => {
    current = STUDY_KO
    renderM16(); await verifier('[data-asm-pas-possible]')
    expect(document.querySelector('[data-asm-pas-possible]')?.textContent).toContain('ne se touchent pas')
    const isolees = [...document.querySelectorAll('[data-asm-isolee]')].map((e) => e.textContent)
    expect(isolees.join('|')).toContain('CT3327')
    // « rien d'autre » : aucun bilan (KPI/charge) quand l'assiette n'est pas d'un seul tenant.
    expect(document.querySelector('[data-asm-kpi="surface"]')).toBeFalsy()
    expect(document.querySelector('[data-asm-charge]')).toBeFalsy()
  })

  it('plus de bouton « Préparer les courriers » dans l\'Assemblage (H5)', async () => {
    renderM16(); await verifier('[data-asm-charge]')
    expect(document.querySelector('[data-asm-courrier]')).toBeFalsy()
  })

  it('8 parcelles maximum : au-delà, la liste est plafonnée et le message s\'affiche', async () => {
    useApp.setState({ msel: Array.from({ length: 9 }, (_, k) => `97415000CT00${10 + k}`) })
    renderM16()
    await waitFor(() => expect(document.querySelector('[data-asm-max]')).toBeTruthy())
    expect(useApp.getState().msel.length).toBe(8)
  })
})
