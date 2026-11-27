// OUTIL-COMMUNES-FIX-7 LOT 0 (filet) — la case « État du PLU » du bandeau porte la date de la dernière
// pièce. ROUGE maintenant (la sous-ligne courante n'affiche pas la date), VERT au LOT 3.
import { describe, expect, it } from 'vitest'
import { bandeauEtatPluSous } from './plu'

describe('bandeauEtatPluSous — la case État du PLU porte la date', () => {
  it('La Plaine-des-Palmistes : dernière pièce 27/11/2025 → la date figure dans la sous-ligne', () => {
    expect(bandeauEtatPluSous('2025-11-27')).toContain('27/11/2025')
  })
  it('sans date → repli lisible (pas de date inventée)', () => {
    expect(bandeauEtatPluSous(null)).toBeTruthy()
  })
  // OUTIL-COMMUNES-FIX-9 LOT C (4) — précision de date variable honnête (mois/année), bonne préposition.
  it('précision MOIS : « 2025-05 » → « en mai 2025 » (jamais un faux 1er du mois)', () => {
    expect(bandeauEtatPluSous('2025-05')).toBe('en mai 2025')
  })
  it('précision ANNÉE : « 2025 » → « en 2025 »', () => {
    expect(bandeauEtatPluSous('2025')).toBe('en 2025')
  })
  it('précision JOUR : « au 29/09/2025 »', () => {
    expect(bandeauEtatPluSous('2025-09-29')).toBe('au 29/09/2025')
  })
})
