import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { fireEvent, render } from '@testing-library/react'
import { useApp } from '../../store/useApp'
import { CompareModule } from './ComparePanel'

// Mandat COMPARAISON — l'outil est ANCRÉ dans Outils : openCompare ouvre le PANNEAU (pas le tableau),
// le picking est ON, et « Comparer (n/3) » ouvre l'overlay. Sélection conservée (SOCLE).
const st = () => useApp.getState()

beforeEach(() => {
  useApp.setState({ compareIdus: [], compareOpen: false, comparePicking: false, compareTouchedAt: null,
    module: null, outilsOpen: false, view: 'cartes', moduleMap: { idus: [], extra: null } })
})
afterEach(() => useApp.setState({ compareIdus: [], compareOpen: false, comparePicking: false, module: null }))

describe('COMPARAISON — ancrage dans Outils', () => {
  it('openCompare ouvre l\'OUTIL (panneau), picking ON, tableau fermé', () => {
    st().openCompare()
    expect(st().module).toBe('comparer')
    expect(st().comparePicking).toBe(true)
    expect(st().compareOpen).toBe(false)     // pas de bascule surprise vers le tableau
  })

  it('entrée depuis une fiche : openCompare puis addToCompare ancre l\'outil + ajoute la parcelle', () => {
    st().openCompare()
    st().addToCompare('97411000BZ1065')
    expect(st().module).toBe('comparer')
    expect(st().compareIdus).toEqual(['97411000BZ1065'])
    expect(st().compareOpen).toBe(false)     // le tableau ne s'ouvre PAS tout seul
  })

  it('le panneau : chips + slots libres + « Comparer (n/3) » ouvre le tableau', () => {
    useApp.setState({ compareIdus: ['97411000BZ1065', '97415000CT1837'] })
    const { container } = render(<CompareModule />)
    // 2 chips de sélection + 1 slot « + 1 libre »
    expect(container.querySelectorAll('[data-compare-chip]')).toHaveLength(2)
    expect(container.textContent).toContain('BZ 1065')           // idu court
    expect(container.textContent).toContain('+ 1 libre')
    // le panneau monté a armé le picking (clic-carte ajoute)
    expect(st().comparePicking).toBe(true)
    // « Comparer (2/3) » ouvre l'overlay
    const btn = container.querySelector('[data-compare-ouvrir]') as HTMLButtonElement
    expect(btn.textContent).toContain('2/3')
    fireEvent.click(btn)
    expect(st().compareOpen).toBe(true)
  })

  it('retirer une parcelle depuis une chip', () => {
    useApp.setState({ compareIdus: ['97411000BZ1065', '97415000CT1837'] })
    const { container } = render(<CompareModule />)
    const chip = container.querySelector('[data-compare-chip] button') as HTMLButtonElement
    fireEvent.click(chip)
    expect(st().compareIdus).toEqual(['97415000CT1837'])
  })
})
