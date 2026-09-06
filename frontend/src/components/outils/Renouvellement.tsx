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
 *     entier, pagination SOCLE (200 par 200, « Voir plus » — jamais de « tout charger »).
 */
import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { getFiche, getRenouvListe, RENOUV_PAGE } from '../../lib/api'
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
        surélévations : une parcelle <b className="text-txt">en zone constructible, déjà bâtie</b>, dont
        la <b className="text-txt">SDP résiduelle</b> dépasse le seuil de surface constructible et
        représente une <b className="text-txt">part significative de la SDP autorisée</b>.
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
// OUTILS-1 B7 — l'export CSV (csvEscape/exporterCsv + bouton) est RETIRÉ : consultation illimitée,
// extraction de la base non.

export function DensifierTablePanel() {
  const module = useApp((s) => s.module)
  const open = useApp((s) => s.densifierTableOpen)
  const setOpen = useApp((s) => s.setDensifierTableOpen)
  const select = useApp((s) => s.select)
  const commune = useApp((s) => s.commune)
  // OUTILS-FIX-2 A2 — pont Densifier → Faisabilité par parcelle (parcelPrefill, consommé par M22).
  const setParcelPrefill = useApp((s) => s.setParcelPrefill)
  const setModule = useApp((s) => s.setModule)
  // OUTILS-FIX-2 A5 — pont Listes → Comparer (même geste/compteur que Courrier ; limite 3 côté Comparer).
  const addToCompare = useApp((s) => s.addToCompare)
  const openCompare = useApp((s) => s.openCompare)
  const pushOutilRetour = useApp((s) => s.pushOutilRetour)   // OUTILS-FIX-3 Lot D — fil de retour
  // OUTILS-FIX-3 Lot D — l'outil cible affiche « ← Densifier » ; le retour rouvre le grand tableau.
  const RETOUR_DENSIFIER = { module: 'renouvellement', label: 'Densifier', restore: { densifierTableOpen: true } } as const
  const [sort, setSort] = useState<(typeof SORTS)[number]['key']>('score')
  const [inclure, setInclure] = useState(false)   // LOT12b — écartées MASQUÉES par défaut (comme Solaire)
  const [sel, setSel] = useState<Set<string>>(new Set())   // A5 — sélection pour Comparer

  const q = useInfiniteQuery({
    queryKey: ['renouv-table', sort, commune],
    queryFn: ({ pageParam }) => getRenouvListe(sort, commune, pageParam),
    initialPageParam: 0,
    // offset suivant = nb de lignes déjà chargées ; undefined = épuisé.
    getNextPageParam: (last, pages) => { const n = pages.reduce((s, p) => s + p.items.length, 0); return n < last.total ? n : undefined },
    enabled: open && module === 'renouvellement',
  })
  const items = q.data?.pages.flatMap((p) => p.items) ?? []
  // LOT12b — les ÉCARTÉES (etage0) sont masquées par défaut (une écartée à score 100 ne doit pas
  // trôner en tête du tri Score) ; « les inclure » les révèle. Filtre client sur les pages chargées
  // (même patron que Solaire) : le compteur d'écartées porte sur ce qui est chargé.
  const visibles = inclure ? items : items.filter((it) => !it.etage0)
  const nHidden = items.length - visibles.length
  const total = q.data?.pages[0]?.total ?? 0
  const meta = q.data?.pages[0]

  // RETOURS-10 (T3) — plus de « Tout charger » : « Voir 200 de plus » seul, jamais de tir massif.

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
            {/* O18 (d) — le score est une note RELATIVE (percentile) : les meilleures parcelles se
                tassent naturellement près de 100, il départage donc mal la tête de liste. Le tri
                « SDP résiduelle » sépare plus finement le haut du classement. */}
            <p className="text-[9.5px] text-txt-dim">Score = note relative (percentile) — près du sommet il départage peu ; pour la tête de liste, trier par SDP résiduelle.</p>
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
              {/* RETOURS-12 T4 — .thead-sticky : fond opaque + z-20 (l'en-tête se superposait aux lignes faute de z-index). */}
              <thead className="thead-sticky text-left text-[10px] uppercase tracking-wide text-txt-dim">
                <tr>
                  {/* A5 — case de sélection (Comparer) */}
                  <th className="w-6 px-2 py-1.5">
                    <input type="checkbox" aria-label="Tout sélectionner" className="h-3 w-3 accent-mint"
                      checked={visibles.length > 0 && visibles.every((i) => sel.has(i.idu))}
                      onChange={(e) => setSel(e.target.checked ? new Set(visibles.map((i) => i.idu)) : new Set())} />
                  </th>
                  <th className="px-2 py-1.5">Parcelle</th>
                  {/* LOT12a — DEUX grandeurs DISTINCTES, étiquetées : le Classement est le tier canonique
                      (parcel_p_score_v2, même partout) ; le Score est la note de densification (0-100,
                      parcel_renouvellement). Le score n'EST PAS le tier. */}
                  <th className="px-2 py-1.5" title="Classement canonique — le tier de la parcelle (même que la fiche et la carte). Différent du score de densification.">Classement</th>
                  <th className="px-2 py-1.5 text-right" title="Score de densification 0-100 (potentiel de renouvellement) — une grandeur DIFFÉRENTE du classement.">Score densif.</th>
                  {/* RETOURS-11F M9 — capacité NETTE des contraintes (PPR rouge, pente > 30 %, ravine) :
                      c'est ELLE qui pilote le score de densification. La SDP brute est en infobulle. */}
                  <th className="px-2 py-1.5 text-right" title="SDP résiduelle NETTE des contraintes physiques (PPR zone rouge, pente > 30 %, ravine). C'est la capacité réellement mobilisable — et ce qui classe la parcelle.">SDP nette</th>
                  <th className="px-2 py-1.5 text-right">Surface</th>
                  <th className="px-2 py-1.5">Bâti existant</th>
                  {/* OUTILS-FIX-1 C1 — colonne « Surélévation » retirée : le batch servait une valeur
                      périmée (débranchée depuis EXPORTS-1). Le signal vivant vit dans l'onglet Faisabilité. */}
                  <th className="px-2 py-1.5">Zone</th>
                  {/* LOT12c — rang DANS la commune par score de densification (1 = meilleure de la commune) */}
                  <th className="px-2 py-1.5 text-right" title="Rang de la parcelle dans sa commune par score de densification (1 = la meilleure de la commune).">Rang commune</th>
                  {/* A2 — pont par ligne vers Faisabilité */}
                  <th className="px-2 py-1.5" />
                </tr>
              </thead>
              <tbody>
                {visibles.map((it) => (
                  <tr key={it.idu} data-densifier-row className="hover-fill cursor-pointer border-t border-line"
                    onClick={() => { select(it.idu); setOpen(false) }}>
                    {/* A5 — sélection (Comparer), n'ouvre pas la fiche */}
                    <td className="px-2 py-1.5" onClick={(e) => e.stopPropagation()}>
                      <input type="checkbox" data-densifier-sel className="h-3 w-3 accent-mint"
                        checked={sel.has(it.idu)}
                        onChange={() => setSel((s) => { const n = new Set(s); n.has(it.idu) ? n.delete(it.idu) : n.add(it.idu); return n })} />
                    </td>
                    <td className="px-2 py-1.5 font-mono text-txt">{it.idu}</td>
                    <td className="px-2 py-1.5">
                      {(() => { const v = verdictMeta(null, it.tier_v2, it.etage0); return (
                        <span className="rounded-full px-1.5 py-0.5 text-[10px] font-medium" style={{ background: `${v.color}22`, color: v.color }}>{v.label}</span>
                      ) })()}
                    </td>
                    <td className="px-2 py-1.5 text-right font-medium" style={{ color: TOKENS.renouv }}>{it.renouv_score}</td>
                    {/* SDP NETTE + puce « −N % » quand une contrainte a été déduite (brute en infobulle) */}
                    <td className="px-2 py-1.5 text-right text-txt-mut" title={it.contrainte_pct ? `SDP brute ${fmtM2(it.sdp_residuelle_m2)} — ${it.contrainte_pct} % déduits (PPR rouge, pente > 30 %, ravine)` : undefined}>
                      {fmtM2(it.sdp_nette_m2 ?? it.sdp_residuelle_m2)}
                      {it.contrainte_pct != null && it.contrainte_pct > 0 && (
                        <span className="ml-1 rounded bg-st-amber/15 px-1 text-[9px] text-st-amber">−{it.contrainte_pct} %</span>
                      )}
                    </td>
                    <td className="px-2 py-1.5 text-right text-txt-mut">{fmtM2(it.surface_m2)}</td>
                    {/* « Bâti existant » : la surface bâtie en m² n'est PAS servie par l'endpoint (absente de
                        parcel_renouvellement) — on sert le TYPE d'occupation (déjà bâtie / ensemble bâti),
                        jamais un m² inventé. */}
                    <td className="px-2 py-1.5 text-txt-dim">{CODE_LABEL[it.code_bati_origine] ?? it.code_bati_origine}</td>
                    {/* OUTILS-FIX-1 C1 — colonne « Surélévation » retirée (batch débranché, valeur périmée). */}
                    <td className="px-2 py-1.5 text-txt-mut">{it.zone_plu ?? '—'}</td>
                    <td className="px-2 py-1.5 text-right text-txt-mut">{it.rang_commune}</td>
                    {/* A2 — pont Faisabilité par parcelle (ouvre M22 mode « par parcelle » pré-rempli). */}
                    <td className="px-2 py-1.5 text-right" onClick={(e) => e.stopPropagation()}>
                      <button data-densifier-faisabilite onClick={() => { setParcelPrefill(it.idu); setModule('programme'); setOpen(false); pushOutilRetour(RETOUR_DENSIFIER) }}
                        className="whitespace-nowrap text-[10px] font-medium text-mint hover:underline" title="Ouvrir la faisabilité détaillée de cette parcelle">Faisabilité →</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* pied : écartées (LOT12b) + pagination SOCLE (200 par 200, « Voir plus » seul) */}
        <div className="border-t border-line px-4 py-2">
          {/* A5 — pont Comparer sur la sélection (limite 3 côté Comparer). */}
          {sel.size > 0 && (
            <div className="mb-1.5">
              <button data-densifier-comparer
                onClick={() => { [...sel].slice(0, 3).forEach(addToCompare); openCompare(); pushOutilRetour(RETOUR_DENSIFIER) }}
                className="rounded-lg border border-mint/50 bg-mint/10 px-2.5 py-1 text-[11px] font-medium text-mint transition-colors duration-quick hover:bg-mint/20">
                Comparer ({Math.min(sel.size, 3)}) →
              </button>
              {sel.size > 3 && <span className="ml-2 text-[10px] text-txt-dim">Comparer se limite à 3 parcelles.</span>}
            </div>
          )}
          {(nHidden > 0 || inclure) && (
            <div className="mb-1.5 flex items-center gap-2 text-[10px] text-txt-dim">
              <span>{inclure ? 'écartées incluses' : `${fmtInt(nHidden)} écartée${nHidden > 1 ? 's' : ''} masquée${nHidden > 1 ? 's' : ''}`}</span>
              <button data-densifier-ecartees onClick={() => setInclure((v) => !v)} className="text-mint hover:underline">{inclure ? 'les masquer' : 'les inclure'}</button>
            </div>
          )}
          <ListPaginationFooter
            className="flex flex-wrap items-center gap-3 text-[11px] text-txt-mut"
            shown={visibles.length} total={total} step={RENOUV_PAGE}
            onMore={() => q.fetchNextPage()}
          >
            {q.isFetchingNextPage && <span className="text-txt-dim">chargement…</span>}
            {/* OUTILS-1 B7 — export CSV RETIRÉ (la consultation reste illimitée, l'extraction de la base non). */}
          </ListPaginationFooter>
        </div>
      </div>
    </div>
  )
}
