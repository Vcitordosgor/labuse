// IMPLANTATION-4 (LOT A) — LA CARTE INTÉGRÉE de l'écran Étude dans Docs. L'Étude vit désormais dans un
// overlay plein écran (patron BilanEcran) qui MASQUE la carte de fond ; le plan masse a donc besoin de
// SA carte, embarquée dans l'overlay. Ce composant est une instance MapLibre AUTONOME (sa propre source
// + ses propres calques `etude-*`, copiés AU TRAIT de MapView), qui ne touche JAMAIS la carte globale
// (aucun setModuleMap). Elle ne fait qu'AFFICHER le GeoJSON déjà servi par l'Étude (actif.geojson filtré
// par couche cochée) : aucun second calcul, aucune requête — le fond ortho (proxy) donne le contexte.
import { useEffect, useRef } from 'react'
import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { FeatureCollection } from 'geojson'
import { reglerWorkerMaplibre } from '../map/maplibreWorker'
import { BASEMAP_SOURCES } from '../map/basemaps'

type FC = FeatureCollection
const EMPTY_FC = { type: 'FeatureCollection', features: [] } as const
const ILE_BOUNDS: [number, number, number, number] = [55.20, -21.42, 55.87, -20.85]

// Calques du plan masse — MÊMES filtres `kind` + MÊME palette que MapView (etude-*), pour que le plan
// soit identique à l'ancien écran Outils. Parcelle / voie / assiette toujours dessinés ; le reste est
// filtré en amont (l'Étude n'injecte que les `kind` des couches cochées).
function ajouterCalquesPlan(m: maplibregl.Map): void {
  m.addSource('plan', { type: 'geojson', data: EMPTY_FC as never })
  const F = (kind: string) => ['==', ['get', 'kind'], kind] as never
  m.addLayer({ id: 'p-zone-fill', type: 'fill', source: 'plan', filter: F('zone'), paint: { 'fill-color': '#4ADE80', 'fill-opacity': 0.1 } })
  m.addLayer({ id: 'p-zone-line', type: 'line', source: 'plan', filter: F('zone'), paint: { 'line-color': '#15803D', 'line-width': 1.4, 'line-dasharray': [3, 2] } })
  m.addLayer({ id: 'p-ppr-rouge', type: 'fill', source: 'plan', filter: F('ppr_rouge'), paint: { 'fill-color': '#DC2626', 'fill-opacity': 0.22 } })
  m.addLayer({ id: 'p-ppr-bleue', type: 'fill', source: 'plan', filter: F('ppr_bleue'), paint: { 'fill-color': '#3B82F6', 'fill-opacity': 0.16 } })
  m.addLayer({ id: 'p-libre', type: 'fill', source: 'plan', filter: F('espace_libre'), paint: { 'fill-color': '#BBF7D0', 'fill-opacity': 0.55 } })
  m.addLayer({ id: 'p-allee', type: 'fill', source: 'plan', filter: F('allee'), paint: { 'fill-color': '#D1D5DB', 'fill-opacity': 0.9 } })
  m.addLayer({ id: 'p-acces', type: 'fill', source: 'plan', filter: F('acces'), paint: { 'fill-color': '#B45309', 'fill-opacity': 0.85 } })
  m.addLayer({ id: 'p-place', type: 'fill', source: 'plan', filter: F('place'), paint: { 'fill-color': '#FFFFFF', 'fill-opacity': 0.9 } })
  m.addLayer({ id: 'p-place-line', type: 'line', source: 'plan', filter: F('place'), paint: { 'line-color': '#6B7280', 'line-width': 0.5 } })
  m.addLayer({ id: 'p-bati', type: 'fill', source: 'plan', filter: F('batiment_emprise'), paint: { 'fill-color': '#1F2A24', 'fill-opacity': 0.88 } })
  m.addLayer({ id: 'p-coursive', type: 'fill', source: 'plan', filter: F('coursive'), paint: { 'fill-color': '#E5E7EB', 'fill-opacity': 0.6 } })
  m.addLayer({ id: 'p-module', type: 'fill', source: 'plan', filter: F('module'), paint: { 'fill-color': '#ECFDF3', 'fill-opacity': 0.72 } })
  m.addLayer({ id: 'p-module-line', type: 'line', source: 'plan', filter: F('module'), paint: { 'line-color': '#15803D', 'line-width': 0.5 } })
  m.addLayer({ id: 'p-noyau', type: 'fill', source: 'plan', filter: F('noyau'), paint: { 'fill-color': '#9CA3AF', 'fill-opacity': 0.9 } })
  m.addLayer({ id: 'p-voie', type: 'line', source: 'plan', filter: F('voie'), paint: { 'line-color': '#B45309', 'line-width': 3, 'line-opacity': 0.9 } })
  m.addLayer({ id: 'p-parcelle', type: 'line', source: 'plan', filter: F('parcelle'), paint: { 'line-color': '#9CA3AF', 'line-width': 0.7, 'line-dasharray': [3, 2] } })
  m.addLayer({ id: 'p-assiette', type: 'line', source: 'plan', filter: F('assiette'), paint: { 'line-color': '#DC2626', 'line-width': 1.6, 'line-dasharray': [4, 2.5] } })
}

// Emprise du GeoJSON ([lon,lat], tous types confondus) — même balayage récursif que MapView (fit).
function bbox(fc: FC): [[number, number], [number, number]] | null {
  let minX = 180, minY = 90, maxX = -180, maxY = -90, seen = false
  const scan = (co: unknown): void => {
    if (!Array.isArray(co)) return
    if (typeof co[0] === 'number' && typeof co[1] === 'number') {
      const [x, y] = co as [number, number]
      if (x < minX) minX = x; if (x > maxX) maxX = x
      if (y < minY) minY = y; if (y > maxY) maxY = y; seen = true
      return
    }
    for (const c of co) scan(c)
  }
  for (const feat of fc.features) scan((feat.geometry as { coordinates?: unknown } | null)?.coordinates)
  return seen && maxX >= minX && maxY >= minY ? [[minX, minY], [maxX, maxY]] : null
}

export function PlanMasseCarte({ fc, className }: { fc: FC | null; className?: string }) {
  const ref = useRef<HTMLDivElement | null>(null)
  const map = useRef<maplibregl.Map | null>(null)
  const pret = useRef(false)

  // création unique (l'instance vit le temps de l'overlay, détruite au démontage).
  useEffect(() => {
    if (!ref.current || map.current) return
    reglerWorkerMaplibre()
    const ortho = BASEMAP_SOURCES['bm-ortho-now']
    const m = new maplibregl.Map({
      container: ref.current,
      // fond sombre (canvas) + ortho Express via le proxy backend : le plan masse se lit sur la photo,
      // sans dépendre d'une clé ni d'un service tiers (même source que la carte principale).
      style: {
        version: 8,
        sources: { ortho: { type: 'raster', tiles: ortho.tiles, tileSize: 256, attribution: ortho.attribution, maxzoom: ortho.maxzoom } },
        layers: [
          { id: 'bg', type: 'background', paint: { 'background-color': '#06130C' } },
          { id: 'ortho', type: 'raster', source: 'ortho' },
        ],
      },
      bounds: ILE_BOUNDS,
      attributionControl: false,
      maxBounds: [54.9, -21.6, 56.1, -20.6],
      minZoom: 8, maxZoom: 19,
    })
    map.current = m
    m.on('error', (e) => { const msg = String(e.error?.message ?? ''); if (/AJAXError|40[04]/.test(msg)) return; console.error(e.error ?? e) })
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
    m.on('load', () => { ajouterCalquesPlan(m); pret.current = true; poser() })
    return () => { pret.current = false; m.remove(); map.current = null }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // données + cadrage — rejoués à chaque changement de plan (onglet A/B/C, couche cochée).
  const poser = () => {
    const m = map.current
    if (!m || !pret.current) return
    const data = (fc ?? EMPTY_FC) as FC
    ;(m.getSource('plan') as maplibregl.GeoJSONSource | undefined)?.setData(data as never)
    const b = fc ? bbox(data) : null
    if (b) m.fitBounds(b, { padding: 36, maxZoom: 18, duration: 600 })
  }
  useEffect(poser, [fc])   // eslint-disable-line react-hooks/exhaustive-deps

  return <div ref={ref} data-plan-masse-carte className={className ?? 'h-full w-full'} />
}
