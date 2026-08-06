import { STATUT_META, TIER_DECLASSE_META, TIER_V2_META, effectiveTier, type TierDeclasse } from '../../lib/status'
import type { Statut } from '../../lib/types'

/** M5.1 lot 3.1 — badge de verdict des modules Outils : le TIER v2 effectif (étage 0 du run
 *  servi prime) est le label. Sans run v2 ni statut → « hors run » (repli honnête).
 *  M30 item 3 : tier declasse_* → label MOTIVÉ (avant : repli matrice muet).
 *  M37 : la mention secondaire « (matrice : X) » est RETIRÉE (arbitrage Vic — un seul
 *  classement à l'écran, le tier servi ; plus de matrice historique en surface). */
export function TierBadge({ tier, etage0, statut }: {
  tier?: string | null
  etage0?: boolean | number | null
  statut?: string | null
}) {
  const t = effectiveTier(tier, etage0)
  const meta = (t ? TIER_V2_META[t] : null)
    ?? (tier ? TIER_DECLASSE_META[tier as TierDeclasse] : null)
    ?? (statut ? STATUT_META[statut as Statut] : null)
  if (!meta) return <span className="text-[11px] text-txt-dim">hors run</span>
  return (
    <span className="inline-flex items-center gap-1 whitespace-nowrap text-[11px]" style={{ color: meta.color }}>
      <span aria-hidden className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: meta.color }} />
      {meta.label}
    </span>
  )
}
