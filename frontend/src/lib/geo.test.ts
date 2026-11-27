import { describe, expect, it } from 'vitest'
import { fmtArea, fmtDistance, pathLength, polygonArea, type LngLat } from './geo'

// Saint-Denis. Valeurs de référence obtenues avec pyproj.Geod(ellps="WGS84").
const trace: LngLat[] = [[55.451, -20.896], [55.451, -20.886], [55.458, -20.886]]

describe('mesures de carte', () => {
  it('cumule les segments sans fermer la ligne', () => {
    expect(pathLength(trace)).toBeCloseTo(1835.50013, 4)
    expect(fmtDistance(pathLength(trace))).toBe('1,84 km')
  })

  it('ferme le polygone et conserve son aire dans les deux sens', () => {
    for (const sommets of [trace, [...trace].reverse(), [...trace, trace[0]]]) {
      expect(polygonArea(sommets)).toBeCloseTo(403195.26085, 4)
      expect(fmtArea(polygonArea(sommets))).toBe('40,32 ha')
    }
  })

  it('renvoie zéro pour les tracés trop courts', () => {
    expect(pathLength(trace.slice(0, 1))).toBe(0)
    expect(polygonArea(trace.slice(0, 2))).toBe(0)
  })
})
