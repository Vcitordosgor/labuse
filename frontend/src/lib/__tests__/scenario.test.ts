// ECRANS-NOV-2 — le vocabulaire et l'ordonnancement de l'écran « Analyse LABUSE par scénario ».
// On vérifie les LIBELLÉS du mandat, les couleurs (bande si estimée, sinon statut), la phrase qui
// dit ce qui classe, et le résumé replié des filtres. La construction de la requête API est
// vérifiée côté getAnalyseScenarios (params narrowent la liste, jamais les effectifs : côté back).
import { describe, expect, it } from 'vitest'

import { BANDE_META, SIGNAL_META } from '../status'
import {
  BANDES_CHIP, STATUTS_CHIP, NIVEAUX_CHIP, NIVEAU_META, STATUT_SCN_META,
  bandeLabel, couleurParcelle, phraseClassement, resumeFiltres, venteLabel,
  equipementLabel, FONCIER_PUBLIC_LABEL,
} from '../scenario'

describe('libellés du mandat', () => {
  it('nomme les statuts non estimés comme le mandat', () => {
    expect(STATUT_SCN_META.TO_VERIFY.label).toBe('À vérifier')
    expect(STATUT_SCN_META.DEFERRED.label).toBe('À différer')
    expect(STATUT_SCN_META.NO_MARGIN.label).toBe('Aucun ajout')
    expect(STATUT_SCN_META.OUTSIDE_OBJECTIVE.label).toBe('Hors projet')
    expect(STATUT_SCN_META.COMPUTE_PENDING.label).toBe('Calcul à compléter')
  })
  it('la rangée de puces potentiel = 4 bandes puis 5 statuts', () => {
    expect(BANDES_CHIP).toEqual(['A', 'B', 'C', 'D'])
    expect(STATUTS_CHIP).toEqual(['TO_VERIFY', 'DEFERRED', 'NO_MARGIN', 'OUTSIDE_OBJECTIVE', 'COMPUTE_PENDING'])
  })
  it('la rangée prospection = niveaux de Vente (Signal renommé), non évaluée en fin', () => {
    expect(NIVEAUX_CHIP).toEqual(['fort', 'moyen', 'faible', 'non_evalue'])
    expect(NIVEAU_META.fort.color).toBe(SIGNAL_META.fort.color)
    expect(NIVEAU_META.fort.label).toBe('forte')
    expect(NIVEAU_META.non_evalue.label).toBe('non évaluée')
    expect(venteLabel('fort')).toBe('Vente : forte')
    expect(venteLabel(null)).toBeNull()
  })
})

describe('couleur d’une parcelle', () => {
  it('prend la couleur de la BANDE quand la parcelle est estimée', () => {
    expect(couleurParcelle('ESTIMATED', 'A')).toBe(BANDE_META.A.color)
    expect(couleurParcelle('ESTIMATED', 'C')).toBe(BANDE_META.C.color)
  })
  it('prend la couleur du STATUT quand elle n’est pas estimée (bande ignorée)', () => {
    expect(couleurParcelle('TO_VERIFY', 'A')).toBe(STATUT_SCN_META.TO_VERIFY.color)
    expect(couleurParcelle('OUTSIDE_OBJECTIVE', null)).toBe(STATUT_SCN_META.OUTSIDE_OBJECTIVE.color)
  })
  it('bandeLabel résout A→Excellente, inconnu→null', () => {
    expect(bandeLabel('A')).toBe('Excellente')
    expect(bandeLabel(null)).toBeNull()
    expect(bandeLabel('ZZ')).toBeNull()
  })
})

describe('la phrase qui dit ce qui classe', () => {
  it('prospection : par Signal, bande indicative', () => {
    expect(phraseClassement('sale', 'keep')).toMatch(/Signal de mutation à 12 mois/)
    expect(phraseClassement('sale', 'keep')).toMatch(/ne classe pas/)
  })
  it('bâti conservé : par bande puis surface de plancher', () => {
    expect(phraseClassement('potential', 'keep')).toMatch(/surface de plancher supplémentaire/)
  })
  it('reconstruction : par bande puis capacité, gain net signé', () => {
    expect(phraseClassement('potential', 'rebuild')).toMatch(/capacité du nouveau projet/)
    expect(phraseClassement('potential', 'rebuild')).toMatch(/gain net est signé/)
  })
})

describe('résumé replié des choix (cohortes cochées)', () => {
  it('potentiel reconstruction, deux bandes cochées', () => {
    expect(resumeFiltres('potential', 'rebuild', ['Excellente', 'Bonne']))
      .toBe('Potentiel · Reconstruction · Excellente, Bonne')
  })
  it('potentiel bâti conservé, une bande', () => {
    expect(resumeFiltres('potential', 'keep', ['Excellente'])).toBe('Potentiel · Bâti conservé · Excellente')
  })
  it('prospection (pas de scénario)', () => {
    expect(resumeFiltres('sale', 'keep', ['Fort', 'Moyen'])).toBe('Prospection · Fort, Moyen')
  })
  it('aucune cochée', () => {
    expect(resumeFiltres('potential', 'keep', [])).toBe('Potentiel · Bâti conservé · aucune')
  })
})

describe('FONCIER-PUBLIC-1 — libellés foncier / équipement public', () => {
  it('« équipement public : <type> » quand une catégorie est servie', () => {
    expect(equipementLabel('enseignement')).toBe('Équipement public : enseignement')
    expect(equipementLabel('santé')).toBe('Équipement public : santé')
  })
  it('aucune catégorie → pas de libellé', () => {
    expect(equipementLabel(null)).toBeNull()
    expect(equipementLabel(undefined)).toBeNull()
  })
  it('la puce « Foncier public » est libellée', () => {
    expect(FONCIER_PUBLIC_LABEL).toBe('Foncier public')
  })
})
