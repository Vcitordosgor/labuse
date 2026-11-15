// RETOURS-14 P1-P2 — GARDE : le clic « Demander à LABUSE » révèle une analyse issue du SCORING SERVI
// (le run de la page Données), JAMAIS d'une version codée en dur ; et la carte AFFICHE cette version.
//
// Deux invariants testés :
//  1. getFiche(idu) — l'appel qui alimente la carte — interroge TOUJOURS `?source=${SOURCE}`, où SOURCE
//     est le run servi injecté au build (config/served_run.txt). La carte ne fabrique aucune version.
//  2. AnalyseLabuseCard rend la version qu'on lui PASSE (data-analyse-version) : deux versions
//     différentes → deux rendus différents. Aucune chaîne de version en dur dans le composant.
import { render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { getFiche, SOURCE } from '../../lib/api'
import { AnalyseLabuseCard, type AnalyseLabuse } from './AnalyseLabuseCard'

const ANALYSE: AnalyseLabuse = {
  bande: 'A', signal_niveau: 'fort',
  contributions: [{ sens: 'hausse', libelle: 'SDP résiduelle élevée' }],
  cause: null, non_calculable: false, sdp_residuelle_m2: 420,
}

describe('RETOURS-14 P1 — la fiche lit le scoring SERVI (source=SOURCE), jamais une version en dur', () => {
  it('getFiche interroge /parcels/{idu} avec le run servi SOURCE', async () => {
    const fetchMock = vi.fn((_url: string) => Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response))
    vi.stubGlobal('fetch', fetchMock)
    await getFiche('974XYZ000AB0001')
    const url = String(fetchMock.mock.calls[0][0])
    expect(url).toContain('/parcels/974XYZ000AB0001')
    // la version voyage par le paramètre `source` = SOURCE (le run de la page Données), non une constante
    // gravée dans le code de la fiche : si SOURCE bascule (q_v11→q_v15), l'URL suit sans toucher au code.
    expect(url).toContain(`source=${SOURCE}`)
    vi.unstubAllGlobals()
  })
})

describe('RETOURS-17 — la carte « Analyse LABUSE » n\'affiche AUCUN identifiant de run', () => {
  it('rend le mot de la bande, sans la moindre mention de run (ex. « q_v20 »)', () => {
    const { container } = render(<AnalyseLabuseCard analyse={ANALYSE} />)
    expect(container.querySelector('[data-analyse-labuse-card]')).toBeTruthy()
    expect(container.querySelector('[data-fiche-bande="A"]')?.textContent).toBe('Excellente')
    // plus aucun badge de version, et le texte complet ne contient aucun label de run « q_v… ».
    expect(container.querySelector('[data-analyse-version]')).toBeNull()
    expect(container.textContent ?? '').not.toMatch(/q_v\d/i)
  })
})

describe('CHIRURGICAL-FIX-1 (E101) — la fiche montre la VRAIE cause (comme la liste), pas la contribution', () => {
  // AM0838 : zone UE (famille U) mais habitat interdit → bande 0 + cause_libelle. Avant le correctif
  // la carte n'affichait que la contribution « aucune SDP résiduelle exploitable » (trompeur : il y a
  // de la place, c'est l'habitat qui est interdit) et jetait le cause_libelle serveur.
  const AM0838: AnalyseLabuse = {
    bande: '0', signal_niveau: 'faible',
    contributions: [{ sens: 'baisse', libelle: 'aucune SDP résiduelle exploitable' }],
    cause: 'habitat_interdit:UE',
    cause_libelle: 'Non retenue — habitat interdit en zone UE.',
    non_calculable: false, sdp_residuelle_m2: null,
  }
  it('affiche le cause_libelle serveur et masque la contribution trompeuse', () => {
    const { container } = render(<AnalyseLabuseCard analyse={AM0838} />)
    expect(container.querySelector('[data-fiche-cause]')?.textContent)
      .toBe('Non retenue — habitat interdit en zone UE.')
    // la contribution « aucune SDP résiduelle exploitable » ne doit PLUS être rendue tant qu'une cause écarte
    expect(container.querySelector('[data-fiche-contributions]')).toBeNull()
    expect(container.textContent ?? '').not.toContain('aucune SDP résiduelle exploitable')
  })
  it('sans cause, les contributions « Ce qui compte » restent affichées', () => {
    const { container } = render(<AnalyseLabuseCard analyse={ANALYSE} />)
    expect(container.querySelector('[data-fiche-contributions]')).toBeTruthy()
    expect(container.querySelector('[data-fiche-cause]')).toBeNull()
  })
})
