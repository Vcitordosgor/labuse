// FICHE-FIX-4 (Lot B) — le format partagé des 11 sections de la fiche : décimales à la virgule,
// dates JJ/MM/AAAA, année SIRENE 1900 = « n.c. ». Verrou.
import { describe, expect, it } from 'vitest'
import { fmtDec, fmtInt, fmtDateNum, fmtDateSirene, anneeSirene, aCommune, adresseInsecable } from './format'

describe('OUTILS-P0-2 L2 — trait d’union insécable sur le nom de commune', () => {
  it('« Saint-Denis » après le code postal passe en U+2011, la rue reste intacte', () => {
    const out = adresseInsecable('75 Rue de la Clinique, 97490 Saint-Denis')
    expect(out).toBe('75 Rue de la Clinique, 97490 Saint‑Denis')
    expect(out).not.toMatch(/97490 Saint-Denis/)          // plus de trait d’union sécable sur la commune
    expect(out).toContain('Rue de la Clinique')           // la rue n’est pas touchée
    expect(adresseInsecable(null)).toBe('')
  })
})

describe('OUTILS-P0-2 — « à {commune} » avec contraction de l’article', () => {
  it('au Tampon / au Port, aux Avirons, à La Possession, à Saint-Denis', () => {
    expect(aCommune('Le Tampon')).toBe('au Tampon')
    expect(aCommune('Le Port')).toBe('au Port')
    expect(aCommune('Les Avirons')).toBe('aux Avirons')
    expect(aCommune('La Possession')).toBe('à La Possession')
    expect(aCommune('Saint-Denis')).toBe('à Saint-Denis')
    expect(aCommune(null)).toBe('')
  })
})

describe('format partagé de la fiche', () => {
  it('décimales à la virgule, jamais le point', () => {
    expect(fmtDec(3.6)).toBe('3,6')
    expect(fmtDec(63.9, 1)).toBe('63,9')
    expect(fmtDec(10.34, 2)).toBe('10,34')
    expect(fmtDec(null)).toBe('—')
  })

  it('entiers groupés avec espace insécable (jamais coupés)', () => {
    // 17 515 avec l'espace fine insécable U+202F → ne casse pas en fin de ligne
    expect(fmtInt(17515)).toBe('17 515')
  })

  it('dates numériques en JJ/MM/AAAA (pas d\'ISO brut)', () => {
    expect(fmtDateNum('2025-09-29')).toBe('29/09/2025')
    expect(fmtDateNum(null)).toBe('—')
  })

  it('date SIRENE 1900 = inconnue → n.c.', () => {
    expect(fmtDateSirene('1900-01-01')).toBe('n.c.')
    expect(fmtDateSirene('2005-10-01')).toBe('01/10/2005')
    expect(fmtDateSirene(null)).toBe('n.c.')
  })

  it('année SIRENE : 2005, ou n.c. quand 1900', () => {
    expect(anneeSirene('2005-10-01')).toBe('2005')
    expect(anneeSirene(1900)).toBe('n.c.')
    expect(anneeSirene('1900')).toBe('n.c.')
    expect(anneeSirene(null)).toBe('n.c.')
  })
})
