import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { O6Comparateur } from './blocB'

// Mandat COMMUNES — le tableau des 24 communes : en-têtes lisibles (fin de « VÉLO »), étiquettes
// HONNÊTES (permis = 5 ans, pas « 12 m »), légende permanente, réconciliation € ancien, affordance
// de clic, meilleure valeur en vert. Ces contrats sont sensibles à la doctrine (jamais un faux label).
const COMMUNES = {
  communes: [
    { insee: '97411', commune: 'Saint-Denis', stock: 90, velocite: 12, permis: 3000, deficit_sru: 6.7, prix_ancien: 2800, prix_neuf: 4100 },
    { insee: '97415', commune: 'Saint-Paul', stock: 318, velocite: 9, permis: 1967, deficit_sru: 6.7, prix_ancien: 4278, prix_neuf: 4730 },
    { insee: '97410', commune: 'Saint-Pierre', stock: 152, velocite: 8, permis: 1831, deficit_sru: 2.1, prix_ancien: 3015, prix_neuf: 4258 },
  ],
}

function renderO6() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <O6Comparateur onSelect={() => {}} />
    </QueryClientProvider>,
  )
}

describe('COMMUNES — O6Comparateur (table des 24 communes)', () => {
  beforeEach(() => {
    global.fetch = vi.fn(async () => ({ ok: true, json: async () => COMMUNES })) as unknown as typeof fetch
  })
  afterEach(() => vi.restoreAllMocks())

  it('« VÉLO » n\'existe plus ; en-têtes lisibles + étiquette permis HONNÊTE (5 ans, pas 12 m)', async () => {
    renderO6()
    await screen.findByText('Saint-Paul')
    expect(screen.queryByText(/vélo/i)).toBeNull()
    expect(screen.getByText(/Instruction \(mois\)/)).toBeTruthy()
    expect(screen.getByText(/Permis \(5 ans\)/)).toBeTruthy()      // la donnée est un cumul 5 ans
    expect(screen.getByText(/Déficit SRU \(pts\)/)).toBeTruthy()   // en-tête (la légende dit « Déficit SRU » sans unité)
  })

  it('légende permanente + réconciliation € ancien (commune entière)', async () => {
    renderO6()
    await screen.findByText('Saint-Paul')
    const leg = screen.getByText('Légende :').closest('[data-o6-legende]') as HTMLElement
    expect(leg).toBeTruthy()
    expect(leg.textContent).toContain('Permis 5 ans')
    expect(leg.textContent).toContain('commune entière')          // distingue du prix LOCAL de la fiche
  })

  it('OUTILS-1 B4 — « Fiche → » PERMANENT sur chaque ligne (plus au survol)', async () => {
    renderO6()
    await screen.findByText('Saint-Paul')
    expect(screen.getAllByText('Fiche →')).toHaveLength(3)
    // RETOURS-13 R11 — action SECONDAIRE : jaune opaque au survol (classe hover-jaune)
    for (const el of screen.getAllByText('Fiche →')) expect(el.className).toContain('hover-jaune')
  })

  it('meilleure valeur en vert : stock MAX (318) et instruction MIN (8)', async () => {
    const { container } = renderO6()
    await screen.findByText('Saint-Paul')
    const bestStock = [...container.querySelectorAll('[data-o6-cell="stock"]')].find((el) => el.textContent === '318')
    expect(bestStock?.className).toContain('text-mint')
    const bestInstr = [...container.querySelectorAll('[data-o6-cell="velocite"]')].find((el) => el.textContent === '8')
    expect(bestInstr?.className).toContain('text-mint')
    // les prix restent NEUTRES (pas de faux signal bon/mauvais)
    const prix = [...container.querySelectorAll('[data-o6-cell="prix_ancien"]')]
    expect(prix.every((el) => !el.className.includes('text-mint'))).toBe(true)
  })
})
