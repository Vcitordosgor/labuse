import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useApp } from '../../store/useApp'
import { HistoireFrise } from './HistoireFrise'

// OUTILS-MUSCLER-2 Lot C — la frise des faits : mailles VISIBLES (point jour / anneau année /
// tirets millésime), empilement sans masquage, détail au clic (source + date à sa maille), ponts
// FIX-3 (Permis / fiche-ventes / Scan patrimoine) avec fil de retour, état vide honnête (C5).

const REP = {
  idu: '97499000TE0001', n: 4, cap_filiation: 12,
  faits: [
    { famille: 'vente', date: '2023-05-12', maille: 'jour', annee: 2023, libelle: 'Vente — Maison',
      chiffres: { prix_eur: 250000, surface_bati_m2: 90, statut: 'Sourcé' }, source: 'DVF (DGFiP) — ventes actées' },
    { famille: 'proprietaire', date: null, maille: 'millesime', annee: 2023, de_millesime: 2022, a_millesime: 2023,
      libelle: 'Changement de propriétaire (personne morale)',
      avant: { siren: '111222333', denomination: 'SCI AVANT' }, apres: { siren: '444555666', denomination: 'SCI APRES' },
      chiffres: { statut: 'Sourcé' }, source: 'DGFiP — parcelles des personnes morales (millésimes annuels)' },
    { famille: 'permis', date: '2021', maille: 'annee', annee: 2021, libelle: 'Permis PC déposé',
      permit_id: 'PC974TEST1', type_permis: 'PC', chiffres: { nb_logements: 3, statut: 'Sourcé' },
      source: 'Sit@del (SDES) — autorisations d’urbanisme' },
    { famille: 'decoupe', date: '2019-03-04', maille: 'jour', annee: 2019, libelle: 'Parcelle issue d’un document d’arpentage',
      parcelles_liees: ['97499000ZZ0001'], n_parcelles_liees: 1, chiffres: { statut: 'Sourcé' },
      source: 'DFI — documents de filiation informatisés (DGFiP)' },
  ],
  sources: [
    { cle: 'dvf', nom: 'DVF (DGFiP)', maj: '2025-12-31' },
    { cle: 'sitadel', nom: 'Sit@del (SDES)', maj: '2026-07-31' },
    { cle: 'ff', nom: 'Fichiers fonciers PM (DGFiP)', maj: 'millésimes 2019→2024' },
    { cle: 'dfi', nom: 'DFI (DGFiP)', maj: '2025-12-29' },
  ],
}

const qc = () => new QueryClient({ defaultOptions: { queries: { retry: false } } })
const monter = () => render(<QueryClientProvider client={qc()}><HistoireFrise idu="97499000TE0001" /></QueryClientProvider>)

describe('HistoireFrise — les faits datés sous le comparateur', () => {
  beforeEach(() => {
    global.fetch = vi.fn(async () => ({ ok: true, json: async () => REP })) as unknown as typeof fetch
  })
  afterEach(() => { vi.restoreAllMocks(); useApp.setState({ outilRetour: [], permitToOpen: null, m02Prefill: null }) })

  it('un repère par fait, marqueur par famille, bandeau des millésimes de sources (C2/C6)', async () => {
    monter()
    await waitFor(() => expect(document.querySelectorAll('[data-histoire-fait]').length).toBe(4))
    for (const fam of ['vente', 'permis', 'proprietaire', 'decoupe'])
      expect(document.querySelector(`[data-histoire-fait="${fam}"]`)).toBeTruthy()
    // C6 : le bandeau cite les sources et leurs millésimes (forme fraîcheur de l'app)
    const bandeau = document.querySelector('[data-histoire-sources]')?.textContent ?? ''
    expect(bandeau).toContain('DVF')
    expect(bandeau).toContain('Sit@del')
    expect(bandeau).toContain('2019→2024')
  })

  it('détail au clic : date à sa MAILLE réelle (année seule ≠ 01/01), source, pont permis (C3/C4)', async () => {
    monter()
    await waitFor(() => expect(document.querySelector('[data-histoire-fait="permis"]')).toBeTruthy())
    fireEvent.click(document.querySelector('[data-histoire-fait="permis"]')!)
    const detail = document.querySelector('[data-histoire-detail]')
    expect(detail?.textContent).toContain('2021 (année seule')          // jamais « 01/01/2021 »
    expect(detail?.textContent).not.toContain('01/01/2021')
    expect(detail?.textContent).toContain('Sit@del')
    // pont C4 → Permis sur CE permis, fil de retour empilé (FIX-3)
    fireEvent.click(document.querySelector('[data-histoire-pont-permis]')!)
    const st = useApp.getState()
    expect(st.permitToOpen).toBe('PC974TEST1')
    expect(st.module).toBe('permis')
    expect(st.outilRetour.at(-1)?.module).toBe('temps')
    expect(st.outilRetour.at(-1)?.restore?.parcelPrefill).toBe('97499000TE0001')
  })

  it('changement de propriétaire : PM nommées avant→après, écart de millésimes (jamais une date)', async () => {
    monter()
    await waitFor(() => expect(document.querySelector('[data-histoire-fait="proprietaire"]')).toBeTruthy())
    fireEvent.click(document.querySelector('[data-histoire-fait="proprietaire"]')!)
    const detail = document.querySelector('[data-histoire-detail]')?.textContent ?? ''
    expect(detail).toContain('SCI AVANT')
    expect(detail).toContain('SCI APRES')
    expect(detail).toContain('entre le 1ᵉʳ janv. 2022 et le 1ᵉʳ janv. 2023')
  })

  it('C5 — état vide honnête : la frise ne bloque rien', async () => {
    global.fetch = vi.fn(async () => ({ ok: true, json: async () => ({ ...REP, n: 0, faits: [] }) })) as unknown as typeof fetch
    monter()
    await waitFor(() => expect(document.querySelector('[data-histoire-vide]')).toBeTruthy())
    expect(document.querySelector('[data-histoire-vide]')?.textContent).toContain('Aucun fait daté connu')
  })
})
