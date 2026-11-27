import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// ETUDE-AUDIT-FIX-1 — FILET front : défaut 7 (type « Collectif » absent de l'étape 2) et défaut 9
// (en lotissement, « Analyser mon projet » reste désactivé tant qu'aucun logement n'est saisi).
// Rouges tant que EtudeV6.tsx n'offre pas le collectif / exige un programme en lotissement.

const PARC = (idu: string, ref: string) => ({
  idu, commune: 'Saint-Leu', section: ref.split(' ')[0], numero: ref.split(' ')[1], reference: ref,
  contenance_cadastrale_m2: 5000, surface_reelle_m2: 5000, ecart_m2: 0,
  zone_plu: 'UD', zone_famille: 'U', qualite_geometrique: 'régulière', polsby_popper: 0.77,
  largeur_inscriptible_m: 40, disparue_le: null,
  regles_plu: [{ nom: "Hauteur à l'égout", valeur: 10, unite: 'm', article: 'UD 2.5', page_pdf: 30 }],
})
const OUT = {
  parcelles: [PARC('97413000AC0261', 'AC 261'), PARC('97413000AC0264', 'AC 264')],
  union: { surface_reelle_m2: 10000, perimetre_m: 400, aire_cadastrale_m2: 10000, ecart_m2: 0, nb_parcelles: 2 },
  contiguite: { ok: true, composantes: [['97413000AC0261', '97413000AC0264']], aretes: [], tolerance_m: 0.5, message: null },
  signaux: { communes_differentes: null, zones_differentes: null, ravine_traversante: null, proprietaires_presumes: null, proprietaires_statut: 'non vérifié' },
  sources: { cadastre: { source: 'Cadastre', millesime: 'PCI', derniere_synchro: '2026-10-11' }, plu: { source: 'PLU', millesime: null, derniere_synchro: null } },
}
const STATIO = { commune: 'Saint-Leu', insee: '97413', zone: 'UD', type_projet: 'collectif',
  regimes: { general: { mode: 'par_logement', validee: true, ratio_par_logement: 1, article: 'UD 12', page_pdf: 40, millesime: '2026', citation: '1 place', applique: true, etat: 'règle vérifiée' } } }
const JAUGE = { estimable: true, commune: 'Saint-Leu', zone: 'UD', zone_implantation_m2: 8000, niveaux: 3,
  niveaux_label: 'R+2', coef_plancher: 0.8, m2_par_place_aerien: 18.0,
  places_par_type: { T1: 1, T2: 1, T3: 1.5, T4: 1.5 }, hauteur_egout_m: 10, ces_pct: 50, manquant: [], etiquette: 'estimé', note: '…' }

vi.mock('../../lib/api', () => ({
  postEtudeParcelles: vi.fn(),
  postEtude: vi.fn(),
  postEtudeStationnement: vi.fn(),
  postEtudeJauge: vi.fn(),
  getEtudeRevisionParConfig: vi.fn(),
}))
import { postEtudeParcelles, postEtudeStationnement, postEtudeJauge } from '../../lib/api'
import { EtudeV6 } from './EtudeV6'

const qc = () => new QueryClient({ defaultOptions: { queries: { retry: false } } })
const renderV6 = (idus: string[]) => render(<QueryClientProvider client={qc()}><EtudeV6 initialIdus={idus} /></QueryClientProvider>)

afterEach(() => vi.clearAllMocks())
beforeEach(() => {
  vi.mocked(postEtudeParcelles).mockResolvedValue(OUT as any)
  vi.mocked(postEtudeStationnement).mockResolvedValue(STATIO as any)
  vi.mocked(postEtudeJauge).mockResolvedValue(JAUGE as any)
})

describe('ETUDE-AUDIT-FIX-1 — filet front', () => {
  it('défaut 7 : le type « Collectif » est proposé à l\'étape 2', async () => {
    renderV6(['97413000AC0261', '97413000AC0264'])
    await waitFor(() => screen.getByText('AC 261'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByText('Quel type de projet ?'))
    expect(document.body.textContent).toMatch(/Collectif/)
  })

  it('défaut 9 : en lotissement, « Analyser mon projet » reste actif avec T1–T4 à zéro', async () => {
    renderV6(['97413000AC0261', '97413000AC0264'])
    await waitFor(() => screen.getByText('AC 261'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByText('Quel type de projet ?'))
    fireEvent.click(screen.getByText('Lotissement'))
    fireEvent.click(screen.getByRole('button', { name: /Continuer/ }))
    await waitFor(() => screen.getByRole('button', { name: /Analyser mon projet/ }))
    const btn = screen.getByRole('button', { name: /Analyser mon projet/ }) as HTMLButtonElement
    expect(btn.disabled).toBe(false)
  })
})
