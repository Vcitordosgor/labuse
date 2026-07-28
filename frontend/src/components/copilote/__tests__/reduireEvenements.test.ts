// M26-B — le réducteur pur : statuts conformes à events.reduce_run, rejeu after_seq
// sans doublon ni trou (verrou SSE du mandat, niveau fonction).
import { describe, expect, it } from 'vitest'
import { VUE_INITIALE, reduireEvenements } from '../reduireEvenements'
import { etat1Calibre } from './fixtures'

describe('reduireEvenements', () => {
  it('réduit l’état 1 complet : done, recap, 8 étapes faites', () => {
    const vue = reduireEvenements(etat1Calibre())
    expect(vue.statut).toBe('done')
    expect(vue.recap?.n_restituees).toBe(20)
    expect(vue.recap?.n_retenues).toBe(2753)
    expect(vue.etapes).toHaveLength(8)
    expect(vue.etapes.every((e) => e.etat === 'faite')).toBe(true)
    expect(vue.final?.duree_totale_ms).toBe(56_000)
  })

  it('rejeu after_seq : rejouer un suffixe chevauchant ne crée ni doublon ni trou', () => {
    const evts = etat1Calibre()
    const enUneFois = reduireEvenements(evts)
    // coupure au milieu puis reprise LARGE (le back rejoue à partir d'after_seq — on
    // simule pire : un chevauchement complet du déjà-vu)
    const avant = reduireEvenements(evts.slice(0, 9))
    const apres = reduireEvenements(evts.slice(4), avant)   // seq 5..9 déjà vus
    expect(apres).toEqual(enUneFois)
  })

  it('l’ordre d’arrivée ne compte pas : les événements sont triés par seq', () => {
    const evts = etat1Calibre()
    const melange = [...evts].reverse()
    expect(reduireEvenements(melange)).toEqual(reduireEvenements(evts))
  })

  it('un état terminal est absorbant', () => {
    const evts = etat1Calibre()
    const vue = reduireEvenements(evts)
    const fantome = { seq: 999, kind: 'step_started' as const,
      payload: { moteur: 'criblage' }, created_at: '2026-07-27T00:00:00Z' }
    expect(reduireEvenements([fantome], vue)).toEqual(vue)
  })

  it('statuts intermédiaires : interpreting → running pendant les étapes', () => {
    const evts = etat1Calibre()
    expect(reduireEvenements(evts.slice(0, 1)).statut).toBe('interpreting')
    expect(reduireEvenements(evts.slice(0, 2)).statut).toBe('running')
    const partiel = reduireEvenements(evts.slice(0, 5))
    expect(partiel.statut).toBe('running')
    expect(partiel.recap).toBeNull()          // règle 5 : rien d'assemblé avant la fin
  })

  it('VUE_INITIALE n’est jamais mutée', () => {
    const gel = JSON.stringify(VUE_INITIALE)
    reduireEvenements(etat1Calibre())
    expect(JSON.stringify(VUE_INITIALE)).toBe(gel)
  })
})
