import { describe, expect, it, beforeEach } from 'vitest'
import { useApp } from '../../store/useApp'

// RETOURS-8 (R9) — le bouton « Fiche commune » reparaît avec la commune (ContexteButton rend dès que
// `commune` est posé), et l'ouverture depuis ce bouton (focusCommune) comme depuis l'omnibox/sélecteur
// (setContexteCommune) donne LE MÊME écran : toutes deux posent `contexteCommune`. On verrouille
// l'invariant pour qu'une future régression ne dissocie pas les deux portes.
describe('RETOURS-8 R9 — Fiche commune', () => {
  beforeEach(() => { useApp.setState({ commune: null, contexteCommune: null }) })

  it('focusCommune pose commune (le bouton apparaît) ET contexteCommune (le volet s\'ouvre)', () => {
    useApp.getState().focusCommune('Saint-Paul')
    const s = useApp.getState()
    expect(s.commune).toBe('Saint-Paul')            // ContexteButton devient visible
    expect(s.contexteCommune).toBe('Saint-Paul')    // même écran que l'omnibox
  })

  it('setContexteCommune (omnibox / sélecteur) ouvre le même écran (contexteCommune)', () => {
    useApp.getState().setContexteCommune('Saint-Paul')
    expect(useApp.getState().contexteCommune).toBe('Saint-Paul')
  })
})
