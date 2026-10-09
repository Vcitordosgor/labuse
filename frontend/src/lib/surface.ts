/** CONTENANCE-1 (Lot B) — LA source unique de « la surface du terrain » côté client.
 *
 *  `surface_m2` = aire du DESSIN du plan cadastral (ST_Area). `contenance_m2` / `surface_terrain_m2`
 *  = contenance cadastrale, le chiffre de l'acte. Décision de Vic : la surface affichée au client,
 *  c'est la CONTENANCE si on l'a, sinon le dessin (mention « mesurée sur le plan »). Le dessin ne
 *  sert plus qu'aux formes.
 *
 *  Tout écran/liste/filtre/tri passe par `surfaceTerrain(p)`. Plus personne ne lit `p.surface_m2`
 *  seul pour afficher une surface de terrain. */

export type SurfaceSource = 'cadastre' | 'plan'

/** Objet minimal portant une surface de parcelle (sur-ensemble toléré). */
export type AvecSurface = {
  surface_terrain_m2?: number | null
  surface_m2?: number | null
  surface_dessin_m2?: number | null
  surface_source?: SurfaceSource | null
  contenance_m2?: number | null
} | null | undefined

/** La surface du terrain à afficher : contenance si présente, sinon dessin (repli). */
export function surfaceTerrain(p: AvecSurface): number | null {
  if (p == null) return null
  if (p.surface_terrain_m2 != null) return p.surface_terrain_m2
  if (p.contenance_m2 != null) return p.contenance_m2
  return p.surface_m2 ?? null
}

/** L'aire du dessin du plan (pour la ligne discrète « Dessin du plan »). */
export function surfaceDessin(p: AvecSurface): number | null {
  if (p == null) return null
  return p.surface_dessin_m2 ?? p.surface_m2 ?? null
}

/** Provenance de la surface affichée : 'cadastre' (acte) ou 'plan' (repli mesuré). */
export function surfaceSource(p: AvecSurface): SurfaceSource {
  if (p == null) return 'plan'
  if (p.surface_source === 'cadastre' || p.surface_source === 'plan') return p.surface_source
  return p.contenance_m2 != null || p.surface_terrain_m2 != null ? 'cadastre' : 'plan'
}

/** Écart relatif dessin↔terrain, en % du terrain (null si l'une manque). Sert à décider si on
 *  montre la ligne discrète « Dessin du plan » (B3 : masquée sous 1 %). */
export function ecartDessinPct(p: AvecSurface): number | null {
  const t = surfaceTerrain(p)
  const d = surfaceDessin(p)
  if (t == null || d == null || t === 0) return null
  return (100 * (d - t)) / t
}

/** La contenance diffère-t-elle assez du dessin pour mériter la ligne « Dessin du plan » ? (≥ 1 %) */
export function montrerDessin(p: AvecSurface): boolean {
  if (surfaceSource(p) !== 'cadastre') return false
  const e = ecartDessinPct(p)
  return e != null && Math.abs(e) >= 1
}
