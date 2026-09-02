import { describe, expect, it } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Catalogue } from './Sources'
import type { AdminSource } from '../../lib/api'

// SUITE-1 · S2 bis — le CATALOGUE : UNE table, une ligne par source, colonnes servi/amont/dernier
// passage/fraîcheur/alimente/actions. Chaque source apparaît UNE FOIS (plus de panneau de veille
// séparé). Filtres : toutes · nouvelle version · en erreur · rappels manuels · non surveillées.

// RETOURS-9 (Q2) — l'état unique R1 (arbitre serveur) est dérivé ici pour refléter le backend :
// nouvelle_version > jamais_verifiee (surveillée jamais sondée) > a_jour ; rappel en retard = a_rafraichir ;
// sinon non_surveillee. Les tests peuvent toujours forcer `etat` explicitement.
const deriveEtat = (v: AdminSource['veille']): AdminSource['etat'] => {
  if (v.surveillee) {
    if (v.nouvelle_version) return 'nouvelle_version'
    if (v.statut == null || v.statut === '') return 'jamais_verifiee'
    return 'a_jour'
  }
  if (v.nature === 'rappel') return v.rappel_retard ? 'a_rafraichir' : 'a_jour'
  return 'non_surveillee'
}
const src = (over: Partial<AdminSource> & { id: number; name: string }): AdminSource => {
  const base: AdminSource = {
    category: null, millesime: '2025-S2', horizon: null, ingere_le: null, cadence: null,
    a_jour: true, relance: null, affichage_desactive: false, fournisseur: 'IGN',
    etat: 'a_jour', etat_client: 'a_jour', etat_phrase: '', publie_le: null,
    alimente: { moteurs: [], surfaces: [], cable: false },
    veille: { nature: 'non_surveillable', surveillee: false, actif: null, methode: null, statut: null, millesime_amont: null,
      nouvelle_version: false, passage_at: null, message: null, echecs: 0, echec_confirme: false,
      raison: 'Import manuel — pas d\'URL de version.', injectable: false, injection_lancee_at: null, injection_vu: null,
      mail_alerte: false,
      cadence_attendue_jours: null, convention_echeance: null, jours_depuis_maj: null, rappel_retard: false },
    ...over,
  }
  // etat non fourni explicitement → dérivé de l'état de veille final
  if (!('etat' in over)) base.etat = deriveEtat(base.veille)
  return base
}
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

  it('le filtre « Non surveillée » ne montre que les non surveillées', () => {
    const sources = [
      src({ id: 1, name: 'Surveillée X', veille: surv({}) }),
      src({ id: 2, name: 'Manuelle Y' }),
    ]
    const { getByText, queryByText } = renderCat(sources)
    fireEvent.click(getByText(/Non surveillée/))
    expect(getByText('Manuelle Y')).toBeTruthy()
    expect(queryByText('Surveillée X')).toBeNull()
  })

  // ─────────────── RETOURS-9 (Q2) — les chips par état, la somme = total, jamais vérifiée ───────────────
  it('Q2.1 — cinq chips d\'état ; leur somme fait le total (partition du catalogue)', () => {
    const sources = [
      src({ id: 1, name: 'À jour A', veille: surv({ statut: 'ok', passage_at: new Date().toISOString() }) }),
      src({ id: 2, name: 'Neuf B', relance: 'dvf', veille: surv({ statut: 'nouvelle_version', nouvelle_version: true, millesime_amont: '2026', injectable: true }) }),
      src({ id: 3, name: 'Jamais vérifiée C', veille: surv({ statut: null }) }),
      src({ id: 4, name: 'Non surveillée D' }),
      src({ id: 5, name: 'Rappel retard E', a_jour: null, veille: { ...src({ id: 5, name: 'x' }).veille, nature: 'rappel', methode: 'rappel', cadence_attendue_jours: 7, rappel_retard: true } }),
    ]
    const { getByText, container } = renderCat(sources)
    const chipN = (f: string) => {
      const btn = container.querySelector(`[data-cat-filtre="${f}"]`) as HTMLElement
      return Number(btn.querySelector('span')!.textContent)
    }
    expect(chipN('a_jour')).toBe(1)
    expect(chipN('nouvelle_version')).toBe(1)
    expect(chipN('a_rafraichir')).toBe(1)
    expect(chipN('non_surveillee')).toBe(1)
    expect(chipN('jamais_verifiee')).toBe(1)
    // partition : somme des 5 états = total (« Toutes »)
    const somme = chipN('a_jour') + chipN('nouvelle_version') + chipN('a_rafraichir') + chipN('non_surveillee') + chipN('jamais_verifiee')
    expect(somme).toBe(chipN('toutes'))
    expect(somme).toBe(5)
    // Q2.2 — la source jamais vérifiée propose « Vérifier maintenant » comme action PRINCIPALE (jamais « — »)
    const btn = container.querySelector('[data-verifier="3"]') as HTMLElement
    expect(btn?.textContent).toContain('Vérifier maintenant')
    expect(getByText(/en attente de la 1/)).toBeTruthy()
  })

  it('Q2.3 — étiquette AUTO / MANUELLE / non surveillée sous le nom', () => {
    const sources = [
      src({ id: 1, name: 'Auto A', veille: surv({ statut: 'ok', methode: 'page' }) }),
      src({ id: 2, name: 'Rappel B', veille: { ...src({ id: 2, name: 'x' }).veille, nature: 'rappel', methode: 'rappel', cadence_attendue_jours: 30 } }),
      src({ id: 3, name: 'Muette C' }),
    ]
    const { getByText } = renderCat(sources)
    expect(getByText(/auto · agent quotidien · page/)).toBeTruthy()
    expect(getByText(/manuelle · rappel 30 j/)).toBeTruthy()
    expect(getByText(/non surveillée ·/)).toBeTruthy()
  })

  it('Q2.4 — un bouton « Vérifier toutes les sources maintenant » en tête', () => {
    const { getByText } = renderCat([src({ id: 1, name: 'X', veille: surv({}) })])
    expect(getByText('Vérifier toutes les sources maintenant')).toBeTruthy()
  })

  it('Q3 — la barre de recherche a disparu', () => {
    const { container } = renderCat([src({ id: 1, name: 'X', veille: surv({}) })])
    expect(container.querySelector('[data-sources-filtre]')).toBeNull()
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
