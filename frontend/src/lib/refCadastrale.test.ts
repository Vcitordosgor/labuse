// RETOURS-12 T1 — le test qui aurait attrapé « BW0917 ne donne aucun résultat ».
// La grammaire de la référence cadastrale courte (section + numéro) vit dans format.ts (LOI-3) ;
// on vérifie ici la reconnaissance ET la normalisation vers la forme que /parcels/search matche
// (fin d'IDU, numéro sur 4 chiffres). Test paramétré sur les 3 formes d'écriture demandées.
import { describe, it, expect } from 'vitest'
import { estSectionNumero, normSectionNumero, estIdu } from './format'

describe('référence cadastrale courte (T1)', () => {
  it('reconnaît les 3 formes d’écriture d’une même référence', () => {
    for (const s of ['BW0917', 'BW 917', 'bw 0917', 'BW-917']) {
      expect(estSectionNumero(s)).toBe(true)
    }
  })

  it('normalise casse, espaces, tirets et zéros de tête vers la fin d’IDU', () => {
    expect(normSectionNumero('BW0917')).toBe('BW0917')
    expect(normSectionNumero('BW 917')).toBe('BW0917')
    expect(normSectionNumero('bw 0917')).toBe('BW0917')
    expect(normSectionNumero('BW-917')).toBe('BW0917')
    expect(normSectionNumero('AC 253')).toBe('AC0253')
  })

  it('ne confond pas une référence courte avec un IDU 14 (qui commence par 5 chiffres)', () => {
    expect(estSectionNumero('97415000DK1044')).toBe(false)
    expect(estIdu('BW0917')).toBe(false)
    expect(estIdu('97415000DK1044')).toBe(true)
  })

  it('rejette ce qui n’est ni IDU ni référence courte (adresse)', () => {
    expect(estSectionNumero('12 rue du Général')).toBe(false)
    expect(estSectionNumero('Saint-Denis')).toBe(false)
  })
})
