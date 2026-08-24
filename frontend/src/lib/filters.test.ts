import { describe, expect, it } from 'vitest'
import { filtersFromHash, filtersToHash, hasOpinion } from './filters'
import { EMPTY_FILTERS, type Filters } from '../store/useApp'

// M55-D : la persistance couvre TOUS les champs, reste rétro-compatible, et l'interrupteur
// « analyse » (analyseLabuse) est biunivoque avec la présence de critères d'opinion (stage 4).
describe('filters URL persistence (M55-D)', () => {
  it('round-trips EVERY field (terrain + opinion + interrupteur allumé)', () => {
    const f: Filters = {
      ...EMPTY_FILTERS,
      tiers: ['brulante', 'chaude'],
      surfaceMin: 1000, surfaceMax: 5000, sdpMin: 300, sdpMax: 2000,
      capaciteMin: 10, multMin: 2, rangMax: 100, budgetMax: 200000,
      chargeMin: 1000, chargeMax: 90000, prixMarcheMin: 100, prixMarcheMax: 900, caMin: 1_000_000,
      veille: true, horsCopro: true, personneMorale: true, sousDensite: true,
      renouvellement: true, npnru: true, adresseAbsente: true,
      marcheFiable: true, modeBRentable: true,
      flagsExclus: ['icpe'], communes: ['Saint-Paul'],
      zonagePlu: ['U', 'AU'], constructibilite: ['constructible'], etatSol: ['nu'],
      zonePlu: ['UA'], proprietaireType: ['pm'], etatSociete: ['radiee'], copro: ['sans'],
      signaux: ['defisc', 'friche'],   // stage 6 : le groupe Signaux de vie persiste (clé sv)
      analyseLabuse: true,   // stage 4 : allumé (cohérent avec les critères d'opinion présents)
    }
    const hash = filtersToHash(f, null)
    const back = { ...EMPTY_FILTERS, ...(filtersFromHash(hash)!.filters) }
    expect(back).toEqual(f)
  })

  it('stage 4 : un lien TERRAIN-only laisse l\'interrupteur ÉTEINT', () => {
    const back = filtersFromHash('#f=1&smin=1500')!.filters
    expect(back.analyseLabuse).toBe(false)
    expect(back.surfaceMin).toBe(1500)
  })

  it('stage 4 : un lien portant un tier ALLUME l\'interrupteur (vieux lien)', () => {
    const back = filtersFromHash('#f=1&tv=chaude&smin=2000')!.filters
    expect(back.analyseLabuse).toBe(true)
    expect(back.tiers).toEqual(['chaude'])
    expect(back.surfaceMin).toBe(2000)
  })

  it('hasOpinion distingue terrain (faux) et opinion (vrai)', () => {
    expect(hasOpinion({ ...EMPTY_FILTERS, surfaceMin: 1000, zonagePlu: ['U'], etatSol: ['nu'] })).toBe(false)
    expect(hasOpinion({ ...EMPTY_FILTERS, tiers: ['chaude'] })).toBe(true)
    expect(hasOpinion({ ...EMPTY_FILTERS, rangMax: 70 })).toBe(true)   // rangMax = opinion (classement)
  })

  it('stage 6 : le legacy ev=1 mappe vers le signal « procédure collective »', () => {
    const back = filtersFromHash('#f=1&ev=1&smin=1000')!.filters
    expect(back.evenement).toBe(false)
    expect(back.signaux).toEqual(['procedure'])
    expect(back.surfaceMin).toBe(1000)
  })

  it('keeps historical keys readable (retro-compat) — legacy q= et fl= IGNORÉS sans erreur', () => {
    // FIX-SCOREMIN : un vieux lien portant `q=` (scoreMin, matrice morte) s'ouvre toujours, mais
    // `q` est désormais IGNORÉ (comme `fl=`) — jamais lu dans un champ puis silencieusement non filtré.
    const back = filtersFromHash('#f=1&tv=chaude&q=70&hc=1&fl=pente,ravine')!.filters
    expect(back.tiers).toEqual(['chaude'])
    expect('scoreMin' in back).toBe(false)   // la clé q n'alimente plus aucun champ
    expect(back.horsCopro).toBe(true)
    expect(back.flags ?? []).toEqual([])   // la clé contraintes est ignorée, le lien s'ouvre
  })
})
