import { describe, expect, it } from 'vitest'
import { BASEMAP_SOURCES, ORTHO_YEARS, TEMPS_MILLESIMES, activeBasemapKey, basemapLabel } from './basemaps'

// FIX-FONDS — un seul jeu de millésimes pour les deux surfaces (B5), attribution exacte par fond ET
// par millésime (B2), plus de BASEMAP_CHOICES (B6).
describe('FIX-FONDS — fonds de carte', () => {
  it('B5 : ORTHO_YEARS = Actuelle + les 6 millésimes de TEMPS_MILLESIMES (source unique)', () => {
    expect(ORTHO_YEARS).toHaveLength(TEMPS_MILLESIMES.length + 1)
    expect(ORTHO_YEARS[0].an).toBe('now')
    for (const m of TEMPS_MILLESIMES) {
      const y = ORTHO_YEARS.find((o) => o.key === m.key)
      expect(y?.an).toBe(m.an)                          // même identifiant des deux côtés
      expect(BASEMAP_SOURCES[m.key]).toBeTruthy()       // un fond réel derrière chaque millésime
    }
  })

  it('B5 : activeBasemapKey rend les millésimes récents SÉLECTIONNABLES (plus de couches mortes)', () => {
    expect(activeBasemapKey('clair', 'now')).toBeNull()          // Clair = aucune tuile
    expect(activeBasemapKey('dark', 'now')).toBeNull()           // FOND-SOMBRE : Sombre = aucune tuile (CARTO retiré)
    expect(activeBasemapKey('plan', 'now')).toBe('bm-plan')
    expect(activeBasemapKey('ortho', 'now')).toBe('bm-ortho-now')
    expect(activeBasemapKey('ortho', '2016')).toBe('bm-ortho-2016')   // avant : couche morte, maintenant servie
    expect(activeBasemapKey('ortho', '1950')).toBe('bm-ortho-1950')
  })

  it('B2 : l\'attribution de chaque fond ortho porte son millésime', () => {
    expect(BASEMAP_SOURCES['bm-ortho-2000'].attribution).toContain('2000-2005')
    expect(BASEMAP_SOURCES['bm-ortho-2016'].attribution).toContain('2016-2020')
    expect(BASEMAP_SOURCES['bm-ortho-now'].attribution).toContain('IGN')
  })

  it('B6 : basemapLabel résout tous les fonds SANS BASEMAP_CHOICES', () => {
    expect(basemapLabel('bm-ortho-now')).toBe('Actuelle')
    expect(basemapLabel('bm-ortho-2011')).toBe('2011-2015')
    expect(basemapLabel('bm-plan')).toBe('Plan IGN')
  })

  // FOND-SOMBRE : plus AUCUNE source CARTO (clé requise) — le Sombre est rendu sans raster.
  it('FOND-SOMBRE : aucun fond ne pointe vers cartocdn/carto.com', () => {
    expect(BASEMAP_SOURCES['bm-carto']).toBeUndefined()
    for (const def of Object.values(BASEMAP_SOURCES)) {
      for (const url of def.tiles) expect(url).not.toMatch(/cartocdn|carto\.com/)
    }
  })
})
