import { describe, expect, it } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { VeillePanel } from './Sources'
import type { AdminSource } from '../../lib/api'

// SENTINELLE-2 (X3.3/X4) — le panneau « Agent de veille des sources » liste MAINTENANT toutes les
// sources : surveillées (millésime servi vs amont, actions) ET non surveillées (état explicite « non
// surveillée » + raison en infobulle, jamais un blanc). Tri par défaut (nouvelle version → sonde en
// échec → à jour → non surveillée) et filtre (tout / nouvelle version / sonde en échec / non surveillée).

const src = (over: Partial<AdminSource> & { id: number; name: string }): AdminSource => ({
  category: null, millesime: '2025-S2', horizon: null, ingere_le: null, cadence: null,
  a_jour: true, relance: null, affichage_desactive: false, fournisseur: 'IGN',
  veille: { nature: 'non_surveillable', surveillee: false, actif: null, methode: null, statut: null, millesime_amont: null,
    nouvelle_version: false, passage_at: null, message: null, echecs: 0, echec_confirme: false,
    raison: 'Import manuel — pas d\'URL de version.', injectable: false, injection_lancee_at: null, injection_vu: null,
    cadence_attendue_jours: null, convention_echeance: null, jours_depuis_maj: null, rappel_retard: false },
  ...over,
})
const surv = (o: Partial<AdminSource['veille']>): AdminSource['veille'] => ({
  nature: 'version', surveillee: true, actif: true, methode: 'page', statut: 'ok', millesime_amont: null,
  nouvelle_version: false, passage_at: null, message: null, echecs: 0, echec_confirme: false, raison: null,
  injectable: false, injection_lancee_at: null, injection_vu: null,
  cadence_attendue_jours: null, convention_echeance: null, jours_depuis_maj: null, rappel_retard: false, ...o,
})

const renderPanel = (sources: AdminSource[]) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><VeillePanel sources={sources} /></QueryClientProvider>)
}

describe('SENTINELLE-2 — panneau de veille des sources', () => {
  it('affiche surveillées ET non surveillées (état explicite + raison), jamais un blanc', () => {
    const sources = [
      src({ id: 1, name: 'DVF surveillée', veille: surv({ statut: 'nouvelle_version', millesime_amont: '2026-S1', nouvelle_version: true }) }),
      src({ id: 2, name: 'Source non surveillée' }),
    ]
    const { getByText, getAllByText } = renderPanel(sources)
    expect(getByText('DVF surveillée')).toBeTruthy()
    expect(getByText('2026-S1')).toBeTruthy()                 // millésime amont mis en avant
    expect(getByText('Source non surveillée')).toBeTruthy()   // NON masquée : état explicite
    expect(getAllByText('non surveillable').length).toBeGreaterThan(0)   // SENTINELLE-3 — nature explicite
  })

  // SENTINELLE-3 (Y4/Y5.4) — un rappel manuel : nature « rappel manuel », cadence attendue, et « non
  // rafraîchie » quand le délai est dépassé. Ce n'est PAS une sonde (pas d'action Vérifier/Suspendre).
  it('affiche un rappel manuel avec sa cadence et l\'état « non rafraîchie » en retard', () => {
    const rappel = src({ id: 1, name: 'Radar pige' })
    rappel.veille = { ...rappel.veille, nature: 'rappel', methode: 'rappel', cadence_attendue_jours: 7, jours_depuis_maj: 40, rappel_retard: true }
    const { getByText, getAllByText } = renderPanel([rappel])
    expect(getAllByText('rappel manuel').length).toBeGreaterThan(0)
    expect(getByText(/cadence attendue 7 j/)).toBeTruthy()
    expect(getByText('non rafraîchie')).toBeTruthy()
  })

  // SENTINELLE-3 (Y5.4) — une source à requête témoin est « changement détectable ».
  it('marque une sonde témoin « changement détectable »', () => {
    const t = src({ id: 1, name: 'Géorisques cavités', veille: surv({ nature: 'changement', methode: 'temoin' }) })
    const { getAllByText } = renderPanel([t])
    expect(getAllByText('changement détectable').length).toBeGreaterThan(0)
  })

  it('propose les deux actions par source surveillée', () => {
    const sources = [src({ id: 1, name: 'A', veille: surv({ methode: 'entete' }) })]
    const { getByText } = renderPanel(sources)
    expect(getByText('Vérifier maintenant')).toBeTruthy()
    expect(getByText('Suspendre la veille')).toBeTruthy()
  })

  it('trie : nouvelle version d\'abord, puis sonde en échec, puis à jour, puis non surveillée', () => {
    const sources = [
      src({ id: 1, name: 'ZZ non surveillée' }),
      src({ id: 2, name: 'BB à jour', veille: surv({}) }),
      src({ id: 3, name: 'CC échec', veille: surv({ statut: 'injoignable', echecs: 3, echec_confirme: true }) }),
      src({ id: 4, name: 'DD nouvelle', veille: surv({ statut: 'nouvelle_version', nouvelle_version: true, millesime_amont: '2030' }) }),
    ]
    const { container } = renderPanel(sources)
    const noms = Array.from(container.querySelectorAll('tbody tr td:first-child'))
      .map((t) => t.textContent?.replace(/API|PAGE|ENTETE/gi, '').trim())
    expect(noms[0]).toContain('DD nouvelle')
    expect(noms[1]).toContain('CC échec')
    expect(noms[2]).toContain('BB à jour')
    expect(noms[3]).toContain('ZZ non surveillée')
  })

  it('le filtre « non surveillée » ne montre que les non surveillées', () => {
    const sources = [
      src({ id: 1, name: 'Surveillée X', veille: surv({}) }),
      src({ id: 2, name: 'Manuelle Y' }),
    ]
    const { getByText, queryByText } = renderPanel(sources)
    fireEvent.click(getByText(/Non surveillée/))
    expect(getByText('Manuelle Y')).toBeTruthy()
    expect(queryByText('Surveillée X')).toBeNull()
  })

  // SENTINELLE-2 (X6) — « Injecter cette version » : sur nouvelle version SI une commande existe.
  it('propose « Injecter cette version » sur une nouvelle version injectable, pas sinon', () => {
    const sources = [
      src({ id: 1, name: 'DVF neuf injectable', veille: surv({ statut: 'nouvelle_version', nouvelle_version: true, millesime_amont: '2026', injectable: true }) }),
      src({ id: 2, name: 'IGN neuf non-injectable', veille: surv({ statut: 'nouvelle_version', nouvelle_version: true, millesime_amont: '2026', injectable: false }) }),
      src({ id: 3, name: 'À jour', veille: surv({ injectable: true }) }),
    ]
    const { getByText, queryAllByText } = renderPanel(sources)
    expect(getByText('Injecter cette version')).toBeTruthy()   // 1 seul bouton (source injectable + neuve)
    expect(queryAllByText('Injecter cette version').length).toBe(1)
    expect(getByText('injection manuelle')).toBeTruthy()        // neuve mais sans commande → mention honnête
  })
})
