import { useInfiniteQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { postProgramme } from '../../lib/api'
import { fmtInt } from '../../lib/format'
import { useApp } from '../../store/useApp'
import { FaisabiliteTab } from '../fiche/Fiche'
import { ListPaginationFooter } from '../ListPagination'
import { CommuneScope } from './ModulePanel'
import { ParcelPicker } from './ParcelPicker'
import { TierBadge } from './TierBadge'

/** M22 · FAISABILITÉ — 2 entrées (M15-C) :
 *  · « Par critères » (SENS 2) : on décrit un programme, LABUSE propose les parcelles qui matchent.
 *    Le copilote pré-remplit le formulaire ; le moteur déterministe calcule. RG1 : le périmètre
 *    commune est SAISI ICI (plus hérité du filtre carte).
 *  · « Par parcelle » (SENS 1) : on désigne UNE parcelle (IDU / adresse / clic carte) et on voit sa
 *    faisabilité — exactement l'onglet Faisabilité des fiches, porté dans l'outil (aucune divergence). */
// export CSV (client-side) des parcelles candidates — mêmes colonnes que l'écran (mandat pagination).
function csvCell(v: unknown): string {
  const s = v == null ? '' : String(v)
  return /[";\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}
function exportProgrammeCsv(items: Record<string, any>[]) {
  const head = ['Parcelle', 'Commune', 'SDP gabarit (m²)', 'Zone', 'Hauteur PLU (m)', 'Marge capacité', 'Classement']
  const rows = items.map((i) => [i.idu, i.commune ?? '', i.sdp ?? '', i.zone ?? '', i.hauteur_verifiee ? i.hauteur_plu_m : 'à instruire',
    `x${i.marge_capacite}`, i.statut ?? ''])
  const csv = [head, ...rows].map((r) => r.map(csvCell).join(';')).join('\n')
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = 'faisabilite-programme.csv'; a.click()
  URL.revokeObjectURL(url)
}

export function M22() {
  const { m22Prefill, setM22Prefill, parcelPrefill, setParcelPrefill, setModuleMap, select } = useApp()
  const [mode, setMode] = useState<'criteres' | 'parcelle'>('criteres')
  const [commune, setCommune] = useState<string | null>(null)   // RG1 : périmètre saisi dans l'outil
  const [picked, setPicked] = useState<string | null>(null)     // mode « par parcelle »
  const [form, setForm] = useState({ batiments: 1, niveaux: 2, logements_par_batiment: 8, surface_unite_m2: 60, circulation_pct: 20 })
  // coef utile→SDP = 1 + circulations % (hypothèse éditable ; défaut 20 %, bas de fourchette 20-25 %)
  // FAISABILITE (pagination SOCLE) : le formulaire soumis est FIGÉ dans `query` ; une useInfiniteQuery
  // pagine les résultats par `offset`. « Trouver » (re)pose le snapshot ; changer le formulaire ne
  // relance rien tant qu'on ne resoumet pas (comportement d'avant, + pagination).
  const [query, setQuery] = useState<Record<string, unknown> | null>(null)
  const [chargeTout, setChargeTout] = useState(false)
  const lancer = (f = form, c = commune) => { setChargeTout(false); setQuery({ ...f, commune: c, coef_circulation: 1 + f.circulation_pct / 100 }) }
  const results = useInfiniteQuery({
    queryKey: ['programme', query],
    queryFn: ({ pageParam }) => postProgramme({ ...(query as Record<string, unknown>), offset: pageParam }),
    initialPageParam: 0,
    getNextPageParam: (last: any, pages) => { const n = pages.reduce((s, p: any) => s + (p.items?.length ?? 0), 0); return n < (last.n ?? 0) ? n : undefined },
    enabled: mode === 'criteres' && !!query,
  })

  useEffect(() => {
    if (m22Prefill) {
      // le copilote pré-remplit le formulaire (mode critères) — on ne remplace QUE les champs fournis
      const fournis = Object.fromEntries(Object.entries(m22Prefill).filter(([, v]) => v != null))
      const merged = { ...form, ...fournis } as typeof form
      setForm(merged)
      setM22Prefill(null)
      setMode('criteres')
      lancer(merged, commune)   // relance directement sur le formulaire mergé (pas de setTimeout fragile)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [m22Prefill])

  // M-ENTREE — porte fiche → Faisabilité : la parcelle amorce le mode « par parcelle » (motif
  // parcelPrefill partagé, consommation-puis-reset). Indépendant du m22Prefill critères (copilote).
  useEffect(() => {
    if (parcelPrefill) {
      setMode('parcelle')
      setPicked(parcelPrefill)
      setParcelPrefill(null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [parcelPrefill])

  const pages = (results.data?.pages ?? []) as Record<string, any>[]
  const meta = pages[0]
  const items = pages.flatMap((p) => (p.items ?? []) as Record<string, any>[])
  const total = meta?.n ?? 0
  // « Tout charger » : enchaîne les pages jusqu'à épuisement.
  useEffect(() => {
    if (!chargeTout) return
    if (results.hasNextPage && !results.isFetchingNextPage) results.fetchNextPage()
    else if (!results.hasNextPage) setChargeTout(false)
  }, [chargeTout, results.hasNextPage, results.isFetchingNextPage, results])
  // carte : résultats en mode critères (accumulés), parcelle désignée en mode parcelle
  useEffect(() => {
    const idus = mode === 'criteres' ? items.map((i) => i.idu as string) : (picked ? [picked] : [])
    setModuleMap({ idus, extra: null })
    return () => setModuleMap({ idus: [], extra: null })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, results.dataUpdatedAt, picked])

  const F = (k: keyof typeof form, label: string, opts?: { min?: number; title?: string }) => (
    <label title={opts?.title} className="min-w-0 flex-1 text-[11px] tracking-wide text-txt-dim">{label}
      <input type="number" min={opts?.min ?? 1} value={form[k] as number}
        onChange={(e) => setForm({ ...form, [k]: Number(e.target.value) })}
        className="mt-0.5 w-full rounded border border-line-2 bg-surface-3 px-2 py-1 text-xs text-txt focus:border-mint focus:outline-none" />
    </label>
  )

  return (
    // §1a — UN SEUL conteneur de défilement (le wrapper ModulePanel est overflow-hidden) : le
    // formulaire haut ne peut plus écraser la liste à 0 → on peut descendre voir les parcelles.
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto pr-0.5">
      {/* SÉLECTEUR DE MODE — deux façons d'entrer une parcelle */}
      <div className="flex gap-1 rounded-lg border border-line-2 bg-surface-2 p-1">
        {([['criteres', 'Par critères'], ['parcelle', 'Par parcelle']] as const).map(([m, l]) => (
          <button key={m} data-faisa-mode={m} onClick={() => setMode(m)}
            className={`flex-1 rounded-md py-1 text-[11px] font-medium transition-colors duration-quick ${mode === m ? 'bg-mint text-bg' : 'text-txt-mut hover:text-txt'}`}>
            {l}
          </button>
        ))}
      </div>

      {mode === 'criteres' && (
        <>
          <div className="rounded-lg border border-mint/40 bg-mint/[0.07] px-3 py-2 text-[10.5px] leading-relaxed text-txt-mut">
            Recherche de foncier pour du <b>logement</b> — décrivez le programme, les critères sont
            <b> calculés et affichés</b> (SDP au gabarit R+N, hauteur PLU). Le copilote sait pré-remplir :
            « un terrain pour 3 immeubles R+3 de 8 logements ».
          </div>
          <CommuneScope commune={commune} onChange={setCommune} />
          {/* LOT2 — grille 2 colonnes UNIQUE : les 5 champs s'alignent en colonnes (M²/UNITÉ et
              Circulations % ne décrochent plus sur une ligne à part). `items-end` aligne les inputs
              même quand un libellé passe sur 2 lignes. */}
          <div className="grid grid-cols-2 items-end gap-x-2 gap-y-1.5">
            {F('batiments', 'BÂTIMENTS')}
            {F('niveaux', 'R+N', { min: 0 })}
            {F('logements_par_batiment', 'UNITÉS/BÂT')}
            {F('surface_unite_m2', 'M²/UNITÉ (utile)', { min: 15 })}
            {F('circulation_pct', 'Circulations & murs %', { min: 0, title: 'Surface perdue en circulations, murs et parties communes, ajoutée à la surface habitable pour obtenir la SDP (hypothèse ; défaut 20 %, bas de la fourchette 20-25 %).' })}
          </div>
          <button onClick={() => lancer()} disabled={results.isLoading}
            className="rounded-lg bg-mint py-1.5 text-xs font-medium text-bg transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">
            {results.isLoading ? 'Calcul…' : 'Trouver les parcelles'}
          </button>
          {results.isError && <p className="text-[11px] text-st-ecartee">Recherche indisponible — réessayez.</p>}
          {meta && (
            <>
              {/* PROGRAMME ÉPINGLÉ (mandat) — le récap reste STICKY en tête pendant le scroll des résultats :
                  on sait toujours ce qu'on cherche. */}
              <div data-prog-count className="sticky top-0 z-10 -mx-1 rounded-lg border border-mint/40 bg-surface-1/95 px-3 py-2 backdrop-blur">
                {/* FIX-INTEGRATION I1 — « SDP gabarit » = capacité constructible au gabarit PLU (R+N,
                    hauteur, coef circulations éditable ci-dessus). À NE PAS confondre avec la « SDP
                    estimée » de l'Assemblage (par analogie DVF) ni avec la « SHAB vendable » de la
                    Faisabilité (SDP × rendement 0,8) : trois grandeurs distinctes, jamais comparables. */}
                <p className="text-[12px] leading-snug text-txt">
                  <b className="num-key text-mint">{fmtInt(total)}</b> parcelle{total > 1 ? 's' : ''} · <b className="text-txt">{meta.criteres.unites}</b> unités → <span title="Capacité constructible au gabarit PLU (R+N, hauteur), coef circulations appliqué — pas la SDP estimée de l'Assemblage ni la SHAB vendable de la Faisabilité">SDP gabarit</span> ≥ <b className="tnum text-mint">{fmtInt(meta.criteres.sdp_min_m2)} m²</b>
                  <span className="text-txt-dim">{commune ? ` · ${commune}` : ' · toute l’île'}</span>
                </p>
                <p className="mt-0.5 text-[9.5px] leading-snug text-txt-dim">{meta.criteres.hauteur_regle} · triées par marge de capacité décroissante.</p>
              </div>
              <div className="flex flex-col gap-1.5">
                {items.map((i) => (
                  <button key={i.idu} data-prog-item onClick={() => select(i.idu)}
                    className="flex w-full items-center gap-2 rounded-lg border border-line-2 bg-surface-3 px-3 py-2 text-left transition-colors duration-quick hover:border-mint/50">
                    <div className="min-w-0 flex-1">
                      <div className="font-mono text-xs text-txt-hi">{i.idu.slice(8, 10)} {i.idu.slice(10)}
                        {!commune && i.commune && <span className="ml-1.5 font-sans text-[11px] text-txt-dim">{i.commune}</span>}
                      </div>
                      <div className="truncate text-[10.5px] text-txt-mut">
                        <span title="Capacité constructible au gabarit PLU — ≠ SDP estimée (Assemblage) ≠ SHAB vendable (Faisabilité)">SDP gabarit</span> {fmtInt(i.sdp)} m² · zone {i.zone ?? '?'} {i.hauteur_verifiee ? `(h ${i.hauteur_plu_m} m ✓)` : '(hauteur à instruire)'}
                        {i.capacite_estimee && <span className="ml-1 rounded bg-amber-500/15 px-1 text-[9.5px] text-amber-500"
                          title="Capacité ESTIMÉE — zone non calibrée finement (hypothèses génériques)">estimée</span>}
                      </div>
                    </div>
                    <div className="shrink-0 text-right">
                      <div className="num-key text-sm text-mint">×{i.marge_capacite}</div>
                      <div>
                        <TierBadge tier={i.tier_v2 as string | null} etage0={i.etage0 as boolean | null} statut={i.statut as string | null} />
                      </div>
                    </div>
                  </button>
                ))}
              </div>
              {/* PAGINATION SOCLE + export CSV (client-side, mêmes colonnes que l'écran). */}
              <ListPaginationFooter
                className="flex flex-wrap items-center gap-3 border-t border-line pt-2 text-[11px] text-txt-mut"
                shown={items.length} total={total} step={meta.cap ?? 200}
                onMore={() => results.fetchNextPage()} onAll={() => setChargeTout(true)}
                allLabel={`Tout charger (${fmtInt(total)})`}>
                {results.isFetchingNextPage && <span className="text-txt-dim">chargement…</span>}
                <button data-prog-csv onClick={() => exportProgrammeCsv(items)}
                  className="ml-auto text-[11px] text-mint hover:underline">⬇ Exporter CSV</button>
              </ListPaginationFooter>
            </>
          )}
        </>
      )}

      {mode === 'parcelle' && (
        <>
          <div className="rounded-lg border border-mint/40 bg-mint/[0.07] px-3 py-2 text-[10.5px] leading-relaxed text-txt-mut">
            Désignez une parcelle : sa <b>faisabilité complète</b> (capacité, calcul tracé, explication IA,
            charge foncière) — le même calcul que l'onglet Faisabilité de la fiche.
          </div>
          {!picked ? (
            <ParcelPicker onPick={setPicked} picked={picked} />
          ) : (
            <>
              <div className="flex items-center gap-2 text-[11px] text-txt-mut">
                <span>Parcelle <b className="font-mono text-txt">{picked.slice(8, 10)} {picked.slice(10)}</b></span>
                <button data-faisa-changer onClick={() => setPicked(null)}
                  className="ml-auto rounded border border-line-2 px-2 py-0.5 text-[10.5px] text-txt-dim transition-colors duration-quick hover:text-txt">changer</button>
              </div>
              <div data-faisa-parcelle className="pr-0.5">
                <FaisabiliteTab idu={picked} />
              </div>
            </>
          )}
        </>
      )}
    </div>
  )
}
