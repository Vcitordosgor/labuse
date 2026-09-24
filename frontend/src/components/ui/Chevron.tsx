// DA-FIX-3 Lot 5 (DA-031) — LE chevron d'accordéon unique.
// DA-FIX-5 P1 — Fermé = ◀ (pointe à GAUCHE) ; ouvert = ▼ (pointe en BAS, rotation -90°). Ouvert = fond
// vert opaque, glyphe sombre, rayon 4 (inchangé). Un seul dessin partout — remplace les ≥ 6 systèmes
// (SVG ◂/▾, SVG ›, glyphes texte ▸ ▾ › ▶). La légende carte cesse d'afficher ▾ dans les deux états.
// DA-FIX-4 Lot 0 (régression [A]) — `boite` : sur une BARRE À FOND PLEIN survolée (`.hover-fill`
// group), le chevron n'a PAS de fond propre (la règle CSS `.chev-boite` le rend transparent + inverse
// le glyphe en encre sombre) ; hors survol, son contour bordé reste visible. À utiliser dans les
// en-têtes d'accordéon posés sur une barre `.hover-fill` (ChevronSection).
export function Chevron({ open, boite = false, className = '' }: { open: boolean; boite?: boolean; className?: string }) {
  const box = boite
    ? 'chev-boite h-7 w-7 rounded-md border border-line-2 bg-surface-2/50 text-txt-dim group-hover:bg-surface-3 group-hover:text-txt-hi'
    : `h-5 w-5 rounded-[4px] ${open ? 'bg-mint text-mint-on' : 'text-txt-dim'}`
  return (
    <span aria-hidden="true"
      className={`inline-flex shrink-0 items-center justify-center transition-colors duration-quick ${box} ${className}`.trim()}>
      <svg viewBox="0 0 12 12" className={`h-3 w-3 transition-transform duration-quick ${open ? '-rotate-90' : ''}`}>
        {/* dessiné vers la GAUCHE (fermé = ◀) ; ouvert = -90° → pointe en bas (▼). */}
        <polyline points="7.5,2.75 4,6 7.5,9.25" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </span>
  )
}

export default Chevron
