/**
 * Bloc « Pourquoi ce score » — Scoring v2 (M5 lot 4.1), ADDITIF.
 *
 * Décisions produit gravées : JAMAIS de probabilité brute (saturation isotonique
 * en tête) — affichage = « ×N vs moyenne » + percentile + rang + tier ; badges
 * copro / veille succession / événement daté ; 5 contributions lisibles (signe +
 * libellé de bin en français). Auto-porté : fetch /v2/score/{idu}, aucun impact
 * sur la fiche existante s'il échoue (bloc absent, jamais d'erreur bloquante).
 */
import { useQuery } from '@tanstack/react-query'
import { TIER_V2_META } from '../../lib/status'

type Contribution = { feature: string; bin: string; signe: '+' | '-'; libelle: string; log_hazard: number }
type ScoreV2 = {
  parcelle_id: string; mult_base: number; percentile: number | null; rang: number | null
  tier: string; contrib_z: number; contrib_d: number; pourquoi: Contribution[]
  badges: { copro: boolean; evenement_date: string | null; veille_succession: boolean }
  model_version: string; avertissement: string
}

// palette des tiers v2 : source unique dans lib/status.ts (correctif M5 — le verdict
// d'en-tête et ce bloc doivent être rigoureusement raccord)
const TIER_META = TIER_V2_META as Record<string, { label: string; color: string }>

export function ScoreV2Block({ idu }: { idu: string }) {
  const { data } = useQuery<ScoreV2>({
    queryKey: ['score-v2', idu],
    queryFn: async () => {
      const r = await fetch(`/v2/score/${idu}`)
      if (!r.ok) throw new Error(`v2 ${r.status}`)
      return r.json()
    },
    retry: false, staleTime: 5 * 60_000,
  })
  if (!data) return null
  const tier = TIER_META[data.tier] ?? { label: data.tier, color: '#8FA69A' }
  return (
    <div data-score-v2 className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2.5">
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-txt-hi">Probabilité de mutation (P v2)</span>
        <span className="rounded-full px-2 py-0.5 text-[10.5px] font-semibold"
          style={{ backgroundColor: `${tier.color}22`, color: tier.color }}>{tier.label}</span>
        {data.badges.copro && (
          <span className="rounded-full bg-[#2A2438] px-2 py-0.5 text-[10.5px] text-[#B7A8E0]"
            title="Copropriété — hors du classement foncier par défaut">copro</span>
        )}
        {data.badges.veille_succession && (
          <span className="rounded-full bg-[#14251E] px-2 py-0.5 text-[10.5px] text-mint"
            title="Radar patrimonial 3-7 ans — jamais brûlante">veille succession</span>
        )}
        {data.badges.evenement_date && (
          <span className="rounded-full bg-[#33201A] px-2 py-0.5 text-[10.5px] text-st-chaude"
            title="Événement tracé v1.3 (BODACC)">événement {data.badges.evenement_date}</span>
        )}
      </div>

      <div className="mt-2 flex items-baseline gap-3">
        {/* JAMAIS la probabilité brute : ×N vs moyenne, percentile, rang */}
        <span className="font-mono text-xl font-semibold text-txt-hi">×{data.mult_base.toFixed(1)}</span>
        <span className="text-[11px] text-txt-dim">vs moyenne du parc hors copro</span>
        {data.percentile != null && (
          <span className="font-mono text-xs text-txt">percentile {data.percentile.toFixed(1)}</span>
        )}
        {data.rang != null && <span className="font-mono text-xs text-txt-dim">rang {data.rang}</span>}
      </div>

      <p className="mt-2 font-mono text-[10.5px] uppercase tracking-widest text-txt-mut">Pourquoi ce score</p>
      <ul className="mt-1 flex flex-col gap-0.5">
        {data.pourquoi.map((c, i) => (
          <li key={i} className="flex items-baseline gap-2 text-[11.5px]">
            <span className={`w-12 shrink-0 text-right font-mono font-semibold ${
              c.signe === '+' ? 'text-st-chaude' : 'text-st-ecartee'}`}>
              {c.signe}{Math.abs(c.log_hazard).toFixed(2)}
            </span>
            <span className="text-txt">{c.libelle}{c.bin ? <span className="text-txt-dim"> [{c.bin}]</span> : null}</span>
          </li>
        ))}
      </ul>

      <p className="mt-2 text-[10.5px] leading-snug text-txt-dim" title={data.avertissement}>
        modèle {data.model_version} — {data.avertissement}
      </p>
    </div>
  )
}
