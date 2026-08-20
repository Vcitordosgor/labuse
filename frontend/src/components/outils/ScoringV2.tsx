/**
 * Module « Scoring v2 (P) » — M5 lot 4.2, ADDITIF.
 * Trois onglets : Brûlantes v2 · Réserve foncière · Top P (avec toggle copro).
 * Lecture des endpoints /v2 précalculés uniquement. Jamais de probabilité brute.
 */
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useApp } from '../../store/useApp'
import { Loading } from '../Loading'
import { ErrorState } from '../States'

type Item = {
  parcelle_id: string; mult_base: number; fraction?: string | null; percentile: number | null; rang: number | null
  tier: string; pourquoi: { libelle: string; bin: string; signe: string; log_hazard: number }[]
  badges: { copro: boolean; evenement_date: string | null; veille_succession: boolean }
}
type Liste = { run_id: string; n: number; items: Item[]; note?: string; avertissement: string }

const TABS = [
  { key: 'brulantes', label: 'Priorité' },
  { key: 'reserve', label: 'Long terme' },
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

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2">
      {/* M135 — bandeau client : la probabilité en FRACTION, l'échelle d'ACTION. */}
      <div className="rounded-lg border border-mint/30 bg-mint/[0.06] px-3 py-2 text-[10.5px] leading-relaxed text-txt-mut">
        Le <b className="text-txt">classement</b> des parcelles par <b className="text-txt">probabilité
        de vente</b> sous 1 an. La <b className="text-mint">fraction</b> (« 1/5 ») dit la chance qu’une
        vente intervienne dans l’année ; sous 1/50, un tiret « — » (<b>peu probable</b>). <b>Priorité</b> =
        à contacter d’abord ; <b>Long terme</b> = fort potentiel mais vente peu probable à court terme ;
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
        <label className="flex items-center gap-2 text-[11px] text-txt">
          <input type="checkbox" checked={copro} onChange={(e) => setCopro(e.target.checked)} />
          inclure les copropriétés (hors classement foncier par défaut)
        </label>
      )}

      {isLoading && <Loading label="Chargement du scoring" className="text-[11px]" />}
      {!!error && (
        <ErrorState className="py-6" message="Scoring indisponible."
          hint="Aucun run n'est servi pour l'instant — les listes apparaîtront dès le prochain run de scoring." />
      )}

      <div className="min-h-0 flex-1 overflow-y-auto">
        {data?.items.map((it) => (
          <button key={it.parcelle_id} onClick={() => select(it.parcelle_id)}
            className="mb-1 flex min-h-7 w-full items-center gap-2 rounded-md border border-line-2 bg-surface-2 px-2 py-1.5 text-left transition-colors duration-quick hover:border-mint/40">
            <span className="tnum font-mono text-[11px] text-txt-hi" title="Probabilité de vente sous 1 an (fraction humaine)">{it.fraction ?? '—'}</span>
            <span className="flex-1 truncate font-mono text-[10.5px] text-txt">{it.parcelle_id}</span>
            {it.badges.copro && <span className="text-[9.5px] text-txt-dim">copro</span>}
            {it.badges.evenement_date && <span className="text-[9.5px] text-st-chaude" title={`Événement BODACC — ${it.badges.evenement_date}`}>évén.</span>}
            {/* M137-J — badge succession (signal fort, 7 129 parcelles) : dormait côté back (payload
                servi), jamais affiché. Même patron que copro/événement ; signal d'ÉTAT patrimonial. */}
            {it.badges.veille_succession && <span className="text-[9.5px] text-mint" title="Radar patrimonial — bien en cours de succession (signal d'état, pas un événement daté)">succession en cours</span>}
            {it.rang != null && <span className="font-mono text-[10px] text-txt-dim">#{it.rang}</span>}
          </button>
        ))}
        {data && !data.items.length && <p className="text-[11px] text-txt-dim">aucune parcelle.</p>}
      </div>
      {data && (
        <p className="shrink-0 text-[9.5px] leading-snug text-txt-dim">{data.avertissement}</p>
      )}
    </div>
  )
}
