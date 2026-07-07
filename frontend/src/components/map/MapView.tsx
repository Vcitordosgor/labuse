import { useQuery } from '@tanstack/react-query'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useRef, useState } from 'react'
import { getCommunes, getFiche, getMapLayer, getParcelsGeojson } from '../../lib/api'
import { fmtArea, fmtDistance, pathLength, polygonArea, roughCentroid, type LngLat } from '../../lib/geo'
import { useApp, type Filters, type MapTool } from '../../store/useApp'
import { Legend } from './Legend'
import { MapToolbar } from './MapToolbar'

// ── Fonds de plan. Géoplateforme IGN (tuiles libres « essentiels », TESTÉES sur le 974) ; pas de
// tuiles Google (CGU) — le deep-link « Ouvrir dans Google Maps » vit dans la fiche.
const WMTS = (layer: string, format: string) =>
  `https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&STYLE=normal&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&LAYER=${layer}&FORMAT=${format}`
const BASEMAP_SOURCES: Record<string, { tiles: string[]; attribution: string; maxzoom?: number }> = {
  'bm-carto': {
    tiles: ['https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png', 'https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png'],
    attribution: '© OSM · CARTO',
  },
  'bm-plan': { tiles: [WMTS('GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2', 'image/png')], attribution: '© IGN Géoplateforme' },
  'bm-ortho-now': { tiles: [WMTS('ORTHOIMAGERY.ORTHOPHOTOS', 'image/jpeg')], attribution: '© IGN BD ORTHO' },
  'bm-ortho-2000': { tiles: [WMTS('ORTHOIMAGERY.ORTHOPHOTOS2000-2005', 'image/jpeg')], attribution: '© IGN ortho 2000-2005', maxzoom: 17 },
  'bm-ortho-1950': { tiles: [WMTS('ORTHOIMAGERY.ORTHOPHOTOS.1950-1965', 'image/png')], attribution: '© IGN ortho 1950-1965', maxzoom: 15 },
}

const STYLE: maplibregl.StyleSpecification = {
  version: 8,
  glyphs: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/{fontstack}/{range}.pbf',
  sources: {},
  layers: [{ id: 'bg', type: 'background', paint: { 'background-color': '#060A08' } }],
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
  if (f.statuts.length) c.push(['in', ['get', 'status'], ['literal', f.statuts]])
  if (f.scoreMin != null) c.push(['>=', ['coalesce', ['get', 'q_score'], 0], f.scoreMin])
  if (f.surfaceMin != null) c.push(['>=', ['coalesce', ['get', 'surface_m2'], 0], f.surfaceMin])
  if (f.surfaceMax != null) c.push(['<=', ['coalesce', ['get', 'surface_m2'], 0], f.surfaceMax])
  if (f.sdpMin != null) c.push(['>=', ['coalesce', ['get', 'sdp_residuelle_m2'], -1], f.sdpMin])
  if (f.evenement) c.push(['==', ['get', 'evenement'], 'rouge'])
  if (f.vueMer) c.push(['==', ['get', 'vue_mer'], 'oui'])
  if (f.flags.length) c.push(['any', ...f.flags.map((fl) => ['in', fl, ['get', 'flags']] as maplibregl.ExpressionSpecification)])
  return ['all', ...c] as maplibregl.FilterSpecification
}

const SP_BOUNDS: [number, number, number, number] = [55.21, -21.14, 55.35, -20.97]
const ILE_BOUNDS: [number, number, number, number] = [55.20, -21.42, 55.87, -20.85]
const EMPTY_FC = { type: 'FeatureCollection', features: [] } as const

const OVERLAYS = {
  zonage: {
    paint: {
      'fill-color': ['case',
        ['in', ['slice', ['upcase', ['coalesce', ['get', 'subtype'], '']], 0, 1], ['literal', ['U']]],
        '#5CE6A1', '#8a6b3f'] as unknown as maplibregl.ExpressionSpecification,
      'fill-opacity': 0.10,
    },
  },
  ppr: { paint: { 'fill-color': '#E8695A', 'fill-opacity': 0.14 } },
  parc: { paint: { 'fill-color': '#4ADE96', 'fill-opacity': 0.10 } },
  anru: { paint: { 'fill-color': '#8FB4F0', 'fill-opacity': 0.16 } },
} as const

//: ÉQUIPEMENTS (contexte promotrice, affichage seul) — 5 catégories, couleurs différenciées
const EQUIP_CATS = ['mairie', 'ecole', 'sante', 'police', 'sport'] as const
const EQUIP_COLOR: maplibregl.ExpressionSpecification = ['match', ['get', 'subtype'],
  'mairie', '#B497F0', 'ecole', '#5CE6A1', 'sante', '#E8695A', 'police', '#8FB4F0', 'sport', '#E8B44C', '#8FA69A']

/** Machine à mesurer : points cliqués + rendu geojson + lecture (distance/surface/alti/zone). */
interface Measure {
  pts: LngLat[]
  alti: { pt: LngLat; z: number } | null
}

export function MapView() {
  const ref = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map | null>(null)
  const ready = useRef(false)
  const [mapReady, setMapReady] = useState(false) // state : re-déclenche les effets APRÈS le load (remontage CRM→cartes)
  const { mode, selectedIdu, select, filters, layers, basemap, orthoYear, terrain3d, tool, setTool, zone, setZone, moduleMap, flyTo, setFlyTo, commune } = useApp()
  const ile = commune == null
  const toolRef = useRef<MapTool | null>(null)
  toolRef.current = tool
  const [measure, setMeasure] = useState<Measure>({ pts: [], alti: null })
  const measureRef = useRef(measure)
  measureRef.current = measure
  const labelMarker = useRef<maplibregl.Marker | null>(null)

  const geo = useQuery({ queryKey: ['geojson', commune], queryFn: getParcelsGeojson, enabled: !ile })
  const zonage = useQuery({ queryKey: ['layer', 'zonage', commune], queryFn: () => getMapLayer('plu_gpu_zone'), enabled: layers.zonage && !ile })
  const ppr = useQuery({ queryKey: ['layer', 'ppr', commune], queryFn: () => getMapLayer('ppr'), enabled: layers.ppr && !ile })
  const parc = useQuery({ queryKey: ['layer', 'parc', commune], queryFn: () => getMapLayer('parc_national'), enabled: layers.parc && !ile })
  const anru = useQuery({ queryKey: ['layer', 'anru', commune], queryFn: () => getMapLayer('anru'), enabled: layers.anru && !ile })
  const equip = useQuery({ queryKey: ['layer', 'equip', commune], queryFn: () => getMapLayer('amenite'), enabled: layers.equipements && !ile })
  const communes = useQuery({ queryKey: ['communes'], queryFn: getCommunes })

  // ───────────────────────── init ─────────────────────────
  useEffect(() => {
    if (!ref.current || map.current) return
    const m = new maplibregl.Map({
      container: ref.current,
      style: STYLE,
      // île par défaut ; une commune restaurée par l'URL cadre directement chez elle (Saint-Paul
      // connu statiquement, les autres via fitBounds dès que /communes répond)
      bounds: useApp.getState().commune == null ? ILE_BOUNDS
        : useApp.getState().commune === 'Saint-Paul' ? SP_BOUNDS : ILE_BOUNDS,
      fitBoundsOptions: { padding: 40 },
      attributionControl: false,
      maxPitch: 70,
    })
    map.current = m
    // tuiles hors-emprise (océan) : l'IGN répond 400 → bruit inévitable, avalé ici pour que la
    // console ne montre que les VRAIES erreurs (règle d'inspection : zéro ligne rouge parasite)
    m.on('error', (e) => {
      const msg = String((e as { error?: Error }).error?.message ?? '')
      if (/AJAXError|40[04]/.test(msg)) return
      console.error(e.error ?? e)
    })
    m.on('load', () => {
      // fonds de plan (tous chargés, visibilité pilotée)
      for (const [id, src] of Object.entries(BASEMAP_SOURCES)) {
        m.addSource(id, { type: 'raster', tiles: src.tiles, tileSize: 256, attribution: src.attribution, ...(src.maxzoom ? { maxzoom: src.maxzoom } : {}) })
        m.addLayer({ id, type: 'raster', source: id, layout: { visibility: id === 'bm-carto' ? 'visible' : 'none' },
          paint: { 'raster-opacity': id === 'bm-carto' ? 0.55 : 1 } })
      }
      // MNT (relief 3D) — terrarium AWS (libre)
      m.addSource('dem', { type: 'raster-dem', encoding: 'terrarium', tileSize: 256, maxzoom: 13,
        tiles: ['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'] })

      m.addSource('parcels', { type: 'geojson', data: EMPTY_FC as never, promoteId: 'idu' })
      for (const k of Object.keys(OVERLAYS)) m.addSource(`ov-${k}`, { type: 'geojson', data: EMPTY_FC as never })
      for (const [k, o] of Object.entries(OVERLAYS)) {
        m.addLayer({ id: `ov-${k}`, type: 'fill', source: `ov-${k}`, layout: { visibility: 'none' }, paint: o.paint as never })
      }
      m.addLayer({ id: 'parcels-fill', type: 'fill', source: 'parcels', paint: { 'fill-color': STATUS_COLOR, 'fill-opacity': STATUS_OPACITY } })
      // contours : promues (statut) OU toutes (couche « limites parcelles »)
      m.addLayer({ id: 'parcels-limites', type: 'line', source: 'parcels', layout: { visibility: 'none' },
        paint: { 'line-color': '#8FA69A', 'line-width': 0.3, 'line-opacity': 0.4 } })
      m.addLayer({ id: 'parcels-line', type: 'line', source: 'parcels', filter: PROMUES_FILTER, paint: { 'line-color': STATUS_COLOR, 'line-width': 0.6, 'line-opacity': 0.9 } })
      m.addLayer({
        id: 'parcels-vuemer', type: 'line', source: 'parcels', layout: { visibility: 'none' },
        filter: ['all', PROMUES_FILTER, ['==', ['get', 'vue_mer'], 'oui']] as never,
        paint: { 'line-color': '#7DE8E0', 'line-width': 1.4, 'line-opacity': 0.95 },
      })
      m.addLayer({ id: 'parcels-sel', type: 'line', source: 'parcels', filter: ['==', ['get', 'idu'], ''], paint: { 'line-color': '#ECF5EF', 'line-width': 2 } })

      // ── mode ÎLE : calques jumeaux sur tuiles MVT (431k parcelles — le GeoJSON ne tient pas) ──
      m.addSource('parcels-ile', { type: 'vector', minzoom: 10, maxzoom: 15,
        tiles: [`${window.location.origin}/map/tiles/{z}/{x}/{y}.pbf`] })
      const SL = { source: 'parcels-ile', 'source-layer': 'parcels' } as const
      m.addLayer({ id: 'ile-fill', type: 'fill', ...SL, layout: { visibility: 'none' },
        paint: { 'fill-color': STATUS_COLOR, 'fill-opacity': STATUS_OPACITY } })
      m.addLayer({ id: 'ile-limites', type: 'line', ...SL, layout: { visibility: 'none' },
        paint: { 'line-color': '#8FA69A', 'line-width': 0.3, 'line-opacity': 0.4 } })
      m.addLayer({ id: 'ile-line', type: 'line', ...SL, layout: { visibility: 'none' },
        filter: PROMUES_FILTER, paint: { 'line-color': STATUS_COLOR, 'line-width': 0.6, 'line-opacity': 0.9 } })
      m.addLayer({ id: 'ile-vuemer', type: 'line', ...SL, layout: { visibility: 'none' },
        filter: ['all', PROMUES_FILTER, ['==', ['get', 'vue_mer'], 'oui']] as never,
        paint: { 'line-color': '#7DE8E0', 'line-width': 1.4, 'line-opacity': 0.95 } })
      m.addLayer({ id: 'ile-sel', type: 'line', ...SL, layout: { visibility: 'none' },
        filter: ['==', ['get', 'idu'], ''], paint: { 'line-color': '#ECF5EF', 'line-width': 2 } })

      // mesure (ligne + polygone + points + étiquette)
      m.addSource('measure', { type: 'geojson', data: EMPTY_FC as never })
      m.addLayer({ id: 'measure-fill', type: 'fill', source: 'measure', filter: ['==', ['geometry-type'], 'Polygon'], paint: { 'fill-color': '#5CE6A1', 'fill-opacity': 0.12 } })
      m.addLayer({ id: 'measure-line', type: 'line', source: 'measure', filter: ['in', ['geometry-type'], ['literal', ['LineString', 'Polygon']]], paint: { 'line-color': '#5CE6A1', 'line-width': 2, 'line-dasharray': [2, 1.5] } })
      m.addLayer({ id: 'measure-pts', type: 'circle', source: 'measure', filter: ['==', ['geometry-type'], 'Point'], paint: { 'circle-radius': 3.5, 'circle-color': '#5CE6A1', 'circle-stroke-color': '#06130C', 'circle-stroke-width': 1.5 } })

      // calques MODULE (violet) : surlignage de parcelles + géométries propres (lots, permis)
      m.addSource('module-extra', { type: 'geojson', data: EMPTY_FC as never })
      m.addLayer({ id: 'module-hl', type: 'line', source: 'parcels', filter: ['==', ['get', 'idu'], ''],
        paint: { 'line-color': '#B497F0', 'line-width': 1.6, 'line-opacity': 0.95 } })
      m.addLayer({ id: 'ile-hl', type: 'line', source: 'parcels-ile', 'source-layer': 'parcels',
        layout: { visibility: 'none' }, filter: ['==', ['get', 'idu'], ''],
        paint: { 'line-color': '#B497F0', 'line-width': 1.6, 'line-opacity': 0.95 } })
      m.addLayer({ id: 'module-lot', type: 'line', source: 'module-extra',
        filter: ['==', ['get', 'kind'], 'lot'],
        paint: { 'line-color': '#B497F0', 'line-width': 1.8, 'line-dasharray': [2, 1.6] } })
      m.addLayer({ id: 'module-pts', type: 'circle', source: 'module-extra',
        filter: ['==', ['get', 'kind'], 'permis'],
        paint: { 'circle-radius': 4, 'circle-color': '#B497F0', 'circle-opacity': 0.85,
                 'circle-stroke-color': '#120d1d', 'circle-stroke-width': 1.2 } })

      // équipements (points OSM, affichage seul) — cercles colorés, plancher z13 (pas
      // d'icônes par milliers à l'écran), clic = nom de l'équipement
      m.addSource('ov-equip', { type: 'geojson', data: EMPTY_FC as never })
      m.addLayer({ id: 'ov-equip', type: 'circle', source: 'ov-equip', minzoom: 13,
        layout: { visibility: 'none' },
        paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 13, 3, 17, 7],
                 'circle-color': EQUIP_COLOR, 'circle-opacity': 0.9,
                 'circle-stroke-color': '#06130C', 'circle-stroke-width': 1.2 } })
      m.on('click', 'ov-equip', (e) => {
        const f = (e as maplibregl.MapLayerMouseEvent).features?.[0]
        if (!f) return
        const cat = String(f.properties?.subtype ?? '')
        const nom = f.properties?.name && f.properties.name !== 'null' ? String(f.properties.name) : '(sans nom OSM)'
        new maplibregl.Popup({ closeButton: false, className: 'labuse-popup' })
          .setLngLat((e as maplibregl.MapLayerMouseEvent).lngLat)
          .setHTML(`<div style="background:#0F1A14;border:1px solid #2E6B4F;color:#ECF5EF;font:12px Inter,sans-serif;padding:6px 10px;border-radius:8px">${nom}<div style="color:#8FA69A;font-size:10px">${cat}</div></div>`)
          .addTo(m)
      })
      m.on('mouseenter', 'ov-equip', () => { if (!toolRef.current) m.getCanvas().style.cursor = 'pointer' })
      m.on('mouseleave', 'ov-equip', () => { m.getCanvas().style.cursor = toolRef.current ? 'crosshair' : '' })

      // zone dessinée persistante (filtre les résultats)
      m.addSource('zone', { type: 'geojson', data: EMPTY_FC as never })
      m.addLayer({ id: 'zone-fill', type: 'fill', source: 'zone', paint: { 'fill-color': '#5CE6A1', 'fill-opacity': 0.06 } })
      m.addLayer({ id: 'zone-line', type: 'line', source: 'zone', paint: { 'line-color': '#5CE6A1', 'line-width': 1.6, 'line-dasharray': [3, 2] } })

      for (const layerId of ['parcels-fill', 'ile-fill']) {
        m.on('click', layerId, (e) => {
          if (toolRef.current) return // un outil actif consomme le clic
          const f = (e as maplibregl.MapLayerMouseEvent).features?.[0]
          if (!f) return
          const idu = String(f.properties?.idu)
          const st = useApp.getState()
          if (st.module === 'assemblage') {              // M16 : le clic compose l'assiette
            st.setMsel(st.msel.includes(idu) ? st.msel.filter((x) => x !== idu) : [...st.msel, idu])
            return
          }
          select(idu)
        })
        m.on('mouseenter', layerId, () => { if (!toolRef.current) m.getCanvas().style.cursor = 'pointer' })
        m.on('mouseleave', layerId, () => { m.getCanvas().style.cursor = toolRef.current ? 'crosshair' : '' })
      }
      ready.current = true
      setMapReady(true)
      ;(window as unknown as Record<string, unknown>).__labuse_map = m // hook QA (ping sémantique)
      m.fire('labuse:ready' as never)
    })
    return () => { m.remove(); map.current = null; ready.current = false }
  }, [select])

  // ───────────────────────── données ─────────────────────────
  useEffect(() => {
    const m = map.current
    if (m && ready.current && geo.data) (m.getSource('parcels') as maplibregl.GeoJSONSource | undefined)?.setData(geo.data as never)
  }, [geo.data, geo.dataUpdatedAt, mapReady])

  useEffect(() => {
    const m = map.current
    if (!m || !ready.current) return
    const pairs: [string, typeof zonage][] = [['zonage', zonage], ['ppr', ppr], ['parc', parc], ['anru', anru]]
    for (const [k, qy] of pairs) if (qy.data) (m.getSource(`ov-${k}`) as maplibregl.GeoJSONSource | undefined)?.setData(qy.data as never)
    if (equip.data) {
      const feats = equip.data.features.filter((f) => EQUIP_CATS.includes((f.properties as { subtype?: string }).subtype as never))
      ;(m.getSource('ov-equip') as maplibregl.GeoJSONSource | undefined)?.setData({ type: 'FeatureCollection', features: feats } as never)
    }
  }, [zonage.data, ppr.data, parc.data, anru.data, equip.data, mapReady])

  // ───────────────────────── fond de plan + relief ─────────────────────────
  useEffect(() => {
    const m = map.current
    if (!m || !ready.current) return
    const active = basemap === 'dark' ? 'bm-carto' : basemap === 'plan' ? 'bm-plan'
      : orthoYear === '2000' ? 'bm-ortho-2000' : orthoYear === '1950' ? 'bm-ortho-1950' : 'bm-ortho-now'
    for (const id of Object.keys(BASEMAP_SOURCES)) {
      if (m.getLayer(id)) m.setLayoutProperty(id, 'visibility', id === active ? 'visible' : 'none')
    }
    // sur ortho/plan (fonds clairs ou photo), les écartées quasi invisibles gênent moins que le voile sombre
    if (m.getLayer('parcels-fill') && mode === 'verdict') {
      m.setPaintProperty('parcels-fill', 'fill-opacity', filters.statuts.length === 0 ? STATUS_OPACITY : 0.72)
      m.setPaintProperty('ile-fill', 'fill-opacity', filters.statuts.length === 0 ? STATUS_OPACITY : 0.72)
    }
  }, [basemap, orthoYear, mode, filters.statuts, mapReady])

  useEffect(() => {
    const m = map.current
    if (!m || !ready.current) return
    if (terrain3d) {
      m.setTerrain({ source: 'dem', exaggeration: 1.35 })
      if (m.getPitch() < 20) m.easeTo({ pitch: 55, duration: 800 })
    } else {
      m.setTerrain(null)
      m.easeTo({ pitch: 0, duration: 600 })
    }
  }, [terrain3d])

  // ───────────────────────── couches / filtres / mode ─────────────────────────
  useEffect(() => {
    const m = map.current
    if (!m || !ready.current || !m.getLayer('parcels-fill')) return
    const vis = (on: boolean) => (on ? 'visible' : 'none')
    // deux jeux de calques (GeoJSON commune / MVT île) — un seul visible à la fois
    m.setLayoutProperty('parcels-fill', 'visibility', vis(layers.parcelles && !ile))
    m.setLayoutProperty('parcels-line', 'visibility', vis(layers.parcelles && !ile))
    m.setLayoutProperty('parcels-limites', 'visibility', vis(layers.limites && !ile))
    m.setLayoutProperty('parcels-vuemer', 'visibility', vis(layers.vue_mer && layers.parcelles && !ile))
    m.setLayoutProperty('ile-fill', 'visibility', vis(layers.parcelles && ile))
    m.setLayoutProperty('ile-line', 'visibility', vis(layers.parcelles && ile))
    m.setLayoutProperty('ile-limites', 'visibility', vis(layers.limites && ile))
    m.setLayoutProperty('ile-vuemer', 'visibility', vis(layers.vue_mer && layers.parcelles && ile))
    m.setLayoutProperty('ile-sel', 'visibility', vis(ile))
    m.setLayoutProperty('ile-hl', 'visibility', vis(ile))
    m.setLayoutProperty('ov-zonage', 'visibility', vis(layers.zonage && !ile))
    m.setLayoutProperty('ov-ppr', 'visibility', vis(layers.ppr && !ile))
    m.setLayoutProperty('ov-parc', 'visibility', vis(layers.parc && !ile))
    m.setLayoutProperty('ov-anru', 'visibility', vis(layers.anru && !ile))
    m.setLayoutProperty('ov-equip', 'visibility', vis(layers.equipements && !ile))
    const expr = toExpr(filters)
    for (const fill of ['parcels-fill', 'ile-fill']) {
      m.setFilter(fill, expr)
      if (mode === 'mutabilite') {
        m.setPaintProperty(fill, 'fill-color', MUTABILITE_COLOR)
        m.setPaintProperty(fill, 'fill-opacity', 0.7)
      } else {
        m.setPaintProperty(fill, 'fill-color', STATUS_COLOR)
        m.setPaintProperty(fill, 'fill-opacity', filters.statuts.length === 0 ? STATUS_OPACITY : 0.72)
      }
    }
    m.setFilter('parcels-line', ['all', PROMUES_FILTER, expr] as maplibregl.FilterSpecification)
    m.setFilter('ile-line', ['all', PROMUES_FILTER, expr] as maplibregl.FilterSpecification)
  }, [mode, filters, layers, geo.dataUpdatedAt, mapReady, ile])

  // ── VAGUE 0 (île) : sous z10 les tuiles parcellaires ne servent rien — l'île raconte où
  // sont les cibles via UN marqueur par commune (nom + chaudes, dimensionné/coloré), cliquable
  // → bascule le sélecteur (fitBounds existant). Marqueurs DOM (pas de dépendance glyphes).
  const aggMarkers = useRef<maplibregl.Marker[]>([])
  useEffect(() => {
    const m = map.current
    if (!m || !ready.current) return
    aggMarkers.current.forEach((mk) => mk.remove())
    aggMarkers.current = []
    if (!ile || !communes.data) return
    const updateVis = () => {
      const show = m.getZoom() < 10
      aggMarkers.current.forEach((mk) => { mk.getElement().style.display = show ? '' : 'none' })
    }
    for (const c of communes.data) {
      if (!c.bbox || c.bbox[0] == null) continue
      const hot = c.chaudes > 0
      const el = document.createElement('button')
      el.setAttribute('data-commune-marker', c.commune)
      el.title = `${c.commune} — ${c.chaudes} chaude${c.chaudes > 1 ? 's' : ''} · cliquer pour ouvrir la commune`
      el.textContent = `${c.commune.replace(/^(Les|Le|La|L')\s?/, '')} ${c.chaudes > 0 ? c.chaudes : ''}`.trim()
      const size = Math.min(13, 10 + Math.log10(Math.max(1, c.chaudes)) * 2)
      el.style.cssText = `cursor:pointer;white-space:nowrap;border-radius:9999px;padding:2px 9px;` +
        `font:600 ${size}px Inter,sans-serif;border:1px solid ${hot ? '#2E6B4F' : '#26302B'};` +
        `background:${hot ? 'rgba(9,26,18,.92)' : 'rgba(10,14,12,.85)'};color:${hot ? '#5CE6A1' : '#8FA69A'};` +
        (hot ? 'box-shadow:0 0 10px rgba(92,230,161,.25);' : '')
      el.onclick = (e) => { e.stopPropagation(); useApp.getState().setCommune(c.commune) }
      aggMarkers.current.push(new maplibregl.Marker({ element: el })
        .setLngLat([(c.bbox[0] + c.bbox[2]) / 2, (c.bbox[1] + c.bbox[3]) / 2]).addTo(m))
    }
    updateVis()
    m.on('zoom', updateVis)
    return () => { m.off('zoom', updateVis); aggMarkers.current.forEach((mk) => mk.remove()); aggMarkers.current = [] }
  }, [ile, communes.data, mapReady])

  // le bandeau bas ne donne JAMAIS une instruction inexécutable : sous z10 en mode île,
  // aucune parcelle n'est cliquable → « Zoomez ou cliquez une commune »
  const [lowZoom, setLowZoom] = useState(false)
  useEffect(() => {
    const m = map.current
    if (!m || !ready.current) return
    const h = () => setLowZoom(m.getZoom() < 10)
    h()
    m.on('zoom', h)
    return () => { m.off('zoom', h) }
  }, [mapReady])

  // changement de commune → recadrage sur son emprise (bbox servie par /communes)
  useEffect(() => {
    const m = map.current
    if (!m || !ready.current) return
    if (ile) { m.fitBounds(ILE_BOUNDS, { padding: 40, duration: 900 }); return }
    const info = communes.data?.find((c) => c.commune === commune)
    if (info?.bbox) m.fitBounds(info.bbox as [number, number, number, number], { padding: 40, duration: 900 })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [commune, communes.data, mapReady])

  useEffect(() => {
    const m = map.current
    if (!m || !ready.current || !m.getLayer('parcels-sel')) return
    m.setFilter('parcels-sel', ['==', ['get', 'idu'], selectedIdu ?? ''])
    m.setFilter('ile-sel', ['==', ['get', 'idu'], selectedIdu ?? ''])
    // PING SYSTÉMATIQUE : toute sélection (liste, module, CRM, notification) recentre + pulse 2 s
    if (!selectedIdu) return
    const feat = geo.data?.features.find((f) => (f.properties as { idu?: string }).idu === selectedIdu)
    let cancelled = false
    const centroidReady = (c: [number, number] | null) => {
      if (!c || cancelled) return
      m.flyTo({ center: c, zoom: Math.max(m.getZoom(), 16), duration: 800 })
    }
    if (feat) centroidReady(roughCentroid(feat.geometry))
    else {
      // mode île (ou parcelle hors du GeoJSON chargé) : le centroïde vient de la fiche API.
      // CONTRAT (Vic, 07/07) : un clic dans la liste = je VOIS la parcelle pulser, où qu'elle
      // soit — le champ est `coords` [lon, lat] (le fallback lat/lon muet était le bug).
      getFiche(selectedIdu).then((f) => {
        const c = (f as unknown as { coords?: [number, number] }).coords
        if (Array.isArray(c) && c.length === 2) centroidReady([c[0], c[1]])
      }).catch(() => undefined)
    }
    const pingId = geo.data && feat ? 'parcels-ping' : 'ile-ping'
    if (!m.getLayer(pingId)) {
      m.addLayer(pingId === 'parcels-ping'
        ? { id: 'parcels-ping', type: 'line', source: 'parcels',
            filter: ['==', ['get', 'idu'], ''], paint: { 'line-color': '#ECF5EF', 'line-width': 6, 'line-opacity': 0.9, 'line-blur': 3 } }
        : { id: 'ile-ping', type: 'line', source: 'parcels-ile', 'source-layer': 'parcels',
            filter: ['==', ['get', 'idu'], ''], paint: { 'line-color': '#ECF5EF', 'line-width': 6, 'line-opacity': 0.9, 'line-blur': 3 } })
    }
    m.setFilter(pingId, ['==', ['get', 'idu'], selectedIdu])
    let t0: number | null = null
    let raf = 0
    const pulse = (ts: number) => {
      if (t0 == null) t0 = ts
      const dt = (ts - t0) / 1000
      // 3 s : en mode île le vol (800 ms) + le chargement des tuiles à destination doivent
      // laisser un pulse VISIBLE à l'arrivée
      if (dt > 3 || !m.getLayer(pingId)) {
        if (m.getLayer(pingId)) m.setPaintProperty(pingId, 'line-opacity', 0)
        return
      }
      m.setPaintProperty(pingId, 'line-opacity', 0.45 + 0.45 * Math.abs(Math.sin(dt * Math.PI * 2)))
      m.setPaintProperty(pingId, 'line-width', 5 + 4 * Math.abs(Math.sin(dt * Math.PI * 2)))
      raf = requestAnimationFrame(pulse)
    }
    raf = requestAnimationFrame(pulse)
    return () => { cancelAnimationFrame(raf); cancelled = true }
  }, [selectedIdu, geo.data, mapReady])

  // module actif → surlignage + géométries propres (les DEUX jeux de calques)
  useEffect(() => {
    const m = map.current
    if (!m || !ready.current || !m.getLayer('module-hl')) return
    const f = moduleMap.idus.length
      ? (['in', ['get', 'idu'], ['literal', moduleMap.idus.slice(0, 4000)]] as never)
      : (['==', ['get', 'idu'], ''] as never)
    m.setFilter('module-hl', f)
    if (m.getLayer('ile-hl')) m.setFilter('ile-hl', f)
    ;(m.getSource('module-extra') as maplibregl.GeoJSONSource | undefined)?.setData((moduleMap.extra ?? EMPTY_FC) as never)
  }, [moduleMap, mapReady])

  // flyTo demandé (fiche → « 1950 », modules…)
  useEffect(() => {
    if (!flyTo || !map.current) return
    map.current.flyTo({ center: flyTo.center, zoom: flyTo.zoom, duration: 900 })
    setFlyTo(null)
  }, [flyTo, setFlyTo])

  // zone dessinée → tracé persistant sur la carte (le filtre des résultats vit dans la liste)
  useEffect(() => {
    const m = map.current
    if (!m || !ready.current) return
    const data = zone
      ? { type: 'FeatureCollection', features: [{ type: 'Feature', geometry: { type: 'Polygon', coordinates: [[...zone, zone[0]]] }, properties: {} }] }
      : EMPTY_FC
    ;(m.getSource('zone') as maplibregl.GeoJSONSource | undefined)?.setData(data as never)
  }, [zone, mapReady])

  // ───────────────────────── outils de mesure ─────────────────────────
  // rendu du geojson de mesure
  useEffect(() => {
    const m = map.current
    if (!m || !ready.current) return
    const feats: object[] = measure.pts.map((p) => ({ type: 'Feature', geometry: { type: 'Point', coordinates: p }, properties: {} }))
    if (measure.pts.length >= 2) {
      const t = toolRef.current
      if ((t === 'surface' || t === 'zone') && measure.pts.length >= 3) {
        feats.push({ type: 'Feature', geometry: { type: 'Polygon', coordinates: [[...measure.pts, measure.pts[0]]] },
          properties: { label: t === 'surface' ? fmtArea(polygonArea(measure.pts)) : '' } })
      } else {
        feats.push({ type: 'Feature', geometry: { type: 'LineString', coordinates: measure.pts },
          properties: { label: t === 'distance' ? fmtDistance(pathLength(measure.pts)) : '' } })
      }
    }
    if (measure.alti) {
      feats.push({ type: 'Feature', geometry: { type: 'Point', coordinates: measure.alti.pt },
        properties: { label: `${measure.alti.z.toFixed(0)} m` } })
    }
    ;(m.getSource('measure') as maplibregl.GeoJSONSource | undefined)?.setData({ type: 'FeatureCollection', features: feats } as never)

    // étiquette de mesure = marker HTML (pas de glyphes carte → pas de dépendance CORS)
    const t = toolRef.current
    const text = t === 'distance' && measure.pts.length >= 2 ? fmtDistance(pathLength(measure.pts))
      : t === 'surface' && measure.pts.length >= 3 ? fmtArea(polygonArea(measure.pts))
      : measure.alti ? `${measure.alti.z.toFixed(0)} m` : null
    const at = measure.alti?.pt ?? measure.pts[measure.pts.length - 1]
    labelMarker.current?.remove()
    labelMarker.current = null
    if (text && at) {
      const el = document.createElement('div')
      el.textContent = text
      el.style.cssText = 'background:#0F1A14;border:1px solid #5CE6A1;color:#5CE6A1;font:600 11px "JetBrains Mono",monospace;padding:2px 7px;border-radius:9999px;transform:translateY(-14px);white-space:nowrap'
      labelMarker.current = new maplibregl.Marker({ element: el, anchor: 'bottom' }).setLngLat(at).addTo(m)
    }
  }, [measure])

  // interactions outil (clic / double-clic / Échap)
  useEffect(() => {
    const m = map.current
    if (!m || !ready.current) return
    m.getCanvas().style.cursor = tool ? 'crosshair' : ''
    if (tool) m.doubleClickZoom.disable()
    else m.doubleClickZoom.enable()
    if (!tool) return

    const onClick = async (e: maplibregl.MapMouseEvent) => {
      const p: LngLat = [e.lngLat.lng, e.lngLat.lat]
      if (tool === 'alti') {
        try {
          const r = await fetch(`https://data.geopf.fr/altimetrie/1.0/calcul/alti/rest/elevation.json?lon=${p[0]}&lat=${p[1]}&resource=ign_rge_alti_wld`)
          const d = await r.json()
          const z = d?.elevations?.[0]?.z
          if (typeof z === 'number') setMeasure((s) => ({ ...s, alti: { pt: p, z } }))
        } catch { /* réseau : silencieux, le point reste sans étiquette */ }
        return
      }
      setMeasure((s) => ({ ...s, pts: [...s.pts, p] }))
    }
    const onDbl = (e: maplibregl.MapMouseEvent) => {
      e.preventDefault()
      const pts = measureRef.current.pts
      if (tool === 'zone' && pts.length >= 3) {
        setZone(pts)
        setTool(null)
        setMeasure({ pts: [], alti: null })
      }
      // distance/surface : le double-clic fige la mesure (l'outil reste actif pour recommencer)
      if (tool === 'distance' || tool === 'surface') setMeasure((s) => ({ ...s, pts: s.pts }))
    }
    const onKey = (ev: KeyboardEvent) => {
      if (ev.key === 'Escape') { setMeasure({ pts: [], alti: null }); setTool(null) }
    }
    m.on('click', onClick)
    m.on('dblclick', onDbl)
    window.addEventListener('keydown', onKey)
    return () => { m.off('click', onClick); m.off('dblclick', onDbl); window.removeEventListener('keydown', onKey) }
  }, [tool, setTool, setZone])

  // changer d'outil = repartir propre
  useEffect(() => {
    setMeasure({ pts: [], alti: null })
    if (!tool) { labelMarker.current?.remove(); labelMarker.current = null }
  }, [tool])

  const readout = tool === 'distance' && measure.pts.length >= 2 ? fmtDistance(pathLength(measure.pts))
    : tool === 'surface' && measure.pts.length >= 3 ? fmtArea(polygonArea(measure.pts))
    : tool === 'alti' && measure.alti ? `${measure.alti.z.toFixed(1)} m NGR`
    : null

  return (
    <div className="relative min-w-0 flex-1">
      <div ref={ref} className="absolute inset-0" />
      <div className="absolute left-4 top-4 flex flex-col gap-2">
        {(['+', '−'] as const).map((s) => (
          <button key={s} onClick={() => map.current?.[s === '+' ? 'zoomIn' : 'zoomOut']()}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-line-2 bg-surface-2 text-txt hover:text-txt-hi"
            title={s === '+' ? 'Zoomer' : 'Dézoomer'}>
            {s}
          </button>
        ))}
      </div>
      <MapToolbar />
      <Legend />
      {tool && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full border border-mint bg-[#0F1A14] px-4 py-1.5 text-xs text-mint">
          {readout ?? (tool === 'alti' ? 'Cliquez un point pour lire l’altitude'
            : tool === 'zone' ? 'Dessinez la zone — double-clic pour fermer et filtrer'
            : 'Cliquez pour mesurer — Échap pour quitter')}
        </div>
      )}
      {!tool && (
        <div className="pointer-events-none absolute bottom-4 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full border border-line-2 bg-surface-2 px-4 py-1.5 text-xs text-txt-mut">
          {ile && lowZoom ? 'Zoomez ou cliquez une commune pour voir ses parcelles' : 'Cliquez une parcelle pour ouvrir sa fiche'}
        </div>
      )}
      <div className="absolute bottom-2 right-3 font-sans text-[11px] text-[#3E4C45]">
        {basemap === 'dark' ? '© OSM · CARTO' : '© IGN Géoplateforme'}
      </div>
    </div>
  )
}
