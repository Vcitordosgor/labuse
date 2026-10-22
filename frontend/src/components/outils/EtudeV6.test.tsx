import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// ETUDE-V6 (Lot A) — le parcours en 3 étapes. On mocke les deux appels API (validation d'assiette +
// analyse) et on VÉRIFIE le parcours : faits par parcelle, contiguïté qui refuse, aucune présélection
// de type, totaux du programme (10×T1 = 300 m² dont 60 varangues / 240 intérieur), et les surfaces qui
// NE sont JAMAIS appelées SDP. Aucun calcul réglementaire côté front : ces totaux sont des hypothèses.

const PARC = (idu: string, ref: string, zone: string, conten: number, reelle: number, qualite = 'régulière') => ({
  idu, commune: "L'Étang-Salé", section: ref.split(' ')[0], numero: ref.split(' ')[1], reference: ref,
  contenance_cadastrale_m2: conten, surface_reelle_m2: reelle, ecart_m2: Math.round((reelle - conten) * 10) / 10,
  zone_plu: zone, zone_famille: 'U', qualite_geometrique: qualite, polsby_popper: qualite === 'irrégulière' ? 0.26 : 0.77,
  largeur_inscriptible_m: 20, disparue_le: null,
})
const OUT = (ok: boolean) => ({
  parcelles: [PARC('97404000AW0099', 'AW 99', 'UA', 501, 504.3), PARC('97404000AW0451', 'AW 451', 'UA', 586, 582.7, 'irrégulière')],
  union: { surface_reelle_m2: ok ? 1086.9 : 1086.9, perimetre_m: 140, aire_cadastrale_m2: 1087, ecart_m2: -0.1, nb_parcelles: 2 },
  contiguite: { ok, composantes: ok ? [['97404000AW0099', '97404000AW0451']] : [['97404000AW0099'], ['97404000AW0451']], aretes: [], tolerance_m: 0.5, message: ok ? null : 'Ces parcelles ne partagent pas de limite commune. Choisissez des parcelles contiguës ou lancez deux études.' },
  signaux: { communes_differentes: null, zones_differentes: null, ravine_traversante: null, proprietaires_presumes: null, proprietaires_statut: 'non vérifié' },
  sources: { cadastre: { source: 'Cadastre (API Carto PCI)', millesime: 'PCI', derniere_synchro: '2026-10-11' }, plu: { source: 'Urbanisme PLU/GPU (API Carto)', millesime: null, derniere_synchro: null } },
})
const GRAND = (v: number | null, statut: string) => ({ valeur_m2: v, statut, detail: '' })
const VARIANTE = (role: string, label: string, logts: number, verdict: string) => ({
  ref: role, role, role_label: label, forme: 'barre', niveaux: 4, niveaux_label: 'R+3',
  statut_etude: 'exploitable en pré-faisabilité', verdict,
  resume: { logements: logts, places: logts, sdp_m2: logts * 60 },
  limite_capacite: 'la hauteur réglementaire',
  controles_compte: { reussi: 5, echoue: 0, non_effectue: 1, non_applicable: 5, a_confirmer: 0 },
  programme: { par_type: { T2: logts }, shab_par_type_m2: {}, shab_estimee_m2: logts * 45, ratio_shab_sdp: 0.6, mixite_applicable: false, logements_aides_imposes: 0, sdp_aidee_imposee_m2: 0 },
  distribution_niveaux: [], stationnement: { places: logts, places_imposees: logts, details_places: {}, m2_par_place: 18, surface_stationnement_m2: 400, note: null, acces: null },
  surfaces_mesurees_m2: {}, emprise_sol_m2: 500, pleine_terre_m2: 600,
  grandeurs: { sol_restant: GRAND(800, 'mesuré'), emprise_mobilisable: GRAND(870, 'dérivé'), sdp_autorisee: GRAND(4888, 'dérivé'), programme_envisageable: GRAND(logts * 60, 'mesuré') },
  ecart: { demande_total: 12, variante_total: logts, reserve_logements: logts - 12, par_type_demande: { T2: 12 }, par_type_variante: { T2: logts }, prouve: true },
  controles: [{ nom: 'Emprise au sol', regle: '≤ 1 222 m²', mesure: '500 m²', resultat: 'Réussi', citation: 'PLU UA p.22', detail: null }],
  checks_geometriques: [], geojson: { type: 'FeatureCollection', features: [] },
})
const RESULTAT = {
  moteur: {}, entrees: {}, regles: { zone: 'UA', insee: '97404', lignes: [] },
  terrain: { contenance_totale_m2: 1746 },
  hypotheses: {}, programme_saisi: null, statut_global: 'exploitable en pré-faisabilité',
  verdict: 'Exploitable sous hypothèses', message: null, depassement: null,
  scenarios: [], variantes: [VARIANTE('votre_programme', 'Votre programme', 20, 'Exploitable sous hypothèses'),
                             VARIANTE('optimisation', 'Optimisation', 28, 'Exploitable sous hypothèses'),
                             VARIANTE('alternative', 'Alternative', 27, 'Exploitable sous hypothèses')],
}
// variante ABSENTE : seul le rôle + une raison (mandat §C : l'onglet reste, il dit pourquoi).
const RESULTAT_ALT_ABSENTE = {
  ...RESULTAT,
  variantes: [VARIANTE('votre_programme', 'Votre programme', 12, 'À compléter'),
              VARIANTE('optimisation', 'Optimisation', 12, 'À compléter'),
              { ref: 'alternative', role: 'alternative', role_label: 'Alternative', absente: true,
                raison: 'Aucune autre forme ne fait mieux que l\'optimisation sur ce terrain.' }],
}

vi.mock('../../lib/api', () => ({
  postEtudeParcelles: vi.fn(),
  postEtude: vi.fn(),
}))
import { postEtudeParcelles, postEtude } from '../../lib/api'
import { EtudeV6 } from './EtudeV6'

const qc = () => new QueryClient({ defaultOptions: { queries: { retry: false } } })
const renderV6 = (idus: string[]) => render(<QueryClientProvider client={qc()}><EtudeV6 initialIdus={idus} /></QueryClientProvider>)

afterEach(() => vi.clearAllMocks())

describe('ETUDE-V6 Lot A — parcours 3 étapes', () => {
  it('étape 1 : affiche les faits par parcelle + l\'assiette contiguë, Continuer actif', async () => {
    vi.mocked(postEtudeParcelles).mockResolvedValue(OUT(true) as any)
    renderV6(['97404000AW0099', '97404000AW0451'])
    await waitFor(() => expect(screen.getByText('AW 99')).toBeTruthy())
    expect(screen.getAllByText(/Contenance/).length).toBeGreaterThan(0)
    expect(screen.getByText('géométrie irrégulière')).toBeTruthy()  // AW451 PP 0,26
    expect(document.body.textContent).toContain('Contiguës, assiette fusionnée')
    const cont = screen.getByRole('button', { name: /Continuer/ })
    expect((cont as HTMLButtonElement).disabled).toBe(false)
  })

  it('refuse une sélection non contiguë et bloque Continuer', async () => {
    vi.mocked(postEtudeParcelles).mockResolvedValue(OUT(false) as any)
    renderV6(['97404000AW0099', '97404000AW0451'])
    await waitFor(() => expect(document.body.textContent).toContain('ne partagent pas de limite commune'))
    expect((screen.getByRole('button', { name: /Continuer/ }) as HTMLButtonElement).disabled).toBe(true)
  })

  it('étape 2 : aucun type présélectionné (récap « À choisir »)', async () => {
    vi.mocked(postEtudeParcelles).mockResolvedValue(OUT(true) as any)
    renderV6(['97404000AW0099', '97404000AW0451'])
    await waitFor(() => screen.getByText('AW 99'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => expect(screen.getByText('Quel type de projet ?')).toBeTruthy())
    expect(document.body.textContent).toContain('À choisir')  // récap : projet non choisi
    expect(screen.getByText('Résidence étudiante')).toBeTruthy()
    expect(screen.getByText('Lotissement')).toBeTruthy()
  })

  it('étape 3 : 10 × T1 = 300 m² dont 60 varangues / 240 intérieur, jamais appelé SDP', async () => {
    vi.mocked(postEtudeParcelles).mockResolvedValue(OUT(true) as any)
    renderV6(['97404000AW0099', '97404000AW0451'])
    await waitFor(() => screen.getByText('AW 99'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByText('Quel type de projet ?'))
    fireEvent.click(screen.getByText('Résidence senior'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByText('Combien de logements souhaitez-vous ?'))
    fireEvent.change(document.querySelector('[data-etude-count="T1"]') as HTMLInputElement, { target: { value: '10' } })
    await waitFor(() => expect(document.body.textContent).toContain('10 logements au programme'))
    expect(document.body.textContent).toContain('60,0 m² de varangues')
    expect(document.body.textContent).toContain("240,0 m² d'intérieur indicatif")
    expect(document.body.textContent).toContain('300,0 m²')
    // la surface du programme n'est JAMAIS labellisée « SDP »
    expect(document.body.textContent).not.toContain('SDP du programme')
  })

  it('analyse : le résultat qui explique — verdict, 3 variantes, 4 grandeurs, récit', async () => {
    vi.mocked(postEtudeParcelles).mockResolvedValue(OUT(true) as any)
    vi.mocked(postEtude).mockResolvedValue(RESULTAT as any)
    renderV6(['97404000AW0099', '97404000AW0451'])
    await waitFor(() => screen.getByText('AW 99'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByText('Quel type de projet ?'))
    fireEvent.click(screen.getByText('Logement social'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByText('Combien de logements souhaitez-vous ?'))
    fireEvent.change(document.querySelector('[data-etude-count="T2"]') as HTMLInputElement, { target: { value: '12' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyser mon projet/ }))
    // verdict global + les 3 variantes + le récit
    await waitFor(() => expect(screen.getByText('Verdict de l\'étude')).toBeTruthy())
    expect(screen.getAllByText('Exploitable sous hypothèses').length).toBeGreaterThan(0)
    expect(document.querySelector('[data-variante="votre_programme"]')).toBeTruthy()
    expect(document.querySelector('[data-variante="optimisation"]')).toBeTruthy()
    expect(document.querySelector('[data-variante="alternative"]')).toBeTruthy()
    // les 4 grandeurs nommées séparément + le récit (demande → accueil → écart → limite)
    expect(screen.getByText('Sol restant')).toBeTruthy()
    expect(screen.getByText('SDP autorisée')).toBeTruthy()
    expect(document.querySelector('[data-recit="Votre demande"]')).toBeTruthy()
    expect(document.querySelector('[data-recit="Ce que le terrain accueille"]')).toBeTruthy()
    expect(document.querySelector('[data-recit="Ce qui limite"]')).toBeTruthy()
    expect(vi.mocked(postEtude)).toHaveBeenCalledWith(expect.objectContaining({
      idus: ['97404000AW0099', '97404000AW0451'], type_projet: 'collectif',
      programme: expect.objectContaining({ mode: 'saisi' }),
    }))
  })

  it('variantes : cliquer « Optimisation » change le plan masse actif', async () => {
    vi.mocked(postEtudeParcelles).mockResolvedValue(OUT(true) as any)
    vi.mocked(postEtude).mockResolvedValue(RESULTAT as any)
    renderV6(['97404000AW0099', '97404000AW0451'])
    await waitFor(() => screen.getByText('AW 99'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByText('Quel type de projet ?'))
    fireEvent.click(screen.getByText('Résidence étudiante'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByText('Combien de logements souhaitez-vous ?'))
    fireEvent.change(document.querySelector('[data-etude-count="T2"]') as HTMLInputElement, { target: { value: '12' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyser mon projet/ }))
    await waitFor(() => expect(document.querySelector('[data-variante="optimisation"]')).toBeTruthy())
    // par défaut « votre programme » (20 logts) ; après clic « Optimisation » → 28 logts dans le récit
    expect(document.querySelector('[data-recit="Ce que le terrain accueille"]')!.textContent).toContain('20 logements')
    fireEvent.click(document.querySelector('[data-variante="optimisation"]') as HTMLElement)
    expect(document.querySelector('[data-recit="Ce que le terrain accueille"]')!.textContent).toContain('28 logements')
  })

  it('variante absente : l\'onglet reste et dit pourquoi (mandat §C)', async () => {
    vi.mocked(postEtudeParcelles).mockResolvedValue(OUT(true) as any)
    vi.mocked(postEtude).mockResolvedValue(RESULTAT_ALT_ABSENTE as any)
    renderV6(['97404000AW0099', '97404000AW0451'])
    await waitFor(() => screen.getByText('AW 99'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByText('Quel type de projet ?'))
    fireEvent.click(screen.getByText('Résidence senior'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByText('Combien de logements souhaitez-vous ?'))
    fireEvent.change(document.querySelector('[data-etude-count="T2"]') as HTMLInputElement, { target: { value: '12' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyser mon projet/ }))
    // l'onglet Alternative existe toujours
    await waitFor(() => expect(document.querySelector('[data-variante="alternative"]')).toBeTruthy())
    fireEvent.click(document.querySelector('[data-variante="alternative"]') as HTMLElement)
    // et il affiche la raison de l'absence (pas un panneau vide)
    const panneau = document.querySelector('[data-variante-absente="alternative"]')
    expect(panneau).toBeTruthy()
    expect(panneau!.textContent).toContain('Aucune autre forme ne fait mieux')
  })
})
