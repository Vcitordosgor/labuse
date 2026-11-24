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
  // OUTIL-ASSEMBLAGE-FIX-1 (LOT 1) — `relie` = assiette d'un bloc (gate du chiffrage), `tenant_unique`
  // = vrais bords partout (« contiguës »). `contigu` reste l'alias strict (= tenant_unique).
  n: 3, contigu: true, relie: true, tenant_unique: true, lien_faible: false, tenant_avertissement: null,
  liens: [{ a: '97415000CT1917', b: '97415000CT2565', type: 'bord', longueur_bord_m: 24.3, vide_m: null },
          { a: '97415000CT2565', b: '97415000CT3327', type: 'bord', longueur_bord_m: 18.1, vide_m: null }],
  isolees: [], surface_totale_m2: 14111,
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
// NON reliée : le backend sert relie=false + la liste des parcelles isolées (hors du bloc d'un seul tenant).
const STUDY_KO = { ...STUDY_OK, contigu: false, relie: false, tenant_unique: false, isolees: ['97415000CT3327'], liens: [] }

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

  it('RETOURS-25 — « vs meilleure seule » retirée · charge négative (signe, PAS de rouge) · Bilan (marché de la zone)', async () => {
    renderM16(); await verifier('[data-asm-charge]')
    expect(document.querySelector('[data-asm-kpi="ratio"]')).toBeFalsy()   // tuile « vs meilleure seule » retirée
    const bloc = document.querySelector('[data-asm-charge]') as HTMLElement
    expect(bloc.getAttribute('data-neg')).toBe('1')
    // MINI-CORRECTIONS-2 (pt 21 suite) — plus de texte coloré hors charte : la charge négative n'est
    // plus en rouge (`text-st-ecartee`) ; c'est le SIGNE (− / +) qui dit le négatif.
    expect(bloc.querySelector('.text-st-ecartee')).toBeNull()
    expect(bloc.textContent).toMatch(/[−-]/)                               // le signe négatif est présent
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

  it('LOT 1 : reliée par contact ponctuel/petit vide → « pas d\'un seul tenant » + liens mesurés + caveat, bilan chiffré', async () => {
    current = {
      ...STUDY_OK, contigu: false, tenant_unique: false, lien_faible: true,
      liens: [{ a: '97415000CT1917', b: '97415000CT2565', type: 'bord', longueur_bord_m: 24.3, vide_m: null },
              { a: '97415000CT2565', b: '97415000CT3327', type: 'point', longueur_bord_m: 0, vide_m: null }],
      tenant_avertissement: 'Assiette NON d\'un seul tenant — CT2565–CT3327 : contact par un point (aucun bord commun). Le chiffrage fusionne les polygones réels sans combler ce vide.',
    }
    renderM16(); await verifier('[data-asm-charge]')
    expect(document.querySelector('[data-asm-lien-faible]')?.textContent).toContain("pas d'un seul tenant")
    const liens = document.querySelector('[data-asm-liens]')?.textContent ?? ''
    expect(liens).toContain('24') ; expect(liens).toContain('contact par un point')
    expect(document.querySelector('[data-asm-tenant-avert]')?.textContent).toContain("NON d'un seul tenant")
    // le chiffrage est présent MAIS réservé (pas bloqué comme une assiette isolée).
    expect(document.querySelector('[data-asm-charge]')).toBeTruthy()
    expect(document.querySelector('[data-asm-pas-possible]')).toBeFalsy()
  })

  it('LOT 2 : capacité par zone (table des portions) + contraintes retranchées en m²', async () => {
    current = {
      ...STUDY_OK,
      zones_detail: [
        { zone: 'U2b', fam: 'U', surface_m2: 19475, emprise_m2: 17897, recul_limites_m: 3, recul_voirie_m: 4, sdp_m2: 30673, niveaux: 5, constructible: true },
        { zone: 'U2h', fam: 'U', surface_m2: 2041, emprise_m2: 1112, recul_limites_m: 4, recul_voirie_m: 4, sdp_m2: 1501, niveaux: 3, constructible: true },
      ],
      retranchements: { hors_zone_m2: 193, ppr_rouge_m2: 458, emplacement_reserve_m2: 0, ebc_m2: 0 },
    }
    renderM16(); await verifier('[data-asm-charge]')
    const t = (document.querySelector('[data-asm-zones]')?.textContent ?? '').replace(/\s/g, '')
    expect(t).toContain('U2b'); expect(t).toContain('U2h')
    expect(t).toContain('30673'); expect(t).toContain('1501')   // SDP par zone (niveaux 5 vs 3)
    const r = (document.querySelector('[data-asm-retranche]')?.textContent ?? '').replace(/ | /g, ' ')
    expect(r).toContain('Zone rouge du PPR'); expect(r).toContain('458')
    expect(r).toContain('Hors zone constructible')
  })

  it('FIX-2 LOT 1 : l\'obligation de mixité (bande intermédiaire) est affichée + « borne haute »', async () => {
    current = {
      ...STUDY_OK,
      mixite: { servitude: true, declenchee: true, regime: 'intermediaire', quota_pct: 30,
        produits: 'logements aidés ou accession sociale (PTZ, PSLA)', article: 'Art. 2 (zones U1 à U6)',
        page: 'pp. 14-15', borne_haute: true, critere: 'programme 1 583 m² dans la bande 1 500–1 800 m²' },
    }
    renderM16(); await verifier('[data-asm-charge]')
    const t = document.querySelector('[data-asm-mixite]')?.textContent ?? ''
    expect(t).toContain('Obligation de mixité sociale')
    expect(t).toContain('Art. 2'); expect(t).toContain('pp. 14-15'); expect(t).toContain('30%')
    expect(document.querySelector('[data-asm-mixite-borne]')?.textContent).toContain('borne haute')
  })

  it('FIX-2 LOT 4 : un identifiant introuvable est nommé (plus de « N parcelles » quand il en manque)', async () => {
    current = { ...STUDY_OK, n: 3, introuvables: ['97415000ZZ9999'], n_demandes: 4 }
    renderM16(); await verifier('[data-asm-charge]')
    const t = document.querySelector('[data-asm-introuvables]')?.textContent ?? ''
    expect(t).toContain('introuvable'); expect(t).toContain('ZZ9999')
    expect(t).toContain('4 parcelles demandées'); expect(t).toContain('3 trouvées')
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
