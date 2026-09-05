// RETOURS-12 C3 — le test qui aurait attrapé « les aléas sont un camaïeu, on ne distingue pas
// l'échelle » : chaque rampe (inondation, mouvement de terrain) doit porter TROIS teintes
// franchement DISTINCTES (plus le même ton décliné en opacité), dans les deux thèmes.
import { describe, it, expect } from 'vitest'
import { MAP_THEME } from './mapTheme'

describe('C3 — rampes d\'aléas à teintes distinctes', () => {
  for (const theme of ['sombre', 'clair'] as const) {
    for (const ramp of ['aleaInondationRamp', 'aleaMvtRamp'] as const) {
      it(`${theme}/${ramp} : faible ≠ moyen ≠ fort (3 teintes distinctes)`, () => {
        const r = MAP_THEME[theme][ramp]
        expect(r.faible).not.toBe(r.moyen)
        expect(r.moyen).not.toBe(r.fort)
        expect(r.faible).not.toBe(r.fort)
        for (const v of [r.faible, r.moyen, r.fort]) expect(v).toMatch(/^#[0-9a-fA-F]{6}$/)
      })
    }
  }
  it('opacité d\'aplat désormais UNIQUE (la couleur porte le niveau, plus l\'opacité)', () => {
    expect(typeof MAP_THEME.sombre.aleaFillOpacity).toBe('number')
    expect(typeof MAP_THEME.clair.aleaFillOpacity).toBe('number')
  })
})
