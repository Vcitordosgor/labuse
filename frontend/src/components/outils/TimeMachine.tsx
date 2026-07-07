import { useQuery } from '@tanstack/react-query'
import maplibregl from 'maplibre-gl'
import { useEffect, useRef, useState } from 'react'
import { getParcelsGeojson } from '../../lib/api'

const WMTS = (layer: string, format: string) =>
  `https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&STYLE=normal&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&LAYER=${layer}&FORMAT=${format}`
const SP_BOUNDS: [number, number, number, number] = [55.21, -21.14, 55.35, -20.97]

function mkMap(el: HTMLDivElement, tiles: string, attribution: string, maxzoom = 19) {
  return new maplibregl.Map({
    container: el,
    style: {
      version: 8, sources: { bm: { type: 'raster', tiles: [tiles], tileSize: 256, attribution, maxzoom } },
      layers: [{ id: 'bg', type: 'background', paint: { 'background-color': '#060A08' } },
               { id: 'bm', type: 'raster', source: 'bm' }],
    },
    bounds: SP_BOUNDS, fitBoundsOptions: { padding: 40 }, attributionControl: false,
  })
}

function muteTileErrors(m: maplibregl.Map) {
  m.on('error', (e) => {
    const msg = String((e as { error?: Error }).error?.message ?? '')
    if (/AJAXError|40[04]/.test(msg)) return
    console.error(e.error ?? e)
  })
}

/** M08 — comparateur AVANT/APRÈS : deux cartes superposées, la moderne rognée par la poignée.
 *  Caméras synchronisées dans les deux sens (garde anti-boucle). Parcelles promues des deux côtés. */
export function TimeMachine({ center }: { center?: [number, number] | null }) {
  const leftRef = useRef<HTMLDivElement>(null)
  const rightRef = useRef<HTMLDivElement>(null)
  const maps = useRef<[maplibregl.Map, maplibregl.Map] | null>(null)
  const [split, setSplit] = useState(50)
  const dragging = useRef(false)
  const geo = useQuery({ queryKey: ['geojson'], queryFn: getParcelsGeojson })

  useEffect(() => {
    if (!leftRef.current || !rightRef.current || maps.current) return
    const past = mkMap(leftRef.current, WMTS('ORTHOIMAGERY.ORTHOPHOTOS.1950-1965', 'image/png'), '© IGN 1950-1965', 15) // le millésime 1950 s'arrête ~z15 : overzoom plutôt que NOIR
    const now = mkMap(rightRef.current, WMTS('ORTHOIMAGERY.ORTHOPHOTOS', 'image/jpeg'), '© IGN BD ORTHO')
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
      <span className="absolute bottom-3 left-3 rounded-full border border-line-2 bg-surface-2 px-3 py-1 font-mono text-[11px] text-txt">1950-1965</span>
      <span className="absolute bottom-3 right-3 rounded-full border border-line-2 bg-surface-2 px-3 py-1 font-mono text-[11px] text-txt">aujourd'hui</span>
    </div>
  )
}
