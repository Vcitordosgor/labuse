// DOCS-FIX-1 (Lot 3, P3/P4) — le hook d'ouverture propre : on NE window.open JAMAIS une URL crue.
// Succès → ouverture d'un blob ; 422/404/500 → message FR (jamais de JSON brut, jamais d'onglet blanc),
// avec les manques nommés quand le back les fournit (422).
import { act, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useOuvrirDocument } from './ouvrirDocument'

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300, status,
    json: () => Promise.resolve(body),
    blob: () => Promise.resolve(new Blob(['pdf'], { type: 'application/pdf' })),
  } as unknown as Response)
}

afterEach(() => vi.restoreAllMocks())

describe('useOuvrirDocument (P3/P4)', () => {
  it('succès 200 : ouvre un blob, aucune erreur', async () => {
    vi.stubGlobal('fetch', mockFetch(200, {}))
    const createObjectURL = vi.fn(() => 'blob:x')
    vi.stubGlobal('URL', { ...URL, createObjectURL } as unknown as typeof URL)
    const open = vi.spyOn(window, 'open').mockReturnValue(null)
    const onErr = vi.fn()
    const { result } = renderHook(() => useOuvrirDocument(onErr))
    let ok: boolean | undefined
    await act(async () => { ok = await result.current.ouvrir('/gabarit/X.pdf', 'gabarit') })
    expect(ok).toBe(true)
    expect(open).toHaveBeenCalledWith('blob:x', '_blank', 'noopener')
    expect(onErr).not.toHaveBeenCalled()
  })

  it('422 : NOMME les manques, n’ouvre aucun onglet', async () => {
    vi.stubGlobal('fetch', mockFetch(422, { detail: { manques: [{ libelle: 'régime de TVA' }, { libelle: 'programme' }] } }))
    const open = vi.spyOn(window, 'open').mockReturnValue(null)
    const onErr = vi.fn()
    const { result } = renderHook(() => useOuvrirDocument(onErr))
    let ok: boolean | undefined
    await act(async () => { ok = await result.current.ouvrir('/financier/X.pdf', 'bilan') })
    expect(ok).toBe(false)
    expect(open).not.toHaveBeenCalled()
    expect(onErr).toHaveBeenCalledWith(expect.stringContaining('régime de TVA'))
    expect(onErr).toHaveBeenCalledWith(expect.stringContaining('programme'))
  })

  it('404 : message FR lisible (pas de JSON), aucun onglet', async () => {
    vi.stubGlobal('fetch', mockFetch(404, { detail: 'Parcelle … inconnue de l’analyse en cours.' }))
    const open = vi.spyOn(window, 'open').mockReturnValue(null)
    const { result } = renderHook(() => useOuvrirDocument())
    let ok: boolean | undefined
    await act(async () => { ok = await result.current.ouvrir('/dossier/X.pdf', 'dossier') })
    expect(ok).toBe(false)
    expect(open).not.toHaveBeenCalled()
    expect(result.current.erreur).toContain('inconnue')
  })

  it('500 : message technique FR, aucun onglet', async () => {
    vi.stubGlobal('fetch', mockFetch(500, { detail: { erreur: 'erreur_technique' } }))
    const open = vi.spyOn(window, 'open').mockReturnValue(null)
    const { result } = renderHook(() => useOuvrirDocument())
    await act(async () => { await result.current.ouvrir('/apporteur/X.pdf', 'apporteur') })
    expect(open).not.toHaveBeenCalled()
    expect(result.current.erreur).toMatch(/erreur technique|pas pu être généré/i)
  })
})
