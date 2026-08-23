/**
 * Outil « Densifier l'existant » — M-RENOUV lot B, clé interne `renouvellement` INCHANGÉE (URL, QA,
 * tests, endpoint /renouvellement/liste, table parcel_renouvellement). DOCTRINE : parcelles OCCUPÉES,
 * « potentiel de densification » — jamais « opportunité », jamais mélangé aux Chaudes/Brûlantes.
 *
 * Mandat DENSIFIER (refonte 13 outils) : le panneau de 320 px ne portait plus 67 214 lignes (colonnes
 * coupées, scroll horizontal). Désormais :
 *   • PANNEAU = barre unique (SOCLE) « ma parcelle densifie-t-elle ? » + note datée + top 5 + bouton
 *     « ⛶ Ouvrir le tableau complet ».
 *   • OVERLAY plein écran (DensifierTablePanel, patron Comparaison/Communes, cycle de vie SOCLE via
 *     densifierTableOpen ∈ CLOSE_OVERLAYS) : toutes les colonnes visibles sans scroll horizontal, tri
 *     entier, pagination SOCLE (400 par 400 + tout charger) + export CSV.
 */
import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { getFiche, getRenouvListe, type RenouvItem } from '../../lib/api'
import { fmtInt } from '../../lib/format'
import { verdictMeta } from '../../lib/status'
import { TOKENS } from '../../lib/tokens'
import { useApp } from '../../store/useApp'
import { ListPaginationFooter } from '../ListPagination'
import { ParcelInput } from '../ParcelInput'
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

const fmtM2 = (v: number | null | undefined) => (v == null ? '—' : `${fmtInt(v)} m²`)

// ── PANNEAU latéral (320 px) — recherche directe + repères, PAS la liste des 67 214 ──
export function RenouvellementModule() {
  const select = useApp((s) => s.select)
  const commune = useApp((s) => s.commune)
  const openDensifier = useApp((s) => s.openDensifier)
  const [lookupIdu, setLookupIdu] = useState<string | null>(null)

  // note datée + top 5 : page 0, tri score (l'entrée la plus parlante).
  const { data, isLoading, error } = useQuery({
    queryKey: ['renouv-top', commune],
    queryFn: () => getRenouvListe('score', commune, 0),
    staleTime: 60_000,
  })
  // barre unique (SOCLE) → la parcelle densifie-t-elle ? Sa réponse vit dans le bloc `renouvellement`
  // de la fiche (run servi) — cache partagé `['fiche', idu]`. Bloc absent = hors segment (dit honnêtement).
  const lookup = useQuery({ queryKey: ['fiche', lookupIdu], queryFn: () => getFiche(lookupIdu!), enabled: !!lookupIdu, retry: false })
  const r = lookup.data?.renouvellement ?? null

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      {/* bandeau client — la définition ET la limite, toujours visibles (doctrine) */}
      <div className="rounded-lg border px-3 py-2 text-[10.5px] leading-relaxed text-txt-mut"
        style={{ borderColor: `${TOKENS.renouv}4d`, background: `${TOKENS.renouv}0f` }}>
        Le <b style={{ color: TOKENS.renouv }}>bâti qui peut porter davantage</b> — extensions,
        surélévations : des parcelles <b className="text-txt">déjà occupées</b> en zone constructible
        avec une <b className="text-txt">capacité résiduelle réelle</b>.
        <Tip tip="Parcelles déjà bâties en zone U/AU dont la capacité résiduelle > 100 m² (ou surface ≥ 600 m²), hors copropriété et hors foncier public. Score = heuristique déterministe (percent_rank : SDP résiduelle · assiette · rotation du bâti). Estimé — règles PLU calibrées, pas une expertise.">
          <span className="ml-1 cursor-help rounded-full border border-line-2 px-1 text-[8px] text-txt-dim">i</span>
        </Tip>
      </div>

      {/* BARRE UNIQUE (SOCLE) — « et la mienne ? » sans scroller 67 214 lignes */}
      <div className="rounded-lg border border-line-2 bg-surface-2 p-2.5">
        <ParcelInput dataAttr="renouv-idu" placeholder="Adresse ou IDU — votre parcelle densifie-t-elle ?" onPick={setLookupIdu} />
        {lookupIdu && lookup.isLoading && <p className="mt-1.5 text-[11px] text-txt-mut">Recherche…</p>}
        {lookupIdu && lookup.isError && <p className="mt-1.5 text-[11px] text-st-ecartee">Parcelle introuvable — vérifiez l’IDU.</p>}
        {lookupIdu && lookup.data && (
          r ? (
            <button data-renouv-lookup onClick={() => select(lookupIdu)}
              className="mt-1.5 w-full rounded-lg border px-2.5 py-1.5 text-left transition-colors duration-quick hover:bg-surface-3"
              style={{ borderColor: `${TOKENS.renouv}55` }}>
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-[11px] text-txt">{lookupIdu}</span>
                <span className="tnum text-[11px] font-medium" style={{ color: TOKENS.renouv }}>score {r.renouv_score}</span>
              </div>
              <div className="mt-0.5 text-[10px] text-txt-mut">
                {lookup.data.commune ?? ''} · SDP résid. <b className="text-txt-mut">{fmtM2(r.sdp_residuelle_m2)}</b>
                {r.zone_plu ? ` · ${r.zone_plu}` : ''} · rang commune {r.rang_commune}/{r.total_commune}
              </div>
            </button>
          ) : (
            <p data-renouv-lookup-none className="mt-1.5 text-[10.5px] leading-snug text-txt-dim">
              Cette parcelle n’est <b>pas</b> dans le segment densification (il vise le bâti occupé en zone
              constructible à capacité résiduelle réelle).
            </p>
          )
        )}
      </div>

      {isLoading && <Loading label="Densifier l'existant…" />}
      {error && <ErrorState message="Segment momentanément indisponible — réessayez." />}
      {data && (
        <>
          {/* note d'analyse DATÉE */}
          <div className="rounded-lg bg-surface-2 px-3 py-2 text-[10.5px] leading-snug text-txt-mut">
            <b className="text-txt">Analyse LABUSE</b>{data.maj ? ` · maj ${data.maj}` : ''} ·{' '}
            <b className="tnum text-txt">{fmtInt(data.total)}</b> parcelles occupées en zone constructible à capacité résiduelle réelle{commune ? ` — ${commune}` : ' — toute l’île'}.
            <span className="mt-0.5 block text-[9.5px] text-txt-dim">{data.source}</span>
          </div>

          {/* TOP 5 — repères, pas la liste (elle vit en grand) */}
          <div className="flex flex-col gap-1">
            {data.items.slice(0, 5).map((it) => (
              <button key={it.idu} data-renouv-top onClick={() => select(it.idu)}
                className="flex items-center justify-between gap-2 rounded-lg border border-line-2 bg-surface-1 px-2.5 py-1.5 text-left transition-colors duration-quick hover:bg-surface-2">
                <span className="min-w-0">
                  <span className="font-mono text-[11px] text-txt">{it.idu}</span>
                  <span className="ml-1.5 text-[10px] text-txt-dim">{it.commune_nom} · SDP résid. {fmtM2(it.sdp_residuelle_m2)}</span>
                </span>
                <span className="tnum shrink-0 text-[11px] font-medium" style={{ color: TOKENS.renouv }}>{it.renouv_score}</span>
              </button>
            ))}
          </div>

          {/* OUVRIR LE GRAND TABLEAU (overlay plein écran) */}
          <button data-renouv-ouvrir onClick={openDensifier}
            className="mt-1 rounded-lg py-2 text-center text-xs font-medium transition-[filter] duration-quick hover:brightness-110"
            style={{ background: TOKENS.renouv, color: '#0b0b0d' }}>
            ⛶ Ouvrir le tableau complet ({fmtInt(data.total)})
          </button>
        </>
      )}
    </div>
  )
}

// ── OVERLAY plein écran — le GRAND tableau (patron Comparaison/Communes, cycle de vie SOCLE) ──
function csvEscape(v: unknown): string {
  const s = v == null ? '' : String(v)
  return /[";\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}
function exporterCsv(items: RenouvItem[]) {
  const head = ['Parcelle', 'Classement', 'Score', 'SDP résiduelle (m²)', 'Surface (m²)', 'Occupation', 'Zone', 'Rang commune']
  const lignes = items.map((it) => [
    it.idu, verdictMeta(null, it.tier_v2, it.etage0).label, it.renouv_score,
    it.sdp_residuelle_m2 ?? '', it.surface_m2 ?? '', CODE_LABEL[it.code_bati_origine] ?? it.code_bati_origine,
    it.zone_plu ?? '', it.rang_commune,
  ])
  const csv = [head, ...lignes].map((r) => r.map(csvEscape).join(';')).join('\n')
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' })   // BOM = accents OK sous Excel
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = 'densifier-existant.csv'; a.click()
  URL.revokeObjectURL(url)
}

export function DensifierTablePanel() {
  const module = useApp((s) => s.module)
  const open = useApp((s) => s.densifierTableOpen)
  const setOpen = useApp((s) => s.setDensifierTableOpen)
  const select = useApp((s) => s.select)
  const commune = useApp((s) => s.commune)
  const [sort, setSort] = useState<(typeof SORTS)[number]['key']>('score')
  const [chargeTout, setChargeTout] = useState(false)

  const q = useInfiniteQuery({
    queryKey: ['renouv-table', sort, commune],
    queryFn: ({ pageParam }) => getRenouvListe(sort, commune, pageParam),
    initialPageParam: 0,
    // offset suivant = nb de lignes déjà chargées ; undefined = épuisé.
    getNextPageParam: (last, pages) => { const n = pages.reduce((s, p) => s + p.items.length, 0); return n < last.total ? n : undefined },
    enabled: open && module === 'renouvellement',
  })
  const items = q.data?.pages.flatMap((p) => p.items) ?? []
  const total = q.data?.pages[0]?.total ?? 0
  const meta = q.data?.pages[0]

  // « Tout charger » : enchaîne les pages (400 chacune) jusqu'à épuisement.
  useEffect(() => {
    if (!chargeTout) return
    if (q.hasNextPage && !q.isFetchingNextPage) q.fetchNextPage()
    else if (!q.hasNextPage) setChargeTout(false)
  }, [chargeTout, q.hasNextPage, q.isFetchingNextPage, q])

  if (module !== 'renouvellement' || !open) return null

  return (
    <div data-densifier-table-panel className="absolute inset-0 z-40 flex items-center justify-center bg-black/50 p-6"
      onClick={() => setOpen(false)}>
      <div className="floating flex max-h-full w-full max-w-[1100px] flex-col overflow-hidden" onClick={(e) => e.stopPropagation()}>
        {/* en-tête : titre + compteur + chips de tri ENTIÈRES + fermer */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 border-b border-line px-4 py-2.5">
          <div className="mr-auto">
            <h2 className="text-sm font-medium text-txt-hi">Densifier l’existant — <span className="tnum">{fmtInt(total)}</span> parcelles</h2>
            <p className="text-[10.5px] text-txt-dim">{meta?.maj ? `maj ${meta.maj} · ` : ''}cliquez une ligne pour ouvrir sa fiche{commune ? ` · ${commune}` : ''}</p>
          </div>
          <div className="flex items-center gap-1">
            <span className="mr-1 text-[10px] text-txt-dim">Trier :</span>
            {SORTS.map((s) => (
              <button key={s.key} data-densifier-tri={s.key} onClick={() => setSort(s.key)}
                className={`whitespace-nowrap rounded px-2 py-1 text-[11px] transition-colors duration-quick ${sort === s.key ? 'border bg-surface-3 font-medium' : 'text-txt-mut hover:text-txt'}`}
                style={sort === s.key ? { borderColor: `${TOKENS.renouv}66`, color: TOKENS.renouv } : undefined}>
                {s.label}{sort === s.key ? ' ↓' : ''}
              </button>
            ))}
          </div>
          <button onClick={() => setOpen(false)} className="text-txt-mut hover:text-txt" aria-label="Fermer">✕</button>
        </div>

        {/* corps : le grand tableau — toutes colonnes visibles, zéro scroll horizontal */}
        <div className="min-h-0 flex-1 overflow-y-auto px-3 py-2">
          {q.isLoading && <Loading accent="mint" label="Chargement des parcelles…" />}
          {q.isError && <ErrorState className="py-6" message="Segment momentanément indisponible." retry={() => q.refetch()} />}
          {!q.isLoading && !q.isError && (
            <table className="w-full text-[11px]">
              <thead className="sticky top-0 bg-bg-3 text-left text-[10px] uppercase tracking-wide text-txt-dim">
                <tr>
                  <th className="px-2 py-1.5">Parcelle</th>
                  <th className="px-2 py-1.5">Classement</th>
                  <th className="px-2 py-1.5 text-right">Score</th>
                  <th className="px-2 py-1.5 text-right">SDP résiduelle</th>
                  <th className="px-2 py-1.5 text-right">Surface</th>
                  <th className="px-2 py-1.5">Bâti existant</th>
                  <th className="px-2 py-1.5">Zone</th>
                  <th className="px-2 py-1.5 text-right">Rang commune</th>
                </tr>
              </thead>
              <tbody>
                {items.map((it) => (
                  <tr key={it.idu} data-densifier-row className="cursor-pointer border-t border-line hover:bg-surface-2"
                    onClick={() => { select(it.idu); setOpen(false) }}>
                    <td className="px-2 py-1.5 font-mono text-txt">{it.idu}</td>
                    <td className="px-2 py-1.5">
                      {(() => { const v = verdictMeta(null, it.tier_v2, it.etage0); return (
                        <span className="rounded-full px-1.5 py-0.5 text-[10px] font-medium" style={{ background: `${v.color}22`, color: v.color }}>{v.label}</span>
                      ) })()}
                    </td>
                    <td className="px-2 py-1.5 text-right font-medium" style={{ color: TOKENS.renouv }}>{it.renouv_score}</td>
                    <td className="px-2 py-1.5 text-right text-txt-mut">{fmtM2(it.sdp_residuelle_m2)}</td>
                    <td className="px-2 py-1.5 text-right text-txt-mut">{fmtM2(it.surface_m2)}</td>
                    {/* « Bâti existant » : la surface bâtie en m² n'est PAS servie par l'endpoint (absente de
                        parcel_renouvellement) — on sert le TYPE d'occupation (déjà bâtie / ensemble bâti),
                        jamais un m² inventé. */}
                    <td className="px-2 py-1.5 text-txt-dim">{CODE_LABEL[it.code_bati_origine] ?? it.code_bati_origine}</td>
                    <td className="px-2 py-1.5 text-txt-mut">{it.zone_plu ?? '—'}</td>
                    <td className="px-2 py-1.5 text-right text-txt-mut">{it.rang_commune}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* pied : pagination SOCLE (400 par 400 + tout charger) + export CSV */}
        <div className="border-t border-line px-4 py-2">
          <ListPaginationFooter
            className="flex flex-wrap items-center gap-3 text-[11px] text-txt-mut"
            shown={items.length} total={total} step={meta?.cap ?? 400}
            onMore={() => q.fetchNextPage()}
            onAll={() => setChargeTout(true)}
            allLabel={`Tout charger (${fmtInt(total)})`}
          >
            {q.isFetchingNextPage && <span className="text-txt-dim">chargement…</span>}
            <button data-densifier-csv onClick={() => exporterCsv(items)}
              className="ml-auto rounded-md border px-2 py-1 text-[11px] font-medium transition-colors duration-quick hover:brightness-110"
              style={{ borderColor: `${TOKENS.renouv}66`, color: TOKENS.renouv, background: `${TOKENS.renouv}12` }}>
              ⬇ Exporter CSV ({fmtInt(items.length)})
            </button>
          </ListPaginationFooter>
        </div>
      </div>
    </div>
  )
}
