import { describe, expect, it, vi } from 'vitest'
import { act, render, renderHook, screen } from '@testing-library/react'
import { createElement } from 'react'
import { fmtInt } from '../lib/format'
import { ListPaginationFooter, PAGE_SIZE, usePagination } from './ListPagination'

// SOCLE — critère d'acceptation : « charge par paquets de 400 jusqu'à épuisement, tout charger
// fonctionne, le compteur est exact ».
describe('SOCLE — usePagination', () => {
  it('démarre à une page, charge par paquets, atteint le total EXACT', () => {
    const total = 67_214
    const { result } = renderHook(() => usePagination(total))
    expect(result.current.shown).toBe(PAGE_SIZE)          // 400
    expect(result.current.hasMore).toBe(true)
    act(() => result.current.more())
    expect(result.current.shown).toBe(800)
    act(() => result.current.all())
    expect(result.current.shown).toBe(total)              // tout chargé, pile
    expect(result.current.hasMore).toBe(false)
  })

  it('le dernier paquet ne dépasse jamais le total', () => {
    const { result } = renderHook(() => usePagination(500))
    act(() => result.current.more())
    expect(result.current.shown).toBe(500)                // 400 → 500 (pas 800)
    expect(result.current.hasMore).toBe(false)
  })

  it('total plus petit qu\'une page : tout est visible d\'emblée', () => {
    const { result } = renderHook(() => usePagination(137))
    expect(result.current.shown).toBe(137)
    expect(result.current.hasMore).toBe(false)
  })

  it('un nouveau jeu (total qui change) réinitialise la fenêtre à une page', () => {
    let total = 5000
    const { result, rerender } = renderHook(() => usePagination(total))
    act(() => result.current.all())
    expect(result.current.shown).toBe(5000)
    total = 1200
    rerender()
    expect(result.current.shown).toBe(PAGE_SIZE)          // repart à 400 sur la nouvelle requête
  })
})

describe('SOCLE — ListPaginationFooter', () => {
  // getByText normalise les espaces insécables (U+202F de fmtInt fr) en espace simple ; on aligne.
  const n = (s: string) => s.replace(/\s/g, ' ')

  it('compteur exact + « Voir 400 de plus » + « Tout charger (total) »', () => {
    const onMore = vi.fn(); const onAll = vi.fn()
    render(createElement(ListPaginationFooter, { shown: 400, total: 67_214, onMore, onAll }))
    expect(screen.getByText(n(`${fmtInt(400)} / ${fmtInt(67_214)}`))).toBeTruthy()
    screen.getByText(n(`Voir ${fmtInt(400)} de plus`)).click()
    expect(onMore).toHaveBeenCalledOnce()
    screen.getByText(n(`Tout charger (${fmtInt(67_214)})`)).click()
    expect(onAll).toHaveBeenCalledOnce()
  })

  it('dernière page : le compteur reste, plus de bouton « de plus »', () => {
    render(createElement(ListPaginationFooter, { shown: 137, total: 137, onMore: () => {} }))
    expect(screen.getByText(n(`${fmtInt(137)} / ${fmtInt(137)}`))).toBeTruthy()
    expect(screen.queryByText(/de plus/)).toBeNull()
  })

  it('avant-dernière page : « Voir 37 de plus » (honnête, pas 400)', () => {
    render(createElement(ListPaginationFooter, { shown: 100, total: 137, onMore: () => {} }))
    expect(screen.getByText(n(`Voir ${fmtInt(37)} de plus`))).toBeTruthy()
  })
})
