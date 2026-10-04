// RECETTE-1 (D1, tranché par Vic 04/10) — RÉTABLISSEMENT du survol : tous les « i » (`garder`) se
// révèlent AU SURVOL (délai 150 ms) et au FOCUS clavier ; fermeture à Échap / à la sortie ; sur
// tactile un tap ouvre. Le gate `garder` reste : sans lui, aucune bulle (pas de bulle sauvage).
// Ces tests VERROUILLENT la bascule (annule FINITIONS-1 P1).
import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { Tip } from './Tip'

afterEach(cleanup)

describe('RECETTE-1 D1 — les « i » se révèlent au survol / focus / tap', () => {
  it('SANS garder : aucune bulle au survol ni au focus (gate conservé)', () => {
    const { container } = render(<Tip tip="explication"><button>déclencheur</button></Tip>)
    expect(screen.getByText('déclencheur')).toBeTruthy()
    const wrap = container.querySelector('span')!
    fireEvent.pointerEnter(wrap, { pointerType: 'mouse' })
    fireEvent.focus(wrap)
    expect(document.querySelector('[role="tooltip"]')).toBeNull()
    expect(screen.queryByText('explication')).toBeNull()
  })

  it('AVEC garder : le SURVOL souris ouvre la bulle après le délai (150 ms)', () => {
    vi.useFakeTimers()
    try {
      const { container } = render(<Tip garder tip="explication"><button>i</button></Tip>)
      const wrap = container.querySelector('span')!
      fireEvent.pointerEnter(wrap, { pointerType: 'mouse' })
      expect(document.querySelector('[role="tooltip"]')).toBeNull()   // pas avant le délai
      act(() => { vi.advanceTimersByTime(150) })
      const bulle = document.querySelector('[role="tooltip"]')
      expect(bulle).not.toBeNull()
      expect(bulle!.textContent).toContain('explication')
    } finally {
      vi.useRealTimers()
    }
  })

  it('AVEC garder : le FOCUS clavier ouvre immédiatement, Échap ferme', () => {
    const { container } = render(<Tip garder tip="explication"><button>i</button></Tip>)
    const wrap = container.querySelector('span')!
    fireEvent.focus(wrap)
    expect(document.querySelector('[role="tooltip"]')).not.toBeNull()
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(document.querySelector('[role="tooltip"]')).toBeNull()
  })

  it('AVEC garder : un survol tactile n\'ouvre pas (un tap oui)', () => {
    const { container } = render(<Tip garder tip="x"><button>i</button></Tip>)
    const wrap = container.querySelector('span')!
    fireEvent.pointerEnter(wrap, { pointerType: 'touch' })
    expect(document.querySelector('[role="tooltip"]')).toBeNull()
    fireEvent.click(wrap)
    expect(document.querySelector('[role="tooltip"]')).not.toBeNull()
  })
})
