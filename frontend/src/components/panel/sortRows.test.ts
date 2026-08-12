// M69 PART A — NON-RÉGRESSION : le tri « Surface » doit produire un ordre GLOBAL monotone (les
// deux sens). Ce test ÉCHOUE si le groupement par tier revenait polluer un tri de colonne.
import { describe, it, expect } from 'vitest'
import { sortRows, type SortableRow } from './ResultsSection'

const TIERS = ['brulante', 'chaude', 'reserve_fonciere', 'a_creuser', 'declasse_zone_fermee', null] as const

// 159 lignes déterministes (LCG) — surfaces volontairement DÉSORDONNÉES, tiers panachés.
function mkRows(n: number): SortableRow[] {
  const rows: SortableRow[] = []
  let s = 1
  for (let i = 0; i < n; i++) {
    s = (s * 1103515245 + 12345) % 2147483648
    rows.push({
      etage0: false,
      tier_v2: TIERS[i % TIERS.length] as SortableRow['tier_v2'],
      mult_v2: (s % 1000) / 100,
      surface_m2: 40 + (s % 250000),
      rang_v2: i + 1,
    })
  }
  return rows
}

const nums = (rows: SortableRow[]) => rows.map((r) => r.surface_m2 as number)
const isDesc = (xs: number[]) => xs.every((v, i) => i === 0 || xs[i - 1] >= v)
const isAsc = (xs: number[]) => xs.every((v, i) => i === 0 || xs[i - 1] <= v)
const GROUPE = (r: SortableRow) =>
  r.etage0 ? 6 : ({ brulante: 0, chaude: 1, reserve_fonciere: 2, a_creuser: 3 } as Record<string, number>)[r.tier_v2 ?? ''] ?? (String(r.tier_v2 ?? '').startsWith('declasse') ? 4 : 5)

describe('sortRows — tri Surface GLOBAL et monotone (M69 A)', () => {
  const rows = mkRows(159)

  it('surface (↓) : suite globalement DÉCROISSANTE sur les 159', () => {
    const out = sortRows(rows, 'surface', /* groupes */ false)
    expect(out).toHaveLength(159)
    expect(isDesc(nums(out))).toBe(true)
  })

  it('surface_asc (↑) : suite globalement CROISSANTE sur les 159', () => {
    const out = sortRows(rows, 'surface_asc', false)
    expect(isAsc(nums(out))).toBe(true)
  })

  it('inversion asc/desc = ordre exactement inversé', () => {
    const desc = nums(sortRows(rows, 'surface', false))
    const asc = nums(sortRows(rows, 'surface_asc', false))
    expect(asc).toEqual([...desc].reverse())
  })

  it('groupé (rang, analyse) : groupes en ordre de tier, surface DÉCROISSANTE dans chaque groupe', () => {
    const out = sortRows(rows, 'surface', /* groupes */ true)
    const gs = out.map(GROUPE)
    expect(isAsc(gs)).toBe(true) // groupes non-décroissants (brûlantes → épuisées)
    // dans chaque groupe, surface décroissante
    for (let i = 1; i < out.length; i++) {
      if (gs[i] === gs[i - 1]) {
        expect((out[i - 1].surface_m2 as number) >= (out[i].surface_m2 as number)).toBe(true)
      }
    }
  })

  it('ne mute pas le tableau d\'entrée', () => {
    const before = nums(rows)
    sortRows(rows, 'surface', false)
    expect(nums(rows)).toEqual(before)
  })
})
