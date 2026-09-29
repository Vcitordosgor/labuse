/**
 * Module « Radar des ventes » (Scoring v2 / P) — M5 lot 4.2, ADDITIF.
 * Trois onglets : Brûlantes v2 · Réserve foncière · Top P (avec toggle copro).
 * Lecture des endpoints /v2 précalculés uniquement. Jamais de probabilité brute.
 *
 * ⚠️ DORMANT — retiré du produit le 20/08/2026 (M137-K). Recouvre l'Analyse LABUSE (même table
 *    parcel_p_score_v2, même run servi q_v10_m129, même classement tier/rang), sans carte ni filtres.
 *    N'est plus référencé par le registre ni le panneau (aucune entrée à l'écran). Conservé au dépôt :
 *    ce composant + les endpoints /v2/brulantes|reserve-fonciere|liste + les tests (test_p_v2_api.py).
 *    La fraction « 1/5 » qu'il mettait en avant reste servie sur les cartes de résultat de l'Analyse
 *    (M135 P2, ResultsSection `data-fraction`). Aucun autre consommateur des 3 endpoints (mesuré).
 */
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { getScoringFraction } from '../../lib/api'
import { useApp } from '../../store/useApp'
import { Squelette } from '../Loading'
import { EmptyState, ErrorState } from '../States'
import { Case } from '../ui/Case'

type Item = {
  parcelle_id: string; mult_base: number; fraction?: string | null; percentile: number | null; rang: number | null
  tier: string; pourquoi: { libelle: string; bin: string; signe: string; log_hazard: number }[]
  badges: { copro: boolean; evenement_date: string | null; veille_succession: boolean }
}
type Liste = { run_id: string; n: number; items: Item[]; note?: string; avertissement: string }

const TABS = [
  // REPARATIONS-1 lot 2b — « Priorité » n'est plus servi : l'onglet tête de classement dit « À suivre ».
  { key: 'brulantes', label: 'À suivre (tête)' },
  { key: 'reserve', label: 'Réserve foncière' },   // PALIERS-1 : marqueur de capacité, plus « Long terme »
  { key: 'top', label: 'Classement' },   // M15 E1 : « Top P » (jargon) → « Classement »
] as const

function useListe(tab: string, copro: boolean) {
  const url = tab === 'brulantes' ? '/v2/brulantes'
    : tab === 'reserve' ? '/v2/reserve-fonciere'
    : `/v2/liste?limit=200&include_copro=${copro}`
  return useQuery<Liste>({
    queryKey: ['v2-liste', tab, copro],
    queryFn: async () => {
      const r = await fetch(url)
      if (!r.ok) throw new Error(`v2 ${r.status}`)
      return r.json()
    },
    staleTime: 60_000,
  })
}

export function ScoringV2Module() {
  const [tab, setTab] = useState<(typeof TABS)[number]['key']>('brulantes')
  const [copro, setCopro] = useState(false)
  const select = useApp((s) => s.select)
  const { data, isLoading, error } = useListe(tab, copro)
  // FRONT-CHIFFRES-2 (F26) — le seuil bas (« sous 1/d, peu probable ») vient du back (config
  // scoring_client) ; plus de littéral « 1 sur cinquante » codé dans le texte. Repli 50 au chargement.
  const seuilBas = useQuery({ queryKey: ['scoring-fraction'], queryFn: getScoringFraction, staleTime: 60 * 60 * 1000 })
  const dPeuProbable = seuilBas.data?.seuil_bas_denominateur ?? 50

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2">
      {/* M135 — bandeau client : la probabilité en FRACTION, l'échelle d'ACTION. */}
      <div className="rounded-lg border border-mint/30 bg-mint/[0.06] px-3 py-2 text-[10.5px] leading-relaxed text-txt-mut">
        Le <b className="text-txt">classement</b> des parcelles par <b className="text-txt">probabilité
        de vente</b> sous 1 an. La <b className="text-mint">fraction</b> (« 1/5 ») dit la chance qu’une
        vente intervienne dans l’année ; sous 1/{dPeuProbable}, un tiret « — » (<b>peu probable</b>). <b>À suivre (tête)</b> =
        la tête du classement, à contacter d’abord ; <b>Réserve foncière</b> = forte capacité constructible résiduelle (marqueur, pas un palier) ;
        <b>Classement</b> = toutes, par ordre de priorité.
      </div>
      <div className="flex items-center gap-1">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`min-h-7 rounded px-2 py-1 text-[11px] transition-colors duration-quick ${tab === t.key
              ? 'border border-mint/40 bg-mint/10 text-mint'
              : 'border border-transparent text-txt-mut hover:text-txt'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'reserve' && (
        <p className="rounded-lg bg-surface-3 px-2 py-1.5 text-[10.5px] leading-snug text-txt-mut">
          Vitrine <b className="text-txt">capacité</b> (C fort, P faible) — ce n'est <b className="text-txt">pas</b> un pipeline :
          ces parcelles ont peu de chances d'être vendues à 12 mois.
        </p>
      )}
      {tab === 'top' && (
        <Case className="text-[11px] text-txt" checked={copro} onChange={(e) => setCopro(e.target.checked)}
          label="inclure les copropriétés (hors classement foncier par défaut)" />
      )}

      {isLoading && <Squelette lignes={6} />}
      {!!error && (
        <ErrorState className="py-6" message="Scoring indisponible."
          hint="Aucun run n'est servi pour l'instant — les listes apparaîtront dès le prochain run de scoring." />
      )}

      <div className="min-h-0 flex-1 overflow-y-auto">
        {data?.items.map((it) => (
          <button key={it.parcelle_id} onClick={() => select(it.parcelle_id)}
            className="mb-1 flex min-h-7 w-full items-center gap-2 rounded-md border border-line-2 bg-surface-2 px-2 py-1.5 text-left transition-colors duration-quick hover:border-mint/40">
            <span className="tnum font-mono text-[11px] text-txt-hi">{it.fraction ?? '—'}</span>
            <span className="flex-1 truncate font-mono text-[10.5px] text-txt">{it.parcelle_id}</span>
            {it.badges.copro && <span className="text-[9.5px] text-txt-dim">copro</span>}
            {it.badges.evenement_date && <span className="text-[9.5px] text-st-chaude">évén.</span>}
            {/* M137-J — badge succession (signal fort, 7 129 parcelles) : dormait côté back (payload
                servi), jamais affiché. Même patron que copro/événement ; signal d'ÉTAT patrimonial. */}
            {it.badges.veille_succession && <span className="text-[9.5px] text-mint">succession en cours</span>}
            {it.rang != null && <span className="font-mono text-[10px] text-txt-dim">#{it.rang}</span>}
          </button>
        ))}
        {data && !data.items.length && <EmptyState title="Aucune parcelle." />}
      </div>
      {data && (
        <p className="shrink-0 text-[9.5px] leading-snug text-txt-dim">{data.avertissement}</p>
      )}
    </div>
  )
}
