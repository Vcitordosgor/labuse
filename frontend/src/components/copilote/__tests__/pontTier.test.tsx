// FIX-PONT-TIER — « Voir sur la carte » depuis une réponse du Copilote arme `analyseLabuse`
// SEULEMENT pour une question par TIER. Sinon `tiersParam` (api.ts), en factuel, ignore
// `filters.tiers` et sert la trame entière → la carte contredirait le compte annoncé. Le cas
// NON-TIER (signaux/surface) doit rester FACTUEL (analyseLabuse=false) — parade M137-I intacte.
import { fireEvent, render } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { ReponseInline } from '../ReponseInline'
import { EMPTY_FILTERS, useApp } from '../../../store/useApp'
import type { CopiloteV2Reponse } from '../../../lib/api'

const rep = (filtres: Record<string, unknown>): CopiloteV2Reponse => ({
  text: 'réponse', intent: 'QUESTION',
  carte_filtre: { commune: 'Saint-Paul', filtres, libelle: 'les parcelles à Saint-Paul' },
} as unknown as CopiloteV2Reponse)

const filtres = () => useApp.getState().filters

beforeEach(() => useApp.setState({ filters: { ...EMPTY_FILTERS } }))
afterEach(() => useApp.setState({ filters: { ...EMPTY_FILTERS } }))

function voirCarte(v2: CopiloteV2Reponse) {
  const { container } = render(<ReponseInline v2={v2} />)
  fireEvent.click(container.querySelector('[data-reponse-carte]')!)
}

describe('FIX-PONT-TIER — ouvrirCarte arme analyseLabuse par tier', () => {
  it('question PAR TIER → analyseLabuse armé, tiers + commune posés', () => {
    voirCarte(rep({ tiers: ['brulante'] }))
    expect(filtres().analyseLabuse).toBe(true)
    expect(filtres().tiers).toEqual(['brulante'])
    expect(filtres().communes).toEqual(['Saint-Paul'])
  })

  it('réserve foncière (tier canonique) → armé aussi', () => {
    voirCarte(rep({ tiers: ['reserve_fonciere'] }))
    expect(filtres().analyseLabuse).toBe(true)
    expect(filtres().tiers).toEqual(['reserve_fonciere'])
  })

  it('plusieurs tiers (opportunités) → armé, les deux posés', () => {
    voirCarte(rep({ tiers: ['brulante', 'chaude'] }))
    expect(filtres().analyseLabuse).toBe(true)
    expect(filtres().tiers).toEqual(['brulante', 'chaude'])
  })

  it('question NON-TIER (signaux) → reste FACTUEL (analyseLabuse=false), M137-I intact', () => {
    voirCarte(rep({ signaux: ['procedure'] }))
    expect(filtres().analyseLabuse).toBe(false)
    expect(filtres().signaux).toEqual(['procedure'])
    expect(filtres().tiers).toEqual([])
  })

  it('question NON-TIER (surface) → reste FACTUEL', () => {
    voirCarte(rep({ surfaceMin: 1000 }))
    expect(filtres().analyseLabuse).toBe(false)
    expect(filtres().surfaceMin).toBe(1000)
  })
})
