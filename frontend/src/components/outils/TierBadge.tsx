import { STATUT_META, TIER_DECLASSE_META, TIER_V2_META, codePalier, effectiveTier, type TierDeclasse } from '../../lib/status'
import type { Statut } from '../../lib/types'
import { usePaliersDA } from '../../lib/usePaliers'
import { Badge } from '../ui/Badge'

/** M5.1 lot 3.1 — badge de verdict des modules Outils : le TIER v2 effectif (étage 0 du run
 *  servi prime) est le label. Sans run v2 ni statut → « hors run » (repli honnête).
 *  M30 item 3 : tier declasse_* → label MOTIVÉ (avant : repli matrice muet).
 *  M37 : la mention secondaire « (matrice : X) » est RETIRÉE (arbitrage Vic — un seul
 *  classement à l'écran, le tier servi ; plus de matrice historique en surface).
 *  FRONT-CHIFFRES-2 (F29) — la COULEUR (ton) et le libellé viennent du back (source unique
 *  scoring/tiers_client, servie par /vocabulaire/paliers) : plus de correspondance hex→ton codée
 *  ici. Le front résout tier→code (codePalier, garanti anti-dérive) puis lit le ton servi ; repli
 *  neutre tant que la carte n'est pas chargée (jamais une couleur inventée). Même source que la
 *  pastille Projets (F13) — à q_v15 (bandes A/B/C/D) seul le back change. */
export function TierBadge({ tier, etage0, statut }: {
  tier?: string | null
  etage0?: boolean | number | null
  statut?: string | null
}) {
  const paliers = usePaliersDA()
  const t = effectiveTier(tier, etage0)
  const meta = (t ? TIER_V2_META[t] : null)
    ?? (tier ? TIER_DECLASSE_META[tier as TierDeclasse] : null)
    ?? (statut ? STATUT_META[statut as Statut] : null)
  if (!meta) return <span className="text-[11px] text-txt-dim">hors run</span>
  const servi = paliers?.[codePalier(t ?? tier ?? statut) ?? '']
  return <Badge point ton={servi?.ton ?? 'neutre'}>{servi?.chip ?? meta.label}</Badge>
}
