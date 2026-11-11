// BANDES-UNIFIEES (fix/logements-source-unique) — UN SEUL libellé de bande, celui de la fiche,
// écran Comparer ET PDF Comparatif : « lettre · libellé client · Signal X ». Ce test FIGE le
// vocabulaire front (BANDE_META/SIGNAL_META) et la forme rendue par l'écran Comparer ; le miroir
// Python (barème `vocabulaire_client` + signal_mutation.NIVEAU_LABELS, rendu comparatif.py) est
// figé par tests/test_logements_source_unique.py — les deux tests se répondent.
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { BANDE_META, SIGNAL_META, bandeMeta, signalMeta } from './status'

describe('BANDES-UNIFIEES — libellés écran = vocabulaire de la fiche', () => {
  it('le vocabulaire client des bandes est gravé (miroir du barème Python)', () => {
    expect(BANDE_META.A.label).toBe('Excellente')
    expect(BANDE_META.B.label).toBe('Bonne')
    expect(BANDE_META.C.label).toBe('À étudier')
    expect(BANDE_META.D.label).toBe('Faible')
    expect(BANDE_META['0'].label).toBe('Non retenue')
    expect(BANDE_META.NC.label).toBe('Analyse incomplète')
  })

  it('les libellés du Signal sont gravés (miroir de signal_mutation.NIVEAU_LABELS)', () => {
    expect(SIGNAL_META.fort.label).toBe('Signal fort')
    expect(SIGNAL_META.moyen.label).toBe('Signal moyen')
    expect(SIGNAL_META.faible.label).toBe('Signal faible')
  })

  it('le vocabulaire des bandes/Signal se recompose (fiche + Analyse)', () => {
    // le vocabulaire reste gravé pour la fiche et l'écran Analyse (forme « C · À étudier · Signal faible »).
    const bm = bandeMeta('C')!
    const sm = signalMeta('faible')!
    expect(`C · ${bm.label} · ${sm.label}`).toBe('C · À étudier · Signal faible')
    // RETOURS-29 (maquette 15-comparatif-v2) — l'écran Comparer NE PORTE PLUS de classement LABUSE ni de
    // puce de vente (l'analyse reste dans son écran). On vérifie donc l'ABSENCE de ce rendu.
    const panel = readFileSync(resolve(__dirname, '../components/compare/ComparePanel.tsx'), 'utf8')
    expect(panel).not.toContain('{r.bande} · {bm.label}')
    expect(panel).not.toContain('Classement LABUSE')
  })
})
