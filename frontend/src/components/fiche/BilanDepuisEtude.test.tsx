import { describe, expect, it } from 'vitest'
import { entreesInitiales, type BilanDepuisEtude } from './BilanEcran'
import type { BilanModele } from '../../lib/api'

// IMPLANTATION-4 (LOT B) — le pré-remplissage du Bilan :
//   (1) PAR DÉFAUT, aucun nombre de logements de l'ancien moteur (produits à blanc, SDP vide) ;
//   (2) « depuis l'Étude », le programme du scénario (logements par type + SDP) amorce le Bilan.
const MODELE: BilanModele = {
  sourcee: { terrain: 1000, commune: "L'Étang-Salé", non_constructible_pct: 0, constructible_m2: null, zonage: null } as never,
  ratios_compte: {}, calendrier: [], blocs: [], reperes_publics: {},
} as unknown as BilanModele

describe('LOT B — pré-remplissage du Bilan', () => {
  it('par défaut : AUCUN logement pré-rempli (produits à blanc, SDP vide)', () => {
    const e = entreesInitiales(MODELE)
    expect(e.programme.sdp).toBeNull()                 // SDP non pré-remplie par l'ancien moteur
    expect(e.produits[0].lots).toBeNull()              // aucun nombre de logements
    expect(e.produits[0].libelle).toBe('Produit 1')
  })

  it('depuis l\'Étude : SDP du scénario + logements (par type) amorcent le Bilan', () => {
    const etude: BilanDepuisEtude = { ref: 'A', logements: 28, par_type: { T2: 20, T3: 8 }, sdp_m2: 1800, shab_m2: 1100 }
    const e = entreesInitiales(MODELE, etude)
    expect(e.programme.sdp).toBe(1800)                 // SDP du scénario
    expect(e.produits[0].lots).toBe(28)                // les logements du scénario = lots du 1er produit
    expect(e.produits[0].suv).toBe(1100)               // SHAB estimée du scénario
    expect(e.produits[0].libelle).toContain('Logements')
    expect(e.produits[0].libelle).toContain('T2×20')   // la répartition par type est reportée dans le libellé
    expect(e.programme.terrain).toBe(1000)             // le terrain Sourcé reste pré-rempli, inchangé
  })
})
