// CONNEXIONS-2 Lot 8 (C1) — la barre du bandeau résout IDU · SIREN/SIRET · nom de propriétaire ·
// projet du compte · commune · adresse. Nom & SIREN ouvrent Scan patrimoine à l'ÉTAT 2 (propriétaire
// posé) ; un projet ouvre le projet. Échoue sur l'ancien code (SIREN/nom/projet → toast « rien trouvé »).
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useApp } from '../../store/useApp'
import { Omnibox } from './Header'

function mockFetch() {
  global.fetch = vi.fn(async (url: string) => {
    const u = String(url)
    const json = async (v: unknown) => v
    if (u.includes('/modules/patrimoine/search')) {
      // un propriétaire n'est renvoyé que pour un NOM d'entreprise (contient « SCI »).
      const owner = u.toLowerCase().includes('sci') ? [{ siren: '123456789', nom: 'SCI TEST', n: 4 }] : []
      return { ok: true, json: () => json(owner) }
    }
    if (u.includes('/projets')) return { ok: true, json: () => json([{ id: 7, nom: 'Mon projet test', statut: 'actif', counts: {} }]) }
    if (u.includes('/communes')) return { ok: true, json: () => json([{ insee: '97415', commune: 'Saint-Paul' }]) }
    if (u.includes('/adresses/autocomplete')) return { ok: true, json: () => json({ features: [] }) }
    if (u.includes('/parcels/search')) return { ok: true, json: () => json([]) }
    return { ok: true, json: () => json({}) }
  }) as unknown as typeof fetch
}

function renderOmnibox() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><Omnibox /></QueryClientProvider>)
}

async function chercher(container: HTMLElement, texte: string) {
  const input = container.querySelector<HTMLInputElement>('[data-omnibox]')!
  fireEvent.change(input, { target: { value: texte } })
  fireEvent.keyDown(input, { key: 'Enter' })
}

describe('CONNEXIONS-2 Lot 8 — omnibox multi-type', () => {
  beforeEach(() => {
    mockFetch()
    useApp.setState({ commune: null, module: null, m02Prefill: null, openProjet: null })
  })
  afterEach(() => { vi.restoreAllMocks(); useApp.setState({ module: null, m02Prefill: null, openProjet: null }) })

  it('un SIREN ouvre Scan patrimoine à l\'état 2 (propriétaire posé)', async () => {
    const { container } = renderOmnibox()
    await chercher(container, '123456789')
    await waitFor(() => expect(useApp.getState().module).toBe('patrimoine'))
    expect(useApp.getState().m02Prefill).toBe('123456789')
  })

  it('un NOM de propriétaire ouvre Scan patrimoine à l\'état 2', async () => {
    const { container } = renderOmnibox()
    await chercher(container, 'SCI TEST')
    await waitFor(() => expect(useApp.getState().module).toBe('patrimoine'))
    expect(useApp.getState().m02Prefill).toBe('123456789')
  })

  it('un nom de PROJET ouvre le projet', async () => {
    const { container } = renderOmnibox()
    await chercher(container, 'Mon projet test')
    await waitFor(() => expect(useApp.getState().openProjet?.id).toBe(7))
    expect(useApp.getState().module).toBeNull()
  })

  it('une COMMUNE pose le périmètre (pas Scan patrimoine)', async () => {
    const { container } = renderOmnibox()
    await chercher(container, 'Saint-Paul')
    await waitFor(() => expect(useApp.getState().filters.communes).toContain('Saint-Paul'))
    expect(useApp.getState().module).toBeNull()
  })
})
