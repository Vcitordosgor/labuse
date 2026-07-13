import { STATUT_META, TIER_V2_META, effectiveTier } from '../../lib/status'
import type { Statut } from '../../lib/types'

/** M5.1 lot 3.1 — badge de verdict des modules Outils : le TIER v2 effectif (étage 0 du run
 *  servi prime) est le label PRINCIPAL ; le statut matrice legacy reste lisible en secondaire
 *  discret « (matrice : X) ». Sans run v2 ni statut → « hors run » (repli honnête). */
export function TierBadge({ tier, etage0, statut }: {
  tier?: string | null
  etage0?: boolean | number | null
  statut?: string | null
}) {
  const t = effectiveTier(tier, etage0)
  const meta = t ? TIER_V2_META[t] : statut ? STATUT_META[statut as Statut] : null
  if (!meta) return <span className="text-[11px] text-txt-dim">hors run</span>
  return (
    <span className="text-[11px]" style={{ color: meta.color }}>
      {meta.label}
      {t && statut && (
        <span className="ml-1 text-[9px] text-txt-dim">
          (matrice : {STATUT_META[statut as Statut]?.label ?? statut})
        </span>
      )}
    </span>
  )
}
