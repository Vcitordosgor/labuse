import { render } from '@testing-library/react'
import { expect, it } from 'vitest'
import { ReglementPluBlock } from './blocks'

it('ouvre le barème de stationnement sur sa propre page à Saint-Pierre', () => {
  const pdf = 'https://data.geopf.fr/reglement.pdf'
  const { container } = render(<ReglementPluBlock rp={{ disclaimer: '', zones: [{
    zone: 'Ud', calibree: true, note: null, document: 'Règlement', articles: [],
    url: pdf + '#page=81', regles_valeurs: [{ cle: 'stationnement', libelle: 'Stationnement',
      valeur: '1 place / 75 m²', etat: 'texte', reference: 'Art. Ud6 · p.93', url: pdf + '#page=93' }],
  }] }} />)
  expect(container.querySelector('a[href$="#page=93"]')?.textContent).toContain('93')
})
