import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import ficheTemoin from '../../../../qa/m19/data/fiche.json'
import { useApp } from '../../store/useApp'
import { O5Servitudes } from '../outils/blocB'
import { Fiche } from './Fiche'

const idu = ficheTemoin.idu

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  useApp.setState({ selectedIdu: null })
})

it.each([
  { categories: ['PPR', 'Bruit', 'Bruit', 'Préemption'], attendu: 3, sdp: 0, verdict: 'exclu' },
  { categories: [], attendu: 0, sdp: null, verdict: 'ppr_partiel' },
  { categories: [], attendu: null, sdp: 45, verdict: 'modere' },
])('la fiche et l’outil affichent $attendu pour $categories', async ({ categories, attendu, sdp, verdict }) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } })
  qc.setQueryData(['fiche', idu], {
    ...ficheTemoin,
    potentiel_transformation: { ...ficheTemoin.potentiel_transformation, sdp_residuelle_m2: sdp, niveau: verdict },
  })
  const servitudes = categories.map((categorie, i) => ({ categorie, effet: 'Effet ' + i, source: 'Source' }))
  const payload = { idu, n: servitudes.length, servitudes, non_couvert: [] }
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    if (attendu != null && String(url).includes('/servitudes-invisibles/')) return { ok: true, json: async () => payload }
    return { ok: false, status: 404 }
  }))
  useApp.setState({ selectedIdu: idu })
  const { container } = render(<QueryClientProvider client={qc}>
    <Fiche idu={idu} /><div data-outil><O5Servitudes /></div>
  </QueryClientProvider>)
  await waitFor(() => {
    const tuiles = [...container.querySelectorAll('[data-bandeau-chiffres] .stat')]
    const risques = tuiles.find(el => el.textContent?.includes('PIÈGES ET RISQUES'))
    expect(risques?.querySelector('.stat-v')?.textContent).toBe(attendu == null ? '—' : String(attendu))
    const badge = container.querySelector('[data-drawer="risques"] button')?.textContent
    if (attendu == null) {
      expect(badge).toContain('Indisponible')
      expect(container.querySelector('[data-outil]')?.textContent).toContain('Servitudes indisponibles')
    } else {
      expect(badge).toContain(attendu + ' contrainte')
      expect(container.querySelector('[data-outil] .num-key')?.textContent).toBe(String(attendu))
    }
    const potentiel = tuiles.find(el => el.textContent?.includes('SDP RESTANTE'))
    expect(potentiel?.querySelector('.stat-v')?.textContent).toBe(sdp == null ? '—' : sdp + ' m²')
    if (verdict === 'ppr_partiel') expect(potentiel?.textContent).toContain('à étudier hors zone rouge')
  })
})
