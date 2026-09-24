// DA-FIX-3 Lot 1 (DA-025) — LE composant chip unique (puce de filtre / statut).
// 32 px, pilule, contour neutre au repos ; coché = aplat opaque de son ton + coche + contenu sombre ;
// survol (non coché) = aplat opaque de son ton ; désactivé = règle globale (opacity .4 + not-allowed).
// Le ton (admin) devient une prop. Remplace le Chip de FiltreLabuse, le Chip admin et les pastilles inline.
import type { ButtonHTMLAttributes, ReactNode } from 'react'

export type ChipTon = 'vert' | 'ambre' | 'neutre' | 'ia'

const ON: Record<ChipTon, string> = {
  vert:   'border-mint bg-mint text-mint-on',
  ambre:  'border-amber bg-amber text-[#241a06]',
  neutre: 'border-txt-mut bg-txt-mut text-bg',
  ia:     'border-violet bg-violet text-[#14091f]',
}
const HOVER: Record<ChipTon, string> = {
  vert:   'hover:border-mint hover:bg-mint hover:text-mint-on',
  ambre:  'hover:border-amber hover:bg-amber hover:text-[#241a06]',
  neutre: 'hover:border-txt-mut hover:bg-txt-mut hover:text-bg',
  ia:     'hover:border-violet hover:bg-violet hover:text-[#14091f]',
}

export interface ChipProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'> {
  on?: boolean
  ton?: ChipTon
  children: ReactNode
}

export function Chip({ on = false, ton = 'vert', className = '', children, ...rest }: ChipProps) {
  return (
    <button type="button" aria-pressed={on}
      className={`inline-flex h-8 items-center gap-1 rounded-full border px-3 text-[12px] font-medium leading-none transition-colors duration-quick focus-visible:outline-none ${
        on ? ON[ton] : `border-line-2 bg-surface-3 text-txt-mut ${HOVER[ton]}`} ${className}`.trim()}
      {...rest}>
      {on && (
        <svg aria-hidden="true" viewBox="0 0 12 12" className="h-3 w-3 shrink-0">
          <polyline points="2.5,6.5 5,9 9.5,3.5" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )}
      {children}
    </button>
  )
}

export default Chip
