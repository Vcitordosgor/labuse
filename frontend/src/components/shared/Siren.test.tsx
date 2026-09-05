// RETOURS-12 T2 — le test qui garde le composant SIREN/SIRET → Pappers.
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Siren } from './Siren'

describe('<Siren/> (T2)', () => {
  it('un SIREN (9 chiffres) devient un lien Pappers, nouvelle fenêtre, rel noopener', () => {
    render(<Siren value="552081317" />)
    const a = screen.getByRole('link') as HTMLAnchorElement
    expect(a.getAttribute('href')).toBe('https://www.pappers.fr/entreprise/552081317')
    expect(a.getAttribute('target')).toBe('_blank')
    expect(a.getAttribute('rel')).toContain('noopener')
  })

  it('un SIRET (14 chiffres) s’affiche entier mais lie sur les 9 premiers (l’entreprise)', () => {
    render(<Siren value="55208131700024" />)
    const a = screen.getByRole('link') as HTMLAnchorElement
    expect(a.getAttribute('href')).toBe('https://www.pappers.fr/entreprise/552081317')
    expect(a.textContent).toContain('55208131700024')
  })

  it('une valeur non conforme (ni 9 ni 14 chiffres) n’est JAMAIS un lien mort', () => {
    render(<Siren value="123" />)
    expect(screen.queryByRole('link')).toBeNull()
    expect(screen.getByText('123')).toBeInTheDocument()
  })

  it('valeur vide → repli « — », pas de lien', () => {
    render(<Siren value={null} />)
    expect(screen.queryByRole('link')).toBeNull()
    expect(screen.getByText('—')).toBeInTheDocument()
  })
})
