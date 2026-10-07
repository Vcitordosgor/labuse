// CHARGEMENT-1 (point 6) — VERROUS de la détection « ordinateur seulement ». Une fenêtre de bureau
// rétrécie n'est PAS bloquée si l'écran physique fait ≥ 1 024 px ; iPhone/iPad/petit écran le sont.
import { afterEach, describe, expect, it, vi } from 'vitest'
import { estAppareilMobile } from './appareil'

function simuler(opts: { ua?: string; platform?: string; touch?: number; coarse?: boolean; screenW?: number }) {
  vi.stubGlobal('navigator', {
    userAgent: opts.ua ?? 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
    platform: opts.platform ?? 'MacIntel',
    maxTouchPoints: opts.touch ?? 0,
  })
  vi.stubGlobal('window', {
    screen: { width: opts.screenW ?? 1920 },
    matchMedia: (q: string) => ({ matches: q.includes('coarse') ? !!opts.coarse : false }),
  })
}

afterEach(() => { vi.unstubAllGlobals() })

describe('CHARGEMENT-1 point 6 — estAppareilMobile', () => {
  it('ordinateur de bureau (souris, grand écran) → NON bloqué', () => {
    simuler({ screenW: 1920 })
    expect(estAppareilMobile()).toBe(false)
  })

  it('fenêtre de bureau rétrécie mais écran ≥ 1024 → NON bloqué', () => {
    // innerWidth ignoré : on ne lit QUE screen.width (physique).
    simuler({ screenW: 1920 })
    expect(estAppareilMobile()).toBe(false)
  })

  it('iPhone (UA mobile) → bloqué', () => {
    simuler({ ua: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)', platform: 'iPhone', touch: 5, coarse: true, screenW: 390 })
    expect(estAppareilMobile()).toBe(true)
  })

  it('iPad déguisé en Mac (MacIntel + tactile) → bloqué', () => {
    simuler({ platform: 'MacIntel', touch: 5, coarse: true, screenW: 1024 })
    expect(estAppareilMobile()).toBe(true)
  })

  it('petit écran physique < 1024 px → bloqué', () => {
    simuler({ screenW: 800 })
    expect(estAppareilMobile()).toBe(true)
  })

  it('écran exactement 1024 px, souris → NON bloqué (seuil strict < 1024)', () => {
    simuler({ screenW: 1024 })
    expect(estAppareilMobile()).toBe(false)
  })
})
