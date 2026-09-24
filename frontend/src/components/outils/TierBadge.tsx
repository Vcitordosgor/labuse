import { STATUT_META, TIER_DECLASSE_META, TIER_V2_META, effectiveTier, type TierDeclasse } from '../../lib/status'
import type { Statut } from '../../lib/types'
import { Badge, type BadgeTon } from '../ui/Badge'

// DA-034 — la couleur meta du tier (voir lib/status) est mappée vers les 3 tons du Badge :
//   vert   = tiers hauts / positifs (verts vifs #5CE6A1 / #4ADE96) ;
//   ambre  = intermédiaire / alerte (ambres #E8B44C / #E8B23A ET le corail d'alerte #E8695A) ;
//   neutre = faible / gris-vert (#8FA69A / #6B7A72 / #8A8FA0 / #4A5A52 / #5C7268 …).
function tonDeCouleur(color: string): BadgeTon {
  const c = color.toUpperCase()
  if (c === '#5CE6A1' || c === '#4ADE96') return 'vert'
  if (c === '#E8B44C' || c === '#E8B23A' || c === '#E8695A') return 'ambre'
  return 'neutre'
}

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
  return <Badge point ton={tonDeCouleur(meta.color)}>{meta.label}</Badge>
}
