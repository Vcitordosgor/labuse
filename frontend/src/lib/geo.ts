import { Geodesic } from 'geographiclib-geodesic'

export type LngLat = [number, number]

/** Longueur horizontale du tracé sur l’ellipsoïde WGS84, en mètres. */
export function pathLength(pts: LngLat[]): number {
  const line = Geodesic.WGS84.Polygon(true)
  for (const [lng, lat] of pts) line.AddPoint(lat, lng)
  return line.Compute(false, true).perimeter
}

/** Aire horizontale du contour sur WGS84, en mètres carrés. */
export function polygonArea(pts: LngLat[]): number {
  const polygon = Geodesic.WGS84.Polygon()
  for (const [lng, lat] of pts) polygon.AddPoint(lat, lng)
  return Math.abs(polygon.Compute(false, true).area!)
}

/** Point dans polygone (ray casting). */
export function pointInPolygon(p: LngLat, poly: LngLat[]): boolean {
  let inside = false
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i]
    const [xj, yj] = poly[j]
    if (yi > p[1] !== yj > p[1] && p[0] < ((xj - xi) * (p[1] - yi)) / (yj - yi) + xi) inside = !inside
  }
  return inside
}

/** Centroïde approx d'une géométrie GeoJSON Polygon/MultiPolygon (moyenne de l'anneau extérieur). */
export function roughCentroid(geometry: unknown): LngLat | null {
  const g = geometry as { type?: string; coordinates?: unknown }
  let ring: number[][] | undefined
  if (g?.type === 'Polygon') ring = (g.coordinates as number[][][])?.[0]
  else if (g?.type === 'MultiPolygon') ring = (g.coordinates as number[][][][])?.[0]?.[0]
  if (!ring?.length) return null
  let x = 0
  let y = 0
  for (const [lng, lat] of ring) { x += lng; y += lat }
  return [x / ring.length, y / ring.length]
}

const deuxDecimales = new Intl.NumberFormat('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

export const fmtDistance = (m: number) => (m >= 1000 ? `${deuxDecimales.format(m / 1000)} km` : `${Math.round(m)} m`)
export const fmtArea = (m2: number) =>
  m2 >= 10_000 ? `${deuxDecimales.format(m2 / 10_000)} ha` : `${Math.round(m2).toLocaleString('fr-FR')} m²`
