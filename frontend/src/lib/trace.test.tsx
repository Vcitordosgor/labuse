// CIRCUIT-1 lot 7.2 — LE test snapshot du traçage : éteint, le rendu est STRICTEMENT
// identique aux enfants (aucun wrapper) ; allumé, l'étiquette data-chiffre apparaît.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { useApp } from '../store/useApp'
import { Trace } from './trace'

const qc = new QueryClient()
const rend = (ui: React.ReactElement) =>
  render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)

describe('Trace (mode traçage)', () => {
  it('éteint : rendu strictement identique aux enfants (snapshot)', () => {
    useApp.setState({ tracage: false })
    const avec = rend(<Trace id="prix_ancien_median_eur_m2"><b>4 500 €/m²</b></Trace>)
    const sans = rend(<b>4 500 €/m²</b>)
    expect(avec.container.innerHTML).toBe(sans.container.innerHTML)
    expect(avec.container.querySelector('[data-chiffre]')).toBeNull()
  })

  it("allumé : le nombre porte son chiffre_id (étiquette jaune, clic → tiroir)", () => {
    useApp.setState({ tracage: true })
    const { container } = rend(<Trace id="taux_lls_pct"><span>23 %</span></Trace>)
    const tag = container.querySelector('[data-chiffre]')
    expect(tag).not.toBeNull()
    expect(tag!.getAttribute('data-chiffre')).toBe('taux_lls_pct')
    useApp.setState({ tracage: false })   // ne pas polluer les autres tests
  })
})
