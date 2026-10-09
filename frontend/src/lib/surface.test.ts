import { describe, it, expect } from 'vitest'
import { surfaceTerrain, surfaceDessin, surfaceSource, ecartDessinPct, montrerDessin } from './surface'

// CONTENANCE-1 (Lot B) — la surface de terrain = contenance si présente, sinon dessin (repli).

describe('surfaceTerrain', () => {
  it('rend la contenance quand elle est présente (chiffre de l’acte)', () => {
    expect(surfaceTerrain({ surface_terrain_m2: 25633, surface_m2: 27156 })).toBe(25633)
    expect(surfaceSource({ surface_terrain_m2: 25633, surface_m2: 27156, surface_source: 'cadastre' })).toBe('cadastre')
  })
  it('replie sur le dessin quand la contenance manque (B4)', () => {
    expect(surfaceTerrain({ surface_m2: 664 })).toBe(664)
    expect(surfaceSource({ surface_m2: 664 })).toBe('plan')
  })
  it('déduit la contenance depuis contenance_m2 seul', () => {
    expect(surfaceTerrain({ contenance_m2: 694, surface_m2: 664 })).toBe(694)
    expect(surfaceSource({ contenance_m2: 694, surface_m2: 664 })).toBe('cadastre')
  })
  it('null quand rien n’est connu', () => {
    expect(surfaceTerrain({})).toBeNull()
    expect(surfaceTerrain(null)).toBeNull()
  })
})

describe('surfaceDessin + écart', () => {
  it('expose le dessin pour la ligne « Dessin du plan »', () => {
    expect(surfaceDessin({ surface_dessin_m2: 27156, surface_terrain_m2: 25633 })).toBe(27156)
  })
  it('calcule l’écart relatif dessin↔terrain', () => {
    expect(ecartDessinPct({ surface_terrain_m2: 25633, surface_dessin_m2: 27156 })!).toBeCloseTo(5.94, 1)
    expect(ecartDessinPct({ surface_terrain_m2: 694, surface_dessin_m2: 664 })!).toBeCloseTo(-4.32, 1)
  })
})

describe('montrerDessin (B3 : ligne masquée sous 1 %)', () => {
  it('montre le dessin quand l’écart dépasse 1 %', () => {
    expect(montrerDessin({ surface_source: 'cadastre', surface_terrain_m2: 25633, surface_dessin_m2: 27156 })).toBe(true)
  })
  it('masque quand l’écart est sous 1 %', () => {
    expect(montrerDessin({ surface_source: 'cadastre', surface_terrain_m2: 1000, surface_dessin_m2: 1005 })).toBe(false)
  })
  it('jamais de ligne « Dessin » en repli plan (pas de contenance)', () => {
    expect(montrerDessin({ surface_m2: 664 })).toBe(false)
  })
})
