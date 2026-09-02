import { describe, expect, it, vi } from 'vitest'
import { act, render, renderHook, screen } from '@testing-library/react'
import { createElement } from 'react'
import { fmtInt } from '../lib/format'
import { ListPaginationFooter, PAGE_SIZE, usePagination } from './ListPagination'

// RETOURS-10 (T3) — doctrine : page de 200, « Voir N de plus » incrémental, JAMAIS de « Tout charger ».
describe('T3 — usePagination', () => {
  it('la page est de 200', () => {
    expect(PAGE_SIZE).toBe(200)
  })

  it('une liste de 33 910 ne montre que 200 au premier rendu, puis 200 de plus par clic', () => {
    const { result } = renderHook(() => usePagination(33_910))
    expect(result.current.shown).toBe(200)          // premier rendu : 200, pas 33 910
    expect(result.current.hasMore).toBe(true)
    act(() => result.current.more())
    expect(result.current.shown).toBe(400)          // +200
    act(() => result.current.more())
    expect(result.current.shown).toBe(600)          // +200 encore — jamais de saut à 33 910
    expect(result.current.hasMore).toBe(true)
  })

  it('le dernier paquet ne dépasse jamais le total', () => {
    const { result } = renderHook(() => usePagination(300))
    act(() => result.current.more())
    expect(result.current.shown).toBe(300)          // 200 → 300 (pas 400)
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
    act(() => { result.current.more(); result.current.more() })
    expect(result.current.shown).toBe(600)
    total = 1200
    rerender()
    expect(result.current.shown).toBe(PAGE_SIZE)    // repart à 200 sur la nouvelle requête
  })
})

describe('T3 — ListPaginationFooter', () => {
  // getByText normalise les espaces insécables (U+202F de fmtInt fr) en espace simple ; on aligne.
  const n = (s: string) => s.replace(/\s/g, ' ')

  it('compteur exact + « Voir 200 de plus » ; AUCUN bouton « tout charger »', () => {
    const onMore = vi.fn()
    render(createElement(ListPaginationFooter, { shown: 200, total: 33_910, onMore }))
    expect(screen.getByText(n(`${fmtInt(200)} / ${fmtInt(33_910)}`))).toBeTruthy()
    screen.getByText(n(`Voir ${fmtInt(200)} de plus`)).click()
    expect(onMore).toHaveBeenCalledOnce()
    // le bouton de chargement massif n'existe plus (il figeait l'app)
    expect(screen.queryByText(/[Tt]out charger/)).toBeNull()
  })

  it('dernière page : le compteur reste, plus de bouton « de plus »', () => {
    render(createElement(ListPaginationFooter, { shown: 137, total: 137, onMore: () => {} }))
    expect(screen.getByText(n(`${fmtInt(137)} / ${fmtInt(137)}`))).toBeTruthy()
    expect(screen.queryByText(/de plus/)).toBeNull()
  })

  it('avant-dernière page : « Voir 37 de plus » (honnête, pas 200)', () => {
    render(createElement(ListPaginationFooter, { shown: 100, total: 137, onMore: () => {} }))
    expect(screen.getByText(n(`Voir ${fmtInt(37)} de plus`))).toBeTruthy()
  })
})
