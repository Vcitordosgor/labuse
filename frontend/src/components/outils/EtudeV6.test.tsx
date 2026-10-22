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
const RESULTAT = {
  moteur: {}, entrees: {}, regles: { zone: 'UA', insee: '97404', lignes: [] },
  terrain: { contenance_totale_m2: 1746 },
  hypotheses: {}, programme_saisi: null, statut_global: 'exploitable en pré-faisabilité', message: null,
  scenarios: [{ ref: 'A', forme: 'barre', resume: { logements: 40, places: 40, sdp_m2: 1360 }, programme: {}, controles: [], geojson: { type: 'FeatureCollection', features: [] } }],
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

  it('analyse : « Analyser mon projet » appelle le moteur et affiche le résultat', async () => {
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
    await waitFor(() => expect(screen.getByText(/Scénario A/)).toBeTruthy())
    expect(screen.getByText('Exploitable sous hypothèses')).toBeTruthy()
    expect(vi.mocked(postEtude)).toHaveBeenCalledWith(expect.objectContaining({
      idus: ['97404000AW0099', '97404000AW0451'],
      type_projet: 'collectif',
      programme: expect.objectContaining({ mode: 'saisi' }),
    }))
  })
})
