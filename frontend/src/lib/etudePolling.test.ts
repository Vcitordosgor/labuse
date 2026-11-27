import { afterEach, expect, it, vi } from 'vitest'
import { postEtude } from './api'

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

it('attend le résultat tant que le serveur confirme que le calcul avance', async () => {
  vi.useFakeTimers()
  let lectures = 0
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    if (url.endsWith('/async')) return Response.json({ study_id: 'EF-test', etat: 'en_cours' })
    lectures++
    return Response.json(lectures <= 451 ? { etat: 'en_cours' } : { etat: 'pret', payload: { verdict: 'À compléter' } })
  }))
  const verification = expect(postEtude({ idus: ['temoin'] })).resolves.toEqual({ verdict: 'À compléter' })
  await vi.runAllTimersAsync()
  await verification
})

it('signale un calcul introuvable après deux reprises infructueuses', async () => {
  vi.useFakeTimers()
  let lancements = 0
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    if (url.endsWith('/async')) {
      lancements++
      return Response.json({ study_id: 'EF-test', etat: 'en_cours' })
    }
    return Response.json({ etat: 'inconnu' })
  }))
  const verification = expect(postEtude({ idus: ['temoin'] })).rejects.toThrow(/perdu le suivi/)
  await vi.runAllTimersAsync()
  await verification
  expect(lancements).toBe(3)
})
