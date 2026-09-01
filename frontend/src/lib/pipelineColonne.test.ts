// CONNEXIONS-2 Lot 3 (KO-8) — « Ajouter au CRM » transmet la COLONNE choisie au back (plus
// d'imposition silencieuse de la colonne par défaut). Ce test échoue si `addToPipeline` n'envoie
// pas le `status` fourni.
import { afterEach, describe, expect, it, vi } from 'vitest'
import { addToPipeline } from './api'

function capture() {
  const calls: Array<{ url: string; body: unknown }> = []
  global.fetch = vi.fn(async (url: string, init?: RequestInit) => {
    calls.push({ url: String(url), body: init?.body ? JSON.parse(String(init.body)) : null })
    return { ok: true, status: 200, json: async () => ({ ok: true, already: false, entry: {} }) }
  }) as unknown as typeof fetch
  return calls
}

describe('addToPipeline — colonne CRM choisie (KO-8)', () => {
  afterEach(() => vi.restoreAllMocks())

  it('transmet le status quand une colonne est choisie', async () => {
    const calls = capture()
    await addToPipeline('97411000BZ1065', 'a_contacter')
    expect(calls[0].url).toContain('/pipeline')
    expect(calls[0].body).toEqual({ idu: '97411000BZ1065', status: 'a_contacter' })
  })

  it('sans colonne : n\'envoie que l\'IDU (le back applique la 1re colonne)', async () => {
    const calls = capture()
    await addToPipeline('97411000BZ1065')
    expect(calls[0].body).toEqual({ idu: '97411000BZ1065' })
  })
})
