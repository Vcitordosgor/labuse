import { describe, expect, it } from 'vitest'
import { filtersFromHash, filtersToHash } from './filters'
import { EMPTY_FILTERS, type Filters } from '../store/useApp'

// M55-D phase 2 (Q2) : la persistance doit couvrir TOUS les champs et rester rétro-compatible.
describe('filters URL persistence (M55-D)', () => {
  it('round-trips EVERY field (tri + mode)', () => {
    const f: Filters = {
      ...EMPTY_FILTERS,
      tiers: ['brulante', 'chaude'],
      scoreMin: 80, surfaceMin: 1000, surfaceMax: 5000, sdpMin: 300, sdpMax: 2000,
      capaciteMin: 10, multMin: 2, rangMax: 100, budgetMax: 200000,
      chargeMin: 1000, chargeMax: 90000, prixMarcheMin: 100, prixMarcheMax: 900, caMin: 1_000_000,
      evenement: true, veille: true, horsCopro: true, personneMorale: true, sousDensite: true,
      renouvellement: true, divisionOr: true, npnru: true, adresseAbsente: true,
      marcheFiable: true, modeBRentable: true,
      flags: ['pente', 'ravine'], flagsExclus: ['icpe'], communes: ['Saint-Paul'],
      zonagePlu: ['U', 'AU'], constructibilite: ['constructible'], etatSol: ['nu'],
      zonePlu: ['UA'], proprietaireType: ['pm'], etatSociete: ['radiee'], copro: ['sans'],
      analyseLabuse: false,
    }
    const hash = filtersToHash(f, null)
    const back = { ...EMPTY_FILTERS, ...(filtersFromHash(hash)!.filters) }
    expect(back).toEqual(f)
  })

  it('defaults analyseLabuse to true when absent (old link)', () => {
    // ancien lien : uniquement une surface, pas de clé `al`
    const back = filtersFromHash('#f=1&smin=1500')!.filters
    expect(back.analyseLabuse).toBe(true)
    expect(back.surfaceMin).toBe(1500)
  })

  it('keeps historical keys readable (retro-compat)', () => {
    const back = filtersFromHash('#f=1&tv=chaude&q=70&hc=1&fl=pente,ravine')!.filters
    expect(back.tiers).toEqual(['chaude'])
    expect(back.scoreMin).toBe(70)
    expect(back.horsCopro).toBe(true)
    expect(back.flags).toEqual(['pente', 'ravine'])
  })
})
