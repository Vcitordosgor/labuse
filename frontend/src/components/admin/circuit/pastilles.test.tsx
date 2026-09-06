// CIRCUIT-P3 (lot 2.4) — les pastilles d'un bloc reflètent l'état de chaque élément : un bloc
// « tout va bien » ne porte aucune pastille ambre/rouge/mauve, et un bloc « n à regarder » en porte.
import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { CircuitDiagram } from './CircuitDiagram'
import type { CircuitData } from './types'

const data = {
  run_servi: 'q_v11', candidat: null, manifeste: {}, residuel: { changees: false },
  reservoirs: [
    { id: 1, nom: 'Cadastre', etat: ['mint', 'à jour'], ko: false, slug: 'c', taps: [], millesime: null, dernier_controle: null, cadence_jours: null },
    { id: 2, nom: 'DVF', etat: ['gris', 'dépôt manuel'], ko: false, slug: 'd', taps: [], millesime: null, dernier_controle: null, cadence_jours: null },
    { id: 3, nom: 'SITADEL', etat: ['ambre', 'nouvelle version à injecter'], ko: true, slug: 's', taps: [], millesime: null, dernier_controle: null, cadence_jours: null },
    { id: 4, nom: 'Géorisques', etat: ['rouge', 'en quarantaine'], ko: true, slug: 'g', taps: [], millesime: null, dernier_controle: null, cadence_jours: null },
  ],
  robinets: [],
  familles: [
    { nom: 'Bloc sain', ids: [1, 2] },        // mint + gris → « tout va bien »
    { nom: 'Bloc à regarder', ids: [3, 4] },  // ambre + rouge → « n à regarder »
  ],
  categories: [],
  chiffres: {}, fuites: [],
  compteurs: { chiffres: 0, reservoirs: 4, a_jour: 1, a_regarder: 2, vides: 1, robinets: 0, robinets_a_regarder: 0, robinets_coherents: 0 },
} as unknown as CircuitData

describe('CIRCUIT-P3 lot 2.4 — pastilles ↔ état du bloc', () => {
  it('« tout va bien » = aucune pastille ambre/rouge/mauve ; « à regarder » en porte', () => {
    const { container } = render(<CircuitDiagram data={data} groupe={null} onOpen={() => {}} />)
    const blocs = [...container.querySelectorAll('.node[data-fam]')] as HTMLElement[]
    expect(blocs.length).toBe(2)
    for (const bloc of blocs) {
      const av = bloc.querySelector('.av')!
      const alertes = bloc.querySelectorAll('.dots i.ambre, .dots i.rouge, .dots i.mauve')
      if (av.classList.contains('ok')) {
        // bloc « tout va bien » → aucune pastille d'alerte
        expect(av.textContent).toBe('tout va bien')
        expect(alertes.length).toBe(0)
      } else {
        // bloc « n à regarder » → au moins une pastille d'alerte
        expect(av.textContent).toMatch(/à regarder/)
        expect(alertes.length).toBeGreaterThan(0)
      }
    }
  })
})
