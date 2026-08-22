/**
 * Module « Densifier l'existant » — M-RENOUV lot B, ADDITIF (clé interne `renouvellement` inchangée :
 * URL, QA, tests, endpoint /renouvellement/liste, table parcel_renouvellement — tous conservés).
 * Liste triable du segment (score / SDP / surface / rang commune). DOCTRINE : parcelles OCCUPÉES,
 * « potentiel de densification » — jamais « opportunité », jamais mélangé aux Chaudes/Brûlantes.
 */
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { getRenouvListe } from '../../lib/api'
import { verdictMeta } from '../../lib/status'
import { TOKENS } from '../../lib/tokens'
import { useApp } from '../../store/useApp'
import { Loading } from '../Loading'
import { ErrorState } from '../States'
import { Tip } from '../Tip'

const SORTS = [
  { key: 'score', label: 'Score' },
  { key: 'sdp', label: 'SDP résiduelle' },
  { key: 'surface', label: 'Surface' },
  { key: 'rang_commune', label: 'Rang commune' },
] as const

const CODE_LABEL: Record<string, string> = {
  deja_bati: 'déjà bâtie',
  deja_bati_probable: 'déjà bâtie (probable)',
  ensemble_bati: 'ensemble bâti',
}

export function RenouvellementModule() {
  const [sort, setSort] = useState<(typeof SORTS)[number]['key']>('score')
  const select = useApp((s) => s.select)
  const commune = useApp((s) => s.commune)
  const { data, isLoading, error } = useQuery({
    queryKey: ['renouv-liste', sort, commune],
    queryFn: () => getRenouvListe(sort, commune),
    staleTime: 60_000,
  })

  if (isLoading) return <Loading label="Densifier l'existant…" />
  if (error || !data) return <ErrorState message="Segment momentanément indisponible — réessayez." />

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2">
      {/* bandeau client — la définition ET la limite, toujours visibles (doctrine) */}
      <div className="rounded-lg border px-3 py-2 text-[10.5px] leading-relaxed text-txt-mut"
        style={{ borderColor: `${TOKENS.renouv}4d`, background: `${TOKENS.renouv}0f` }}>
        Le <b style={{ color: TOKENS.renouv }}>bâti qui peut porter davantage</b> — extensions,
        surélévations : des parcelles <b className="text-txt">déjà occupées</b> en zone constructible
        avec une <b className="text-txt">capacité résiduelle réelle</b>. {data.avertissement}
        {/* « i » — la MÉTHODE et sa limite (Estimé), toujours à portée */}
        <Tip tip="Parcelles déjà bâties en zone U/AU dont la capacité résiduelle > 100 m² (ou surface ≥ 600 m²), hors copropriété et hors foncier public. Score = heuristique déterministe (percent_rank : SDP résiduelle · assiette · rotation du bâti). Estimé — règles PLU calibrées, pas une expertise.">
          <span className="ml-1 cursor-help rounded-full border border-line-2 px-1 text-[8px] text-txt-dim">i</span>
        </Tip>
        {/* M47 : étiquette source · millésime — comme toute couche servie. */}
        <span className="mt-1 block text-[9.5px] text-txt-dim">
          {data.source}
          {data.maj ? ` · maj ${data.maj}` : ''}
        </span>
      </div>
      <div className="flex items-center gap-1">
        <span className="mr-1 text-[10px] text-txt-dim">Trier :</span>
        {SORTS.map((s) => (
          <button key={s.key} onClick={() => setSort(s.key)}
            className={`min-h-7 rounded px-2 py-1 text-[11px] transition-colors duration-quick ${sort === s.key
              ? 'border bg-surface-3 font-medium' : 'text-txt-mut hover:text-txt'}`}
            style={sort === s.key ? { borderColor: `${TOKENS.renouv}66`, color: TOKENS.renouv } : undefined}>
            {s.label}
          </button>
        ))}
        <span className="ml-auto text-[10px] text-txt-dim">
          {data.tronquee
            ? `les ${data.n} premières sur ${data.total.toLocaleString('fr-FR')}`
            : `${data.n} sur ${data.total.toLocaleString('fr-FR')}`}{commune ? ` — ${commune}` : ' — île'}
        </span>
      </div>
      {/* le tri est SERVEUR (l'ordre affiché = l'ordre servi) — on le DIT, pas d'ORDER BY décoratif */}
      <p className="-mt-1 text-[9.5px] text-txt-dim">
        Triées par <b className="text-txt-mut">{SORTS.find((s) => s.key === sort)?.label.toLowerCase()}</b> décroissant.
      </p>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <table className="w-full text-[11px]">
          <thead className="sticky top-0 bg-surface-2 text-left text-[10px] uppercase tracking-wide text-txt-dim">
            <tr>
              <th className="px-2 py-1.5">Parcelle</th>
              <th className="px-2 py-1.5">Classement</th>
              <th className="px-2 py-1.5 text-right">Score</th>
              <th className="px-2 py-1.5 text-right">SDP rés.</th>
              <th className="px-2 py-1.5 text-right">Surface</th>
              <th className="px-2 py-1.5">Zone</th>
              <th className="px-2 py-1.5">Occupation</th>
              <th className="px-2 py-1.5 text-right">Rang cne</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((it) => (
              <tr key={it.idu} data-renouv-row className="cursor-pointer border-t border-line hover:bg-surface-2"
                onClick={() => select(it.idu)}>
                <td className="px-2 py-1.5 font-mono text-txt">{it.idu}</td>
                {/* §1 — la puce d'action : le verdict SERVI (tier v2 + étage 0), M135/M137 ; jamais
                    « Classement historique » (on ne sert pas le statut matrice legacy). */}
                <td className="px-2 py-1.5">
                  {(() => { const v = verdictMeta(null, it.tier_v2, it.etage0); return (
                    <span className="rounded-full px-1.5 py-0.5 text-[10px] font-medium"
                      style={{ background: `${v.color}22`, color: v.color }}>{v.label}</span>
                  ) })()}
                </td>
                <td className="px-2 py-1.5 text-right font-medium" style={{ color: TOKENS.renouv }}>{it.renouv_score}</td>
                <td className="px-2 py-1.5 text-right text-txt-mut">{it.sdp_residuelle_m2 != null ? `${it.sdp_residuelle_m2.toLocaleString('fr-FR')} m²` : '—'}</td>
                <td className="px-2 py-1.5 text-right text-txt-mut">{it.surface_m2 != null ? `${it.surface_m2.toLocaleString('fr-FR')} m²` : '—'}</td>
                <td className="px-2 py-1.5 text-txt-mut">{it.zone_plu ?? '—'}</td>
                <td className="px-2 py-1.5 text-txt-dim">{CODE_LABEL[it.code_bati_origine] ?? it.code_bati_origine}</td>
                <td className="px-2 py-1.5 text-right text-txt-mut">{it.rang_commune}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
