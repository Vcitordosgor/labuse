import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useApp } from '../../store/useApp'
import { M10 } from './ModulePanel'

// Mandat PIEGES — « Un lot » : liste de chips, plus d'export PDF, âge_dirigeant masqué sur un
// particulier, et pont Courrier (« Préparer les courriers (n) » via courrierPrefillIdus).
const DILIGENCE = {
  n_demandes: 2, n_trouvees: 2, non_couvert: [],
  items: [
    { idu: '97411000BZ1065', commune: 'Saint-Denis', surface_m2: 1625, statut: 'neutre', tier_v2: 'neutre',
      etage0: false, risque: 30, proprio: { type: 'particulier' },
      checklist: [
        { layer: 'age_dirigeant', severity: 'faible', result: 'UNKNOWN', detail: 'Âge dirigeant inconnu (PM sans dirigeant physique daté).' },
        { layer: 'risques', severity: 'moyen', result: 'SOFT_FLAG', detail: 'Zone bleue PPR inondation' },
      ] },
    { idu: '97415000CT1837', commune: 'Saint-Paul', surface_m2: 900, statut: 'neutre', tier_v2: 'neutre',
      etage0: false, risque: 40, proprio: { type: 'personne_morale', denomination: 'SCI X', siren: '123' },
      checklist: [
        { layer: 'age_dirigeant', severity: 'faible', result: 'UNKNOWN', detail: 'Âge dirigeant inconnu (PM sans dirigeant physique daté).' },
      ] },
  ],
}

function mockFetch() {
  global.fetch = vi.fn(async (url: string) => {
    if (String(url).includes('/duediligence')) return { ok: true, json: async () => DILIGENCE }
    return { ok: true, json: async () => ({}) }
  }) as unknown as typeof fetch
}
function renderM10() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><M10 /></QueryClientProvider>)
}
// construit le lot via le collage (fiable en jsdom), puis analyse.
function batirEtAnalyser() {
  const paste = document.querySelector('[data-diligence-paste]') as HTMLTextAreaElement
  fireEvent.change(paste, { target: { value: '97411000BZ1065\n97415000CT1837' } })
  fireEvent.click(document.querySelector('[data-diligence-add]')!)
  fireEvent.click(document.querySelector('[data-diligence-analyser]')!)
}

describe('PIEGES — « Un lot »', () => {
  beforeEach(() => { mockFetch(); useApp.setState({ courrierPrefillIdus: null, module: 'risques' }) })
  afterEach(() => { vi.restoreAllMocks(); useApp.setState({ courrierPrefillIdus: null, module: null }) })

  it('la barre/collage construit un lot de chips', async () => {
    renderM10()
    const paste = document.querySelector('[data-diligence-paste]') as HTMLTextAreaElement
    fireEvent.change(paste, { target: { value: '97411000BZ1065\n97415000CT1837' } })
    fireEvent.click(document.querySelector('[data-diligence-add]')!)
    expect(document.querySelectorAll('[data-diligence-chip]')).toHaveLength(2)
  })

  it('âge_dirigeant masqué sur un particulier, gardé sur une PM ; plus aucun PDF', async () => {
    renderM10()
    batirEtAnalyser()
    await waitFor(() => expect(document.querySelectorAll('[data-diligence-item]').length).toBe(2))
    // 2 items ont un age_dirigeant en cascade, mais seul celui de la PM s'affiche
    expect(screen.getAllByText(/Âge dirigeant inconnu/)).toHaveLength(1)
    // export PDF retiré
    expect(screen.queryByText(/⬇ PDF/)).toBeNull()
  })

  it('pont Courrier : « Préparer les courriers » pose courrierPrefillIdus + ouvre l\'outil', async () => {
    renderM10()
    batirEtAnalyser()
    const btn = await waitFor(() => { const b = document.querySelector('[data-diligence-courrier]'); if (!b) throw new Error('no btn'); return b as HTMLElement })
    expect(btn.textContent).toContain('(2)')
    fireEvent.click(btn)
    expect(useApp.getState().courrierPrefillIdus).toEqual(['97411000BZ1065', '97415000CT1837'])
    expect(useApp.getState().module).toBe('courriers')
  })
})
