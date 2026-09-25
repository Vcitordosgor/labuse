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

describe('RETOURS-14 P1 — la carte « Analyse LABUSE » affiche la version servie (param, pas en dur)', () => {
  it('rend le mot de la bande et la version passée', () => {
    const { container } = render(<AnalyseLabuseCard analyse={ANALYSE} version="q_v11_m137" />)
    expect(container.querySelector('[data-analyse-labuse-card]')).toBeTruthy()
    expect(container.querySelector('[data-fiche-bande="A"]')?.textContent).toBe('Excellente')
    expect(container.querySelector('[data-analyse-version]')?.textContent).toContain('q_v11_m137')
  })

  it('une AUTRE version servie → un AUTRE rendu (donc rien de codé en dur)', () => {
    const { container } = render(<AnalyseLabuseCard analyse={ANALYSE} version="q_v99_futur" />)
    expect(container.querySelector('[data-analyse-version]')?.textContent).toContain('q_v99_futur')
  })

  it('sans version servie, aucune mention de version fantôme', () => {
    const { container } = render(<AnalyseLabuseCard analyse={ANALYSE} version="" />)
    expect(container.querySelector('[data-analyse-version]')).toBeNull()
  })
})
