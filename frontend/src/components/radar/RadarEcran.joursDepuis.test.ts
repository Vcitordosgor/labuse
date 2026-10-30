// RECETTE-4 — verrou du compteur de jours du Radar. Une date de publication ABSENTE était lue comme
// 1970 (époque) → « en vente depuis 20 756 j ». Règle : aucune date valable → null (aucune durée) ;
// jamais un calcul depuis zéro.
import { describe, expect, it } from 'vitest'
import { joursDepuis } from './RadarEcran'

describe('joursDepuis — Radar (RECETTE-4)', () => {
  it('date absente → null (jamais 1970)', () => {
    expect(joursDepuis(null)).toBeNull()
    expect(joursDepuis(undefined)).toBeNull()
    expect(joursDepuis('')).toBeNull()
  })

  it('sentinelle 1970 / époque → null (pas 20 756 j)', () => {
    expect(joursDepuis('1970-01-01')).toBeNull()
    expect(joursDepuis('1970-01-01T00:00:00')).toBeNull()
    expect(joursDepuis('2004-12-31')).toBeNull()   // avant le plancher 2005
  })

  it('date illisible → null', () => {
    expect(joursDepuis('pas-une-date')).toBeNull()
  })

  it('date plausible récente → un nombre ≥ 0', () => {
    const hier = new Date(Date.now() - 86_400_000).toISOString().slice(0, 10)
    const j = joursDepuis(hier)
    expect(j).not.toBeNull()
    expect(j as number).toBeGreaterThanOrEqual(0)
    expect(j as number).toBeLessThan(3)
  })
})
