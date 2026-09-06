// CIRCUIT-P2 (lot 3.1) — l'interrupteur « Ne montrer que ce qui cloche » filtre bien les lignes :
// allumé (défaut) = seulement les éléments à regarder ; éteint = tous. Le titre de colonne dit le
// même nombre dans les deux positions (lu des compteurs). Fixture de trois réservoirs (2 ko, 1 ok).
import { fireEvent, render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { CircuitDiagram } from './CircuitDiagram'
import type { CircuitData } from './types'

const data = {
  run_servi: 'q_v11', candidat: null, manifeste: {}, residuel: { changees: false },
  reservoirs: [
    { id: 1, nom: 'Cadastre', etat: ['mint', 'à jour'], slug: 'c', taps: [], millesime: 'PCI', dernier_controle: null, cadence_jours: null },
    { id: 2, nom: 'DVF', etat: ['ambre', 'jamais vérifié'], slug: 'd', taps: [], millesime: null, dernier_controle: null, cadence_jours: null },
    { id: 3, nom: 'SITADEL', etat: ['rouge', 'en quarantaine'], slug: 's', taps: [], millesime: null, dernier_controle: null, cadence_jours: null },
  ],
  robinets: [],
  familles: [{ nom: 'Parcelles et propriété', ids: [1, 2, 3] }],
  categories: [],
  chiffres: {}, fuites: [],
  compteurs: { chiffres: 0, reservoirs: 3, a_jour: 1, a_regarder: 2, vides: 0, robinets: 0, robinets_a_regarder: 0, robinets_coherents: 0 },
} as unknown as CircuitData

describe('CIRCUIT-P2 lot 3.1 — l\'interrupteur filtre les lignes', () => {
  it('allumé = 2 à regarder ; éteint = les 3 ; titre identique', () => {
    const { container } = render(<CircuitDiagram data={data} groupe={null} onOpen={() => {}} />)
    // le titre de colonne lit les compteurs (indépendant de la position de l'interrupteur)
    expect(container.querySelector('.colh span')?.textContent).toBe('3, 2 à regarder')
    // allumé par défaut : seules les 2 lignes « à regarder » sont rendues
    expect(container.querySelectorAll('.node .row').length).toBe(2)
    // on éteint : les 3 lignes
    fireEvent.click(container.querySelector('.sw') as HTMLElement)
    expect(container.querySelectorAll('.node .row').length).toBe(3)
    // le titre n'a pas bougé
    expect(container.querySelector('.colh span')?.textContent).toBe('3, 2 à regarder')
    // on rallume : de nouveau 2
    fireEvent.click(container.querySelector('.sw') as HTMLElement)
    expect(container.querySelectorAll('.node .row').length).toBe(2)
  })
})
