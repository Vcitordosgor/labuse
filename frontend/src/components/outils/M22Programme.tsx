import { useInfiniteQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { postProgramme } from '../../lib/api'
import { fmtInt } from '../../lib/format'
import { useApp } from '../../store/useApp'
import { FaisabiliteTab } from '../fiche/Fiche'
import { ListPaginationFooter } from '../ListPagination'
import { CommuneScope } from './ModulePanel'
import { Tip } from '../Tip'
import { DestinationBadge, DestinationSelect, useDestinationsRef } from './DestinationSelect'
import { ParcelPicker } from './ParcelPicker'
import { TierBadge } from './TierBadge'

/** M22 · FAISABILITÉ — 2 entrées (M15-C) :
 *  · « Par critères » (SENS 2) : on décrit un programme, LABUSE propose les parcelles qui matchent.
 *    Le copilote pré-remplit le formulaire ; le moteur déterministe calcule. RG1 : le périmètre
 *    commune est SAISI ICI (plus hérité du filtre carte).
 *  · « Par parcelle » (SENS 1) : on désigne UNE parcelle (IDU / adresse / clic carte) et on voit sa
 *    faisabilité — exactement l'onglet Faisabilité des fiches, porté dans l'outil (aucune divergence). */

export function M22() {
  const { m22Prefill, setM22Prefill, parcelPrefill, setParcelPrefill, setModuleMap, select } = useApp()
  // OUTILS-FIX-2 A5 — pont Faisabilité par critères → Comparer (sélection ; limite 3 côté Comparer).
  const addToCompare = useApp((s) => s.addToCompare)
  const openCompare = useApp((s) => s.openCompare)
  const [selCmp, setSelCmp] = useState<Set<string>>(new Set())
  const [mode, setMode] = useState<'criteres' | 'parcelle'>('criteres')
  const [commune, setCommune] = useState<string | null>(null)   // RG1 : périmètre saisi dans l'outil
  const [picked, setPicked] = useState<string | null>(null)     // mode « par parcelle »
  const [form, setForm] = useState({ batiments: 1, niveaux: 2, logements_par_batiment: 8, surface_unite_m2: 60, circulation_pct: 20 })
  // RETOURS-11 (O2c) — filtre de zonage côté client, DÉCOCHÉ = on masque les zones agricoles (A) et
  // naturelles (N) éventuelles. Le moteur exclut DÉJÀ ces zones (constructible_neuf faux) : ce garde-fou
  // ne fait donc que confirmer visuellement, et laisse à l'utilisateur le choix de les réafficher.
  const [inclureAgriNat, setInclureAgriNat] = useState(false)
  // DESTINATIONS-1 (X4.3) — sous-destination R151-28 du programme (facultative) : elle AGIT (zone au
  // verdict « interdit » écartée et comptée, « sous condition »/« calibration » annotées par parcelle).
  const [dest, setDest] = useState<string | null>(null)
  const refDest = useDestinationsRef()
  const destLabel = (slug: string) => refDest.data?.sous_destinations.find((s) => s.slug === slug)?.libelle ?? slug
  // coef utile→SDP = 1 + circulations % (hypothèse éditable ; défaut 20 %, bas de fourchette 20-25 %)
  // FAISABILITE (pagination SOCLE) : le formulaire soumis est FIGÉ dans `query` ; une useInfiniteQuery
  // pagine les résultats par `offset`. « Trouver » (re)pose le snapshot ; changer le formulaire ne
  // relance rien tant qu'on ne resoumet pas (comportement d'avant, + pagination).
  const [query, setQuery] = useState<Record<string, unknown> | null>(null)
  const lancer = (f = form, c = commune, d = dest) => {
    setQuery({ ...f, commune: c, coef_circulation: 1 + f.circulation_pct / 100, ...(d ? { destination: d } : {}) })
  }
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
  const brut = pages.flatMap((p) => (p.items ?? []) as Record<string, any>[])
  // RETOURS-11 (O2c) — la famille de zone se lit sur la 1re lettre du code PLU fin renvoyé (« Ud », « 1AUb »,
  // « Nto », « Ap »…) : A = agricole, N = naturel. Les zones AU fermées (secteurs de transition « AU…st »)
  // sont déjà écartées par le moteur ; on complète le garde-fou pour la forme « <chiffre>?AU…st ».
  const estAgriNat = (z: unknown): boolean => {
    const c = String(z ?? '').trim().toUpperCase()
    if (!c) return false
    if (/^A/.test(c) && !/^AU/.test(c)) return true          // A… (agricole) mais pas AU…
    if (/^N/.test(c)) return true                            // N… (naturel)
    if (/^\d*AU\w*ST$/.test(c)) return true                  // AU fermée (secteur de transition)
    return false
  }
  // B1 — le tri par ADÉQUATION est fait par le SERVEUR (écart au programme croissant) AVANT la
  // troncature : la page servie EST déjà celle des mieux ajustées. Le front n'y touche plus (le
  // re-tri des seules lignes chargées masquait le vrai classement — VERIF-1 Q2). On garde l'ordre servi.
  const items = inclureAgriNat ? brut : brut.filter((i) => !estAgriNat(i.zone))
  const total = meta?.n ?? 0
  const masquees = brut.length - items.length                // lignes agri/nat masquées (honnêteté compteur)
  // RETOURS-10 (T3) — plus de « Tout charger » : « Voir 200 de plus » seul, jamais de tir massif.
  // carte : résultats en mode critères (accumulés), parcelle désignée en mode parcelle
  useEffect(() => {
    const idus = mode === 'criteres' ? items.map((i) => i.idu as string) : (picked ? [picked] : [])
    setModuleMap({ idus, extra: null })
    return () => setModuleMap({ idus: [], extra: null })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, results.dataUpdatedAt, picked, inclureAgriNat])

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
          {/* RETOURS-13 R20 — le paragraphe d'aide est RETIRÉ (demande Vic) : l'aide vit derrière
              le « i » à côté du périmètre, plus en bloc permanent. */}
          <div className="flex items-center gap-1.5">
            <div className="min-w-0 flex-1"><CommuneScope commune={commune} onChange={setCommune} /></div>
            <Tip side="bottom" tip="Décrivez votre programme — bâtiments, hauteur, logements par bâtiment, surface par logement. LABUSE calcule la surface de plancher nécessaire et trouve les parcelles où le PLU la permet. Le Copilote peut remplir le formulaire pour vous : « 3 immeubles R+3 de 8 logements ».">
              <span role="button" tabIndex={0} aria-label="Aide"
                className="flex h-[15px] w-[15px] shrink-0 items-center justify-center rounded-full border border-line-2 text-[9px] font-bold leading-none text-txt-dim hover:border-mint hover:text-mint">i</span>
            </Tip>
          </div>
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
          {/* DESTINATIONS-1 (X4.3) — la destination AGIT : zone « interdit » écartée (et comptée),
              « sous condition » / « calibration en cours » annotées sur chaque parcelle. */}
          <DestinationSelect dataAttr="programme" value={dest} onChange={setDest} />
          <button onClick={() => lancer()} disabled={results.isLoading}
            className="rounded-lg bg-mint py-1.5 text-xs font-medium text-bg transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">
            {results.isLoading ? 'Calcul…' : 'Trouver les parcelles'}
          </button>
          {results.isError && <p className="text-[11px] text-st-ecartee">Recherche indisponible — réessayez.</p>}
          {meta && (
            <>
              {/* PROGRAMME ÉPINGLÉ (mandat) — le récap reste STICKY en tête pendant le scroll des résultats :
                  on sait toujours ce qu'on cherche. */}
              <div data-prog-count className="sticky top-0 z-10 -mx-1 rounded-lg border border-line-2 bg-surface-1/95 px-3 py-2 backdrop-blur">
                {/* FIX-INTEGRATION I1 — « SDP gabarit » = capacité constructible au gabarit PLU (R+N,
                    hauteur, coef circulations éditable ci-dessus). À NE PAS confondre avec la « SDP
                    estimée » de l'Assemblage (par analogie DVF) ni avec la « SHAB vendable » de la
                    Faisabilité (SDP × rendement 0,8) : trois grandeurs distinctes, jamais comparables. */}
                <p className="text-[12px] leading-snug text-txt">
                  <b className="num-key text-mint">{fmtInt(total)}</b> parcelle{total > 1 ? 's' : ''} · <b className="text-txt">{meta.criteres.unites}</b> unités → <span title="Capacité constructible au gabarit PLU (R+N, hauteur), coef circulations appliqué — pas la SDP estimée de l'Assemblage ni la SHAB vendable de la Faisabilité">SDP gabarit</span> ≥ <b className="tnum text-mint">{fmtInt(meta.criteres.sdp_min_m2)} m²</b>
                  <span className="text-txt-dim">{commune ? ` · ${commune}` : ' · toute l’île'}</span>
                </p>
                {/* B2 — compte et liste sur le MÊME ensemble : le tri « adéquation » est désormais fait
                    côté serveur avant la troncature, donc « les mieux ajustées d'abord » est vrai. */}
                <p className="mt-0.5 text-[9.5px] leading-snug text-txt-dim">{meta.criteres.hauteur_regle} · <b className="text-txt-mut">{fmtInt(items.length)}</b> affichée{items.length > 1 ? 's' : ''} sur {fmtInt(total)}, les mieux ajustées au programme d’abord.</p>
                {/* RETOURS-11 (O2c) — le zonage agricole/naturel est masqué par défaut ; case pour le réafficher. */}
                <label className="mt-1 flex cursor-pointer items-center gap-1.5 text-[9.5px] text-txt-dim hover-fill rounded px-1 py-0.5">
                  <input type="checkbox" checked={inclureAgriNat} onChange={(e) => setInclureAgriNat(e.target.checked)}
                    className="h-3 w-3 accent-mint" />
                  Inclure les zones agricoles (A) et naturelles (N)
                  {masquees > 0 && !inclureAgriNat && <span className="text-txt-mut">· {fmtInt(masquees)} masquée{masquees > 1 ? 's' : ''}</span>}
                </label>
                {/* DESTINATIONS-1 (X4.3) — l'écart est DIT : combien de parcelles la destination a écartées. */}
                {meta.criteres.destination && (
                  <p data-prog-dest-ecartees className="mt-0.5 text-[9.5px] leading-snug text-txt-mut"
                    title={meta.criteres.destination_regle ?? undefined}>
                    Destination « {destLabel(meta.criteres.destination)} » —{' '}
                    <b className="text-txt">{fmtInt(meta.criteres.destination_ecartees ?? 0)}</b>{' '}
                    parcelle{(meta.criteres.destination_ecartees ?? 0) > 1 ? 's' : ''} écartée{(meta.criteres.destination_ecartees ?? 0) > 1 ? 's' : ''} : destination interdite dans leur zone.
                  </p>
                )}
              </div>
              {/* A5 — pont Comparer sur la sélection (même geste/compteur que Courrier). */}
              {selCmp.size > 0 && (
                <div className="flex flex-wrap items-center gap-2">
                  <button data-prog-comparer onClick={() => { [...selCmp].slice(0, 3).forEach(addToCompare); openCompare() }}
                    className="rounded-lg border border-mint/50 bg-mint/10 px-2.5 py-1 text-[11px] font-medium text-mint transition-colors duration-quick hover:bg-mint/20">
                    Comparer ({Math.min(selCmp.size, 3)}) →
                  </button>
                  {selCmp.size > 3 && <span className="text-[10px] text-txt-dim">Comparer se limite à 3.</span>}
                </div>
              )}
              <div className="flex flex-col gap-1.5">
                {items.map((i) => (
                  <div key={i.idu} data-prog-item
                    className="flex w-full items-center gap-2 rounded-lg border border-line-2 bg-surface-3 px-2.5 py-2 transition-colors duration-quick hover:border-mint/50">
                    {/* A5 — case de sélection (Comparer), n'ouvre pas la fiche */}
                    <input type="checkbox" data-prog-sel className="h-3 w-3 shrink-0 accent-mint" checked={selCmp.has(i.idu)}
                      onChange={() => setSelCmp((s) => { const n = new Set(s); n.has(i.idu) ? n.delete(i.idu) : n.add(i.idu); return n })} />
                    <button onClick={() => select(i.idu)} className="flex min-w-0 flex-1 items-center gap-2 text-left">
                    <div className="min-w-0 flex-1">
                      <div className="font-mono text-xs text-txt-hi">{i.idu.slice(8, 10)} {i.idu.slice(10)}
                        {!commune && i.commune && <span className="ml-1.5 font-sans text-[11px] text-txt-dim">{i.commune}</span>}
                      </div>
                      <div className="truncate text-[10.5px] text-txt-mut">
                        <span title="Capacité constructible au gabarit PLU — ≠ SDP estimée (Assemblage) ≠ SHAB vendable (Faisabilité)">SDP gabarit</span> {fmtInt(i.sdp)} m² · zone {i.zone ?? '—'} {i.hauteur_verifiee ? `(h ${i.hauteur_plu_m} m ✓)` : '(hauteur à instruire)'}
                        {i.capacite_estimee && <span className="ml-1 rounded bg-amber-500/15 px-1 text-[9.5px] text-amber-500"
                          title="Capacité ESTIMÉE — zone non calibrée finement (hypothèses génériques)">estimée</span>}
                        {/* DESTINATIONS-1 (X4.3) — verdict destination annoté (phrase sourcée au survol). */}
                        {i.destination_verdict && i.destination_verdict.etat !== 'autorise' && (
                          <span className="ml-1 inline-flex align-middle" title={i.destination_verdict.phrase ?? undefined}>
                            <DestinationBadge etat={i.destination_verdict.etat} />
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="shrink-0 text-right">
                      <div className="num-key text-sm text-mint">×{i.marge_capacite}</div>
                      <div>
                        <TierBadge tier={i.tier_v2 as string | null} etage0={i.etage0 as boolean | null} statut={i.statut as string | null} />
                      </div>
                    </div>
                    </button>
                  </div>
                ))}
              </div>
              {/* PAGINATION SOCLE — 200 par 200, jamais de tir massif ni d'export. */}
              <ListPaginationFooter
                className="flex flex-wrap items-center gap-3 border-t border-line pt-2 text-[11px] text-txt-mut"
                shown={items.length} total={total} step={meta.cap ?? 200}
                onMore={() => results.fetchNextPage()}>
                {results.isFetchingNextPage && <span className="text-txt-dim">chargement…</span>}
              </ListPaginationFooter>
            </>
          )}
        </>
      )}

      {mode === 'parcelle' && (
        <>
          <div className="rounded-lg border border-line-2 bg-mint/[0.05] px-3 py-2 text-[10.5px] leading-relaxed text-txt-mut">
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
