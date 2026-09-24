// RECHERCHE-2 Lot 1 — test-garde : tout usage de ParcelInput SANS props de grammaires interroge
// /api/recherche/suggest avec les QUATRE familles (adresse, cadastre, propriétaire, SIREN), et un
// pick propriétaire déroule ses parcelles → onPick(idu) comme un clic carte.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, waitFor } from '@testing-library/react'
import { ParcelInput } from './ParcelInput'

let calls: string[] = []

function mockFetch() {
  calls = []
  global.fetch = vi.fn(async (url: string) => {
    const u = String(url)
    calls.push(u)
    const json = async (v: unknown) => v
    if (u.includes('/api/recherche/suggest')) {
      return { ok: true, json: () => json({
        q: 'CBO', total: 1, ms: 1, formats: '',
        groupes: [{ type: 'proprietaire', items: [{ label: 'CBO TERRITORIA', sub: '1833 parcelles', siren: '452038805' }] }],
      }) }
    }
    if (u.includes('/modules/patrimoine')) {
      return { ok: true, json: () => json({
        siren: '452038805', nom: 'CBO TERRITORIA', n_parcelles: 2, tronquee: false,
        items: [
          { idu: '97415000CM1799', commune: 'Saint-Paul', surface_m2: 812, sdp: null },
          { idu: '97411000BW0917', commune: 'Saint-Denis', surface_m2: 1300, sdp: null },
        ],
      }) }
    }
    return { ok: true, json: () => json({}) }
  }) as unknown as typeof fetch
}

describe('RECHERCHE-2 Lot 1 — ParcelInput, 4 familles par défaut', () => {
  beforeEach(() => { mockFetch() })
  afterEach(() => { vi.restoreAllMocks() })

  it('interroge le suggest avec les 4 grammaires quand aucune prop de grammaires n’est passée', async () => {
    const { container } = render(<ParcelInput onPick={() => {}} withCarte={false} />)
    const input = container.querySelector<HTMLInputElement>('[data-suggest-input]')!
    fireEvent.change(input, { target: { value: 'CBO' } })
    await waitFor(() => {
      const suggest = calls.find((u) => u.includes('/api/recherche/suggest'))
      expect(suggest).toBeTruthy()
      // les 4 familles du mandat, aucune de plus, aucune de moins
      expect(suggest).toContain('types=adresse,cadastre,proprietaire,siren')
    })
  })

  it('un pick propriétaire déroule ses parcelles → onPick(idu)', async () => {
    const picked: string[] = []
    render(<ParcelInput onPick={(idu) => picked.push(idu)} withCarte={false} />)
    const input = document.querySelector<HTMLInputElement>('[data-suggest-input]')!
    fireEvent.change(input, { target: { value: 'CBO' } })
    // la suggestion propriétaire apparaît (portal dans document.body)
    const opt = await waitFor(() => {
      const el = document.querySelector('[data-suggest-item="proprietaire"]')
      expect(el).toBeTruthy()
      return el as HTMLElement
    })
    fireEvent.mouseDown(opt)
    // le sous-panneau liste ses parcelles
    const parcelles = await waitFor(() => {
      const els = document.querySelectorAll('[data-owner-parcelle]')
      expect(els.length).toBe(2)
      return els
    })
    fireEvent.click(parcelles[1] as HTMLElement)
    expect(picked).toEqual(['97411000BW0917'])
  })

  it('onProprietaire (Scan patrimoine) court-circuite le sous-panneau', async () => {
    const owners: string[] = []
    const picked: string[] = []
    render(<ParcelInput onPick={(idu) => picked.push(idu)} onProprietaire={(s) => owners.push(s)} withCarte={false} />)
    const input = document.querySelector<HTMLInputElement>('[data-suggest-input]')!
    fireEvent.change(input, { target: { value: 'CBO' } })
    const opt = await waitFor(() => {
      const el = document.querySelector('[data-suggest-item="proprietaire"]')
      expect(el).toBeTruthy()
      return el as HTMLElement
    })
    fireEvent.mouseDown(opt)
    await waitFor(() => expect(owners).toEqual(['452038805']))
    // pas de sous-panneau parcelle, pas d'appel patrimoine
    expect(document.querySelector('[data-owner-parcelles]')).toBeFalsy()
    expect(calls.some((u) => u.includes('/modules/patrimoine'))).toBe(false)
  })
})
