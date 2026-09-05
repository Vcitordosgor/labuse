import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useApp } from '../../store/useApp'
import { M16 } from './moteurs'

// Mandat ASSEMBLAGE — surface d'assiette ≠ SDP cumulée (2 KPI), ×1,03 (+3 %), charge cumulée
// négative en ROUGE (traitement ETUDIER) + réf marché, pont Courrier unique (courrierPrefillIdus).
const IDUS = ['97415000CT1917', '97415000CT2565', '97415000CT3327']
const STUDY = {
  n: 3, contigu: false, surface_totale_m2: 14111, sdp_combinee_m2: 11065, sdp_max_seule_m2: 10726,
  // CONNEXIONS-2 Lot 9.3 (KO-15) — le backend sert désormais gain_ratio (2 déc.) ET gain_pct ; le front
  // affiche ces valeurs, il ne re-divise plus (11 065 / 10 726 = 1,03 → +3 %, calculé côté serveur).
  gain_ratio: 1.03, gain_pct: 3, logements_combine: [78, 89], n_proprietaires: 3, n_personnes_morales: 1, n_particuliers: 2,
  tous_personnes_morales: false, proprietaires_pm: [], sans_potentiel: false, n_chiffrables: 3,
  ca: { central: 5000000 }, charge_fonciere: { central: -1879117, par_m2_terrain: -133 },
  terrain_zone_eur_m2: 479, terrain_zone_fiabilite: 'moyenne', zones_mixtes: false, note_sdp: 'Indicatif.',
  items: IDUS.map((idu, k) => ({ idu, surface_m2: [619, 250, 13242][k], sdp_m2: [217, 122, 10726][k],
    tier_v2: 'neutre', etage0: false, proprio: { type: k === 0 ? 'personne_morale' : 'particulier', denomination: 'SEDRE', siren: '1' } })),
}

function mockFetch() {
  global.fetch = vi.fn(async (url: string) => {
    if (String(url).includes('/moteurs/assemblage')) return { ok: true, json: async () => STUDY }
    return { ok: true, json: async () => ({}) }
  }) as unknown as typeof fetch
}
function renderM16() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><M16 /></QueryClientProvider>)
}
async function analyser() {
  const [btn] = [...document.querySelectorAll('button')].filter((b) => /Analyser l'assiette/.test(b.textContent ?? ''))
  fireEvent.click(btn!)
  await waitFor(() => expect(document.querySelector('[data-asm-charge]')).toBeTruthy())
}

describe('ASSEMBLAGE — libellés + charge négative + pont Courrier', () => {
  beforeEach(() => { mockFetch(); useApp.setState({ msel: IDUS, parcelPrefill: null, courrierPrefillIdus: null, module: 'assemblage' }) })
  afterEach(() => { vi.restoreAllMocks(); useApp.setState({ msel: [], courrierPrefillIdus: null, module: null }) })

  it('deux KPI distincts : surface d\'assiette (14 111) ≠ SDP cumulée (11 065)', async () => {
    renderM16(); await analyser()
    expect(document.querySelector('[data-asm-kpi="surface"]')?.textContent).toContain('111')   // 14 111
    expect(document.querySelector('[data-asm-kpi="sdp"]')?.textContent).toContain('065')        // 11 065
  })

  it('×gain à 2 décimales : ×1,03 (+3 %)', async () => {
    renderM16(); await analyser()
    const kpi = document.querySelector('[data-asm-kpi="ratio"]')?.textContent ?? ''
    expect(kpi).toContain('1,03')
    expect(kpi).toContain('3')   // +3 %
  })

  it('charge cumulée négative = bloc ROUGE + phrase + réf marché', async () => {
    renderM16(); await analyser()
    const bloc = document.querySelector('[data-asm-charge]') as HTMLElement
    expect(bloc.getAttribute('data-neg')).toBe('1')
    expect(bloc.querySelector('.text-st-ecartee')).toBeTruthy()   // rouge (traitement ETUDIER)
    // RETOURS-12 T7 — résultat d'un scénario d'opération, jamais un verdict sur les parcelles.
    expect(bloc.textContent).toContain('ne dégage rien pour le terrain')
    expect(bloc.textContent).toContain('scénario')
    expect(bloc.textContent).toContain('479')                     // marché zone
  })

  it('pont Courrier : un seul bouton pré-remplit les 3 parcelles + ouvre l\'outil', async () => {
    renderM16(); await analyser()
    const btn = document.querySelector('[data-asm-courrier]') as HTMLElement
    expect(btn.textContent).toContain('(3)')
    fireEvent.click(btn)
    expect(useApp.getState().courrierPrefillIdus).toEqual(IDUS)
    expect(useApp.getState().module).toBe('courriers')
  })
})
