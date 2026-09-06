// CIRCUIT-P (lot 2.3) — zéro problème → « Tout coule. » ; chaque type de ligne rend son verbe et
// mène à sa cible.
import { fireEvent, render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { Resume } from './Resume'
import type { CircuitData } from './types'

const kpis = [
  { valeur: 10, sur: 12, libelle: 'réservoirs à jour et vérifiés' },
  { valeur: 100, sur: 120, libelle: 'robinets sans rien à signaler' },
  { valeur: 88, libelle: 'chiffres définis une fois' },
  { valeur: 'q_v11_m137', candidat: null, libelle: 'run servi' },
]
const reste = { reservoirs: 12, robinets: 120, chiffres: 88 }

const donnees = (groupes: any[]): CircuitData => ({
  resume: { total: groupes.reduce((a, g) => a + g.lignes.length, 0), kpis, groupes, reste },
  dernier_controle: null,
} as any)

describe('Resume', () => {
  it('zéro problème → « Tout coule. »', () => {
    const g = [
      { titre: 'À faire, un geste de toi', lignes: [] },
      { titre: 'À corriger, un mandat pour CC', lignes: [] },
      { titre: 'À décider, quand tu veux', lignes: [] },
    ]
    const { getByText, getAllByText } = render(<Resume data={donnees(g)} onCible={() => {}} />)
    expect(getByText('Tout coule.')).toBeInTheDocument()
    expect(getAllByText('Rien.').length).toBe(3)   // un « Rien. » par groupe vide
  })

  it('chaque ligne rend son verbe et clique vers sa cible', () => {
    const g = [
      { titre: 'À faire, un geste de toi', lignes: [
        { n: 1, couleur: 'rouge', titre: 'version en quarantaine', phrase: 'x', verbe: 'Décider', cible: { type: 'reservoir', ids: [3] } },
        { n: 2, couleur: 'ambre', titre: 'réservoir plein, à injecter', phrase: 'y', verbe: 'Injecter', cible: { type: 'reservoir', ids: [4, 5] } },
      ] },
      { titre: 'À corriger, un mandat pour CC', lignes: [
        { n: 4, couleur: 'rouge', titre: 'fuites mesurées', phrase: 'z', verbe: 'Voir', cible: { type: 'robinet', ids: ['a'] } },
      ] },
      { titre: 'À décider, quand tu veux', lignes: [] },
    ]
    const onCible = vi.fn()
    const { getByText } = render(<Resume data={donnees(g)} onCible={onCible} />)
    expect(getByText(/choses à regarder/)).toBeInTheDocument()   // titre : « 3 choses à regarder »
    expect(getByText('Décider →')).toBeInTheDocument()
    expect(getByText('Injecter →')).toBeInTheDocument()
    expect(getByText('Voir →')).toBeInTheDocument()
    fireEvent.click(getByText('Décider →'))
    expect(onCible).toHaveBeenCalledWith({ type: 'reservoir', ids: [3] })
  })
})
