// DA-FIX-3 Lot 5 (DA-031) — LE chevron d'accordéon unique.
// Fermé = ▶ (pointe à DROITE) ; ouvert = ▼ (pointe en BAS, rotation 90°). Ouvert = fond vert opaque,
// glyphe sombre, rayon 4. Un seul dessin partout — remplace les ≥ 6 systèmes (SVG ◂/▾, SVG ›, glyphes
// texte ▸ ▾ › ▶). La légende carte cesse d'afficher ▾ dans les deux états.
export function Chevron({ open, className = '' }: { open: boolean; className?: string }) {
  return (
    <span aria-hidden="true"
      className={`inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-[4px] transition-colors duration-quick ${
        open ? 'bg-mint text-mint-on' : 'text-txt-dim'} ${className}`.trim()}>
      <svg viewBox="0 0 12 12" className={`h-3 w-3 transition-transform duration-quick ${open ? 'rotate-90' : ''}`}>
        {/* dessiné vers la DROITE (fermé = ▶) ; ouvert = +90° → pointe en bas (▼). */}
        <polyline points="4.5,2.75 8,6 4.5,9.25" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </span>
  )
}

export default Chevron
