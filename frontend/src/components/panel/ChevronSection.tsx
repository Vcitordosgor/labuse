// M55-G point 1 — CONTRÔLES D'ENTÊTE : UN patron pour la croix ET les chevrons (constat Vic :
// glyphes flottants, désalignés, sans boîte). La boîte est CONSTANTE (bordure visible hors
// survol, plus seulement un fond au hover), gabarit unique h-7 w-7 (l'ancienne variante
// `petit` h-6 disparaît), glyphe centré optiquement, hover franc (fond + glyphe éclairci).
// Tous les contrôles sont flush à droite de leur entête → une même colonne verticale
// (croix du panneau, chevrons Couches/Filtres/tiroirs, chevron de la légende Verdict).
const BOITE = 'flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-line-2/70 bg-surface-2/50 text-txt-dim transition-colors duration-quick'

// Chevron de section repliable — seule la FLÈCHE tourne (fermé → gauche, ouvert → bas,
// patron M55-A/C), la boîte reste stable. Le hover suit l'entête entière (via `group`).
export function ChevronSection({ open }: { open: boolean }) {
  return (
    <span aria-hidden="true"
      className={`${BOITE} group-hover:bg-surface-3 group-hover:text-txt-hi`}>
      <span className={`-mt-px text-[15px] leading-none transition-transform duration-soft ease-cockpit ${open ? '' : 'rotate-90'}`}>⌄</span>
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
