type Pt = [number, number]
export const cleImplantation = (idu: string) => 'gabarit-implantation-v1:'+idu

export function lireImplantation(idu: string) {
  try {
    const v = JSON.parse(localStorage.getItem(cleImplantation(idu)) ?? 'null')
    if (Array.isArray(v?.pts) && v.pts.length <= 256 && v.pts.every((pt: unknown) =>
      Array.isArray(pt) && pt.length === 2 && pt.every(Number.isFinite))) {
      return { pts: v.pts as Pt[], ferme: v.ferme === true && v.pts.length >= 3 }
    }
  } catch { /* Le dessin reste utilisable si le stockage local est indisponible. */ }
  return { pts: [] as Pt[] as Pt[], ferme: false }
}
