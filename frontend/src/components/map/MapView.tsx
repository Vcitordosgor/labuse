import { useQuery } from '@tanstack/react-query'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useRef } from 'react'
import { getMapLayer, getParcelsGeojson } from '../../lib/api'
import { useApp, type Filters } from '../../store/useApp'
import { Legend } from './Legend'

const CARTO_DARK: maplibregl.StyleSpecification = {
  version: 8,
  glyphs: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/{fontstack}/{range}.pbf',
  sources: {
    carto: {
      type: 'raster',
      tiles: ['https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png', 'https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png'],
      tileSize: 256,
      attribution: '© OSM · CARTO',
    },
  },
  layers: [{ id: 'carto', type: 'raster', source: 'carto', paint: { 'raster-opacity': 0.55 } }],
}

const STATUS_COLOR: maplibregl.ExpressionSpecification = [
  'match', ['get', 'status'],
  'chaude', '#5CE6A1', 'a_surveiller', '#4ADE96', 'a_creuser', '#E8B44C', 'ecartee', '#E8695A',
  '#39463F',
]
const STATUS_OPACITY: maplibregl.ExpressionSpecification = [
  'match', ['get', 'status'],
  'chaude', 0.92, 'a_surveiller', 0.85, 'a_creuser', 0.55, 'ecartee', 0.04,
  0.03,
]
const PROMUES_FILTER: maplibregl.FilterSpecification = ['in', ['get', 'status'], ['literal', ['chaude', 'a_surveiller', 'a_creuser']]]
const MUTABILITE_COLOR: maplibregl.ExpressionSpecification = [
  'interpolate', ['linear'], ['coalesce', ['get', 'sdp_residuelle_m2'], 0],
  0, '#1E2A23', 300, '#2E6B4F', 2000, '#46A88A', 5000, '#5CE6A1',
]

function toExpr(f: Filters): maplibregl.FilterSpecification {
  const c: maplibregl.ExpressionSpecification[] = []
  if (f.statut !== 'all') c.push(['==', ['get', 'status'], f.statut])
  if (f.scoreMin != null) c.push(['>=', ['coalesce', ['get', 'q_score'], 0], f.scoreMin])
  if (f.surfaceMin != null) c.push(['>=', ['coalesce', ['get', 'surface_m2'], 0], f.surfaceMin])
  return ['all', ...c] as maplibregl.FilterSpecification
}

const SP_BOUNDS: [number, number, number, number] = [55.21, -21.14, 55.35, -20.97]
const EMPTY_FC = { type: 'FeatureCollection', features: [] } as const

// Couches overlay (id → style). Zonage : U/AU menthe pâle · A/N brun · PPR rouge · Parc vert.
const OVERLAYS = {
  zonage: {
    kind: 'plu_gpu_zone',
    paint: {
      'fill-color': ['case',
        ['in', ['slice', ['upcase', ['coalesce', ['get', 'subtype'], '']], 0, 1], ['literal', ['U']]],
        '#5CE6A1', '#8a6b3f'] as unknown as maplibregl.ExpressionSpecification,
      'fill-opacity': 0.10,
    },
  },
  ppr: { kind: 'ppr', paint: { 'fill-color': '#E8695A', 'fill-opacity': 0.14 } },
  parc: { kind: 'parc_national', paint: { 'fill-color': '#4ADE96', 'fill-opacity': 0.10 } },
} as const

export function MapView() {
  const ref = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map | null>(null)
  const ready = useRef(false)
  const { mode, selectedIdu, select, filters, layers } = useApp()
  const geo = useQuery({ queryKey: ['geojson'], queryFn: getParcelsGeojson })
  // overlays chargés uniquement quand activés (enabled)
  const zonage = useQuery({ queryKey: ['layer', 'zonage'], queryFn: () => getMapLayer('plu_gpu_zone'), enabled: layers.zonage })
  const ppr = useQuery({ queryKey: ['layer', 'ppr'], queryFn: () => getMapLayer('ppr'), enabled: layers.ppr })
  const parc = useQuery({ queryKey: ['layer', 'parc'], queryFn: () => getMapLayer('parc_national'), enabled: layers.parc })

  useEffect(() => {
    if (!ref.current || map.current) return
    const m = new maplibregl.Map({
      container: ref.current,
      style: CARTO_DARK,
      bounds: SP_BOUNDS,
      fitBoundsOptions: { padding: 40 },
      attributionControl: false,
    })
    map.current = m
    m.on('load', () => {
      // sources
      m.addSource('parcels', { type: 'geojson', data: EMPTY_FC as never, promoteId: 'idu' })
      for (const k of Object.keys(OVERLAYS)) m.addSource(`ov-${k}`, { type: 'geojson', data: EMPTY_FC as never })
      // overlays SOUS les parcelles
      for (const [k, o] of Object.entries(OVERLAYS)) {
        m.addLayer({ id: `ov-${k}`, type: 'fill', source: `ov-${k}`, layout: { visibility: 'none' }, paint: o.paint as never })
      }
      // parcelles
      m.addLayer({ id: 'parcels-fill', type: 'fill', source: 'parcels', paint: { 'fill-color': STATUS_COLOR, 'fill-opacity': STATUS_OPACITY } })
      m.addLayer({ id: 'parcels-line', type: 'line', source: 'parcels', filter: PROMUES_FILTER, paint: { 'line-color': STATUS_COLOR, 'line-width': 0.6, 'line-opacity': 0.9 } })
      // vue mer : liseré cyan sur les parcelles promues avec vue dégagée
      m.addLayer({
        id: 'parcels-vuemer', type: 'line', source: 'parcels', layout: { visibility: 'none' },
        filter: ['all', PROMUES_FILTER, ['==', ['get', 'vue_mer'], 'oui']] as never,
        paint: { 'line-color': '#7DE8E0', 'line-width': 1.4, 'line-opacity': 0.95 },
      })
      m.addLayer({ id: 'parcels-sel', type: 'line', source: 'parcels', filter: ['==', ['get', 'idu'], ''], paint: { 'line-color': '#ECF5EF', 'line-width': 2 } })
      m.on('click', 'parcels-fill', (e) => { const f = e.features?.[0]; if (f) select(String(f.properties?.idu)) })
      m.on('mouseenter', 'parcels-fill', () => { m.getCanvas().style.cursor = 'pointer' })
      m.on('mouseleave', 'parcels-fill', () => { m.getCanvas().style.cursor = '' })
      ready.current = true
      m.fire('labuse:ready' as never)
    })
    return () => { m.remove(); map.current = null; ready.current = false }
  }, [select])

  // données parcelles
  useEffect(() => {
    const m = map.current
    if (m && ready.current && geo.data) (m.getSource('parcels') as maplibregl.GeoJSONSource | undefined)?.setData(geo.data as never)
  }, [geo.data, geo.dataUpdatedAt])

  // données overlays
  useEffect(() => {
    const m = map.current
    if (!m || !ready.current) return
    const pairs: [string, typeof zonage][] = [['zonage', zonage], ['ppr', ppr], ['parc', parc]]
    for (const [k, qy] of pairs) {
      if (qy.data) (m.getSource(`ov-${k}`) as maplibregl.GeoJSONSource | undefined)?.setData(qy.data as never)
    }
  }, [zonage.data, ppr.data, parc.data])

  // visibilité couches + filtres + mode
  useEffect(() => {
    const m = map.current
    if (!m || !ready.current || !m.getLayer('parcels-fill')) return
    const vis = (on: boolean) => (on ? 'visible' : 'none')
    m.setLayoutProperty('parcels-fill', 'visibility', vis(layers.parcelles))
    m.setLayoutProperty('parcels-line', 'visibility', vis(layers.parcelles))
    m.setLayoutProperty('parcels-vuemer', 'visibility', vis(layers.vue_mer && layers.parcelles))
    m.setLayoutProperty('ov-zonage', 'visibility', vis(layers.zonage))
    m.setLayoutProperty('ov-ppr', 'visibility', vis(layers.ppr))
    m.setLayoutProperty('ov-parc', 'visibility', vis(layers.parc))

    const expr = toExpr(filters)
    m.setFilter('parcels-fill', expr)
    m.setFilter('parcels-line', ['all', PROMUES_FILTER, expr] as maplibregl.FilterSpecification)
    if (mode === 'mutabilite') {
      m.setPaintProperty('parcels-fill', 'fill-color', MUTABILITE_COLOR)
      m.setPaintProperty('parcels-fill', 'fill-opacity', 0.7)
    } else {
      m.setPaintProperty('parcels-fill', 'fill-color', STATUS_COLOR)
      m.setPaintProperty('parcels-fill', 'fill-opacity', filters.statut === 'all' ? STATUS_OPACITY : 0.72)
    }
  }, [mode, filters, layers, geo.dataUpdatedAt])

  // surbrillance sélection
  useEffect(() => {
    const m = map.current
    if (m && ready.current && m.getLayer('parcels-sel')) m.setFilter('parcels-sel', ['==', ['get', 'idu'], selectedIdu ?? ''])
  }, [selectedIdu])

  return (
    <div className="relative min-w-0 flex-1">
      <div ref={ref} className="absolute inset-0" />
      <div className="absolute left-4 top-4 flex flex-col gap-2">
        {(['+', '−'] as const).map((s) => (
          <button
            key={s}
            onClick={() => map.current?.[s === '+' ? 'zoomIn' : 'zoomOut']()}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-line-2 bg-surface-2 text-txt hover:text-txt-hi"
            title={s === '+' ? 'Zoomer' : 'Dézoomer'}
          >
            {s}
          </button>
        ))}
      </div>
      <Legend />
      <div className="pointer-events-none absolute bottom-4 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full border border-line-2 bg-surface-2 px-4 py-1.5 text-xs text-txt-mut">
        Cliquez une parcelle pour ouvrir sa fiche
      </div>
      <div className="absolute bottom-2 right-3 font-sans text-[11px] text-[#3E4C45]">© OSM · CARTO</div>
    </div>
  )
}
