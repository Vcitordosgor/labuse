// Helper : (lon, lat, zoom) → {z,x,y} tuile XYZ (Web Mercator), partagé par les sweeps.
export function tile(lon, lat, z) {
  const n = 2 ** z
  const x = Math.floor(((lon + 180) / 360) * n)
  const latRad = (lat * Math.PI) / 180
  const y = Math.floor(((1 - Math.asinh(Math.tan(latRad)) / Math.PI) / 2) * n)
  return { z, x, y }
}
// Ancres La Réunion
export const REUNION_ILE = { lon: 55.53, lat: -21.13 }      // centre île (vue z9)
export const STDENIS_RUE = { lon: 55.448, lat: -20.882 }    // Saint-Denis, ~ témoin AN0347 (vue z14)
