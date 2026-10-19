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

  it('l’écran Comparer rend « lettre · libellé » + badge Signal (même forme que le PDF)', () => {
    // la forme « C · À étudier · Signal faible » du PDF (comparatif.py:_classement) se recompose
    // exactement depuis les mêmes briques front :
    const bm = bandeMeta('C')!
    const sm = signalMeta('faible')!
    expect(`C · ${bm.label} · ${sm.label}`).toBe('C · À étudier · Signal faible')
    // et ComparePanel rend bien cette forme (val + badge) — figé au niveau source.
    const panel = readFileSync(resolve(__dirname, '../components/compare/ComparePanel.tsx'), 'utf8')
    expect(panel).toContain('`${r.bande} · ${bm.label}`')
    expect(panel).toContain('{r.bande} · {bm.label}')
  })
})
