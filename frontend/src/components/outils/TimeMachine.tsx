import { useQuery } from '@tanstack/react-query'
import maplibregl from 'maplibre-gl'
import { useEffect, useRef, useState } from 'react'
import { getParcelsGeojson } from '../../lib/api'
import { useApp } from '../../store/useApp'
import { BASEMAP_SOURCES, basemapLabel, type BasemapDef } from '../map/basemaps'

const SP_BOUNDS: [number, number, number, number] = [55.21, -21.14, 55.35, -20.97]

// Comparateur générique : les deux fonds sont choisis (défaut 1950 ↔ aujourd'hui, l'usage « 1950 »).
const DEFAULT_LEFT = 'bm-ortho-1950'
const DEFAULT_RIGHT = 'bm-ortho-now'

/** Carte nue (fond sombre) — le fond de plan est posé/échangé ensuite par applyBasemap. */
function mkMap(el: HTMLDivElement) {
  return new maplibregl.Map({
    container: el,
    style: {
      version: 8, sources: {},
      layers: [{ id: 'bg', type: 'background', paint: { 'background-color': '#060A08' } }],
    },
    bounds: SP_BOUNDS, fitBoundsOptions: { padding: 40 }, attributionControl: false,
  })
}

/** Pose/échange le fond de plan SUR PLACE (même instance → caméra, synchro et parcelles préservées).
 *  Le raster 'bm' est réinséré SOUS la couche parcelles 'p' pour que le contour reste au-dessus. */
function applyBasemap(m: maplibregl.Map, def: BasemapDef) {
  const add = () => {
    if (m.getLayer('bm')) m.removeLayer('bm')
    if (m.getSource('bm')) m.removeSource('bm')
    m.addSource('bm', { type: 'raster', tiles: def.tiles, tileSize: 256, attribution: def.attribution, maxzoom: def.maxzoom ?? 19 })
    m.addLayer({ id: 'bm', type: 'raster', source: 'bm' }, m.getLayer('p') ? 'p' : undefined)
  }
  if (m.isStyleLoaded()) add()
  else m.once('load', add)
}

function muteTileErrors(m: maplibregl.Map) {
  m.on('error', (e) => {
    const msg = String((e as { error?: Error }).error?.message ?? '')
    if (/AJAXError|40[04]/.test(msg)) return
    console.error(e.error ?? e)
  })
}

/** M08 / point 24 — comparateur SWIPE de fonds de plan : deux cartes superposées, celle de droite
 *  rognée par la poignée (clip-path). Caméras synchronisées dans les deux sens (garde anti-boucle).
 *  Défaut = 1950 ↔ aujourd'hui (l'usage historique « 1950 ») ; les deux fonds sont maintenant
 *  librement choisis. Parcelles promues affichées des deux côtés. */
export function TimeMachine({ center }: { center?: [number, number] | null }) {
  const leftRef = useRef<HTMLDivElement>(null)
  const rightRef = useRef<HTMLDivElement>(null)
  const maps = useRef<[maplibregl.Map, maplibregl.Map] | null>(null)
  const [split, setSplit] = useState(50)
  const [leftKey] = useState<string>(DEFAULT_LEFT)
  const [rightKey] = useState<string>(DEFAULT_RIGHT)
  const dragging = useRef(false)
  const commune = useApp((s) => s.commune)
  // mode île : pas de GeoJSON (431k features) — le comparateur reste utilisable sans la
  // surcouche parcelles (l'ortho historique est l'objet de l'outil)
  const geo = useQuery({ queryKey: ['geojson', commune], queryFn: getParcelsGeojson, enabled: commune != null })

  useEffect(() => {
    if (!leftRef.current || !rightRef.current || maps.current) return
    const past = mkMap(leftRef.current)
    const now = mkMap(rightRef.current)
    maps.current = [past, now]
    muteTileErrors(past)
    muteTileErrors(now)
    ;(window as unknown as Record<string, unknown>).__labuse_tm = { past, now } // hook QA (synchro)
    let lock = false
    const sync = (src: maplibregl.Map, dst: maplibregl.Map) => () => {
      if (lock) return
      lock = true
      dst.jumpTo({ center: src.getCenter(), zoom: src.getZoom(), bearing: src.getBearing(), pitch: src.getPitch() })
      lock = false
    }
    past.on('move', sync(past, now))
    now.on('move', sync(now, past))
    const addParcels = (m: maplibregl.Map) => m.on('load', () => {
      m.addSource('p', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } as never })
      m.addLayer({ id: 'p', type: 'line', source: 'p',
        filter: ['in', ['get', 'status'], ['literal', ['chaude', 'a_surveiller', 'a_creuser']]],
        paint: { 'line-color': '#5CE6A1', 'line-width': 1 } })
    })
    addParcels(past); addParcels(now)
    if (center) { past.jumpTo({ center, zoom: 17 }) }
    return () => { past.remove(); now.remove(); maps.current = null }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Fond de gauche / de droite : posés au montage, ré-échangés sur place si le choix change.
  useEffect(() => {
    const m = maps.current?.[0]
    if (m && BASEMAP_SOURCES[leftKey]) applyBasemap(m, BASEMAP_SOURCES[leftKey])
  }, [leftKey])
  useEffect(() => {
    const m = maps.current?.[1]
    if (m && BASEMAP_SOURCES[rightKey]) applyBasemap(m, BASEMAP_SOURCES[rightKey])
  }, [rightKey])

  useEffect(() => {
    for (const m of maps.current ?? []) {
      if (geo.data && m.isStyleLoaded()) (m.getSource('p') as maplibregl.GeoJSONSource | undefined)?.setData(geo.data as never)
      else if (geo.data) m.once('load', () => (m.getSource('p') as maplibregl.GeoJSONSource | undefined)?.setData(geo.data as never))
    }
  }, [geo.data])

  useEffect(() => {
    const t = setTimeout(() => maps.current?.forEach((m) => m.resize()), 60)
    return () => clearTimeout(t)
  }, [split])

  return (
    <div
      className="relative min-w-0 flex-1 select-none"
      onMouseMove={(e) => {
        if (!dragging.current) return
        const r = (e.currentTarget as HTMLElement).getBoundingClientRect()
        setSplit(Math.min(92, Math.max(8, ((e.clientX - r.left) / r.width) * 100)))
      }}
      onMouseUp={() => { dragging.current = false }}
      onMouseLeave={() => { dragging.current = false }}
    >
      <div ref={leftRef} className="absolute inset-0" />
      <div ref={rightRef} className="absolute inset-0" style={{ clipPath: `inset(0 0 0 ${split}%)` }} />
      {/* poignée */}
      <div className="absolute inset-y-0 z-10 w-[2px] bg-mint" style={{ left: `${split}%` }}>
        <button
          onMouseDown={() => { dragging.current = true }}
          className="absolute left-1/2 top-1/2 flex h-10 w-10 -translate-x-1/2 -translate-y-1/2 cursor-ew-resize items-center justify-center rounded-full border border-mint bg-[#0F1A14] text-mint"
          title="Glisser pour comparer"
        >
          ⇔
        </button>
      </div>
      <span className="absolute bottom-3 left-3 rounded-full border border-line-2 bg-surface-2 px-3 py-1 font-mono text-[11px] text-txt">{basemapLabel(leftKey)}</span>
      <span className="absolute bottom-3 right-3 rounded-full border border-line-2 bg-surface-2 px-3 py-1 font-mono text-[11px] text-txt">{basemapLabel(rightKey)}</span>
    </div>
  )
}
