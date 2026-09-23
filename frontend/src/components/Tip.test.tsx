// FINITIONS-1 (P1, tranché par Vic) — les infobulles AU SURVOL sont RETIRÉES PARTOUT. SEULE exception :
// les 3 outils de mesure de la carte, qui passent `survol`. `garder` monte encore la bulle mais SANS
// survol : elle ne s'ouvre qu'au CLIC ou au FOCUS clavier (les « i » restent lisibles). jsdom +
// testing-library déclenchent fiablement les événements React : ces tests VERROUILLENT la bascule.
import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { Tip } from './Tip'

afterEach(cleanup)

describe('FINITIONS-1 P1 — survol retiré partout sauf `survol`', () => {
  it('SANS garder : aucune bulle au survol ni au focus (les enfants restent)', () => {
    const { container } = render(<Tip tip="explication"><button>déclencheur</button></Tip>)
    expect(screen.getByText('déclencheur')).toBeTruthy()          // le contenu reste
    const wrap = container.querySelector('span')!
    fireEvent.pointerEnter(wrap, { pointerType: 'mouse' })
    fireEvent.focus(wrap)
    expect(document.querySelector('[role="tooltip"]')).toBeNull() // JAMAIS de bulle
    expect(screen.queryByText('explication')).toBeNull()
  })

  it('AVEC garder SANS survol : le SURVOL n\'ouvre plus la bulle (les « i »)', () => {
    const { container } = render(<Tip garder tip="explication"><button>i</button></Tip>)
    const wrap = container.querySelector('span')!
    fireEvent.pointerEnter(wrap, { pointerType: 'mouse' })
    expect(document.querySelector('[role="tooltip"]')).toBeNull() // plus de bulle au survol
    // …mais le CLIC (ou le focus clavier) la révèle toujours : l'info reste accessible.
    fireEvent.click(wrap)
    const bulle = document.querySelector('[role="tooltip"]')
    expect(bulle).not.toBeNull()
    expect(bulle!.textContent).toContain('explication')
  })

  it('AVEC garder + survol : la bulle apparaît au survol (les 3 outils de mesure)', () => {
    const { container } = render(<Tip garder survol tip="explication"><button>i</button></Tip>)
    const wrap = container.querySelector('span')!
    fireEvent.pointerEnter(wrap, { pointerType: 'mouse' })
    const bulle = document.querySelector('[role="tooltip"]')
    expect(bulle).not.toBeNull()
    expect(bulle!.textContent).toContain('explication')
  })

  it('AVEC garder + survol : un survol tactile n\'ouvre pas (comportement inchangé)', () => {
    const { container } = render(<Tip garder survol tip="x"><button>i</button></Tip>)
    fireEvent.pointerEnter(container.querySelector('span')!, { pointerType: 'touch' })
    expect(document.querySelector('[role="tooltip"]')).toBeNull()
  })
})
