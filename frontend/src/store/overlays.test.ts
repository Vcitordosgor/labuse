import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useApp } from './useApp'

// SOCLE (refonte 13 outils) — cycle de vie des overlays plein écran + TTL 15 min de la sélection.
// Critères : « changer d'outil avec un overlay ouvert ne laisse jamais rien à l'écran ; revenir dans
// Comparaison sous 15 min retrouve la sélection ».
const st = () => useApp.getState()

beforeEach(() => {
  // baseline propre : aucun overlay, tiroir fermé, pas de sélection
  useApp.setState({
    compareIdus: [], compareOpen: false, comparePicking: false, compareTouchedAt: null,
    communesTableOpen: false, densifierTableOpen: false, outilsOpen: false, module: null, view: 'cartes',
  })
})
afterEach(() => vi.restoreAllMocks())

describe('cleanup on-leave centralisé', () => {
  it('ouvrir le tiroir Outils ferme l\'overlay Comparaison, la sélection SURVIT', () => {
    st().addToCompare('97411000BZ1065')       // sélection
    st().setCompareOpen(true)                 // tableau ouvert (bouton « Comparer »)
    expect(st().compareOpen).toBe(true)
    st().toggleOutils()                       // outilsOpen était false → branche d'OUVERTURE
    expect(st().outilsOpen).toBe(true)
    expect(st().compareOpen).toBe(false)      // plus de panneau fantôme
    expect(st().compareIdus).toEqual(['97411000BZ1065'])  // sélection conservée
  })

  it('openSources ferme la table Communes ET la comparaison', () => {
    useApp.setState({ compareOpen: true, communesTableOpen: true })
    st().openSources()
    expect(st().compareOpen).toBe(false)
    expect(st().communesTableOpen).toBe(false)
  })

  it('DENSIFIER : openDensifier ouvre le tableau + ferme les autres overlays ; setModule le referme', () => {
    useApp.setState({ compareOpen: true, communesTableOpen: true })
    st().openDensifier()
    expect(st().densifierTableOpen).toBe(true)
    expect(st().compareOpen).toBe(false)         // façon openCompare : ferme les autres
    expect(st().communesTableOpen).toBe(false)
    st().setModule('communes')                    // changement d'outil
    expect(st().densifierTableOpen).toBe(false)   // overlay Densifier fermé (CLOSE_OVERLAYS)
  })

  it('setOpenProjet et toggleSurveillance ferment les overlays', () => {
    useApp.setState({ compareOpen: true, communesTableOpen: true })
    st().setOpenProjet({ id: 1, nom: 'X' })
    expect(st().compareOpen).toBe(false)
    expect(st().communesTableOpen).toBe(false)
    useApp.setState({ compareOpen: true })
    st().toggleSurveillance()
    expect(st().compareOpen).toBe(false)
  })
})

describe('TTL 15 min de la sélection de comparaison', () => {
  it('retrouve la sélection quand on revient sous 15 min', () => {
    const t0 = 1_700_000_000_000
    vi.spyOn(Date, 'now').mockReturnValue(t0)
    st().addToCompare('97411000BZ1065')
    st().addToCompare('97411000BZ1044')
    st().setView('projets')                   // on quitte l'outil
    expect(st().compareOpen).toBe(false)
    expect(st().compareIdus).toHaveLength(2)   // survit
    ;(Date.now as unknown as { mockReturnValue: (v: number) => void }).mockReturnValue(t0 + 14 * 60 * 1000)
    st().openCompare()                         // retour 14 min plus tard
    expect(st().compareIdus).toEqual(['97411000BZ1065', '97411000BZ1044'])
    // COMPARAISON (refonte) : openCompare ouvre l'OUTIL (panneau), pas le tableau — picking ON, table fermée.
    expect(st().module).toBe('comparer')
    expect(st().compareOpen).toBe(false)
    expect(st().comparePicking).toBe(true)
  })

  it('vide une sélection périmée (> 15 min) et rouvre l\'outil en picking', () => {
    const t0 = 1_700_000_000_000
    vi.spyOn(Date, 'now').mockReturnValue(t0)
    st().addToCompare('97411000BZ1065')
    ;(Date.now as unknown as { mockReturnValue: (v: number) => void }).mockReturnValue(t0 + 16 * 60 * 1000)
    st().openCompare()                         // retour 16 min plus tard
    expect(st().compareIdus).toEqual([])
    expect(st().module).toBe('comparer')
    expect(st().comparePicking).toBe(true)
  })

  it('un nouvel ajout après péremption repart de zéro (pas d\'empilement sur du vieux)', () => {
    const t0 = 1_700_000_000_000
    vi.spyOn(Date, 'now').mockReturnValue(t0)
    st().addToCompare('A')
    ;(Date.now as unknown as { mockReturnValue: (v: number) => void }).mockReturnValue(t0 + 20 * 60 * 1000)
    st().addToCompare('B')
    expect(st().compareIdus).toEqual(['B'])
  })
})
