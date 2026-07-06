import { useQuery } from '@tanstack/react-query'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useRef } from 'react'
import { getParcelsGeojson } from '../../lib/api'
import { useApp } from '../../store/useApp'
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
// Contours : uniquement les parcelles PROMUES (sinon 46k écartées forment un maillage rouge).
const PROMUES_FILTER: maplibregl.FilterSpecification = ['in', ['get', 'status'], ['literal', ['chaude', 'a_surveiller', 'a_creuser']]]
// Mutabilité : dégradé continu par SDP résiduelle (combien de m² constructibles).
const MUTABILITE_COLOR: maplibregl.ExpressionSpecification = [
  'interpolate', ['linear'], ['coalesce', ['get', 'sdp_residuelle_m2'], 0],
  0, '#1E2A23', 300, '#2E6B4F', 2000, '#46A88A', 5000, '#5CE6A1',
]

const SP_BOUNDS: [number, number, number, number] = [55.21, -21.14, 55.35, -20.97]

export function MapView() {
  const ref = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map | null>(null)
  const ready = useRef(false)
  const { mode, selectedIdu, select } = useApp()
  const geo = useQuery({ queryKey: ['geojson'], queryFn: getParcelsGeojson })

  // init une fois
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
      ready.current = true
      m.addSource('parcels', { type: 'geojson', data: (geo.data ?? { type: 'FeatureCollection', features: [] }) as never, promoteId: 'idu' })
      m.addLayer({ id: 'parcels-fill', type: 'fill', source: 'parcels', paint: { 'fill-color': STATUS_COLOR, 'fill-opacity': STATUS_OPACITY } })
      m.addLayer({ id: 'parcels-line', type: 'line', source: 'parcels', filter: PROMUES_FILTER, paint: { 'line-color': STATUS_COLOR, 'line-width': 0.6, 'line-opacity': 0.9 } })
      m.addLayer({ id: 'parcels-sel', type: 'line', source: 'parcels', filter: ['==', ['get', 'idu'], ''], paint: { 'line-color': '#ECF5EF', 'line-width': 2 } })
      m.on('click', 'parcels-fill', (e) => { const f = e.features?.[0]; if (f) select(String(f.properties?.idu)) })
      m.on('mouseenter', 'parcels-fill', () => { m.getCanvas().style.cursor = 'pointer' })
      m.on('mouseleave', 'parcels-fill', () => { m.getCanvas().style.cursor = '' })
    })
    return () => { m.remove(); map.current = null; ready.current = false }
  }, [geo.data, select])

  // données chargées après init
  useEffect(() => {
    const m = map.current
    if (m && ready.current && geo.data) (m.getSource('parcels') as maplibregl.GeoJSONSource | undefined)?.setData(geo.data as never)
  }, [geo.data])

  // bascule verdict / mutabilité
  useEffect(() => {
    const m = map.current
    if (!m || !ready.current || !m.getLayer('parcels-fill')) return
    if (mode === 'mutabilite') {
      m.setPaintProperty('parcels-fill', 'fill-color', MUTABILITE_COLOR)
      m.setPaintProperty('parcels-fill', 'fill-opacity', 0.7)
    } else {
      m.setPaintProperty('parcels-fill', 'fill-color', STATUS_COLOR)
      m.setPaintProperty('parcels-fill', 'fill-opacity', STATUS_OPACITY)
    }
  }, [mode])

  // surbrillance sélection
  useEffect(() => {
    const m = map.current
    if (m && ready.current && m.getLayer('parcels-sel')) m.setFilter('parcels-sel', ['==', ['get', 'idu'], selectedIdu ?? ''])
  }, [selectedIdu])

  return (
    <div className="relative flex-1">
      <div ref={ref} className="absolute inset-0" />
      {/* zoom */}
      <div className="absolute left-4 top-4 flex flex-col gap-2">
        {(['+', '−'] as const).map((s) => (
          <button
            key={s}
            onClick={() => map.current?.[s === '+' ? 'zoomIn' : 'zoomOut']()}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-line-2 bg-surface-2 text-txt hover:text-txt-hi"
          >
            {s}
          </button>
        ))}
      </div>
      <Legend />
      <div className="pointer-events-none absolute bottom-4 left-1/2 -translate-x-1/2 rounded-full border border-line-2 bg-surface-2 px-4 py-1.5 text-xs text-txt-mut">
        Cliquez une parcelle pour ouvrir sa fiche
      </div>
      <div className="absolute bottom-2 right-3 font-sans text-[11px] text-[#3E4C45]">© OSM · CARTO</div>
    </div>
  )
}
