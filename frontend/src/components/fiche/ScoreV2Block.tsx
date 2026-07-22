/**
 * Bloc « Pourquoi ce score » — Scoring v2 (M5 lot 4.1), ADDITIF.
 *
 * Décisions produit gravées : JAMAIS de probabilité brute (saturation isotonique
 * en tête) — affichage = « ×N vs moyenne » + percentile + rang + tier ; badges
 * copro / veille succession / événement daté ; 5 contributions lisibles (signe +
 * libellé de bin en français). Auto-porté : fetch /v2/score/{idu}.
 *
 * M6.1 item 5 — fin du silent-fail : une ERREUR de requête (réseau, 5xx) affiche un
 * état visible « Score momentanément indisponible » + bouton réessayer (même gabarit) ;
 * un 404 (parcelle absente du run v2 : copro non classée, hors périmètre) affiche un
 * état honnête « Non scorée » au lieu d'un bloc qui disparaît sans explication.
 */
import { useQuery } from '@tanstack/react-query'
import { TIER_V2_META } from '../../lib/status'
import { Tip } from '../Tip'

type Contribution = { feature: string; bin: string; signe: '+' | '-'; libelle: string; log_hazard: number; phrase?: string }
type ScoreV2 = {
  parcelle_id: string; mult_base: number; percentile: number | null; rang: number | null
  tier: string; contrib_z: number; contrib_d: number; pourquoi: Contribution[]
  badges: { copro: boolean; evenement_date: string | null; veille_succession: boolean }
  model_version: string; avertissement: string
}

// palette des tiers v2 : source unique dans lib/status.ts (correctif M5 — le verdict
// d'en-tête et ce bloc doivent être rigoureusement raccord)
const TIER_META = TIER_V2_META as Record<string, { label: string; color: string }>

type ErreurV2 = Error & { status?: number }

export function ScoreV2Block({ idu }: { idu: string }) {
  const { data, isError, error, refetch, isFetching } = useQuery<ScoreV2, ErreurV2>({
    queryKey: ['score-v2', idu],
    queryFn: async () => {
      const r = await fetch(`/v2/score/${idu}`)
      if (!r.ok) {
        const e: ErreurV2 = new Error(`v2 ${r.status}`)
        e.status = r.status
        throw e
      }
      return r.json()
    },
    retry: false, staleTime: 5 * 60_000,
  })
  if (isError) {
    // 404 = la parcelle n'est pas dans le run v2 (copro non classée / hors périmètre) :
    // état honnête, pas de bouton réessayer (re-demander ne changera rien).
    if (error?.status === 404) {
      return (
        <div data-score-v2="non-scoree" className="card-elev px-3 py-2.5">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-txt-hi">Probabilité de mutation (P v2)</span>
            <span className="rounded-full bg-[#2A2438] px-2 py-0.5 text-[10.5px] text-[#B7A8E0]">non scorée</span>
          </div>
          <p className="mt-1.5 text-[11px] leading-snug text-txt-dim">
            Parcelle absente du dernier run du modèle v2 — copropriété ou hors périmètre du scoring.
          </p>
        </div>
      )
    }
    // Toute autre erreur (réseau, 5xx, run absent) : état visible + réessayer, même gabarit.
    return (
      <div data-score-v2="erreur" className="card-elev px-3 py-2.5">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-txt-hi">Probabilité de mutation (P v2)</span>
          <span className="rounded-full bg-[#33201A] px-2 py-0.5 text-[10.5px] text-st-chaude">indisponible</span>
        </div>
        <p className="mt-1.5 text-[11px] leading-snug text-txt-dim">
          Score momentanément indisponible — le reste de la fiche n'est pas affecté.
        </p>
        <button onClick={() => refetch()} disabled={isFetching}
          className="mt-2 rounded-lg border border-line-2 px-2.5 py-1 text-[11px] text-txt hover:border-mint hover:text-txt-hi disabled:opacity-40">
          {isFetching ? 'Nouvel essai…' : 'Réessayer'}
        </button>
      </div>
    )
  }
  if (!data) return null
  const tier = TIER_META[data.tier] ?? { label: data.tier, color: '#8FA69A' }
  return (
    <div data-score-v2 className="card-elev px-3 py-2.5">
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-txt-hi">Probabilité de mutation (P v2)</span>
        <span className="rounded-full px-2 py-0.5 text-[10.5px] font-semibold"
          style={{ backgroundColor: `${tier.color}22`, color: tier.color }}>{tier.label}</span>
        {data.badges.copro && (
          <Tip tip="Copropriété — hors du classement foncier par défaut">
            <span className="rounded-full bg-[#2A2438] px-2 py-0.5 text-[10.5px] text-[#B7A8E0]">copro</span>
          </Tip>
        )}
        {data.badges.veille_succession && (
          <Tip tip="Radar patrimonial 3-7 ans — jamais brûlante">
            <span className="rounded-full bg-[#14251E] px-2 py-0.5 text-[10.5px] text-mint">veille succession</span>
          </Tip>
        )}
        {data.badges.evenement_date && (
          <Tip tip="Événement tracé v1.3 (BODACC)">
            <span className="rounded-full bg-[#33201A] px-2 py-0.5 text-[10.5px] text-st-chaude">événement {data.badges.evenement_date}</span>
          </Tip>
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

      <p className="label-caps mt-2">Pourquoi ce score</p>
      <ul className="mt-1 flex flex-col gap-0.5">
        {data.pourquoi.map((c, i) => (
          <li key={i} className="flex items-baseline gap-2 text-[11.5px]">
            <span className={`w-12 shrink-0 text-right font-mono font-semibold ${
              c.signe === '+' ? 'text-st-chaude' : 'text-st-ecartee'}`}>
              {c.signe}{Math.abs(c.log_hazard).toFixed(2)}
            </span>
            {/* M5.1 lot 3.3 : la phrase client (table versionnée serveur) remplace le
                « libellé [bin] » technique ; le bin exact reste au survol/tap (audit) */}
            <Tip tip={c.bin ? `${c.libelle} — tranche ${c.bin}` : c.libelle}>
              <span className="text-txt">{c.phrase ?? c.libelle}</span>
            </Tip>
          </li>
        ))}
      </ul>

      <p className="mt-2 text-[10.5px] leading-snug text-txt-dim">
        modèle {data.model_version} — {data.avertissement}
      </p>
    </div>
  )
}
