// CHARGEMENT-1 — VERROUS de l'indicateur unique : trois points menthe, délai de 300 ms (pas de
// clignotement sur les actions rapides), deux variantes inline/bloc.
import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, render } from '@testing-library/react'
import { Chargement } from './Loading'

afterEach(cleanup)

describe('CHARGEMENT-1 — indicateur unique', () => {
  it('ne s\'affiche PAS avant 300 ms (action rapide = aucun clignotement)', () => {
    vi.useFakeTimers()
    try {
      const { container } = render(<Chargement variant="bloc" />)
      expect(container.querySelector('[role="status"]')).toBeNull()
      act(() => { vi.advanceTimersByTime(299) })
      expect(container.querySelector('[role="status"]')).toBeNull()
    } finally {
      vi.useRealTimers()
    }
  })

  it('s\'affiche APRÈS 300 ms : trois points menthe', () => {
    vi.useFakeTimers()
    try {
      const { container } = render(<Chargement variant="bloc" />)
      act(() => { vi.advanceTimersByTime(300) })
      const statut = container.querySelector('[role="status"]')
      expect(statut).not.toBeNull()
      expect(statut!.getAttribute('aria-busy')).toBe('true')
      expect(container.querySelectorAll('.labuse-dot').length).toBe(3)
      expect(container.querySelector('.labuse-dot')!.className).toContain('bg-mint')
    } finally {
      vi.useRealTimers()
    }
  })

  it('delai=0 affiche tout de suite (cas retour immédiat)', () => {
    const { container } = render(<Chargement variant="inline" delai={0} label="Génération…" />)
    expect(container.querySelector('[role="status"]')).not.toBeNull()
    expect(container.textContent).toContain('Génération…')
  })

  it('points TOUJOURS menthe (défaut) ; accent courant (bouton plein) = couleur du texte', () => {
    const m = render(<Chargement variant="inline" delai={0} />)
    expect(m.container.querySelector('.labuse-dot')!.className).toContain('bg-mint')
    cleanup()
    const c = render(<Chargement variant="inline" accent="courant" delai={0} />)
    expect(c.container.querySelector('.labuse-dot')!.className).toContain('bg-current')
  })
})
