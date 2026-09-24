import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useApp } from '../../store/useApp'
import { M22 } from './M22Programme'
import { FaisabiliteTab } from '../fiche/Fiche'

// Mandat FAISABILITE-1 (lot C) — l'outil a UN SEUL mode (par parcelle) ; « Par critères » est retiré
// (remplacé par le groupe Capacité du panneau Filtre). On vérifie : l'ouverture directe sur la saisie
// de parcelle, le sous-titre, le lien discret vers le filtre Capacité, et (blocs suivants) l'étape 12
// (SHAB vendable) + le cantonnement de l'IA dans la trace par parcelle.
const BILAN = {
  idu: '97411000BZ1065',
  capacite: {
    verdict: 'R+1 · ~2 logts', calibree: true, bandeau: 'Estimé.',
    fourchette: { niveaux: 'R+1', niveaux_max: 2, hauteur_m: 6, surface_plancher_m2: 219, shab_vendable_m2: 123, logements_au_sol: [1, 2] },
    steps: [
      { label: 'Surface habitable (rendement)', valeur: '~175 m²', source: 'SDP × 0,8', prov: 'derive' },
      { label: 'Logements retenus au sol', valeur: '~1 à 2', source: 'plafond densité', prov: 'derive' },
    ],
    // FAISABILITE-1 (lot D) — hypothèses éditables servies (le front rend un champ par entrée).
    hypotheses_modifiables: [
      { key: 'coef_occupation', label: 'Occupation du gabarit', valeur: 45, unite: '%', min: 10, max: 100 },
      { key: 'coef_rendement', label: 'Rendement SDP → habitable', valeur: 80, unite: '%', min: 50, max: 100 },
    ],
  },
  marche: null, bilan: null, fiscal: null, rtaa: null,
}

function mockFetch() {
  global.fetch = vi.fn(async (url: string) => {
    const u = String(url)
    if (u.includes('/recalcul')) return { ok: true, json: async () => ({ idu: BILAN.idu, capacite: BILAN.capacite, overrides_retenus: { coef_occupation: 60 } }) }
    if (u.includes('/modules/faisabilite/')) return { ok: true, json: async () => BILAN }
    if (u.includes('/pipeline/parcel/')) return { ok: true, json: async () => ({ in_pipeline: false, entry: null }) }
    if (u.includes('/communes')) return { ok: true, json: async () => [] }
    return { ok: true, json: async () => ({}) }
  }) as unknown as typeof fetch
}
const qc = () => new QueryClient({ defaultOptions: { queries: { retry: false } } })

describe('FAISABILITE-1 (lot C) — un seul mode : saisie de parcelle + lien vers le filtre Capacité', () => {
  beforeEach(() => { mockFetch(); useApp.setState({ parcelPrefill: null }) })
  afterEach(() => vi.restoreAllMocks())

  it('ouvre sur la saisie de parcelle, sous-titre, PAS de sélecteur de mode « Par critères »', () => {
    render(<QueryClientProvider client={qc()}><M22 /></QueryClientProvider>)
    expect(screen.getByText(/Ce que le PLU laisse construire sur cette parcelle/)).toBeTruthy()
    // le mode « Par critères » a disparu (plus de sélecteur de mode)
    expect(document.querySelector('[data-faisa-mode]')).toBeFalsy()
    expect(screen.queryByText('Par critères')).toBeFalsy()
    expect(document.querySelector('[data-prog-item]')).toBeFalsy()
  })

  it('le lien « Chercher des parcelles par capacité → » ouvre la carte sur le panneau Filtre', () => {
    render(<QueryClientProvider client={qc()}><M22 /></QueryClientProvider>)
    const lien = document.querySelector('[data-chercher-capacite]') as HTMLElement
    expect(lien).toBeTruthy()
    fireEvent.click(lien)
    const st = useApp.getState()
    expect(st.view).toBe('cartes')
    expect(st.panneauSection).toBe('filtres')
    expect(st.module).toBeNull()
  })
})

describe('FAISABILITE — étape 12 (SHAB vendable retenue)', () => {
  beforeEach(mockFetch)
  afterEach(() => vi.restoreAllMocks())

  it('la trace par parcelle gagne l\'étape « SHAB vendable retenue » (~123 m²)', async () => {
    render(<QueryClientProvider client={qc()}><FaisabiliteTab idu="97411000BZ1065" /></QueryClientProvider>)
    const ol = await waitFor(() => { const o = document.querySelector('[data-faisa-steps]'); if (!o) throw new Error('no steps'); return o as HTMLElement })
    // 2 étapes moteur + 1 étape ajoutée = 3
    expect(ol.querySelectorAll('li').length).toBe(3)
    const last = ol.querySelectorAll('li')[2]
    expect(last.textContent).toContain('SHAB vendable retenue')
    expect(last.textContent).toContain('123')
  })
})

describe('FAISABILITE-1 (lot D) — hypothèses modifiables (bloc partagé fiche + outil)', () => {
  beforeEach(mockFetch)
  afterEach(() => vi.restoreAllMocks())

  it('rend un champ par hypothèse Estimé ; éditer fait apparaître « Revenir aux hypothèses LABUSE »', async () => {
    render(<QueryClientProvider client={qc()}><FaisabiliteTab idu="97411000BZ1065" /></QueryClientProvider>)
    const bloc = await waitFor(() => { const b = document.querySelector('[data-faisa-hypotheses]'); if (!b) throw new Error('no hyp'); return b as HTMLElement })
    const inputs = bloc.querySelectorAll('input[type="number"]')
    expect(inputs.length).toBe(2)                              // occupation + rendement
    // pas de reset tant qu'aucune hypothèse n'est modifiée
    expect(document.querySelector('[data-faisa-hyp-reset]')).toBeFalsy()
    // édite l'occupation → le bouton « Revenir aux hypothèses LABUSE » apparaît (nOv > 0)
    fireEvent.change(inputs[0], { target: { value: '60' } })
    await waitFor(() => expect(document.querySelector('[data-faisa-hyp-reset]')).toBeTruthy())
    // reset → le bouton disparaît (retour aux hypothèses LABUSE)
    fireEvent.click(document.querySelector('[data-faisa-hyp-reset]') as HTMLElement)
    await waitFor(() => expect(document.querySelector('[data-faisa-hyp-reset]')).toBeFalsy())
  })
})

describe('OUTILS-FIX-3 Lot F — l\'IA est cantonnée : hors fiche (embedded), pas de bouton « Expliquer »', () => {
  beforeEach(mockFetch)
  afterEach(() => vi.restoreAllMocks())

  it('fiche (non embedded) : le bouton IA « Expliquer ce calcul » est présent', async () => {
    render(<QueryClientProvider client={qc()}><FaisabiliteTab idu="97411000BZ1065" /></QueryClientProvider>)
    await waitFor(() => { if (!document.querySelector('[data-faisa-steps]')) throw new Error('no steps') })
    expect(document.querySelector('[data-faisa-explain-btn]')).toBeTruthy()
  })

  it('outil Faisabilité (embedded) : AUCUN point d\'entrée IA', async () => {
    render(<QueryClientProvider client={qc()}><FaisabiliteTab idu="97411000BZ1065" embedded /></QueryClientProvider>)
    await waitFor(() => { if (!document.querySelector('[data-faisa-steps]')) throw new Error('no steps') })
    expect(document.querySelector('[data-faisa-explain]')).toBeFalsy()
    expect(document.querySelector('[data-faisa-explain-btn]')).toBeFalsy()
  })
})
