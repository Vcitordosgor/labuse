/**
 * Module « Renouvellement » — M-RENOUV lot B, ADDITIF.
 * Liste triable du segment (score / SDP / surface / rang commune), lecture de
 * /renouvellement/liste uniquement. DOCTRINE : parcelles OCCUPÉES, « potentiel de
 * renouvellement urbain » — jamais « opportunité », jamais mélangé aux Chaudes/Brûlantes.
 */
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { getRenouvListe } from '../../lib/api'
import { TOKENS } from '../../lib/tokens'
import { useApp } from '../../store/useApp'
import { Loading } from '../Loading'
import { ErrorState } from '../States'

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

  if (isLoading) return <Loading label="Segment Renouvellement…" />
  if (error || !data) return <ErrorState message="Segment Renouvellement momentanément indisponible — réessayez." />

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2">
      {/* bandeau client — la définition ET la limite, toujours visibles (doctrine) */}
      <div className="rounded-lg border px-3 py-2 text-[10.5px] leading-relaxed text-txt-mut"
        style={{ borderColor: `${TOKENS.renouv}4d`, background: `${TOKENS.renouv}0f` }}>
        Des parcelles <b className="text-txt">déjà occupées</b> (écartées du classement principal)
        mais en zone constructible avec une <b className="text-txt">capacité restante réelle</b> :
        un <b style={{ color: TOKENS.renouv }}>potentiel de renouvellement urbain</b> (densifier,
        diviser, reconstruire). {data.avertissement}
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
          {data.n} affichées / {data.total.toLocaleString('fr-FR')} au total{commune ? ` — ${commune}` : ' — île'}
        </span>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <table className="w-full text-[11px]">
          <thead className="sticky top-0 bg-surface-2 text-left text-[10px] uppercase tracking-wide text-txt-dim">
            <tr>
              <th className="px-2 py-1.5">Parcelle</th>
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
