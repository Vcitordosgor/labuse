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
  // CHASSE-FIX-1 (B-2) — SDP-UNIQUE : `sdp_combinee_m2`/`sdp_bati_conserve_m2` = SDP bâti conservé
  // (défaut, comme la fiche) ; `sdp_terrain_libere_m2` = table rase (démolition supposée), dite à côté.
  n: 3, contigu: true, isolees: [], surface_totale_m2: 14111,
  sdp_combinee_m2: 11065, sdp_bati_conserve_m2: 11065, sdp_terrain_libere_m2: 12800,
  sdp_existante_totale_m2: 1735, sdp_conserve_estimation: false,
  sdp_max_seule_m2: 10726, sdp_max_seule_conserve_m2: 9000,
  gain_ratio: 1.03, gain_pct: 3, gain_pct_libere: 19, n_proprietaires: 3, n_personnes_morales: 1, n_particuliers: 2,
  tous_personnes_morales: false, proprietaires_pm: [], sans_potentiel: false, n_chiffrables: 3,
  ca: { central: 5000000 }, charge_fonciere: { central: -1879117, par_m2_terrain: -133 },
  terrain_zone_eur_m2: 479, terrain_zone_fiabilite: 'moyenne', zones_mixtes: false, note_sdp: 'Indicatif.',
  items: IDUS.map((idu, k) => ({ idu, surface_m2: [619, 250, 13242][k], sdp_m2: [217, 122, 10726][k],
    sdp_residuelle_m2: [200, 100, 9000][k], sdp_existante_m2: [17, 22, 1726][k],
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

  it('RETOURS-25 — en-tête « N contiguës » SANS « surface totale » (dédup) + 2 KPI (14 111 / 11 065)', async () => {
    renderM16(); await verifier('[data-asm-charge]')
    const entete = document.querySelector('[data-asm-contigu]')?.textContent ?? ''
    expect(entete).toContain('contiguë')
    expect(entete).not.toContain('surface totale')   // la surface vit UNE SEULE fois, dans la tuile « Surface d'assiette »
    expect(document.querySelector('[data-asm-faits]')).toBeFalsy()   // chips « d'un seul tenant » / « N interlocuteurs » retirées
    expect(document.querySelector('[data-asm-kpi="surface"]')?.textContent).toContain('111')
    expect(document.querySelector('[data-asm-kpi="sdp"]')?.textContent).toContain('065')  // 11 065
  })

  it('RETOURS-25 — « vs meilleure seule » retirée · charge négative ROUGE · Bilan (marché de la zone)', async () => {
    renderM16(); await verifier('[data-asm-charge]')
    expect(document.querySelector('[data-asm-kpi="ratio"]')).toBeFalsy()   // tuile « vs meilleure seule » retirée
    const bloc = document.querySelector('[data-asm-charge]') as HTMLElement
    expect(bloc.getAttribute('data-neg')).toBe('1')
    expect(bloc.querySelector('.text-st-ecartee')).toBeTruthy()           // charge négative en rouge
    // le marché de la zone (479 €/m²) vit DANS le Bilan (4 lignes : charge · prix de sortie · marché · chiffrables)
    expect(document.querySelector('[data-asm-bilan]')?.textContent).toContain('479')
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

  it('OUTILS-P1-1 (pt 2) : trois lectures « Existant » / « Si conservé » / « Après démolition · ±Δ » ; « · terrain libéré » retiré des lignes', async () => {
    renderM16(); await verifier('[data-asm-charge]')
    const sdpKpi = document.querySelector('[data-asm-kpi="sdp"]') as HTMLElement
    // lecture 1 — l'existant (1 735) ancre les trois lectures
    expect(document.querySelector('[data-asm-sdp-existant]')?.textContent).toContain('Existant')
    expect(document.querySelector('[data-asm-sdp-existant]')?.textContent).toContain('735')
    // lecture 2 — « Si conservé » : +11 065 m² estimés (résiduel au-dessus de l'existant)
    expect(document.querySelector('[data-asm-sdp-conserve]')?.textContent).toContain('Si conservé')
    expect(document.querySelector('[data-asm-sdp-conserve]')?.textContent).toContain('065')
    // lecture 3 — « Après démolition » : 12 800 m² estimés + écart SIGNÉ vs existant (+11 065)
    const libere = document.querySelector('[data-asm-sdp-libere]') as HTMLElement
    expect(libere).toBeTruthy()
    expect(libere.textContent).toContain('Après démolition')
    expect(libere.textContent).toContain('800')          // 12 800
    expect(document.querySelector('[data-asm-sdp-ecart]')?.textContent).toContain('par rapport à l\'existant')
    expect(sdpKpi.textContent).not.toContain('Bâti conservé')   // plus de « Reconstruction » SOUS « Bâti conservé »
    // RETOURS-28 : le « (terrain libéré …) » répété par parcelle a disparu
    expect(document.body.textContent).not.toContain('(terrain libéré')
  })

  it('OUTILS-LOT-4 (pt 7) : « fiabilité » écrit en entier dans le Bilan (plus de « fiab. »)', async () => {
    renderM16(); await verifier('[data-asm-charge]')
    const bilan = document.querySelector('[data-asm-bilan]')?.textContent ?? ''
    expect(bilan).toContain('fiabilité moyenne')
    expect(bilan).not.toContain('fiab.')
  })

  it('OUTILS-LOT-4 (pt 6) : note « * SDP bâti conservé estimée » seulement quand un astérisque est posé (conservé > 0)', async () => {
    current = { ...STUDY_OK, sdp_conserve_estimation: true, sdp_bati_conserve_m2: 11065 }
    renderM16(); await verifier('[data-asm-charge]')
    expect(document.querySelector('[data-asm-sdp-conserve]')?.textContent).toContain('*')
    expect(document.querySelector('[data-asm-sdp-estimation]')).toBeTruthy()
  })

  it('OUTILS-LOT-4 (pt 6) : « aucun ajout estimé » (conservé = 0) → ni astérisque ni note orpheline', async () => {
    current = { ...STUDY_OK, sdp_conserve_estimation: true, sdp_bati_conserve_m2: 0 }
    renderM16(); await verifier('[data-asm-charge]')
    expect(document.querySelector('[data-asm-sdp-conserve]')?.textContent).toContain('aucun ajout estimé')
    expect(document.querySelector('[data-asm-sdp-conserve]')?.textContent).not.toContain('*')
    expect(document.querySelector('[data-asm-sdp-estimation]')).toBeFalsy()
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
