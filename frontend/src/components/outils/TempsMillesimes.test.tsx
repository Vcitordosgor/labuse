import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useApp } from '../../store/useApp'
import { BASEMAP_SOURCES, TEMPS_MILLESIMES, basemapLabel } from '../map/basemaps'
import { M08 } from './ModulePanel'

// Mandat TEMPS — 1) frise des millésimes (lot 3 conditionnel : ACTIVÉ, l'inventaire IGN a trouvé
// 5 mosaïques-période servant des dalles sur le 974 EN PLUS de 1950-65) ; 2) légende zones noires ;
// 3) contour de la parcelle épinglé sur les deux fonds (canal store tempsPinIdu).

// maplibre-gl ne tourne pas sous jsdom (WebGL) — stub minimal : la LÉGENDE et les libellés ne
// dépendent que du store, pas du rendu carte, donc le stub suffit à les faire rendre.
vi.mock('maplibre-gl', () => {
  class Map {
    on() { return this } once() { return this } off() { return this }
    jumpTo() {} remove() {} resize() {}
    getCenter() { return { lng: 55.4, lat: -20.9 } } getZoom() { return 15 }
    getBearing() { return 0 } getPitch() { return 0 } isStyleLoaded() { return true }
    getLayer() { return null } getSource() { return undefined }
    addSource() {} addLayer() {} removeLayer() {} removeSource() {} setFilter() {}
  }
  return { default: { Map }, Map }
})

const qc = () => new QueryClient({ defaultOptions: { queries: { retry: false } } })

describe('TEMPS — inventaire des millésimes servant réellement des dalles', () => {
  it('la frise expose 1950-65 + AU MOINS 2 autres millésimes (condition du lot 3)', () => {
    const autres = TEMPS_MILLESIMES.filter((m) => m.key !== 'bm-ortho-1950')
    expect(autres.length).toBeGreaterThanOrEqual(2)
    // chaque millésime de la frise a une source de fond réelle + un libellé résolu (jamais la clé brute)
    for (const m of TEMPS_MILLESIMES) {
      expect(BASEMAP_SOURCES[m.key]).toBeTruthy()
      expect(basemapLabel(m.key)).not.toBe(m.key)
    }
  })
})

describe('TEMPS — la frise (M08) + l\'épingle de la parcelle', () => {
  beforeEach(() => {
    global.fetch = vi.fn(async () => ({ ok: true, json: async () => ({ coords: [55.4, -20.9] }) })) as unknown as typeof fetch
    useApp.setState({ parcelPrefill: '97415000CW0658', cmpLeft: 'bm-ortho-1950', tempsPinIdu: null })
  })
  afterEach(() => { vi.restoreAllMocks(); useApp.setState({ parcelPrefill: null, tempsPinIdu: null }) })

  it('désigner la parcelle l\'ÉPINGLE (store) et déplie la frise chronologique complète', async () => {
    render(<QueryClientProvider client={qc()}><M08 /></QueryClientProvider>)
    // la frise apparaît une fois la parcelle désignée (via parcelPrefill)
    await waitFor(() => expect(document.querySelector('[data-temps-frise]')).toBeTruthy())
    // un bouton par millésime + les nouveaux millésimes visibles
    const boutons = document.querySelectorAll('[data-cmp-left]')
    expect(boutons.length).toBe(TEMPS_MILLESIMES.length)
    for (const an of ['1950', '2006', '2011', '2016', '2021']) expect(screen.getByText(an)).toBeTruthy()
    expect(screen.getByText('Auj.')).toBeTruthy()   // l'« après » verrouillé, borne de droite
    // l'épingle est posée dans le store (consommée par TimeMachine sur les deux fonds)
    expect(useApp.getState().tempsPinIdu).toBe('97415000CW0658')
    // choisir un millésime récent met à jour le fond « avant »
    ;(document.querySelector('[data-cmp-left="bm-ortho-2016"]') as HTMLElement).click()
    expect(useApp.getState().cmpLeft).toBe('bm-ortho-2016')
  })
})

describe('TEMPS — légende des zones noires (comparateur)', () => {
  afterEach(() => useApp.setState({ cmpLeft: 'bm-ortho-1950', cmpRight: 'bm-ortho-now', tempsPinIdu: null }))

  it('présente sous un fond ancien, absente sous l\'ortho actuelle', async () => {
    const { TimeMachine } = await import('./TimeMachine')
    useApp.setState({ cmpLeft: 'bm-ortho-1950', cmpRight: 'bm-ortho-now', commune: null })
    const { rerender } = render(<QueryClientProvider client={qc()}><TimeMachine center={null} /></QueryClientProvider>)
    expect(document.querySelector('[data-temps-legende]')).toBeTruthy()
    expect(document.querySelector('[data-temps-legende]')?.textContent).toContain('pas un défaut de chargement')
    // fond « avant » = ortho actuelle → aucune zone de mission non couverte → pas de légende
    useApp.setState({ cmpLeft: 'bm-ortho-now' })
    rerender(<QueryClientProvider client={qc()}><TimeMachine center={null} /></QueryClientProvider>)
    await waitFor(() => expect(document.querySelector('[data-temps-legende]')).toBeNull())
  })
})
