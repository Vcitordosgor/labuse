import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useApp } from './useApp'

// SOCLE (refonte 13 outils) — cycle de vie des overlays plein écran + TTL 15 min de la sélection.
// Critères : « changer d'outil avec un overlay ouvert ne laisse jamais rien à l'écran ; revenir dans
// Comparaison sous 15 min retrouve la sélection ».
const st = () => useApp.getState()

beforeEach(() => {
  // baseline propre : aucun overlay, tiroir fermé, pas de sélection
  useApp.setState({
    compareIdus: [], compareOpen: false, comparePicking: false,
    communesTableOpen: false, densifierTableOpen: false, outilsOpen: false, module: null, view: 'cartes',
    outilRetour: [], permitToOpen: null, m02Prefill: null,
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

  it('FIX-INTEGRATION I7 : le tiroir de source (sourceLine) tombe au changement d\'outil', () => {
    st().openSourceDrawer({ label: 'source' } as never)   // tiroir ouvert sur une fiche
    expect(st().sourceLine).not.toBeNull()
    st().setModule('assemblage')                          // changement d'outil
    expect(st().sourceLine).toBeNull()                    // fermé via CLOSE_OVERLAYS (plus de résidu)
    // et ouvrir le tiroir ne se sabote pas lui-même (openSourceDrawer ne spread pas CLOSE_OVERLAYS)
    st().openSourceDrawer({ label: 'x' } as never)
    expect(st().sourceLine).not.toBeNull()
  })

  it('FIX-ACCUEIL A3 : openFiltres ferme les overlays (accueil « Commencer » / sélecteur commune du header)', () => {
    useApp.setState({ compareOpen: true, communesTableOpen: true, densifierTableOpen: true, accueilVu: false })
    st().openFiltres()
    expect(st().panneauSection).toBe('filtres')
    expect(st().accueilVu).toBe(true)              // ouvre les Filtres = consomme l'accueil
    expect(st().compareOpen).toBe(false)           // plus de panneau fantôme par-dessus les Filtres
    expect(st().communesTableOpen).toBe(false)
    expect(st().densifierTableOpen).toBe(false)
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

describe('OUTILS-FIX-3 Lot D — fil de retour entre outils', () => {
  it('un pont empile un retour ; retourOutil rouvre l\'outil de départ dans son état', () => {
    // simulation du pont Densifier → Faisabilité : setModule puis pushOutilRetour (ordre du pont).
    st().setModule('programme')
    st().pushOutilRetour({ module: 'renouvellement', label: 'Densifier', restore: { densifierTableOpen: true } })
    expect(st().outilRetour).toHaveLength(1)
    expect(st().outilRetour[0].label).toBe('Densifier')
    st().retourOutil()
    expect(st().module).toBe('renouvellement')      // rouvre l'outil de départ
    expect(st().densifierTableOpen).toBe(true)      // …dans son état (grand tableau rouvert)
    expect(st().outilRetour).toHaveLength(0)         // dépilé
  })

  it('une navigation manuelle (setModule menu) VIDE la pile : pas de « ← » sur un outil ouvert au menu', () => {
    st().pushOutilRetour({ module: 'permis', label: 'Permis', restore: { permitToOpen: 'PC-42' } })
    expect(st().outilRetour).toHaveLength(1)
    st().setModule('communes')                      // ouverture depuis le menu
    expect(st().outilRetour).toHaveLength(0)         // vidée par CLOSE_OVERLAYS
  })

  it('retourOutil restaure un prefill (Permis → drawer, Scan → SIREN) et openCompare vide aussi la pile', () => {
    st().pushOutilRetour({ module: 'permis', label: 'Permis', restore: { permitToOpen: 'PC-42' } })
    st().retourOutil()
    expect(st().module).toBe('permis')
    expect(st().permitToOpen).toBe('PC-42')          // le drawer se rouvre (consommé par M03)
    // openCompare (menu ou pont) vide la pile ; le pont ré-empile APRÈS
    st().pushOutilRetour({ module: 'patrimoine', label: 'Scan patrimoine', restore: { m02Prefill: '123456789' } })
    st().openCompare()
    expect(st().outilRetour).toHaveLength(0)
  })

  it('retourOutil sans pile ne fait rien (garde)', () => {
    useApp.setState({ outilRetour: [], module: 'communes' })
    st().retourOutil()
    expect(st().module).toBe('communes')
  })
})

describe('RETOURS-15 S3 — focusParcelle(idu,{fiche}) : zoom + contour + fiche à la demande', () => {
  beforeEach(() => useApp.setState({ focusIdu: null, selectedIdu: null, focusNonce: 0, contexteCommune: null }))

  it('sans fiche : zoom (focusIdu + nonce) et contour (cible = focusIdu), pas de fiche', () => {
    const n0 = st().focusNonce
    st().focusParcelle('97411000BZ1065')
    expect(st().focusIdu).toBe('97411000BZ1065')   // pilote le zoom et le contour (cible)
    expect(st().focusNonce).toBe(n0 + 1)            // ré-déclenche l'effet carte
    expect(st().selectedIdu).toBeNull()             // la fiche NE s'ouvre PAS
  })

  it('fiche:true : ouvre la fiche (selectedIdu) en plus du zoom + contour', () => {
    useApp.setState({ contexteCommune: { code: '97411' } as never })
    st().focusParcelle('97411000BZ1065', { fiche: true })
    expect(st().focusIdu).toBe('97411000BZ1065')
    expect(st().selectedIdu).toBe('97411000BZ1065') // la fiche s'ouvre
    expect(st().contexteCommune).toBeNull()         // fiche commune fermée (pas de coexistence)
  })

  it('idu vide / « undefined » ne fabrique jamais une sélection fantôme', () => {
    st().focusParcelle('undefined', { fiche: true })
    expect(st().focusIdu).toBeNull()
    expect(st().selectedIdu).toBeNull()
  })
})

// RECETTE-OUTILS-1 (point 23) — plus de TTL 15 min : la sélection Comparer est de SESSION (mémoire),
// pas de péremption dans le temps ; elle est vidée par clearCompare (au démontage de l'outil).
describe('sélection de comparaison — de session, sans TTL (point 23)', () => {
  it('openCompare garde la sélection courante (pas d\'expiration temporelle)', () => {
    st().addToCompare('97411000BZ1065')
    st().addToCompare('97411000BZ1044')
    st().openCompare()
    expect(st().compareIdus).toEqual(['97411000BZ1065', '97411000BZ1044'])
    expect(st().module).toBe('comparer')
    expect(st().compareOpen).toBe(false)
    expect(st().comparePicking).toBe(true)
  })

  it('un ajout empile sur la sélection courante (max 3)', () => {
    st().addToCompare('A'); st().addToCompare('B'); st().addToCompare('C'); st().addToCompare('D')
    expect(st().compareIdus).toEqual(['A', 'B', 'C'])   // plafonné à 3, ordre conservé
  })

  it('clearCompare vide la sélection', () => {
    st().addToCompare('A')
    st().clearCompare()
    expect(st().compareIdus).toEqual([])
    expect(st().compareOpen).toBe(false)
  })
})
