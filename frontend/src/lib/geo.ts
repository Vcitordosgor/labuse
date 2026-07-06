// Géométrie légère (pas de turf) : distances, aires, point-dans-polygone, centroïdes.
// Échelle communale (< 30 km) → approximations planes locales largement suffisantes.

const R = 6_371_000 // rayon terrestre (m)

export type LngLat = [number, number]

/** Distance haversine (m). */
export function haversine(a: LngLat, b: LngLat): number {
  const φ1 = (a[1] * Math.PI) / 180
  const φ2 = (b[1] * Math.PI) / 180
  const dφ = φ2 - φ1
  const dλ = ((b[0] - a[0]) * Math.PI) / 180
  const s = Math.sin(dφ / 2) ** 2 + Math.cos(φ1) * Math.cos(φ2) * Math.sin(dλ / 2) ** 2
  return 2 * R * Math.asin(Math.sqrt(s))
}

export const pathLength = (pts: LngLat[]) =>
  pts.slice(1).reduce((acc, p, i) => acc + haversine(pts[i], p), 0)

/** Aire d'un polygone (m²) — shoelace en projection locale équirectangulaire. */
export function polygonArea(pts: LngLat[]): number {
  if (pts.length < 3) return 0
  const lat0 = (pts[0][1] * Math.PI) / 180
  const mPerLng = (Math.PI / 180) * R * Math.cos(lat0)
  const mPerLat = (Math.PI / 180) * R
  let s = 0
  for (let i = 0; i < pts.length; i++) {
    const [x1, y1] = pts[i]
    const [x2, y2] = pts[(i + 1) % pts.length]
    s += x1 * mPerLng * (y2 * mPerLat) - x2 * mPerLng * (y1 * mPerLat)
  }
  return Math.abs(s / 2)
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

export const fmtDistance = (m: number) => (m >= 1000 ? `${(m / 1000).toFixed(2)} km` : `${Math.round(m)} m`)
export const fmtArea = (m2: number) =>
  m2 >= 10_000 ? `${(m2 / 10_000).toFixed(2)} ha` : `${Math.round(m2).toLocaleString('fr-FR')} m²`
