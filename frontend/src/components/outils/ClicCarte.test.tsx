// RECETTE-OUTILS-2 (R1) — verrou du CLIC CARTE : un clic sur une parcelle de la carte appelle
// `select(idu)` (MapView), que l'outil à parcelle ADOPTE via `selectedIdu` → le bloc EntreeParcelle
// bascule sur « adresse · Changer de parcelle ». La régression (brancher « risques » vers
// `carteOutilIdu`, non consommé) faisait « rien ne se passe » ; ce test garde l'adoption.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactElement } from 'react'
import { useApp } from '../../store/useApp'
import { O5Servitudes } from './blocB'

const renderQC = (ui: ReactElement) =>
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>{ui}</QueryClientProvider>)

beforeEach(() => {
  useApp.setState({ selectedIdu: null, module: 'risques' })
  global.fetch = vi.fn(async (url: string) => {
    const u = String(url)
    if (u.includes('/servitudes-invisibles')) return { ok: true, json: async () => ({ idu: '97408000BL0020', n: 0, synthese: '', servitudes: [], non_couvert: [] }) }
    return { ok: true, json: async () => ({}) }
  }) as unknown as typeof fetch
})
afterEach(() => { cleanup(); vi.restoreAllMocks(); useApp.setState({ selectedIdu: null }) })

describe('R1 — clic carte adopté par l\'outil Pièges et risques (O5Servitudes)', () => {
  it('sans parcelle : le bloc de recherche est affiché (barre + « cliquez la carte »)', () => {
    const { container } = renderQC(<O5Servitudes />)
    expect(container.querySelector('[data-entree-parcelle]')).toBeTruthy()
    expect(container.querySelector('[data-entree-parcelle-choisie]')).toBeNull()
  })

  it('clic carte (select → selectedIdu) : bascule sur « adresse · Changer de parcelle »', () => {
    // le clic carte, côté MapView, fait `select(idu)` → selectedIdu : on le pose avant le montage,
    // l'outil l'adopte (idu initialisé à selectedIdu) et montre la ligne choisie.
    useApp.setState({ selectedIdu: '97408000BL0020' })
    const { container } = renderQC(<O5Servitudes />)
    expect(container.querySelector('[data-entree-parcelle-choisie]')).toBeTruthy()
    expect(container.querySelector('[data-entree-parcelle]')).toBeNull()   // plus le bloc de recherche
  })
})
