// M55-D stage 9 ter — CHEVRON DE SECTION : LE patron unique de tous les chevrons repliables du
// panneau (Couches, Filtres, tiroirs internes, légende Verdict). Même gabarit de boîte que la
// croix ✕ (h-7 w-7, rounded-md), aligné sur sa colonne, état hover VISIBLE (fond léger au
// survol de l'entête, via `group`), glyphe centré optiquement, rotation douce (fermé → gauche,
// ouvert → bas — patron M55-A/C). Plus aucun chevron « nu ».
export function ChevronSection({ open, petit = false }: { open: boolean; petit?: boolean }) {
  return (
    <span aria-hidden="true"
      className={`flex ${petit ? 'h-6 w-6 text-[15px]' : 'h-7 w-7 text-[17px]'} shrink-0 items-center justify-center rounded-md leading-none text-txt-dim transition-[transform,color,background-color] duration-soft ease-cockpit group-hover:bg-surface-3 group-hover:text-txt-hi ${open ? '' : 'rotate-90'}`}>
      <span className="-mt-px">⌄</span>
    </span>
  )
}
