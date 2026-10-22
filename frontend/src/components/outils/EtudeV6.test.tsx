import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
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
  regles_plu: [
    { nom: "Hauteur à l'égout", valeur: 12, unite: 'm', article: 'UA 2.5.2', page_pdf: 19 },
    { nom: 'Emprise au sol (CES)', valeur: 70, unite: '%', article: 'UA 2.4', page_pdf: 18 },
    { nom: 'Pleine terre', valeur: 30, unite: '%', article: 'UA 2.6', page_pdf: 21 },
  ],
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

const STATIO = {
  commune: "L'Étang-Salé", insee: '97404', zone: 'UA', type_projet: 'senior',
  regimes: {
    general: { mode: 'par_logement', validee: true, ratio_par_logement: 1, article: 'Ua.12', page_pdf: 46,
      millesime: '2026-08-05', citation: '1 place par logement', applique: true, etat: 'règle vérifiée' },
    plafond_national: { categorie: 'résidence pour personnes âgées (L151-34, 3°)', reference: 'L151-35',
      ratio_plafond: 0.5, condition_tcsp_sous_800m: true, distance_tcsp_m: 120, eligibilite_categorie: 'À confirmer',
      statut: 'À confirmer', applicable_si_eligible: true, citation: 'L151-35 …', note: 'Le nom ne prouve pas…' },
  },
}
const RESULTAT_LOTISSEMENT = {
  moteur: {}, entrees: { commune: 'Saint-Leu', insee: '97413', zone: 'UD', type_projet: 'lotissement' },
  regles: {}, terrain: {}, hypotheses: {}, statut_global: 'à compléter', verdict: 'À compléter', message: null,
  type_projet: 'lotissement', logements_hypothese: { demande: { T3: 14 } },
  lotissement: {
    commune: 'Saint-Leu', insee: '97413', zone: 'UD', assiette_m2: 9578, contenance_m2: 9979,
    net_constructible_m2: 9578, lot_cible_m2: 450,
    tableau_lots: { nombre: 14, surface_moyenne_m2: 435, surface_min_m2: 357, surface_max_m2: 450,
      surfaces_m2: Array.from({ length: 14 }, (_, i) => 400 + i), acces: 'sur voirie de desserte créée' },
    voirie_m2: 700, voirie_largeur_m: 5, voirie_config: 'voirie en impasse + aire de retournement',
    voirie_largeur_source: 'Largeur hypothèse : aucune règle de voirie au PLU Ud — chaussée 5 m, trottoir à prévoir (Estimé).',
    pleine_terre: { exigee_pct: 40, exigee_m2: 3992, estimee_m2: 5261, jardins_privatifs_m2: 3503,
      communs_m2: 1758, ces_pct: 40, resultat: 'Réussi', article: 'UD 13' },
    controles: [{ nom: 'Perméabilité (pleine terre)', regle: '≥ 3 992 m² (40 % · UD 13)',
      mesure: '5 261 m² (jardins 3 503 + communs 1 758)', resultat: 'Réussi', citation: 'UD 13', detail: 'écart +1 269 m²' }],
    stationnement: { par_lot: 2, article: 'UD 12', total_lots: 28, visiteurs_estimes: 12, note: '…' },
    ebc: { m2: 0, statut: 'non trouvé dans les données LABUSE (à vérifier)' }, ppr_rouge_m2: 0,
    raccordements: [{ reseau: 'Électricité (ligne MT)', distance_m: 0, statut: 'adjacent' }],
    regime_procedural: "Permis d'aménager (lotissement de plus de 2 lots…) — à qualifier.",
    min_lot_plu: { existe: false, note: 'Zone Ud de Saint-Leu : aucune superficie/largeur minimale (loi ALUR).' },
    bilan_surfacique: { assiette_m2: 9578, lots_m2: 5839, voirie_m2: 700, communs_m2: 1758, ppr_rouge_m2: 0,
      ebc_m2: 0, hors_zone_m2: 1281, somme_m2: 9578, ecart_m2: 0, clos: true },
    geojson: { type: 'FeatureCollection', features: [] }, note: 'Pré-lotissement indicatif…',
  },
  study_id: 'EF-abc123def456',
}
// ETUDE-V6-2 (Lot 1) — résultat 10×T1 : la demande (programme_saisi) + les surfaces/varangues servies
// dans le payload. « Votre demande » DOIT lire ces surfaces payload (30/6), pas l'état de l'éditeur.
const RESULTAT_T1 = {
  ...RESULTAT,
  programme_saisi: { demande: { T1: 10 } },
  hypotheses: { surfaces: { T1: 30 }, varangues: { T1: 6 } },
  variantes: [VARIANTE('votre_programme', 'Votre programme', 10, 'Exploitable sous hypothèses'),
              VARIANTE('optimisation', 'Optimisation', 10, 'Exploitable sous hypothèses'),
              VARIANTE('alternative', 'Alternative', 10, 'Exploitable sous hypothèses')],
}
// ETUDE-V6-2 (Lot 2) — capacité maximale STABLE + facteurs limitants classés par impact (stationnement
// prouvé par contrefactuel). La demande (12 T2) est confrontée au maximum (28).
const RESULTAT_CAP = {
  ...RESULTAT,
  programme_saisi: { demande: { T2: 12 } },
  capacite_maximale: {
    logements: 28, par_type: { T2: 16, T3: 8, T4: 4 }, sdp_m2: 1680, niveaux: 4, niveaux_label: 'R+3',
    forme: 'barre', places: 34, surface_stationnement_m2: 612, repartition: 'équilibrée (conventions)',
    note: 'Maximum réglementaire du terrain, indépendant de la demande.',
  },
  confrontation: { demande_logements: 12, capacite_maximale_logements: 28, tient: true, reserve_logements: 16 },
  facteurs_limitants: [
    { facteur: 'stationnement aérien', impact_logements: 12, limitant: true, preuve: 'contrefactuel sans stationnement imposé',
      mesure: '612 m² occupés sur 1746 m² d\'assiette', detail: 'sans stationnement imposé : 40 logements au maximum (vs 28 avec) → +12 logement(s)' },
    { facteur: 'hauteur réglementaire', impact_logements: 7, limitant: true, preuve: 'estimé (un niveau de plus)',
      mesure: 'R+3 atteint (plafond 12 m)', detail: 'un niveau de plus ajouterait ≈ 7 logements, interdit par la hauteur' },
    { facteur: "largeur de la zone d'implantation après reculs", impact_logements: 0, limitant: false,
      preuve: 'motif récurrent des candidats écartés', mesure: '48 candidats écartés', detail: 'impact en logements non chiffré' },
  ],
}
// ETUDE-V6-2 (Lot 4) — jauge d'enveloppe (étape 3). zone 1155 × R+3 × 0.8, moins stationnement aérien.
const JAUGE = {
  estimable: true, commune: "L'Étang-Salé", zone: 'UA', zone_implantation_m2: 1155.3,
  niveaux: 4, niveaux_label: 'R+3', coef_plancher: 0.8, m2_par_place_aerien: 18.0,
  places_par_type: { T1: 1, T2: 1, T3: 1.5, T4: 1.5 }, hauteur_egout_m: 12, ces_pct: 70,
  manquant: [], etiquette: 'estimé', note: '…',
}
const JAUGE_NON_ESTIMABLE = { estimable: false, manquant: ['hauteur réglementaire'], etiquette: 'estimé' }
vi.mock('../../lib/api', () => ({
  postEtudeParcelles: vi.fn(),
  postEtude: vi.fn(),
  postEtudeStationnement: vi.fn(),
  postEtudeJauge: vi.fn(),
}))
import { postEtudeParcelles, postEtude, postEtudeStationnement, postEtudeJauge } from '../../lib/api'
import { EtudeV6 } from './EtudeV6'

const qc = () => new QueryClient({ defaultOptions: { queries: { retry: false } } })
const renderV6 = (idus: string[]) => render(<QueryClientProvider client={qc()}><EtudeV6 initialIdus={idus} /></QueryClientProvider>)

afterEach(() => vi.clearAllMocks())
beforeEach(() => {
  vi.mocked(postEtudeStationnement).mockResolvedValue(STATIO as any)
  vi.mocked(postEtudeJauge).mockResolvedValue(JAUGE as any)
})

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

  it('étape 2 : aucun type présélectionné (récap « — », Lot 5)', async () => {
    vi.mocked(postEtudeParcelles).mockResolvedValue(OUT(true) as any)
    renderV6(['97404000AW0099', '97404000AW0451'])
    await waitFor(() => screen.getByText('AW 99'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => expect(screen.getByText('Quel type de projet ?')).toBeTruthy())
    // ETUDE-V6-2 (Lot 5) — récap : projet non choisi → « — » (plus « À choisir »)
    const recap = [...document.querySelectorAll('aside')].find((a) => /Récapitulatif/.test(a.textContent || ''))
    expect(recap?.textContent).toContain('—')
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
      idus: ['97404000AW0099', '97404000AW0451'], type_projet: 'social',  // Lot C : le vrai type est transmis
      programme: expect.objectContaining({ mode: 'saisi' }),
    }))
  })

  it('hypothèses modifiables : éditer une surface + Recalculer rappelle le moteur avec la valeur éditée', async () => {
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
    // l'éditeur d'hypothèses est dans le résultat
    const hyp = await waitFor(() => { const h = document.querySelector('[data-hypotheses]'); if (!h) throw new Error('no hyp'); return h as HTMLElement })
    expect(hyp.textContent).toContain('Hypothèses modifiables')
    expect(hyp.textContent).toContain('Profondeur bâtiment')          // hypothèse moteur (collectif)
    // on édite la surface du T2 (1er champ « Surface m² ») puis on recalcule
    const champSurf = hyp.querySelectorAll('input[type="number"]')[0] as HTMLInputElement
    fireEvent.change(champSurf, { target: { value: '62' } })
    vi.mocked(postEtude).mockClear()
    fireEvent.click(screen.getByRole('button', { name: /Recalculer/ }))
    await waitFor(() => expect(vi.mocked(postEtude)).toHaveBeenCalledWith(expect.objectContaining({
      programme: expect.objectContaining({ lignes: expect.arrayContaining([expect.objectContaining({ type: 'T2', surface_m2: 62 })]) }),
    })))
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

  it('étape 2 (Lot C) : affiche la règle générale PLU + le plafond L151-35 « À confirmer »', async () => {
    vi.mocked(postEtudeParcelles).mockResolvedValue(OUT(true) as any)
    renderV6(['97404000AW0099', '97404000AW0451'])
    await waitFor(() => screen.getByText('AW 99'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByText('Quel type de projet ?'))
    fireEvent.click(screen.getByText('Résidence senior'))
    // le bloc stationnement apparaît sans autre action : règle générale + plafond national
    const bloc = await waitFor(() => {
      const b = document.querySelector('[data-stationnement]'); if (!b) throw new Error('no statio'); return b
    })
    expect(bloc.textContent).toContain('Règle générale du PLU')
    expect(bloc.textContent).toContain('place / logement')
    expect(bloc.textContent).toContain('L151-35')
    expect(bloc.textContent).toContain('À confirmer')
    // on ne préremplit JAMAIS « 1 place/logement » comme un acquis réduit : le plafond est marqué à confirmer
    expect(bloc.textContent).toMatch(/vérifiée|non remplie/)
  })

  it('lotissement (Lot D) : plan de division, tableau des lots, voirie, pas de superficie minimale PLU', async () => {
    vi.mocked(postEtudeParcelles).mockResolvedValue(OUT(true) as any)
    vi.mocked(postEtude).mockResolvedValue(RESULTAT_LOTISSEMENT as any)
    renderV6(['97413000AC0264'])
    await waitFor(() => screen.getByText('AW 99'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByText('Quel type de projet ?'))
    fireEvent.click(screen.getByText('Lotissement'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByText('Combien de logements souhaitez-vous ?'))
    fireEvent.change(document.querySelector('[data-etude-count="T3"]') as HTMLInputElement, { target: { value: '14' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyser mon projet/ }))
    // résultat lotissement : lots + voirie + tableau, pas des scénarios d'implantation
    await waitFor(() => expect(screen.getByText('Division foncière')).toBeTruthy())
    expect(screen.getByText('lots')).toBeTruthy()      // la carte « N lots »
    expect(screen.getAllByText('14').length).toBeGreaterThan(0)
    expect(screen.getByText(/Plan de division/)).toBeTruthy()
    expect(screen.getByText('Régime procédural')).toBeTruthy()
    expect(document.body.textContent).toContain('aucune règle au PLU Ud')  // pas de superficie minimale (ALUR)
    expect(document.body.textContent).toContain('Permis d\'aménager')
    expect(document.body.textContent).toContain('impasse + aire de retournement')  // voirie réaliste (Lot D corr.)
    expect(screen.getByText('Bilan surfacique')).toBeTruthy()                       // bilan clos (Lot E)
    expect(screen.getByText('Générer le PDF ↓')).toBeTruthy()                       // PDF depuis la même étude (Lot E)
    expect(screen.getByText('Perméabilité (pleine terre)')).toBeTruthy()           // contrôle pleine terre
    expect(screen.getAllByText('Réussi').length).toBeGreaterThan(0)                // avec Réussi/Échoué
    // les T1–T4 saisis = hypothèse, jamais le nombre de lots
    expect(document.body.textContent).toContain('Logements futurs (hypothèse)')
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

  it('Lot 1 : « Votre demande » lit les surfaces du payload (10×T1 = 300 / 60 varangues / 240 intérieur)', async () => {
    vi.mocked(postEtudeParcelles).mockResolvedValue(OUT(true) as any)
    vi.mocked(postEtude).mockResolvedValue(RESULTAT_T1 as any)
    renderV6(['97404000AW0099', '97404000AW0451'])
    await waitFor(() => screen.getByText('AW 99'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByText('Quel type de projet ?'))
    fireEvent.click(screen.getByText('Logement social'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByText('Combien de logements souhaitez-vous ?'))
    fireEvent.change(document.querySelector('[data-etude-count="T1"]') as HTMLInputElement, { target: { value: '10' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyser mon projet/ }))
    const dem = await waitFor(() => { const d = document.querySelector('[data-recit="Votre demande"]'); if (!d) throw new Error('no'); return d as HTMLElement })
    expect(dem.textContent).toContain('10 logements')
    expect(dem.textContent).toContain('300,0 m² de programme')
    expect(dem.textContent).toContain('60,0 m² de varangues')
    expect(dem.textContent).toContain("240,0 m² d'intérieur")
    expect(dem.textContent).toContain('10×T1')
  })

  it('Lot 1 : la surface éditée ne FUIT PAS — « Modifier le programme » rétablit les défauts (T1 30)', async () => {
    vi.mocked(postEtudeParcelles).mockResolvedValue(OUT(true) as any)
    vi.mocked(postEtude).mockResolvedValue(RESULTAT_T1 as any)
    renderV6(['97404000AW0099', '97404000AW0451'])
    await waitFor(() => screen.getByText('AW 99'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByText('Quel type de projet ?'))
    fireEvent.click(screen.getByText('Logement social'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByText('Combien de logements souhaitez-vous ?'))
    fireEvent.change(document.querySelector('[data-etude-count="T1"]') as HTMLInputElement, { target: { value: '10' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyser mon projet/ }))
    // dans le résultat, on bricole la surface T1 à 9 dans l'éditeur (sans recalculer)
    const hyp = await waitFor(() => { const h = document.querySelector('[data-hypotheses]'); if (!h) throw new Error('no hyp'); return h as HTMLElement })
    const champSurf = hyp.querySelectorAll('input[type="number"]')[0] as HTMLInputElement
    fireEvent.change(champSurf, { target: { value: '9' } })
    // puis « Modifier le programme » : on revient à l'étape 3, la saisie de l'éditeur est OUBLIÉE
    fireEvent.click(screen.getByRole('button', { name: /Modifier le programme/ }))
    await waitFor(() => screen.getByText('Combien de logements souhaitez-vous ?'))
    fireEvent.change(document.querySelector('[data-etude-count="T1"]') as HTMLInputElement, { target: { value: '10' } })
    await waitFor(() => expect(document.body.textContent).toContain('10 logements au programme'))
    // 10 × 30 = 300 (le 9 saisi ne FUIT pas → surtout pas 90)
    expect(document.body.textContent).toContain('300,0 m²')
    expect(document.body.textContent).not.toContain('90,0 m²')
  })

  it('Lot 2 : capacité maximale STABLE affichée + demande confrontée + facteurs classés par impact', async () => {
    vi.mocked(postEtudeParcelles).mockResolvedValue(OUT(true) as any)
    vi.mocked(postEtude).mockResolvedValue(RESULTAT_CAP as any)
    renderV6(['97404000AW0099', '97404000AW0451'])
    await waitFor(() => screen.getByText('AW 99'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByText('Quel type de projet ?'))
    fireEvent.click(screen.getByText('Logement social'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByText('Combien de logements souhaitez-vous ?'))
    fireEvent.change(document.querySelector('[data-etude-count="T2"]') as HTMLInputElement, { target: { value: '12' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyser mon projet/ }))
    // capacité maximale, stable + mention d'indépendance à la demande
    const cap = await waitFor(() => { const c = document.querySelector('[data-recit="Capacité maximale du terrain"]'); if (!c) throw new Error('no'); return c as HTMLElement })
    expect(cap.textContent).toContain('28 logements')
    expect(cap.textContent).toContain('deux demandes de même répartition donnent le même maximum')
    expect(cap.textContent).toContain('tient')                       // 12 ≤ 28
    // facteurs classés par impact, stationnement en tête, PROUVÉ par contrefactuel
    const lim = document.querySelector('[data-recit="Ce qui limite"]') as HTMLElement
    expect(lim.textContent).toContain('1. stationnement aérien')
    expect(lim.textContent).toContain('−12 logement(s)')
    expect(lim.textContent).toContain('sans stationnement imposé')
    expect(lim.textContent).toContain('2. hauteur réglementaire')
    expect(lim.textContent).toContain('impact non chiffré')          // largeur de zone, non affirmée limitante
  })

  it('Lot 3 : « Testez en sous-sol » apparaît quand l\'aérien plafonne et relance en sous-sol', async () => {
    vi.mocked(postEtudeParcelles).mockResolvedValue(OUT(true) as any)
    vi.mocked(postEtude).mockResolvedValue(RESULTAT_CAP as any)
    renderV6(['97404000AW0099', '97404000AW0451'])
    await waitFor(() => screen.getByText('AW 99'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByText('Quel type de projet ?'))
    fireEvent.click(screen.getByText('Logement social'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByText('Combien de logements souhaitez-vous ?'))
    fireEvent.change(document.querySelector('[data-etude-count="T2"]') as HTMLInputElement, { target: { value: '12' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyser mon projet/ }))
    // le stationnement aérien plafonne (facteur limitant) → le CTA sous-sol s'affiche
    const cta = await waitFor(() => { const b = document.querySelector('[data-tester-sous-sol]'); if (!b) throw new Error('no'); return b as HTMLButtonElement })
    expect(cta.textContent).toContain('Testez en sous-sol')
    vi.mocked(postEtude).mockClear()
    fireEvent.click(cta)
    // le clic relance l'étude EN SOUS-SOL (calcul à la demande, pas inline)
    await waitFor(() => expect(vi.mocked(postEtude)).toHaveBeenCalledWith(expect.objectContaining({ stationnement: 'sous_sol' })))
  })

  it('Lot 3 : le résultat sous-sol affiche les places au −1, l\'emprise enterrée et la rampe', async () => {
    const ssVar = { ...VARIANTE('votre_programme', 'Votre programme', 48, 'Exploitable sous hypothèses'),
      stationnement: { places: 48, places_imposees: 48, details_places: {}, m2_par_place: null, surface_stationnement_m2: 0,
        note: null, acces: null, mode: 'sous_sol', places_sous_sol: 48, emprise_sous_sol_m2: 1200, rampe_m2: 20 } }
    const RES_SS = { ...RESULTAT, programme_saisi: { demande: { T2: 29 } }, variantes: [ssVar,
      { ref: 'optimisation', role: 'optimisation', role_label: 'Optimisation', absente: true, raison: '—' },
      { ref: 'alternative', role: 'alternative', role_label: 'Alternative', absente: true, raison: '—' }],
      capacite_maximale: { logements: 48, par_type: { T2: 48 }, sdp_m2: 2688, niveaux: 4, niveaux_label: 'R+3', forme: 'barre',
        places: 48, surface_stationnement_m2: 0, repartition: 'votre répartition', stationnement_mode: 'sous_sol', note: '…' } }
    vi.mocked(postEtudeParcelles).mockResolvedValue(OUT(true) as any)
    vi.mocked(postEtude).mockResolvedValue(RES_SS as any)
    renderV6(['97404000AW0099', '97404000AW0451'])
    await waitFor(() => screen.getByText('AW 99'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByText('Quel type de projet ?'))
    fireEvent.click(screen.getByText('Logement social'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByText('Combien de logements souhaitez-vous ?'))
    fireEvent.change(document.querySelector('[data-etude-count="T2"]') as HTMLInputElement, { target: { value: '29' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyser mon projet/ }))
    const acc = await waitFor(() => { const a = document.querySelector('[data-recit="Ce que le terrain accueille"]'); if (!a) throw new Error('no'); return a as HTMLElement })
    expect(acc.textContent).toContain('Stationnement en sous-sol')
    expect(acc.textContent).toContain('48 places au niveau −1')
    expect(acc.textContent).toContain('1 200,0 m²')        // emprise enterrée (séparateur FR insécable)
    // en sous-sol, le CTA « Testez en sous-sol » ne s'affiche PAS (on y est déjà)
    expect(document.querySelector('[data-tester-sous-sol]')).toBeNull()
  })

  it('Lot 4 : jauge d\'enveloppe à l\'étape 3 (estimé) — OK sous l\'enveloppe, rouge au dépassement', async () => {
    vi.mocked(postEtudeParcelles).mockResolvedValue(OUT(true) as any)
    renderV6(['97404000AW0099', '97404000AW0451'])
    await waitFor(() => screen.getByText('AW 99'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByText('Quel type de projet ?'))
    fireEvent.click(screen.getByText('Logement social'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByText('Combien de logements souhaitez-vous ?'))
    // 23 T2 + 6 T3 : 1 708 m² ≤ enveloppe (≈ 1 854 m²) → OK (vert), étiqueté « estimé »
    fireEvent.change(document.querySelector('[data-etude-count="T2"]') as HTMLInputElement, { target: { value: '23' } })
    fireEvent.change(document.querySelector('[data-etude-count="T3"]') as HTMLInputElement, { target: { value: '6' } })
    const jauge = await waitFor(() => { const j = document.querySelector('[data-jauge]'); if (!j || j.getAttribute('data-jauge') === 'chargement') throw new Error('no'); return j as HTMLElement })
    expect(jauge.getAttribute('data-jauge')).toBe('ok')
    expect(jauge.textContent).toContain('estimé')
    expect(jauge.textContent).toContain('R+3')
    // dépassement : 80 T2 → le stationnement aérien mange toute la zone → rouge
    fireEvent.change(document.querySelector('[data-etude-count="T2"]') as HTMLInputElement, { target: { value: '80' } })
    fireEvent.change(document.querySelector('[data-etude-count="T3"]') as HTMLInputElement, { target: { value: '0' } })
    await waitFor(() => expect(document.querySelector('[data-jauge]')?.getAttribute('data-jauge')).toBe('depassement'))
    expect(document.querySelector('[data-jauge]')?.textContent).toContain('dépasse')
  })

  it('Lot 4 : jauge « non estimable » (grise) si une donnée manque', async () => {
    vi.mocked(postEtudeParcelles).mockResolvedValue(OUT(true) as any)
    vi.mocked(postEtudeJauge).mockResolvedValue(JAUGE_NON_ESTIMABLE as any)
    renderV6(['97404000AW0099', '97404000AW0451'])
    await waitFor(() => screen.getByText('AW 99'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByText('Quel type de projet ?'))
    fireEvent.click(screen.getByText('Logement social'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByText('Combien de logements souhaitez-vous ?'))
    fireEvent.change(document.querySelector('[data-etude-count="T2"]') as HTMLInputElement, { target: { value: '12' } })
    const jauge = await waitFor(() => { const j = document.querySelector('[data-jauge="non-estimable"]'); if (!j) throw new Error('no'); return j as HTMLElement })
    expect(jauge.textContent).toContain('non estimable')
    expect(jauge.textContent).toContain('hauteur réglementaire')
  })

  it('Lot 4 : le résultat signale une divergence estimation ↔ calcul > 20 %', async () => {
    vi.mocked(postEtudeParcelles).mockResolvedValue(OUT(true) as any)
    // jauge très optimiste (grande zone) → enveloppe ≫ capacité calculée (sdp 1680) → divergence > 20 %
    vi.mocked(postEtudeJauge).mockResolvedValue({ ...JAUGE, zone_implantation_m2: 5000 } as any)
    vi.mocked(postEtude).mockResolvedValue(RESULTAT_CAP as any)
    renderV6(['97404000AW0099', '97404000AW0451'])
    await waitFor(() => screen.getByText('AW 99'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByText('Quel type de projet ?'))
    fireEvent.click(screen.getByText('Logement social'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByText('Combien de logements souhaitez-vous ?'))
    fireEvent.change(document.querySelector('[data-etude-count="T2"]') as HTMLInputElement, { target: { value: '12' } })
    await waitFor(() => document.querySelector('[data-jauge]'))   // jauge chargée (en cache pour le résultat)
    fireEvent.click(screen.getByRole('button', { name: /Analyser mon projet/ }))
    const div = await waitFor(() => { const d = document.querySelector('[data-divergence]'); if (!d) throw new Error('no'); return d as HTMLElement })
    expect(div.textContent).toContain('divergent')
  })

  it('Lot 5 : étape 1 — règles PLU par parcelle (citées) ; champ vidé après ajout ; pas de bandeau bas de page', async () => {
    vi.mocked(postEtudeParcelles).mockResolvedValue(OUT(true) as any)
    renderV6(['97404000AW0099', '97404000AW0451'])
    await waitFor(() => screen.getByText('AW 99'))
    // règles PLU servies par parcelle, citées
    const regles = document.querySelectorAll('[data-regles-plu]')
    expect(regles.length).toBe(2)
    expect(regles[0].textContent).toContain("Hauteur à l'égout")
    expect(regles[0].textContent).toContain('UA 2.4')      // CES cité
    // le champ de recherche est vidé après ajout (remontage par clé) → value vide
    const champ = document.querySelector('[data-etude-v6-parcelle]') as HTMLInputElement | null
    if (champ) expect(champ.value).toBe('')
    // plus de bandeau descriptif au bas de page
    expect(document.body.textContent).not.toContain('Le regroupement est refusé')
    expect(document.body.textContent).not.toContain("L'analyse explique la réserve")
  })

  it('Lot 5 : récap « — » tant que rien n\'est choisi (jamais 0 ni « Non vérifié »)', async () => {
    vi.mocked(postEtudeParcelles).mockResolvedValue(OUT(true) as any)
    renderV6(['97404000AW0099', '97404000AW0451'])
    await waitFor(() => screen.getByText('AW 99'))
    const recap = [...document.querySelectorAll('aside')].find((a) => /Récapitulatif/.test(a.textContent || '')) as HTMLElement
    expect(recap).toBeTruthy()
    // projet / logements / surface / stationnement non renseignés → « — », jamais 0 ni « Non vérifié »
    expect(recap.textContent).not.toContain('Non vérifié')
    expect(recap.textContent).toContain('—')
    // la ligne « Logements demandés » ne doit pas afficher 0
    expect(recap.textContent).not.toMatch(/Logements demandés\s*0/)
  })
})
