import { describe, it, expect, beforeEach } from 'vitest'
import { empreinte, noterEditeur, noterGeneration, editeurModifie } from './empreinteDoc'

// CHASSE-DOCS-FIX-1 (Lot 5.1) — garde : « Sources modifiées depuis » réagit aux saisies.
describe('empreinteDoc — badge sources modifiées sur saisies', () => {
  beforeEach(() => localStorage.clear())

  it('empreinte stable, insensible à l’ordre des clés', () => {
    expect(empreinte({ a: 1, b: 2 })).toBe(empreinte({ b: 2, a: 1 }))
    expect(empreinte({ a: 1 })).not.toBe(empreinte({ a: 2 }))
  })

  it('juste après génération : à jour (pas modifié)', () => {
    noterGeneration('bilan', '97415000BO0852', { prix: 4000 })
    expect(editeurModifie('bilan', '97415000BO0852')).toBe(false)
  })

  it('édition sans régénérer : modifié', () => {
    noterGeneration('bilan', '97415000BO0852', { prix: 4000 })
    noterEditeur('bilan', '97415000BO0852', { prix: 4800 })   // le client change une hypothèse
    expect(editeurModifie('bilan', '97415000BO0852')).toBe(true)
  })

  it('réédition à la valeur d’origine : de nouveau à jour', () => {
    noterGeneration('bilan', '97415000BO0852', { prix: 4000 })
    noterEditeur('bilan', '97415000BO0852', { prix: 4800 })
    noterEditeur('bilan', '97415000BO0852', { prix: 4000 })
    expect(editeurModifie('bilan', '97415000BO0852')).toBe(false)
  })

  it('régénérer après édition : à jour', () => {
    noterGeneration('etude-faisabilite', '97416000CZ0678', { objectif: 'equilibre' })
    noterEditeur('etude-faisabilite', '97416000CZ0678', { objectif: 'plus_logements' })
    expect(editeurModifie('etude-faisabilite', '97416000CZ0678')).toBe(true)
    noterGeneration('etude-faisabilite', '97416000CZ0678', { objectif: 'plus_logements' })
    expect(editeurModifie('etude-faisabilite', '97416000CZ0678')).toBe(false)
  })

  it('sans génération suivie (autre appareil) : pas de faux positif', () => {
    noterEditeur('bilan', '97415000BO0852', { prix: 4800 })
    expect(editeurModifie('bilan', '97415000BO0852')).toBe(false)   // pas de gen → on ne marque pas
  })
})
