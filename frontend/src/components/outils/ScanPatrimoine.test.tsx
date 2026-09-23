import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ScanPatrimoine } from './ScanPatrimoine'
import { useApp } from '../../store/useApp'

// SCAN-PATRIMOINE-1 (écart 1) — la recherche par NOM qui matche PLUSIEURS sociétés affiche la liste
// (nom · SIREN · nb parcelles) et laisse choisir ; plus d'auto-sélection du plus gros en silence.
const DEUX = [
  { siren: '111111111', nom: 'SCI DUPONT GRANDE', n: 120 },
  { siren: '222222222', nom: 'SCI DUPONT PETITE', n: 8 },
]
const UNE = [{ siren: '333333333', nom: 'SCI UNIQUE', n: 5 }]
const NOMS: Record<string, string> = {
  '111111111': 'SCI DUPONT GRANDE', '222222222': 'SCI DUPONT PETITE', '333333333': 'SCI UNIQUE',
}

function mockFetch(searchResults: { siren: string; nom: string; n: number }[]) {
  global.fetch = vi.fn(async (url: string) => {
    const u = String(url)
    if (u.includes('/patrimoine/search')) return { ok: true, json: async () => searchResults }
    if (u.includes('/patrimoine')) {
      // le portefeuille : on renvoie la raison sociale du SIREN demandé (comme la vraie base)
      const siren = new URL(u, 'http://x').searchParams.get('siren') ?? ''
      return { ok: true, json: async () => ({ siren, nom: NOMS[siren] ?? '?', n_parcelles: 1, total: 1, items: [] }) }
    }
    return { ok: true, json: async () => ({ features: [] }) }   // BAN autocomplete / repli adresse : rien
  }) as unknown as typeof fetch
}
function renderScan() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><ScanPatrimoine /></QueryClientProvider>)
}
function chercher(container: HTMLElement, texte: string) {
  const input = container.querySelector('[data-scan-search]') as HTMLInputElement
  fireEvent.change(input, { target: { value: texte } })
  fireEvent.keyDown(input, { key: 'Enter' })
}

describe('SCAN-PATRIMOINE-1 — choix quand plusieurs sociétés matchent', () => {
  beforeEach(() => { useApp.setState({ m02Prefill: null, veilleFocusSiren: null }) })
  afterEach(() => { vi.restoreAllMocks() })

  it('plusieurs résultats → liste nom · SIREN · nb parcelles, AUCUNE auto-sélection', async () => {
    mockFetch(DEUX)
    const { container } = renderScan()
    chercher(container, 'SCI DUPONT')

    await waitFor(() => expect(container.querySelector('[data-scan-candidats]')).not.toBeNull())
    // les deux candidats sont proposés, avec nb parcelles ET sans que le gros soit déjà retenu
    expect(container.querySelector('[data-scan-candidat="111111111"]')).not.toBeNull()
    expect(container.querySelector('[data-scan-candidat="222222222"]')).not.toBeNull()
    expect(container.textContent).toContain('SCI DUPONT GRANDE')
    expect(container.textContent).toContain('SCI DUPONT PETITE')
    expect(container.textContent).toContain('120 parcelles')
    expect(container.textContent).toContain('8 parcelles')
    expect(container.querySelector('[data-scan-owner]')).toBeNull()   // rien d'auto-sélectionné
  })

  it('on peut retenir la PLUS PETITE (pas le plus gros par défaut)', async () => {
    mockFetch(DEUX)
    const { container } = renderScan()
    chercher(container, 'SCI DUPONT')
    await waitFor(() => expect(container.querySelector('[data-scan-candidat="222222222"]')).not.toBeNull())
    fireEvent.click(container.querySelector('[data-scan-candidat="222222222"]') as HTMLElement)

    // état 2 : l'encart propriétaire s'affiche pour la société CHOISIE, la liste de choix disparaît
    await waitFor(() => expect(container.querySelector('[data-scan-owner]')).not.toBeNull())
    expect(container.querySelector('[data-scan-candidats]')).toBeNull()
    const owner = container.querySelector('[data-scan-owner]') as HTMLElement
    expect(owner.textContent).toContain('SCI DUPONT PETITE')
    expect(owner.textContent).not.toContain('SCI DUPONT GRANDE')   // le gros n'a PAS été retenu
  })

  it('un seul résultat → sélection directe, pas de liste de choix', async () => {
    mockFetch(UNE)
    const { container } = renderScan()
    chercher(container, 'SCI UNIQUE')

    await waitFor(() => expect(container.querySelector('[data-scan-owner]')).not.toBeNull())
    expect(container.querySelector('[data-scan-candidats]')).toBeNull()
    expect((container.querySelector('[data-scan-owner]') as HTMLElement).textContent).toContain('SCI UNIQUE')
  })
})
