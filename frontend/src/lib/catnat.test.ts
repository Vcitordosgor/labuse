// OUTIL-COMMUNES-FIX-6 LOT 0 (filet) — « et N autres » du détail CatNat = total source − affichées.
// ROUGE maintenant (l'implémentation courante calcule sur la liste tronquée à 12 → 6), VERT au LOT 3.
import { describe, expect, it } from 'vitest'
import { catnatReste } from './catnat'

describe('catnatReste — reste calculé sur le total de la source', () => {
  it('Saint-Paul : 24 entrées, 6 affichées → 18 autres (pas 12−6=6)', () => {
    expect(catnatReste(24, 12, 6)).toBe(18)
  })
  it('Saint-Denis : 21 entrées, 6 affichées → 15 autres', () => {
    expect(catnatReste(21, 12, 6)).toBe(15)
  })
  it('total inconnu (null) → repli sur la longueur de liste', () => {
    expect(catnatReste(null, 9, 6)).toBe(3)
  })
  it('tout est affiché → 0 (pas de « et N autres »)', () => {
    expect(catnatReste(6, 6, 6)).toBe(0)
  })
})
