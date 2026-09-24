// DA-FIX-3 Lot 6 (DA-034) — LE composant badge unique.
// Pilule, 11 px / 500, TROIS tons : vert · ambre · neutre. Remplace TierBadge, DestinationBadge,
// copilote.Badge/PillStatut, SourcesPage.Badge, EquipementsBadges, .b/StepProv, ProvBadge, pill-*.
// Pas de 4ᵉ ton : le corail « interdit » de DestinationBadge passe en ambre (sens noté au call-site).
import type { HTMLAttributes, ReactNode } from 'react'

export type BadgeTon = 'vert' | 'ambre' | 'neutre'

const TON: Record<BadgeTon, string> = {
  vert:   'border-mint/40 bg-mint-bg text-mint',
  ambre:  'border-amber/40 bg-amber-bg text-amber',
  neutre: 'border-line-2 bg-surface-3 text-txt-dim',
}

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  ton?: BadgeTon
  /** point de couleur en tête (comme les anciens badges de tier). */
  point?: boolean
  children: ReactNode
}

export function Badge({ ton = 'neutre', point = false, className = '', children, ...rest }: BadgeProps) {
  return (
    <span className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-[11px] font-medium leading-none ${TON[ton]} ${className}`.trim()} {...rest}>
      {point && <span aria-hidden="true" className="h-1.5 w-1.5 shrink-0 rounded-full bg-current" />}
      {children}
    </span>
  )
}

export default Badge
