import { describe, expect, it } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Catalogue } from './Sources'
import type { AdminSource } from '../../lib/api'

// SUITE-1 · S2 bis — le CATALOGUE : UNE table, une ligne par source, colonnes servi/amont/dernier
// passage/fraîcheur/alimente/actions. Chaque source apparaît UNE FOIS (plus de panneau de veille
// séparé). Filtres : toutes · nouvelle version · en erreur · rappels manuels · non surveillées.

const src = (over: Partial<AdminSource> & { id: number; name: string }): AdminSource => ({
  category: null, millesime: '2025-S2', horizon: null, ingere_le: null, cadence: null,
  a_jour: true, relance: null, affichage_desactive: false, fournisseur: 'IGN',
  alimente: { moteurs: [], surfaces: [], cable: false },
  veille: { nature: 'non_surveillable', surveillee: false, actif: null, methode: null, statut: null, millesime_amont: null,
    nouvelle_version: false, passage_at: null, message: null, echecs: 0, echec_confirme: false,
    raison: 'Import manuel — pas d\'URL de version.', injectable: false, injection_lancee_at: null, injection_vu: null,
    mail_alerte: false,
    cadence_attendue_jours: null, convention_echeance: null, jours_depuis_maj: null, rappel_retard: false },
  ...over,
})
const surv = (o: Partial<AdminSource['veille']>): AdminSource['veille'] => ({
  nature: 'version', surveillee: true, actif: true, methode: 'page', statut: 'ok', millesime_amont: null,
  nouvelle_version: false, passage_at: null, message: null, echecs: 0, echec_confirme: false, raison: null,
  injectable: false, injection_lancee_at: null, injection_vu: null, mail_alerte: false,
  cadence_attendue_jours: null, convention_echeance: null, jours_depuis_maj: null, rappel_retard: false, ...o,
})

const renderCat = (sources: AdminSource[]) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><Catalogue sources={sources} cadences={['mensuelle', 'annuelle']} /></QueryClientProvider>)
}

describe('SUITE-1 S2 bis — catalogue une-ligne-par-source', () => {
  it('affiche surveillées ET non surveillées, chaque source UNE fois, jamais un blanc', () => {
    const sources = [
      src({ id: 1, name: 'DVF surveillée', veille: surv({ statut: 'nouvelle_version', millesime_amont: '2026-S1', nouvelle_version: true }) }),
      src({ id: 2, name: 'Source non surveillée' }),
    ]
    const { getByText, getAllByText } = renderCat(sources)
    expect(getByText('DVF surveillée')).toBeTruthy()
    expect(getByText(/2026-S1 disponible/)).toBeTruthy()          // colonne AMONT : nouvelle version
    expect(getByText('Source non surveillée')).toBeTruthy()       // NON masquée : état explicite
    expect(getAllByText('non surveillée').length).toBeGreaterThan(0)
  })

  it('colonne ALIMENTE : chips lus de la matrice, « non câblée » sinon', () => {
    const cable = src({ id: 1, name: 'DVF', alimente: { moteurs: [{ key: 'scoring', label: 'scoring' }], surfaces: [{ key: 'fiche', label: 'Fiche' }], cable: true } })
    const { getByText } = renderCat([cable, src({ id: 2, name: 'Orpheline' })])
    expect(getByText('scoring')).toBeTruthy()
    expect(getByText('non câblée')).toBeTruthy()
  })

  it('un rappel manuel : amont « manuelle », fraîcheur « à rafraîchir » en retard', () => {
    const rappel = src({ id: 1, name: 'Radar pige', a_jour: null })
    rappel.veille = { ...rappel.veille, nature: 'rappel', methode: 'rappel', cadence_attendue_jours: 7, jours_depuis_maj: 40, rappel_retard: true }
    const { getByText } = renderCat([rappel])
    expect(getByText('manuelle')).toBeTruthy()
    expect(getByText(/40 j — à rafraîchir/)).toBeTruthy()
  })

  it('action principale : Injecter sur une nouvelle version injectable, Recharger sinon', () => {
    const sources = [
      src({ id: 1, name: 'DVF neuf injectable', relance: 'dvf', veille: surv({ statut: 'nouvelle_version', nouvelle_version: true, millesime_amont: '2026', injectable: true }) }),
      src({ id: 2, name: 'À jour rechargeable', relance: 'bodacc', veille: surv({ passage_at: new Date().toISOString() }) }),
    ]
    const { getByText } = renderCat(sources)
    expect(getByText(/Injecter 2026/)).toBeTruthy()
    expect(getByText('Recharger')).toBeTruthy()
  })

  it('le filtre « Non surveillées » ne montre que les non surveillées (hors rappels)', () => {
    const sources = [
      src({ id: 1, name: 'Surveillée X', veille: surv({}) }),
      src({ id: 2, name: 'Manuelle Y' }),
    ]
    const { getByText, queryByText } = renderCat(sources)
    fireEvent.click(getByText(/Non surveillées/))
    expect(getByText('Manuelle Y')).toBeTruthy()
    expect(queryByText('Surveillée X')).toBeNull()
  })

  it('groupe par fournisseur avec en-tête repliable', () => {
    const sources = [
      src({ id: 1, name: 'A', fournisseur: 'DGFiP', veille: surv({}) }),
      src({ id: 2, name: 'B', fournisseur: 'INSEE', veille: surv({}) }),
    ]
    const { getByText, queryByText, container } = renderCat(sources)
    // en-têtes de groupe repérés par data-groupe (le fournisseur apparaît aussi dans la sous-ligne de chaque source)
    const hDGFiP = container.querySelector('[data-groupe="DGFiP"]') as HTMLElement
    expect(hDGFiP).toBeTruthy()
    expect(container.querySelector('[data-groupe="INSEE"]')).toBeTruthy()
    fireEvent.click(hDGFiP)                 // replie le groupe DGFiP
    expect(queryByText('A')).toBeNull()
    expect(getByText('B')).toBeTruthy()     // l'autre groupe reste ouvert
  })
})
