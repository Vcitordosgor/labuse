import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useApp } from '../../store/useApp'
import { M09 } from './ModulePanel'

// Mandat COURRIER — service d'envoi en 3 étapes : destinataires → rédaction → DEMANDER l'envoi à
// LABUSE (confirmation + timeline de statut). Import Assemblage via le prefill multi-parcelles.
const FICHE = { commune: 'Saint-Denis', surface_m2: 1625 }
const DEMANDE = { ok: true, id: 42, ts: 't', n: 1, communes: 'Saint-Denis ×1', statut: 'demande' }

function mockFetch() {
  global.fetch = vi.fn(async (url: string, init?: RequestInit) => {
    const u = String(url)
    if (u.includes('/courrier/demande') && init?.method === 'POST') return { ok: true, json: async () => DEMANDE }
    if (u.includes('/courrier/demandes')) return { ok: true, json: async () => ({ demandes: [] }) }
    if (u.includes('/parcels/')) return { ok: true, json: async () => FICHE }
    return { ok: true, json: async () => ({}) }
  }) as unknown as typeof fetch
}
function renderTool() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><M09 /></QueryClientProvider>)
}

describe('COURRIER — service d\'envoi (3 étapes)', () => {
  beforeEach(() => {
    mockFetch()
    // import « en un geste » depuis Assemblage : le prefill multi-parcelles amorce les destinataires.
    useApp.setState({ courrierPrefillIdus: ['97411000BZ1065'], courrierPrefill: null, selectedIdu: null, msel: [] })
  })
  afterEach(() => { vi.restoreAllMocks(); useApp.setState({ courrierPrefillIdus: null }) })

  it('① le prefill Assemblage amorce un destinataire (chip)', async () => {
    renderTool()
    await waitFor(() => expect(document.querySelectorAll('[data-courrier-dest]').length).toBe(1))
    expect(screen.getByText('BZ 1065')).toBeTruthy()   // idu court dans la chip
  })

  it('parcours complet → « Demander l\'envoi » → confirmation + timeline', async () => {
    renderTool()
    await waitFor(() => expect(document.querySelectorAll('[data-courrier-dest]').length).toBe(1))
    // ① → ②
    fireEvent.click(document.querySelector('[data-courrier-next]')!)
    // ② modèles présents (dont « Approche standard »), corps par défaut rempli
    expect(document.querySelector('[data-courrier-modele="standard"]')).toBeTruthy()
    expect((document.querySelector('[data-courrier-texte]') as HTMLTextAreaElement).value.length).toBeGreaterThan(10)
    // ② → ③
    fireEvent.click(document.querySelector('[data-courrier-next]')!)
    // ③ demander l'envoi
    fireEvent.click(document.querySelector('[data-courrier-demander]')!)
    await waitFor(() => expect(document.querySelector('[data-courrier-confirm]')).toBeTruthy())
    expect(screen.getByText(/Demande transmise/)).toBeTruthy()
    expect(screen.getByText('Demandé')).toBeTruthy()   // timeline, 1er statut actif
  })

  it('③ aperçu PDF de relecture disponible (secondaire)', async () => {
    renderTool()
    await waitFor(() => expect(document.querySelectorAll('[data-courrier-dest]').length).toBe(1))
    fireEvent.click(document.querySelector('[data-courrier-next]')!)   // → ②
    fireEvent.click(document.querySelector('[data-courrier-next]')!)   // → ③
    expect(document.querySelector('[data-courrier-pdf]')).toBeTruthy()
  })
})
