import { describe, expect, it } from 'vitest'
import { actesParParcelle, agePermis } from './permisAffichage'

describe('lecture des permis', () => {
  it('compte les années révolues au jour local à La Réunion', () => {
    expect(agePermis('2013-12-03', new Date('2026-12-02T19:59:59Z'))).toBe(12)
    expect(agePermis('2013-12-03', new Date('2026-12-02T20:00:00Z'))).toBe(13)
  })

  it('donne priorité au rattachement et conserve les deux types d’un même numéro', () => {
    const pc = { nature: 'PC', permit_id: '123' }
    const dp = { nature: 'DP', permit_id: '123' }
    const sansPoint = { nature: 'PC', permit_id: '456', geom: null }
    const { tous, voisins } = actesParParcelle({ rattaches: [sansPoint, pc], items: [pc, dp] })
    expect(tous).toEqual([sansPoint, pc, dp])
    expect(voisins).toEqual([dp])
  })
})
