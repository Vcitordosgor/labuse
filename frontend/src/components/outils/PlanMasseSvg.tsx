// IMPLANTATION-4 (suite) — LE PLAN MASSE de l'écran Étude, DESSINÉ (plus de carte). L'Étude vit dans un
// overlay Docs qui n'a plus de fond cartographique ; le plan masse est donc un dessin SVG tiré de la
// géométrie du scénario — LE MÊME rendu que le PDF (exports/etude_faisabilite.py `_svg_plan`), reproduit
// ici au trait : projection équirectangulaire locale (x corrigé par cos(lat)), cadrée sur l'emprise des
// features, y inversé (nord en haut), même z-order. Aucun calcul, aucune requête : on ne fait que
// projeter le GeoJSON déjà servi (actif.geojson), filtré en amont par couche cochée. Fond sombre (thème
// de l'app), palette dérivée de celle du PDF adaptée au sombre (bâtiment clair, places/allées sombres).
import { useEffect, useMemo, useRef, type ReactElement } from 'react'
import type { FeatureCollection, Geometry } from 'geojson'

type FC = FeatureCollection

// Palette écran = palette PDF (_COUL) adaptée au fond sombre : bâtiment clair #E8EDEA (maquette),
// places/allées sombres (lisibles sur #0F1311), reculs/PPR/espaces libres en aplats translucides.
const COUL: Record<string, [string | null, string]> = {
  parcelle: [null, '#9AA0A6'],
  assiette: [null, '#DC2626'],
  zone: ['#4ADE80', '#15803D'],
  espace_libre: ['#4ADE80', '#86EFAC'],
  allee: ['#2E3631', '#3A423C'],
  place: ['#0F1311', '#8A948E'],
  acces: ['#F59E0B', '#F59E0B'],
  batiment_emprise: ['#E8EDEA', '#E8EDEA'],
  noyau: ['#9CA3AF', '#4B5563'],
  coursive: ['#E5E7EB', '#9CA3AF'],
  module: ['#ECFDF3', '#15803D'],
  voie: [null, '#B45309'],
  ppr_rouge: ['#DC2626', '#991B1B'],
  ppr_bleue: ['#3B82F6', '#1D4ED8'],
  // ETUDE-V6 (Lot D) — lotissement : lot à bâtir (vert clair, liseré mint) et EBC (vert boisé translucide).
  lot: ['#ECFDF3', '#15803D'],
  ebc: ['#16A34A', '#166534'],
  // ETUDE-V6-4 (item 9) — niveau −1 DESSINÉ : emprise enterrée (contour), places et allée du sous-sol,
  // rampe d'accès. Dessinés sur la vraie géométrie, projetés comme le reste du plan.
  sous_sol_emprise: ['#1E293B', '#64748B'],
  place_ss: ['#0F1311', '#8A948E'],
  allee_ss: ['#2E3631', '#3A423C'],
  rampe: ['#78350F', '#F59E0B'],
}
// ordre de dessin (z-order) — contexte terrain d'abord, objets du plan ensuite (identique au PDF).
const Z = ['parcelle', 'assiette', 'ppr_rouge', 'ppr_bleue', 'zone', 'espace_libre', 'ebc',
  'sous_sol_emprise', 'allee', 'allee_ss', 'acces', 'place', 'place_ss', 'rampe', 'lot',
  'batiment_emprise', 'coursive', 'noyau', 'module', 'voie']
const TRANSLUCIDE = new Set(['zone', 'ppr_rouge', 'ppr_bleue', 'espace_libre', 'ebc', 'sous_sol_emprise'])

function ringsOf(g: Geometry): number[][][] {
  if (g.type === 'Polygon') return g.coordinates as number[][][]
  if (g.type === 'MultiPolygon') return (g.coordinates as number[][][][]).flat()
  if (g.type === 'LineString') return [g.coordinates as number[][]]
  return []
}

// IMPLANTATION-4 (planche) — quand le serveur fournit la PLANCHE (SVG « façon archi » dessiné depuis la
// géométrie, le MÊME qu'au PDF), on l'INJECTE telle quelle (feuille blanche dans l'app sombre) et on
// montre/masque ses GROUPES `<g id="g-…">` selon les couches cochées. Sinon on retombe sur le plan
// schématique projeté depuis le GeoJSON (ci-dessous). Aucun second calcul dans les deux cas.
export function PlanMasseSvg({ fc, svg, groupesCaches, className }: {
  fc?: FC | null; svg?: string | null; groupesCaches?: string[]; className?: string
}) {
  const host = useRef<HTMLDivElement | null>(null)
  useEffect(() => {
    if (!svg || !host.current) return
    host.current.innerHTML = svg
    const el = host.current.querySelector('svg')
    if (el) { el.setAttribute('width', '100%'); el.removeAttribute('height'); (el as SVGElement).style.height = 'auto'; (el as SVGElement).style.display = 'block' }
  }, [svg])
  useEffect(() => {
    if (!svg || !host.current) return
    const cacher = new Set(groupesCaches ?? [])
    host.current.querySelectorAll('g[id^="g-"]').forEach((g) => {
      (g as SVGGElement).style.display = cacher.has((g as SVGGElement).id) ? 'none' : ''
    })
  }, [svg, groupesCaches])

  const W = 900, H = 420
  const els = useMemo<ReactElement[]>(() => {
    const kindOf = (f: FC['features'][number]) => (f.properties as { kind?: string } | null)?.kind ?? ''
    const feats = (fc?.features ?? []).filter((f) => f.geometry && COUL[kindOf(f)])
    const lons: number[] = [], lats: number[] = []
    for (const f of feats) for (const r of ringsOf(f.geometry as Geometry)) for (const [x, y] of r) { lons.push(x); lats.push(y) }
    if (!lons.length) return []
    const lat0 = (Math.min(...lats) + Math.max(...lats)) / 2
    const kx = Math.cos((lat0 * Math.PI) / 180) || 1
    const xs = lons.map((l) => l * kx)
    const minx = Math.min(...xs), maxx = Math.max(...xs), miny = Math.min(...lats), maxy = Math.max(...lats)
    const dx = (maxx - minx) || 1e-9, dy = (maxy - miny) || 1e-9, pad = 14
    const sc = Math.min((W - 2 * pad) / dx, (H - 2 * pad) / dy)
    const ox = (W - sc * dx) / 2, oy = (H - sc * dy) / 2
    const px = (lon: number, lat: number): [number, number] => [ox + (lon * kx - minx) * sc, H - (oy + (lat - miny) * sc)]
    const ordre = (k: string) => { const i = Z.indexOf(k); return i < 0 ? 99 : i }
    const sorted = [...feats].sort((a, b) => ordre(kindOf(a)) - ordre(kindOf(b)))
    const out: ReactElement[] = []
    sorted.forEach((f, idx) => {
      const kind = kindOf(f)
      const [face, edge] = COUL[kind]
      const g = f.geometry as Geometry
      if (g.type === 'LineString') {
        const pts = (g.coordinates as number[][]).map(([x, y]) => px(x, y).map((n) => n.toFixed(1)).join(',')).join(' ')
        out.push(<polyline key={`l${idx}`} points={pts} fill="none" stroke={edge} strokeWidth={3} strokeLinecap="round" />)
        return
      }
      const dash = kind === 'assiette' ? '6 3' : kind === 'zone' ? '4 3' : undefined
      const op = TRANSLUCIDE.has(kind) ? 0.2 : kind === 'batiment_emprise' ? 0.92 : 1
      ringsOf(g).forEach((ring, ri) => {
        const d = 'M ' + ring.map(([x, y]) => px(x, y).map((n) => n.toFixed(1)).join(' ')).join(' L ') + ' Z'
        out.push(<path key={`p${idx}-${ri}`} d={d} fill={face ?? 'none'} stroke={edge ?? 'none'}
          strokeWidth={kind === 'assiette' ? 1.6 : 0.8} strokeDasharray={dash} fillOpacity={op} />)
      })
    })
    return out
  }, [fc])

  // planche serveur présente → feuille blanche injectée (groupes toggés) ; sinon plan schématique.
  if (svg) {
    return <div ref={host} data-planche-svg
      className={className ?? 'block w-full overflow-hidden rounded-md border border-line-2 bg-white'} />
  }
  return (
    <svg data-plan-masse-svg viewBox={`0 0 ${W} ${H}`} className={className ?? 'block h-auto w-full rounded-md'}
      style={{ background: '#0F1311' }} role="img" aria-label="Plan masse du scénario">
      {els}
    </svg>
  )
}
