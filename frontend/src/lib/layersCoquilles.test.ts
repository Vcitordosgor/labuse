import { describe, expect, it } from 'vitest'
import { LAYER_INFO } from './layers'

// FIX-COUCHES — verrous sur les coquilles des textes « i » des couches (P2 compte BPE ; P5 pôles).
describe('FIX-COUCHES — textes « i » des couches', () => {
  it('P2 — le « i » BPE ne porte plus le compte en dur faux 36 821 (35 546 réel)', () => {
    const bpe = LAYER_INFO.equipements_bpe
    expect(bpe).not.toContain('36 821')
    expect(bpe).toContain('35 546')
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
