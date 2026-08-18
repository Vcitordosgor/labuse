// M114 · Phase 0 (arbitré : vignette RÉELLE) — le SCHÉMA d'emprise du projet. Les centroïdes des
// parcelles (normalisés 0–1 par le serveur) sont dessinés en petits carrés : contour pour les
// parcelles du secteur (proposée/écartée), aplat mint pour les RETENUES. Un projet sans emprise
// (aucune parcelle) rend l'initiale de sa commune — état vide DISTINCT d'un chargement, jamais un
// spinner. Valeurs de couleur/taille : maquette DA-PROJETS-v1 (font foi).
import type { ProjetVignette } from '../../lib/api'

export function Vignette({ v, size }: { v?: ProjetVignette | null; size: 52 | 64 }) {
  const todo = size === 64
  const pts = v?.points ?? []
  const bg = todo ? '#0A1F14' : '#0A150F'          // --vignette-bg / --vignette-dim
  const line = todo ? '#2E6B4A' : '#1E4030'        // --vignette-line / --vignette-line-dim
  const radius = 6

  if (pts.length === 0) {
    // état vide : initiale de la commune (repli Phase 0), jamais un chargement.
    const initial = (v?.commune ?? '').trim().charAt(0).toUpperCase() || '·'
    return (
      <div aria-hidden style={{ width: size, height: size, borderRadius: radius, background: bg,
        display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
          fontSize: todo ? 20 : 16, color: '#3A4A41', fontWeight: 500 }}>{initial}</span>
      </div>
    )
  }

  const sq = 20                                    // taille d'un carré, en % de la boîte
  const place = (n: number) => Math.max(0, Math.min(100 - sq, n * 100 - sq / 2))
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" aria-hidden
      style={{ borderRadius: radius, background: bg, display: 'block' }}>
      {pts.map((p, i) => {
        const x = place(p.x), y = place(p.y)
        return p.r
          ? <rect key={i} x={x} y={y} width={sq} height={sq} rx={2.5} fill="#4ADE80" opacity={0.9} />
          : <rect key={i} x={x} y={y} width={sq} height={sq} rx={2.5} fill="none" stroke={line} strokeWidth={1.2} />
      })}
    </svg>
  )
}
