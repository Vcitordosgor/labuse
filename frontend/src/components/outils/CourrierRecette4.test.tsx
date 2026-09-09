// RECETTE-4 U5 — aucun champ vide ne s'imprime dans la lettre (3 cas + limites).
import { describe, expect, it } from 'vitest'
import { remplirGabaritCourrier } from './ModulePanel'

const TPL = 'Objet : votre parcelle {parcelle}, à {commune}\n\nMadame, Monsieur,\n\n'
  + 'Votre parcelle cadastrée {parcelle} ({surface}), située à {commune}, présente un potentiel.\n\nCordialement,'

function assertPropre(s: string) {
  expect(s).not.toMatch(/\{parcelle\}|\{commune\}|\{surface\}/)  // aucun marqueur résiduel
  expect(s).not.toMatch(/\(\s*\)/)                                // pas de « () » vide
  expect(s).not.toMatch(/à\s*,/)                                  // pas de « à , » (commune manquante)
  expect(s).not.toMatch(/ {2,}/)                                 // pas de double espace
  expect(s).not.toMatch(/,\s*,/)                                 // pas de « ,, »
}

describe('RECETTE-4 U5 — courrier sans champ vide', () => {
  it('parcelle PM sans adresse (DK 1044, Saint-Paul, 426 m²)', () => {
    const s = remplirGabaritCourrier(TPL, 'DK 1044', 'Saint-Paul', '426 m²')
    expect(s).toContain('parcelle DK 1044')
    expect(s).toContain('Saint-Paul')
    expect(s).toContain('(426 m²)')
    assertPropre(s)
  })
  it('parcelle PP avec toutes les données (AD 1237, Le Tampon)', () => {
    assertPropre(remplirGabaritCourrier(TPL, 'AD 1237', 'Le Tampon', '1 204 m²'))
  })
  it('limite : commune ET surface absentes → segments retirés, phrase propre', () => {
    const s = remplirGabaritCourrier(TPL, 'KA 0296', '', '')
    expect(s).toContain('parcelle KA 0296')
    assertPropre(s)
  })
})
