import { describe, it, expect, beforeEach } from 'vitest'
import { empreinte, noterEditeur, editeurDiffere } from './empreinteDoc'

// CHASSE-DOCS-FIX-1 (Lot 5.1) — garde : « Sources modifiées depuis » réagit aux saisies.
// L'empreinte de RÉFÉRENCE est celle STOCKÉE AVEC LE DOCUMENT côté serveur (passée ici en argument,
// comme `hypotheses._empreinte` renvoyée par la bibliothèque) → le badge marche sur un AUTRE poste.
// L'empreinte de l'ÉDITEUR VIVANT est locale (localStorage), publiée par l'éditeur.
describe('empreinteDoc — badge sources modifiées sur saisies (empreinte serveur)', () => {
  beforeEach(() => localStorage.clear())

  it('empreinte stable, insensible à l’ordre des clés', () => {
    expect(empreinte({ a: 1, b: 2 })).toBe(empreinte({ b: 2, a: 1 }))
    expect(empreinte({ a: 1 })).not.toBe(empreinte({ a: 2 }))
  })

  it('juste après génération (éditeur = empreinte serveur) : à jour', () => {
    const serveur = empreinte({ prix: 4000 })
    noterEditeur('bilan', '97415000BO0852', { prix: 4000 })   // l'éditeur reflète ce qui a été généré
    expect(editeurDiffere('bilan', '97415000BO0852', serveur)).toBe(false)
  })

  it('édition sans régénérer : modifié (vs empreinte serveur)', () => {
    const serveur = empreinte({ prix: 4000 })
    noterEditeur('bilan', '97415000BO0852', { prix: 4800 })
    expect(editeurDiffere('bilan', '97415000BO0852', serveur)).toBe(true)
  })

  it('ré-édition à la valeur du document : de nouveau à jour', () => {
    const serveur = empreinte({ prix: 4000 })
    noterEditeur('bilan', '97415000BO0852', { prix: 4800 })
    noterEditeur('bilan', '97415000BO0852', { prix: 4000 })
    expect(editeurDiffere('bilan', '97415000BO0852', serveur)).toBe(false)
  })

  it('étude : objectif changé → modifié', () => {
    const serveur = empreinte({ objectif: 'equilibre' })
    noterEditeur('etude-faisabilite', '97416000CZ0678', { objectif: 'plus_logements' })
    expect(editeurDiffere('etude-faisabilite', '97416000CZ0678', serveur)).toBe(true)
  })

  it('AUTRE POSTE (pas d’éditeur ouvert ici, mais empreinte serveur présente) : pas de faux positif', () => {
    const serveur = empreinte({ prix: 4000 })
    expect(editeurDiffere('bilan', '97415000BO0852', serveur)).toBe(false)   // rien en localStorage
  })

  it('vieux document sans empreinte serveur : pas de badge', () => {
    noterEditeur('bilan', '97415000BO0852', { prix: 4800 })
    expect(editeurDiffere('bilan', '97415000BO0852', undefined)).toBe(false)
    expect(editeurDiffere('bilan', '97415000BO0852', null)).toBe(false)
  })
})
