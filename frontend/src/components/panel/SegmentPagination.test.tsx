// RECETTE-11 C1 — la règle de pagination (200) s'applique AUX SEGMENTS de l'Analyse LABUSE : une
// liste de MOINS de 200 éléments montre tout et n'offre JAMAIS de « charger plus » ; au-delà de 200,
// « Voir 200 de plus ». Ce test ÉCHOUE si un petit segment propose de charger plus.
import { describe, it, expect } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'
import { SegmentList, segmentOffreChargerPlus } from './ResultsSection'

afterEach(cleanup)

function parcels(n: number) {
  return Array.from({ length: n }, (_, i) => ({
    idu: `9741100000A${String(i).padStart(4, '0')}`,
    adresse: null, surface_m2: 500, status: 'chaude', tier_v2: 'chaude',
    etage0: false, mult_v2: 1, rang_v2: i + 1, permis_pro: true, etat_bien: 'bati',
  })) as never[]
}

describe('C1 — pagination des segments', () => {
  it('la règle : « charger plus » seulement fenêtre épuisée + serveur a plus', () => {
    // < 200 entièrement chargé → jamais
    expect(segmentOffreChargerPlus(5, 5, 5, true)).toBe(false)
    expect(segmentOffreChargerPlus(5, 5, 5, false)).toBe(false)
    // fenêtre PAS épuisée (on montre 200 sur 250 en local) → pas de bouton serveur
    expect(segmentOffreChargerPlus(200, 250, 250, true)).toBe(false)
    // île : fenêtre client épuisée ET serveur a d'autres lignes → oui
    expect(segmentOffreChargerPlus(5, 5, 27, true)).toBe(true)
  })

  it('un segment de moins de 200 (chargé entièrement) n’offre AUCUN « charger plus »', () => {
    render(<SegmentList segKey="permis_pro" rows={parcels(5)} serverTotal={5} commune="Saint-Denis"
      serverHasMore={false} serverLoading={false} onServerMore={() => {}} />)
    // 5 cartes visibles, aucun bouton de pagination ni de chargement
    expect(screen.queryByTestId?.('pagination-more') ?? document.querySelector('[data-pagination-more]')).toBeNull()
    expect(document.querySelector('[data-segment-more]')).toBeNull()
  })

  it('un segment de plus de 200 propose « Voir 200 de plus »', () => {
    render(<SegmentList segKey="permis_pro" rows={parcels(250)} serverTotal={250} commune="Saint-Denis"
      serverHasMore={false} serverLoading={false} onServerMore={() => {}} />)
    expect(document.querySelector('[data-pagination-more]')).not.toBeNull()
  })
})
