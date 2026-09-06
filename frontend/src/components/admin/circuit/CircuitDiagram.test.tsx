// CIRCUIT-P (lot 3.3) — le nombre de tuyaux = familles + catégories + 2 ; un survol allume les
// bonnes catégories (fixture de deux réservoirs).
import { describe, expect, it } from 'vitest'

import { cheminsAllumes, construireMaps, koTank, koTap, nbConduits } from './diagram'
import type { CircuitData } from './types'

// deux réservoirs, deux robinets, deux familles, deux catégories.
const data = {
  reservoirs: [
    { id: 1, nom: 'Cadastre', etat: ['mint', 'à jour'], slug: 'cadastre', taps: ['fiche_parcelle'] },
    { id: 2, nom: 'DVF', etat: ['ambre', 'jamais vérifié'], slug: 'dvf', taps: ['fiche_parcelle', 'outil_marche'] },
  ],
  robinets: [
    { id: 'fiche_parcelle', nom: 'Fiche parcelle', categorie: 'fiche', chiffres: ['a'], etat: ['mint', 'cohérent'] },
    { id: 'outil_marche', nom: 'Marché', categorie: 'outil', chiffres: ['b'], etat: ['ambre', '1 hors moteur'] },
  ],
  familles: [{ nom: 'Parcelles et propriété', ids: [1] }, { nom: 'Marché, logement, permis', ids: [2] }],
  categories: [{ slug: 'fiche', nom: 'Fiches', ids: ['fiche_parcelle'] }, { slug: 'outil', nom: 'Outils', ids: ['outil_marche'] }],
  chiffres: {}, fuites: [],
} as unknown as CircuitData

describe('CircuitDiagram — logique', () => {
  it('tuyaux = familles + catégories + 2', () => {
    expect(nbConduits(data.familles.length, data.categories.length)).toBe(2 + 2 + 2)
    expect(nbConduits(9, 12)).toBe(23)
  })

  it('survol d\'un réservoir allume sa famille + les catégories qu\'il alimente', () => {
    const maps = construireMaps(data)
    const lit = cheminsAllumes({ type: 'reservoir', id: 2 }, maps)
    expect([...lit.familles]).toEqual(['Marché, logement, permis'])
    expect(new Set(lit.categories)).toEqual(new Set(['fiche', 'outil']))  // DVF alimente 2 robinets
  })

  it('survol d\'un robinet allume sa catégorie + les familles amont', () => {
    const maps = construireMaps(data)
    const lit = cheminsAllumes({ type: 'robinet', id: 'fiche_parcelle' }, maps)
    expect([...lit.categories]).toEqual(['fiche'])
    expect(new Set(lit.familles)).toEqual(new Set(['Parcelles et propriété', 'Marché, logement, permis']))
  })

  it('ko : ambre/rouge « à regarder », mint/gris non ; « choix à confirmer » compte', () => {
    expect(koTank(['ambre', 'jamais vérifié'])).toBe(true)
    expect(koTank(['mint', 'à jour'])).toBe(false)
    expect(koTank(['gris', 'vide'])).toBe(false)
    expect(koTap(['gris', 'choix à confirmer'])).toBe(true)
    expect(koTap(['gris', 'aucun chiffre'])).toBe(false)
  })
})
