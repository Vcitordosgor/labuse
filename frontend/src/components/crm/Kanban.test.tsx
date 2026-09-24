import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Kanban } from './Kanban'
import type { PipelineEntry } from '../../lib/types'

// DA-FIX-5 P7 — test-garde : le menu « Déplacer vers… » des cartes CRM liste EXACTEMENT les colonnes
// du kanban, dans leur ordre, lues à la même source que les colonnes (meta.columns). Ajouter une
// colonne à cette source l'ajoute donc au menu. Dernière entrée : « Retirer du CRM ».
const ENTRY = {
  id: 1, idu: '974110000AB0001', status: 'cold', priority: 'normal', notes: '',
  parcel: { surface_m2: 300, commune: 'Saint-Paul' },
  prospection: {}, reminder_date: null, projet: null, courrier: null,
  proprietaire_public: null, contact_etiquette: null, contact_etiquette_at: null,
} as unknown as PipelineEntry

function mockFetch(columns: { key: string; label: string; tone?: string }[]) {
  global.fetch = vi.fn(async (url: string) => {
    const u = String(url)
    if (u.includes('/pipeline/meta')) return { ok: true, json: async () => ({ columns, priorities: [], proprietaire_statuts: [], contact_etiquettes: [] }) }
    if (u.endsWith('/pipeline')) return { ok: true, json: async () => [ENTRY] }
    if (u.includes('/events/count')) return { ok: true, json: async () => ({ unread: 0, par_parcelle: {} }) }
    return { ok: true, json: async () => ([]) }
  }) as unknown as typeof fetch
}
function renderKanban() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><Kanban /></QueryClientProvider>)
}
function options(container: HTMLElement) {
  const sel = container.querySelector('[data-crm-move]') as HTMLSelectElement
  return Array.from(sel.options).map((o) => ({ value: o.value, label: o.textContent }))
}

describe('DA-FIX-5 P7 — menu « Déplacer vers… » = les colonnes du kanban', () => {
  afterEach(() => { vi.restoreAllMocks() })

  it('liste exactement les colonnes (même source, même ordre) + « Retirer du CRM »', async () => {
    mockFetch([{ key: 'cold', label: 'À contacter' }, { key: 'warm', label: 'En discussion' }, { key: 'hot', label: 'Chaud' }])
    const { container } = renderKanban()
    await waitFor(() => expect(container.querySelector('[data-crm-move]')).not.toBeNull())
    const opts = options(container)
    expect(opts[0].label).toBe('Déplacer vers…')                       // placeholder
    expect(opts.slice(1, 4).map((o) => o.label)).toEqual(['À contacter', 'En discussion', 'Chaud'])
    expect(opts[opts.length - 1].label).toBe('Retirer du CRM')         // dernière entrée, ton danger
    expect(container.querySelector('[data-piste-courrier]')).toBeNull()   // P9 : bouton Courrier retiré
  })

  it('AJOUTER une colonne l’ajoute au menu (le menu suit meta.columns)', async () => {
    mockFetch([{ key: 'cold', label: 'À contacter' }, { key: 'warm', label: 'En discussion' }, { key: 'hot', label: 'Chaud' }, { key: 'terrain', label: 'Retour terrain' }])
    const { container } = renderKanban()
    await waitFor(() => expect(container.querySelector('[data-crm-move]')).not.toBeNull())
    const labels = options(container).map((o) => o.label)
    expect(labels).toContain('Retour terrain')                         // la 4e colonne apparaît
  })
})
