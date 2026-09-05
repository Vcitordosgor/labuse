// M55-G point 1 — CONTRÔLES D'ENTÊTE : UN patron pour la croix ET les chevrons (constat Vic :
// glyphes flottants, désalignés, sans boîte). La boîte est CONSTANTE (bordure visible hors
// survol, plus seulement un fond au hover), gabarit unique h-7 w-7 (l'ancienne variante
// `petit` h-6 disparaît), glyphe centré optiquement, hover franc (fond + glyphe éclairci).
// Tous les contrôles sont flush à droite de leur entête → une même colonne verticale
// (croix du panneau, chevrons Couches/Filtres/tiroirs, chevron de la légende Verdict).
// RETOURS-19 Y1 — contour PLEIN (`border-line-2`, plus `/70`) : la boîte reste visible hors survol sur
// tous les fonds (avant, à 70 % d'opacité elle disparaissait sur certaines surfaces claires/orthophoto).
const BOITE = 'flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-line-2 bg-surface-2/50 text-txt-dim transition-colors duration-quick'

// Chevron de section repliable — seule la FLÈCHE tourne (fermé → gauche, ouvert → bas,
// patron M55-A/C), la boîte reste stable. Le hover suit l'entête entière (via `group`).
// M55-H point 1 : le glyphe texte « ⌄ » portait un biais optique (ancré sur la ligne de
// base, jamais vraiment centré une fois pivoté) → chevron DESSINÉ (SVG symétrique, centré
// géométriquement = centré optiquement dans les deux états, trait arrondi).
// RETOURS-19 — `chev-boite` : sur une barre survolée à FOND PLEIN (`.hover-fill` / -ia / -amber), la
// boîte du chevron passe SANS fond ni bordure (règle CSS `index.css`), seul le glyphe reste — inversé en
// encre sombre comme le texte de la barre (avant : `group-hover:bg-surface-3` peignait un carré sombre
// sur le vert). Hors barre à fond plein, le hover reste inchangé (fond `surface-3`). Toutes les barres
// qui utilisent ChevronSection en héritent.
export function ChevronSection({ open }: { open: boolean }) {
  return (
    <span aria-hidden="true"
      className={`chev-boite ${BOITE} group-hover:bg-surface-3 group-hover:text-txt-hi`}>
      <svg viewBox="0 0 12 12"
        className={`h-3 w-3 transition-transform duration-soft ease-cockpit ${open ? '' : 'rotate-90'}`}>
        <polyline points="2.75,4.25 6,7.75 9.25,4.25" fill="none" stroke="currentColor"
          strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </span>
  )
}

// Croix de fermeture — même boîte, même colonne que les chevrons. `dataAttr` : marqueur QA
// éventuel (data-couches-fermer…) sans dupliquer le patron.
export function CroixEntete({ onClick, title, dataAttr }: { onClick: () => void; title: string; dataAttr?: string }) {
  const extra = dataAttr ? { [dataAttr]: true } : {}
  return (
    <button {...extra} onClick={onClick} title={title} aria-label={title}
      className={`${BOITE} hover:bg-surface-3 hover:text-txt-hi`}>
      <span className="text-[12px] leading-none">✕</span>
    </button>
  )
}
