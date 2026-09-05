// CIRCUIT-2 lot 1.7 — portée `projet` (DA v3) : une hypothèse SAISIE par le client s'affiche
// en AMBRE (data-saisie-client + classes amber) ; vide (défaut serveur en placeholder), le
// rendu reste neutre — on distingue d'un coup d'œil ce qui vient du client.
import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { HypInput } from './primitives'

describe('HypInput (saisie client — ambre)', () => {
  it('vide : rendu neutre, pas de marquage saisie client', () => {
    const { container } = render(
      <HypInput label="Coût construction" value={null} onChange={() => {}} suffix="€/m²" />)
    const input = container.querySelector('input')!
    expect(input.hasAttribute('data-saisie-client')).toBe(false)
    expect(input.className).not.toContain('text-amber')
  })

  it('saisie : marquage data-saisie-client + ambre (bord et texte)', () => {
    const { container } = render(
      <HypInput label="Coût construction" value={2400} onChange={() => {}} suffix="€/m²" />)
    const input = container.querySelector('input')!
    expect(input.getAttribute('data-saisie-client')).toBe('true')
    expect(input.className).toContain('text-amber')
    expect(container.innerHTML).toContain('border-amber')
  })
})
