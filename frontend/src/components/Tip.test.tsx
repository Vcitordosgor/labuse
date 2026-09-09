// RECETTE-2 (S10, R28 tranché par Vic) — les infobulles au survol sont RETIRÉES partout, SAUF sur
// les contrôles de la carte et les déclencheurs fonctionnels icône-seule, qui passent `garder`.
// jsdom + testing-library déclenchent fiablement les événements React (là où Playwright, via le
// portal, ne le fait pas) : ces tests VERROUILLENT la bascule.
import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { Tip } from './Tip'

afterEach(cleanup)

describe('RECETTE-2 S10 — infobulles retirées sauf `garder`', () => {
  it('SANS garder : aucune bulle au survol ni au focus (les enfants restent)', () => {
    const { container } = render(<Tip tip="explication"><button>déclencheur</button></Tip>)
    expect(screen.getByText('déclencheur')).toBeTruthy()          // le contenu reste
    const wrap = container.querySelector('span')!
    fireEvent.pointerEnter(wrap, { pointerType: 'mouse' })
    fireEvent.focus(wrap)
    expect(document.querySelector('[role="tooltip"]')).toBeNull() // JAMAIS de bulle
    expect(screen.queryByText('explication')).toBeNull()
  })

  it('AVEC garder : la bulle apparaît au survol (contrôle carte / icône-seule)', () => {
    const { container } = render(<Tip garder tip="explication"><button>i</button></Tip>)
    const wrap = container.querySelector('span')!
    fireEvent.pointerEnter(wrap, { pointerType: 'mouse' })
    const bulle = document.querySelector('[role="tooltip"]')
    expect(bulle).not.toBeNull()
    expect(bulle!.textContent).toContain('explication')
  })

  it('AVEC garder : un survol tactile n\'ouvre pas (comportement inchangé)', () => {
    const { container } = render(<Tip garder tip="x"><button>i</button></Tip>)
    fireEvent.pointerEnter(container.querySelector('span')!, { pointerType: 'touch' })
    expect(document.querySelector('[role="tooltip"]')).toBeNull()
  })
})
