/**
 * Module « Scoring v2 (P) » — M5 lot 4.2, ADDITIF.
 * Trois onglets : Brûlantes v2 · Réserve foncière · Top P (avec toggle copro).
 * Lecture des endpoints /v2 précalculés uniquement. Jamais de probabilité brute.
 */
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useApp } from '../../store/useApp'

type Item = {
  parcelle_id: string; mult_base: number; percentile: number | null; rang: number | null
  tier: string; pourquoi: { libelle: string; bin: string; signe: string; log_hazard: number }[]
  badges: { copro: boolean; evenement_date: string | null; veille_succession: boolean }
}
type Liste = { run_id: string; n: number; items: Item[]; note?: string; avertissement: string }

const TABS = [
  { key: 'brulantes', label: 'Brûlantes v2' },
  { key: 'reserve', label: 'Réserve foncière' },
  { key: 'top', label: 'Top P' },
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
      <div className="flex items-center gap-1">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`rounded px-2 py-1 text-[11px] ${tab === t.key
              ? 'bg-[#0F1A14] text-mint border border-[#2E6B4F]'
              : 'text-txt-mut hover:text-txt border border-transparent'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'reserve' && (
        <p className="rounded border border-[#3a5a7a55] bg-[#101a24] px-2 py-1.5 text-[10.5px] leading-snug text-[#8fb8dc]">
          Vitrine <b>capacité</b> (C fort, P faible) — ce n'est <b>pas</b> un pipeline :
          ces parcelles ont peu de chances de muter à 12 mois.
        </p>
      )}
      {tab === 'top' && (
        <label className="flex items-center gap-2 text-[11px] text-txt">
          <input type="checkbox" checked={copro} onChange={(e) => setCopro(e.target.checked)} />
          inclure les copropriétés (hors classement foncier par défaut)
        </label>
      )}

      {isLoading && <p className="text-[11px] text-txt-dim">chargement…</p>}
      {!!error && <p className="text-[11px] text-txt-dim">scoring v2 indisponible — lancer `labuse score-v2`.</p>}

      <div className="min-h-0 flex-1 overflow-y-auto">
        {data?.items.map((it) => (
          <button key={it.parcelle_id} onClick={() => select(it.parcelle_id)}
            className="mb-1 flex w-full items-center gap-2 rounded border border-line-2 bg-surface-2 px-2 py-1.5 text-left hover:border-[#2E6B4F]">
            <span className="font-mono text-[11px] text-txt-hi">×{it.mult_base.toFixed(1)}</span>
            <span className="flex-1 truncate font-mono text-[10.5px] text-txt">{it.parcelle_id}</span>
            {it.badges.copro && <span className="text-[9.5px] text-[#B7A8E0]">copro</span>}
            {it.badges.evenement_date && <span className="text-[9.5px] text-st-chaude">évén.</span>}
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
