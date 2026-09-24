import { Chevron } from '../ui/Chevron'

// M55-G point 1 — CONTRÔLES D'ENTÊTE : UN patron pour la croix ET les chevrons (constat Vic :
// glyphes flottants, désalignés, sans boîte). La boîte est CONSTANTE (bordure visible hors
// survol, plus seulement un fond au hover), gabarit unique h-7 w-7 (l'ancienne variante
// `petit` h-6 disparaît), glyphe centré optiquement, hover franc (fond + glyphe éclairci).
// Tous les contrôles sont flush à droite de leur entête → une même colonne verticale
// (croix du panneau, chevrons Couches/Filtres/tiroirs, chevron de la légende Verdict).
// RETOURS-19 Y1 — contour PLEIN (`border-line-2`, plus `/70`) : la boîte reste visible hors survol sur
// tous les fonds (avant, à 70 % d'opacité elle disparaissait sur certaines surfaces claires/orthophoto).
const BOITE = 'flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-line-2 bg-surface-2/50 text-txt-dim transition-colors duration-quick'

// DA-FIX-3 Lot 5 (DA-031) — ChevronSection rend désormais LE chevron partagé (fermé ▶ / ouvert ▼
// + fond vert opaque). La signature `{ open }` est conservée pour tous les appelants existants.
export function ChevronSection({ open }: { open: boolean }) {
  return <Chevron open={open} />
}

// Croix de fermeture — même boîte, même colonne que les chevrons. `dataAttr` : marqueur QA
// éventuel (data-couches-fermer…) sans dupliquer le patron.
export function CroixEntete({ onClick, title, dataAttr }: { onClick: () => void; title: string; dataAttr?: string }) {
  const extra = dataAttr ? { [dataAttr]: true } : {}
  return (
    <button {...extra} onClick={onClick} aria-label={title}
      className={`${BOITE} hover:bg-surface-3 hover:text-txt-hi`}>
      <span className="text-[12px] leading-none">✕</span>
    </button>
  )
}
