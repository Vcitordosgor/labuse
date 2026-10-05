import { describe, expect, it } from 'vitest'
import { LAYER_INFO } from './layers'

// FIX-COUCHES — verrous sur les coquilles des textes « i » des couches (P2 compte BPE ; P5 pôles).
describe('FIX-COUCHES — textes « i » des couches', () => {
  // CHASSE-FIX-2 — le « i » BPE ne doit porter AUCUN compte en dur : ni le faux 36 821, ni un
  // littéral « 35 546 » (le servi réel est 35 544 et DÉRIVE à chaque ingestion — un nombre figé
  // dans une infobulle statique est exactement l'anti-patron FRONT-CHIFFRES). Le verrou vérifie
  // donc l'ABSENCE de compte figé et la présence de la SOURCE (INSEE / BPE / millésime), jamais
  // un chiffre que le front n'a pas le droit de décider.
  it('P2 — le « i » BPE ne porte aucun compte en dur (ni 36 821, ni 35 546) et cite sa source', () => {
    const bpe = LAYER_INFO.equipements_bpe
    expect(bpe).not.toContain('36 821')
    expect(bpe).not.toContain('35 546')
    expect(bpe).not.toMatch(/\d[\d   ]{3,}\s*équipements/i)   // aucun « NN NNN équipements » figé
    expect(bpe).toMatch(/INSEE.*BPE.*millésime/i)                      // la source, pas un compte
  })

  it('P5 — le « i » Transport ne revendique plus les pôles d’échange, il renvoie à Axes', () => {
    const transport = LAYER_INFO.transport
    // les pôles ne sont plus décrits comme faisant partie de Transport…
    expect(transport).not.toContain('les pôles d’échange (gares')
    // …et le texte pointe explicitement vers la couche Axes.
    expect(transport).toContain('Axes structurants')
  })

  it('P5 — le « i » Axes décrit désormais les pôles d’échange (cohérence avec le câblage M137-X)', () => {
    expect(LAYER_INFO.axes).toContain('pôles d’échange')
  })
})
