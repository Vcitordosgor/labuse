import { describe, it, expect } from 'vitest'
import { communePastille, communeSortKey, trierCommunes, COMMUNES_ARTICLE_GARDE } from './communes'

// RETOURS-11 T6 — référentiel unique des noms de commune (décision Vic 03/09).
describe('communePastille — article sur la carte', () => {
  it('garde l\'article pour les trois communes retenues', () => {
    expect(communePastille('Le Port')).toBe('Le Port')
    expect(communePastille('Le Tampon')).toBe('Le Tampon')
    expect(communePastille('La Possession')).toBe('La Possession')
  })
  it('élide l\'article pour les 21 autres (comportement d\'aujourd\'hui)', () => {
    expect(communePastille('Les Avirons')).toBe('Avirons')
    expect(communePastille('La Plaine-des-Palmistes')).toBe('Plaine-des-Palmistes')
    expect(communePastille("L'Étang-Salé")).toBe('Étang-Salé')
    expect(communePastille('Saint-Denis')).toBe('Saint-Denis')
    expect(communePastille('Sainte-Marie')).toBe('Sainte-Marie')
  })
  it('n\'a que trois communes à article gardé', () => {
    expect(COMMUNES_ARTICLE_GARDE.size).toBe(3)
  })
})

describe('communeSortKey / trierCommunes — tri sans article', () => {
  it('range « Le Port » à P et « Le Tampon » à T', () => {
    expect(communeSortKey('Le Port')).toBe('Port')
    expect(communeSortKey('La Possession')).toBe('Possession')
    expect(communeSortKey("L'Étang-Salé")).toBe('Étang-Salé')
  })
  it('trie une liste en ignorant l\'article', () => {
    const tri = trierCommunes(['Le Tampon', 'Les Avirons', 'La Possession', 'Le Port'], (n) => n)
    // ordre attendu par clé sans article : Avirons, Port, Possession, Tampon
    expect(tri).toEqual(['Les Avirons', 'Le Port', 'La Possession', 'Le Tampon'])
  })
})
