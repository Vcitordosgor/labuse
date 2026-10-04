// RECETTE-1 (F2/F3) — verrou des composants partagés des outils : EntreeParcelle (une entrée grise
// l'autre) et Reinitialiser (vide, reste dans l'outil).
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render } from '@testing-library/react'
import { EntreeParcelle } from './EntreeParcelle'
import { Reinitialiser } from '../ui/Reinitialiser'

afterEach(cleanup)

describe('RECETTE-1 F2 — EntreeParcelle grise l\'entrée non utilisée', () => {
  it('source=null : rien de grisé (les deux entrées actives)', () => {
    const { container } = render(<EntreeParcelle source={null} onPick={() => {}} />)
    expect(container.querySelector('[data-entree-carte]')?.className).not.toContain('opacity-40')
    const champ = container.querySelector('[data-entree-parcelle] > div')
    expect(champ?.className ?? '').not.toContain('opacity-40')
  })

  it('source=adresse : l\'invite carte est grisée', () => {
    const { container } = render(<EntreeParcelle source="adresse" onPick={() => {}} />)
    expect(container.querySelector('[data-entree-carte]')?.className).toContain('opacity-40')
  })

  it('source=carte : le champ adresse/IDU est grisé', () => {
    const { container } = render(<EntreeParcelle source="carte" onPick={() => {}} />)
    const champWrap = container.querySelector('[data-entree-parcelle]')?.querySelector('[aria-disabled="true"]')
    expect(champWrap?.className ?? '').toContain('opacity-40')
  })
})

describe('RECETTE-1 F3 — Reinitialiser', () => {
  it('appelle onReset au clic', () => {
    const onReset = vi.fn()
    const { getByText } = render(<Reinitialiser onReset={onReset} />)
    fireEvent.click(getByText('Réinitialiser'))
    expect(onReset).toHaveBeenCalledTimes(1)
  })
})
