// RECETTE-1 (F2/F3) — verrou des composants partagés des outils : EntreeParcelle (une entrée grise
// l'autre) et Reinitialiser (vide, reste dans l'outil).
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactElement } from 'react'
import { EntreeParcelle } from './EntreeParcelle'
import { Reinitialiser } from '../ui/Reinitialiser'

afterEach(cleanup)

// RECETTE-OUTILS-1 (T4/T5) — EntreeParcelle résout l'adresse de la parcelle choisie (useQuery) : le
// rendu a désormais besoin d'un QueryClientProvider, comme dans l'app.
const qc = () => new QueryClient({ defaultOptions: { queries: { retry: false } } })
const renderQC = (ui: ReactElement) => render(<QueryClientProvider client={qc()}>{ui}</QueryClientProvider>)

describe('RECETTE-1 F2 — EntreeParcelle grise l\'entrée non utilisée', () => {
  it('source=null : rien de grisé (les deux entrées actives)', () => {
    const { container } = renderQC(<EntreeParcelle source={null} onPick={() => {}} />)
    expect(container.querySelector('[data-entree-carte]')?.className).not.toContain('opacity-40')
    const champ = container.querySelector('[data-entree-parcelle] > div')
    expect(champ?.className ?? '').not.toContain('opacity-40')
  })

  it('source=adresse : l\'invite carte est grisée', () => {
    const { container } = renderQC(<EntreeParcelle source="adresse" onPick={() => {}} />)
    expect(container.querySelector('[data-entree-carte]')?.className).toContain('opacity-40')
  })

  it('source=carte : le champ adresse/IDU est grisé', () => {
    const { container } = renderQC(<EntreeParcelle source="carte" onPick={() => {}} />)
    const champWrap = container.querySelector('[data-entree-parcelle]')?.querySelector('[aria-disabled="true"]')
    expect(champWrap?.className ?? '').toContain('opacity-40')
  })

  it('RECETTE-OUTILS-1 (T5) : picked → ligne « Changer de parcelle », plus de champ de recherche', () => {
    const onChanger = vi.fn()
    const { container, getByText } = renderQC(
      <EntreeParcelle source="adresse" onPick={() => {}} picked="97411000AD0213" adresse="14 Rue de Nice, 97400 Saint-Denis" onChanger={onChanger} />)
    expect(container.querySelector('[data-entree-parcelle-choisie]')).toBeTruthy()
    expect(container.querySelector('[data-entree-parcelle]')).toBeNull()
    fireEvent.click(getByText('Changer de parcelle'))
    expect(onChanger).toHaveBeenCalledTimes(1)
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
