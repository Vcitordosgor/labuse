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

// COMMUNE-FIX-1 (B5) — « Voir ses parcelles » : filtre commune + verdict + listing + recadrage carte.
// Le zoom passait par l'effet « fit au changement de commune » ; quand la fiche est ouverte via le
// clic-commune (commune DÉJÀ posée), ce changement n'a pas lieu → le bouton ne bougeait pas la carte.
// `refitCommune()` incrémente un nonce que l'effet de fit observe : le recadrage est forcé.
describe('COMMUNE-FIX-1 (B5) — « Voir ses parcelles »', () => {
  beforeEach(() => useApp.setState({ commune: null, contexteCommune: null, fitCommuneNonce: 0 }))

  it('force le recadrage même quand la commune est déjà la courante (fiche ouverte)', () => {
    useApp.getState().focusCommune('Saint-Paul')   // fiche ouverte : commune DÉJÀ = Saint-Paul
    const avant = useApp.getState().fitCommuneNonce
    const s = useApp.getState()                     // séquence du bouton « Voir ses parcelles »
    s.setView('cartes'); s.setCommune('Saint-Paul'); s.setCommunesFilter(['Saint-Paul'])
    s.setFilter('analyseLabuse', true); s.setVerdict(true)
    s.openListing(); s.refitCommune()
    const apres = useApp.getState()
    expect(apres.fitCommuneNonce).toBe(avant + 1)          // recadrage forcé (zoom)
    expect(apres.filters.communes).toEqual(['Saint-Paul']) // filtre commune
    expect(apres.filters.analyseLabuse).toBe(true)
    expect(apres.verdict).toBe(true)
    expect(apres.panneauSection).toBe('listing')           // listing ouvert
  })
})
