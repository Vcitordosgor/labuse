// CIRCUIT-P7 (lot 2) — l'onglet Sources : le tableau trie les problèmes d'abord, « Toutes » est le
// dernier filtre à droite, et un filtre d'état FILTRE vraiment (prouvé ici, exigence du mandat).
import { fireEvent, render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Sources } from './Sources'
import type { CircuitData } from './types'

const res = (id: number, nom: string, etat: [string, string], extra: any = {}) => ({
  id, nom, producteur: 'X', famille: 'famille', slug: nom, millesime: '2026', ingere_le: null,
  mode: 'api', cadence_jours: null, cadence_statut: null, a_verifier: false, dernier_controle: null,
  etat, ko: false, taps: [], chiffres_ids: [], vanne: { type: 'aucune' },
  veille: { methode: 'api', statut: 'ok', passage: '2026-09-24', vu: null, actif: true },
  filtre: {}, ...extra,
})

const data = (): CircuitData => ({
  reservoirs: [
    res(1, 'Alpha à jour', ['mint', 'à jour']),
    res(2, 'Bravo panne', ['rouge', 'sonde en panne']),
    res(3, 'Charlie neuve', ['ambre', 'nouvelle version']),
  ],
  etats_sources: { 'à jour': 1, 'nouvelle version': 1, 'échue': 0, 'jamais vérifiée': 0, 'sonde en panne': 1, total: 3 },
  hors_vitrine: [],
} as any)

const rows = (c: HTMLElement) => Array.from(c.querySelectorAll('.svt-r'))
const noms = (c: HTMLElement) => rows(c).map((r) => (r.querySelector('.nm')?.textContent) || '')

describe('Sources (lot 2)', () => {
  it('trie les problèmes d\'abord : panne → nouvelle → à jour', () => {
    const { container } = render(<Sources data={data()} onOpen={() => {}} />)
    expect(noms(container)).toEqual(['Bravo panne', 'Charlie neuve', 'Alpha à jour'])
  })

  it('« Toutes » est le dernier chip, et un filtre d\'état filtre vraiment', () => {
    const { container, getByText } = render(<Sources data={data()} onOpen={() => {}} />)
    const chips = Array.from(container.querySelectorAll('.src-chips .chip'))
    expect(chips[chips.length - 1].textContent).toContain('Toutes')   // « Toutes » en dernier
    expect(rows(container).length).toBe(3)                            // par défaut : tout
    fireEvent.click(getByText(/Sonde en panne/))                      // on filtre
    const r = rows(container)
    expect(r.length).toBe(1)
    expect(r[0].textContent).toContain('Bravo panne')
  })
})
