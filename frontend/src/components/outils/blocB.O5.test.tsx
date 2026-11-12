import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useApp } from '../../store/useApp'
import { O5Servitudes } from './blocB'

// OUTILS-P0-1 (#2) — l'écran « Pièges et risques — une parcelle » rend QUATRE états : contrainte (cartes),
// « Aucune intersection détectée » (verifie), « Couverture inconnue » (couverture_inconnue), « Lecture
// indisponible » (lecture_indisponible). Plus de « Vérifié, rien à signaler » ; plus de puce « Procédure
// PLU » fabriquée côté front (elle vient du back, dans la bonne liste selon l'état du radar).
const IDU = '97411000AP0000'

function servitudesPayload(over: Record<string, unknown> = {}) {
  return {
    idu: IDU, n: 0, synthese: 'Aucune servitude dormante détectée dans les couches ingérées.',
    servitudes: [], verifie: [], couverture_inconnue: [], lecture_indisponible: [],
    plu_radar_ok: true, procedure_plu: null, non_couvert: ['Canalisations de transport'],
    avertissement: 'L\'absence d\'une servitude ici ne vaut pas absence réelle.', ...over,
  }
}

function mockFetch(payload: Record<string, unknown>) {
  global.fetch = vi.fn(async (url: string) => {
    if (String(url).includes('/servitudes-invisibles/')) return { ok: true, json: async () => payload }
    return { ok: true, json: async () => ({}) }
  }) as unknown as typeof fetch
}
function renderO5() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><O5Servitudes /></QueryClientProvider>)
}

describe('O5 — quatre états, plus de « vérifié » sans preuve', () => {
  beforeEach(() => { useApp.setState({ selectedIdu: IDU }) })
  afterEach(() => { vi.restoreAllMocks(); useApp.setState({ selectedIdu: null }) })

  it('« Aucune intersection détectée » (verifie) + « Couverture inconnue » ; plus de « Vérifié, rien à signaler »', async () => {
    mockFetch(servitudesPayload({ verifie: ['Sols pollués'], couverture_inconnue: ['Préemption', 'Eau et zones humides'] }))
    renderO5()
    await waitFor(() => expect(document.querySelector('[data-o5-verifie]')).toBeTruthy())
    const clair = document.querySelector('[data-o5-verifie]')!
    expect(clair.textContent).toContain('Aucune intersection détectée')
    expect(clair.textContent).toContain('Sols pollués')
    // l'ancien libellé a disparu
    expect(document.body.textContent).not.toContain('Vérifié, rien à signaler')
    // la section « Couverture inconnue » apparaît avec ses familles
    const inconnu = document.querySelector('[data-o5-couverture-inconnue]')!
    expect(inconnu).toBeTruthy()
    expect(inconnu.textContent).toContain('Couverture inconnue')
    expect(inconnu.textContent).toContain('Préemption')
    expect(inconnu.textContent).toContain('Eau et zones humides')
  })

  it('panne du radar PLU → « Lecture indisponible », JAMAIS dans « Aucune intersection détectée »', async () => {
    mockFetch(servitudesPayload({ verifie: ['Sols pollués'], lecture_indisponible: ['Procédure PLU'], plu_radar_ok: false }))
    renderO5()
    await waitFor(() => expect(document.querySelector('[data-o5-lecture-indisponible]')).toBeTruthy())
    const indispo = document.querySelector('[data-o5-lecture-indisponible]')!
    expect(indispo.textContent).toContain('Lecture indisponible')
    expect(indispo.textContent).toContain('Procédure PLU')
    // « Procédure PLU » n'est PAS présentée comme « rien à signaler »
    expect(document.querySelector('[data-o5-verifie]')?.textContent).not.toContain('Procédure PLU')
  })

  it('OUTILS-LOT-4 bis (pt 2) : parcelle 100 % rouge → badge « Inconstructible » SANS « (partie rouge) »', async () => {
    mockFetch(servitudesPayload({ servitudes: [{
      categorie: 'Risque naturel (PPR / aléa)',
      effet: 'PPR inondation — zone rouge sur 100 % de la parcelle : parcelle entièrement INCONSTRUCTIBLE (interdiction, C. env. L562‑1), quelle que soit la surface.',
      source: 'DEAL', date: 'au 01/01/2026', redhibitoire: true,
    }] }))
    renderO5()
    await waitFor(() => expect(document.body.textContent).toContain('Risque naturel'))
    expect(document.body.textContent).toContain('Inconstructible')
    expect(document.body.textContent).not.toContain('(partie rouge)')
  })

  it('OUTILS-LOT-4 bis (pt 2) : rouge PARTIEL (< 100 %) → le badge garde « Inconstructible (partie rouge) »', async () => {
    mockFetch(servitudesPayload({ servitudes: [{
      categorie: 'Risque naturel (PPR / aléa)',
      effet: 'PPR inondation — zone rouge sur 40 % de la parcelle : partie INCONSTRUCTIBLE (interdiction, C. env. L562‑1), quelle que soit la surface. Partie hors zone rouge (60 %) : constructible selon les règles de sa zone, à confirmer au règlement du PPR.',
      source: 'DEAL', date: 'au 01/01/2026', redhibitoire: true,
    }] }))
    renderO5()
    await waitFor(() => expect(document.body.textContent).toContain('Risque naturel'))
    expect(document.body.textContent).toContain('Inconstructible (partie rouge)')
  })

  it('zone blanche (tout inconnu) : pas de section « Aucune intersection détectée », une « Couverture inconnue »', async () => {
    const dix = ['Sols pollués', 'Bruit', 'Assainissement', 'ICPE', 'Monuments et sites', 'ER / EBC',
      'Préemption', 'Eau et zones humides', 'Espaces naturels', 'Risques naturels']
    mockFetch(servitudesPayload({ verifie: [], couverture_inconnue: dix }))
    renderO5()
    await waitFor(() => expect(document.querySelector('[data-o5-couverture-inconnue]')).toBeTruthy())
    expect(document.querySelector('[data-o5-verifie]')).toBeNull()   // rien n'est « vérifié »
    expect(document.querySelector('[data-o5-couverture-inconnue]')!.textContent).toContain('Risques naturels')
  })
})
