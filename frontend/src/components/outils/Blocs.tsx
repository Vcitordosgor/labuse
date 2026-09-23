/**
 * Outil « Blocs fonciers » — OUTILS-MUSCLER-3. Sert la table `parcel_blocs` (batch
 * `labuse blocs-build`) : les parcelles CONTIGUËS (0,5 m) d'un même propriétaire personne morale
 * (SIREN), regroupées en une assiette, sur toute l'île. Le propriétaire est TOUJOURS une PM nommée
 * (les particuliers, sans identité stable d'une parcelle à l'autre, sont hors périmètre — dit à
 * l'écran). Aucun calcul métier au front (/modules/blocs sert tout) ; aucun badge de score ; aucun
 * export ; aucune surface IA. SDP résiduelle agrégée = Estimé (somme des résiduels de la fiche).
 * Patrons SOCLE : CommuneScope (choix explicite), filtres à paliers, cartes empilées, pagination
 * 200, tiroir méthode, fil de retour. Ponts : Courrier (sélection), Scan patrimoine (SIREN) et
 * Assembler (les IDU du bloc) par carte, « Voir la fiche » sur chaque IDU du détail.
 */
import { useQuery, useInfiniteQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { BLOCS_PAGE, getBlocDetail, getBlocs, type BlocItem } from '../../lib/api'
import { fmtInt } from '../../lib/format'
import { TOKENS } from '../../lib/tokens'
import { useApp } from '../../store/useApp'
import { ListPaginationFooter } from '../ListPagination'
import { Loading } from '../Loading'
import { ErrorState } from '../States'
import { Siren } from '../shared/Siren'
import { Tip } from '../Tip'
import { CommuneScope, useModuleMap } from './ModulePanel'

const fmtM2 = (v: number | null | undefined) => (v == null ? '—' : `${fmtInt(v)} m²`)

// Paliers fixes (un select tient dans les 320 px ; le tri serveur reste résiduel décroissant).
const SURFACE_MIN = [
  { v: 0, label: 'peu importe' }, { v: 1000, label: '≥ 1 000 m²' }, { v: 5000, label: '≥ 5 000 m²' },
  { v: 10000, label: '≥ 1 ha' }, { v: 50000, label: '≥ 5 ha' },
]
const SDP_MIN = [
  { v: 0, label: 'peu importe' }, { v: 200, label: '≥ 200 m²' }, { v: 500, label: '≥ 500 m²' },
  { v: 1000, label: '≥ 1 000 m²' }, { v: 5000, label: '≥ 5 000 m²' },
]
const N_MIN = [
  { v: 2, label: '≥ 2' }, { v: 3, label: '≥ 3' }, { v: 6, label: '≥ 6' }, { v: 11, label: '≥ 11' },
]

const Estime = () => (
  <span className="rounded bg-amber-500/15 px-1 text-[8.5px] font-medium text-amber-500">Estimé</span>
)

// Détail d'un bloc (ouvert au clic) — les IDU, chacun avec surface + zone + « Voir la fiche »,
// et l'emprise du bloc mise en surbrillance sur la carte (mécanisme moduleMap).
function BlocDetail({ blocId }: { blocId: number }) {
  const select = useApp((s) => s.select)
  const setMselPrefill = useApp((s) => s.setMselPrefill)
  const setModule = useApp((s) => s.setModule)
  const pushOutilRetour = useApp((s) => s.pushOutilRetour)
  const q = useQuery({ queryKey: ['bloc', blocId], queryFn: () => getBlocDetail(blocId) })
  const membres = q.data?.membres ?? []
  // Emprise = les parcelles du bloc surlignées sur la carte tant que le détail est ouvert.
  useModuleMap(membres.map((m) => m.idu), null, [q.dataUpdatedAt])

  if (q.isLoading) return <div className="px-2 py-1"><Loading label="Parcelles du bloc…" /></div>
  if (q.isError || !q.data) return null
  return (
    <div className="mt-1 flex flex-col gap-0.5 border-t border-line-2 pt-1">
      {/* RECETTE-1 R21 — le bouton « Voir la fiche » disparaît : cliquer la LIGNE ouvre la fiche. */}
      {membres.map((m) => (
        <div key={m.idu} data-bloc-membre data-bloc-fiche role="button" tabIndex={0}
          onClick={() => select(m.idu)}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); select(m.idu) } }}
          className="flex cursor-pointer items-center gap-1.5 rounded px-1 py-0.5 text-[10.5px] hover-fill">
          <span className="font-mono text-txt-hi">{m.idu}</span>
          <span className="text-txt-dim">{fmtM2(m.surface_m2)}</span>
          {m.zone && <span className="text-txt-dim">· {m.zone}</span>}
          <span className="ml-auto tnum text-txt-mut">{fmtM2(m.sdp_residuelle_m2)}</span>
        </div>
      ))}
      {/* Assembler → : l'outil Assemblage pré-rempli avec les IDU du bloc (fil de retour). */}
      <button data-bloc-assembler className="mt-1 self-start rounded-lg border border-mint/40 bg-mint/10 px-2 py-0.5 text-[10.5px] font-medium text-mint hover:bg-mint/20"
        onClick={() => { setMselPrefill(membres.map((m) => m.idu)); setModule('assemblage'); pushOutilRetour({ module: 'blocs-fonciers', label: 'Blocs fonciers' }) }}>
        ⛶ Assembler ce bloc →
      </button>
    </div>
  )
}

function Carte({ it, ouvert, onToggle }: { it: BlocItem; ouvert: boolean; onToggle: () => void }) {
  const setM02Prefill = useApp((s) => s.setM02Prefill)
  const setModule = useApp((s) => s.setModule)
  const pushOutilRetour = useApp((s) => s.pushOutilRetour)
  return (
    <div className="rounded-lg border border-line-2 bg-surface-3 px-2.5 py-1.5">
      <div data-bloc-row className="flex cursor-pointer items-center gap-2" onClick={onToggle}>
        <span className="text-[9px] text-txt-dim">{ouvert ? '▾' : '▸'}</span>
        <span className="min-w-0 flex-1 truncate text-[11px] text-txt">
          {it.denomination ?? '—'}
        </span>
        <span className="ml-auto tnum text-[11px] text-txt">{fmtM2(it.sdp_residuelle_m2)}</span>
        <Estime />
      </div>
      <div className="mt-0.5 flex flex-wrap items-center gap-x-1.5 gap-y-0.5 pl-4 text-[10.5px] text-txt-mut">
        <span className="shrink-0 text-txt">{it.n_parcelles} parcelles</span>
        <span className="text-txt-dim">·</span>
        <span className="shrink-0">{fmtM2(it.surface_totale_m2)}</span>
        <span className="text-txt-dim">·</span>
        <span className="shrink-0 truncate">{it.communes.join(', ')}</span>
        {it.zonages.length > 0 && <><span className="text-txt-dim">·</span>
          <span className="shrink-0 truncate text-txt-dim">{it.zonages.slice(0, 4).join(' ')}</span></>}
      </div>
      <div className="mt-0.5 flex items-center gap-1.5 pl-4 text-[10px]">
        {it.siren && <Siren value={it.siren} className="font-mono text-[10px] text-txt-dim" />}
        {it.sdp_couverture < it.n_parcelles && (
          <span className="text-txt-dim">
            résiduel sur {it.sdp_couverture}/{it.n_parcelles}
          </span>
        )}
        {/* Scan patrimoine → : tout ce que ce SIREN possède et construit. */}
        <button data-bloc-scan className="ml-auto shrink-0 rounded border border-line-2 px-1 text-[9.5px] text-txt-mut hover:border-mint hover:text-mint"
          onClick={(e) => { e.stopPropagation(); setM02Prefill(it.siren); setModule('patrimoine'); pushOutilRetour({ module: 'blocs-fonciers', label: 'Blocs fonciers' }) }}>
          Scan patrimoine →
        </button>
      </div>
      {ouvert && <BlocDetail blocId={it.bloc_id} />}
    </div>
  )
}

export function Blocs() {
  const setCourrierPrefillIdus = useApp((s) => s.setCourrierPrefillIdus)
  const setModule = useApp((s) => s.setModule)
  const pushOutilRetour = useApp((s) => s.pushOutilRetour)

  const [commune, setCommune] = useState<string | null>(null)   // Toute l'île par défaut
  const [surfMin, setSurfMin] = useState(0)
  const [sdpMin, setSdpMin] = useState(0)
  const [nMin, setNMin] = useState(2)
  const [inclurePublics, setInclurePublics] = useState(false)   // publics écartés par défaut
  const [openId, setOpenId] = useState<number | null>(null)
  const [sel, setSel] = useState<Set<number>>(new Set())   // blocs cochés (par bloc_id)
  // RECETTE-1 R21 — deux temps : (1) on pose ses filtres ; (2) on clique « Voir les parcelles »,
  // le listing s'ouvre et le bloc de filtres se replie en accordéon. `montre` gouverne les deux.
  const [montre, setMontre] = useState(false)
  const [filtresOuverts, setFiltresOuverts] = useState(true)
  const voir = () => { setMontre(true); setFiltresOuverts(false) }

  const reset = () => { setSel(new Set()); setOpenId(null) }
  const q = useInfiniteQuery({
    queryKey: ['blocs', commune, surfMin, sdpMin, nMin, inclurePublics],
    queryFn: ({ pageParam }) => getBlocs(commune, surfMin, sdpMin, nMin, inclurePublics, pageParam),
    initialPageParam: 0,
    getNextPageParam: (last, pages) => { const n = pages.reduce((s, p) => s + p.items.length, 0); return n < last.total ? n : undefined },
    enabled: montre,   // R21 — rien ne charge tant que « Voir les parcelles » n'est pas cliqué
  })
  const items = q.data?.pages.flatMap((p) => p.items) ?? []
  const meta = q.data?.pages[0]
  const total = meta?.total ?? 0
  // Pont Courrier : un IDU représentatif par bloc sélectionné (le Courrier résout le propriétaire).
  const idusCourrier = items.filter((i) => sel.has(i.bloc_id)).map((i) => i.idu_repr).filter((x): x is string => !!x)

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      {/* bandeau client — ce que l'outil EST (et n'est pas) */}
      <div className="rounded-lg border px-3 py-2 text-[10.5px] leading-relaxed text-txt-mut"
        style={{ borderColor: `${TOKENS.mint}4d`, background: `${TOKENS.mint}0f` }}>
        Les parcelles <b className="text-txt">contiguës d'un même propriétaire</b> regroupées en une
        assiette — ce qu'un promoteur ne voit pas parcelle par parcelle. <b className="text-txt">Personnes
        morales seulement</b> (SIREN) : les particuliers n'ont pas d'identité stable d'une parcelle à l'autre.
        <Tip garder tip="Un bloc = des parcelles cadastrales en contact (≤ 0,5 m) appartenant au même SIREN (fichiers des personnes morales, DGFiP). Les particuliers sont hors périmètre : aucun regroupement par nom approché.">
          <span className="ml-1 cursor-help rounded-full border border-line-2 px-1 text-[8px] text-txt-dim">i</span>
        </Tip>
      </div>

      {/* RECETTE-1 R21 — entrée : périmètre + filtres à paliers, DANS un accordéon qui se replie
          quand on clique « Voir les parcelles » (le listing prend alors la place). */}
      <details data-blocs-filtres open={filtresOuverts}
        onToggle={(e) => setFiltresOuverts((e.target as HTMLDetailsElement).open)}
        className="flex flex-col gap-2">
      <summary className="cursor-pointer list-none py-0.5 text-[11px] font-medium text-txt-dim marker:hidden hover:text-mint">
        {filtresOuverts ? 'Filtres ▾' : 'Filtres ▸'}
      </summary>
      <div className="mt-1 flex flex-col gap-2">
      <CommuneScope commune={commune} noteFiltre={false} onChange={(c) => { setCommune(c); reset() }} />
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-txt-mut">
        <label className="flex items-center gap-1.5">Surface totale
          <select data-blocs-surf-min value={surfMin} onChange={(e) => { setSurfMin(Number(e.target.value)); reset() }}
            className="rounded border border-line-2 bg-surface-3 px-1 py-0.5 text-txt focus:border-mint focus:outline-none">
            {SURFACE_MIN.map((o) => <option key={o.v} value={o.v}>{o.label}</option>)}
          </select>
        </label>
        <label className="flex items-center gap-1.5">Résiduel
          <select data-blocs-sdp-min value={sdpMin} onChange={(e) => { setSdpMin(Number(e.target.value)); reset() }}
            className="rounded border border-line-2 bg-surface-3 px-1 py-0.5 text-txt focus:border-mint focus:outline-none">
            {SDP_MIN.map((o) => <option key={o.v} value={o.v}>{o.label}</option>)}
          </select>
        </label>
        <label className="flex items-center gap-1.5">Parcelles
          <select data-blocs-n-min value={nMin} onChange={(e) => { setNMin(Number(e.target.value)); reset() }}
            className="rounded border border-line-2 bg-surface-3 px-1 py-0.5 text-txt focus:border-mint focus:outline-none">
            {N_MIN.map((o) => <option key={o.v} value={o.v}>{o.label}</option>)}
          </select>
        </label>
      </div>
      {/* Propriétaires publics (commune, État, collectivité, EP, SEM — catégorie juridique de la
          source) écartés par défaut ; la case les rétablit. */}
      <label className="flex items-center gap-2 text-[11px] text-txt-mut">
        <input type="checkbox" data-blocs-inclure-publics className="h-3 w-3 accent-mint"
          checked={inclurePublics} onChange={(e) => { setInclurePublics(e.target.checked); reset() }} />
        Inclure les propriétaires publics
        <Tip garder tip="Communes, État, Région/Département/EPCI, établissements publics (dont EPF) et SEM — classés par leur catégorie juridique (fichiers des personnes morales, DGFiP), jamais par une liste de noms. Écartés par défaut car rarement cessibles à un promoteur.">
          <span className="cursor-help rounded-full border border-line-2 px-1 text-[8px] text-txt-dim">i</span>
        </Tip>
      </label>
      </div>
      </details>

      {/* RECETTE-1 R21 — le geste explicite : ouvrir le listing (et replier les filtres). */}
      {!montre && (
        <button data-blocs-voir onClick={voir}
          className="shrink-0 rounded-lg bg-mint py-2 text-xs font-medium text-bg transition-[filter] duration-quick hover:brightness-110">
          Voir les parcelles
        </button>
      )}

      {q.isLoading && <Loading label="Blocs…" />}
      {q.isError && <ErrorState message="Signal momentanément indisponible — réessayez." retry={() => q.refetch()} />}
      {meta && total === 0 && (
        // ÉTAT VIDE HONNÊTE — jamais de zéros : le périmètre est nommé.
        <p data-blocs-vide className="rounded-lg bg-surface-2 px-3 py-2 text-[11px] leading-snug text-txt-mut">
          Aucun bloc de deux parcelles ou plus
          {commune ? <> à <b className="text-txt">{commune}</b></> : ' sur l’île'}
          {surfMin ? ` (surface ≥ ${fmtInt(surfMin)} m²)` : ''}{sdpMin ? ` (résiduel ≥ ${fmtInt(sdpMin)} m²)` : ''}
          {nMin > 2 ? ` (≥ ${nMin} parcelles)` : ''}{meta.maj ? ` au ${meta.maj}` : ''}.
          {!inclurePublics && meta.n_publics > 0 && (
            <> {fmtInt(meta.n_publics)} propriétaire{meta.n_publics > 1 ? 's' : ''} public{meta.n_publics > 1 ? 's' : ''} écarté{meta.n_publics > 1 ? 's' : ''} (cochez « inclure les propriétaires publics » pour les voir).</>
          )}
        </p>
      )}
      {meta && total > 0 && (
        <>
          {/* bandeau de tête : N blocs · signal [source] au [millésime] */}
          <div data-blocs-bandeau className="rounded-lg bg-surface-2 px-3 py-2 text-[10.5px] leading-snug text-txt-mut">
            <b data-blocs-total className="tnum text-txt">{fmtInt(total)}</b> bloc{total > 1 ? 's' : ''} ·
            signal <b className="text-txt">propriétaires PM DGFiP</b>{meta.millesime ? ` (millésime ${meta.millesime})` : ''}
            {meta.maj ? ` au ${meta.maj}` : ''}{commune ? ` — ${commune}` : ' — toute l’île'}
            {!inclurePublics && meta.n_publics > 0 && (
              <span data-blocs-ecartes className="text-txt-dim"> · {fmtInt(meta.n_publics)} propriétaire{meta.n_publics > 1 ? 's' : ''} public{meta.n_publics > 1 ? 's' : ''} écarté{meta.n_publics > 1 ? 's' : ''}</span>
            )}
          </div>

          <div className="flex items-center gap-2 text-[10px] uppercase tracking-wide text-txt-dim">
            <input type="checkbox" aria-label="Tout sélectionner" className="h-3 w-3 accent-mint"
              checked={items.length > 0 && items.every((i) => sel.has(i.bloc_id))}
              onChange={(e) => setSel(e.target.checked ? new Set(items.map((i) => i.bloc_id)) : new Set())} />
            <span>Tout sélectionner</span>
          </div>
          <div className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto">
            {items.map((it) => (
              <div key={it.bloc_id} className="flex items-start gap-1.5">
                <input type="checkbox" data-blocs-sel className="mt-2 h-3 w-3 shrink-0 accent-mint"
                  checked={sel.has(it.bloc_id)}
                  onChange={() => setSel((s) => { const n = new Set(s); n.has(it.bloc_id) ? n.delete(it.bloc_id) : n.add(it.bloc_id); return n })} />
                <div className="min-w-0 flex-1">
                  <Carte it={it} ouvert={openId === it.bloc_id}
                    onToggle={() => setOpenId((o) => (o === it.bloc_id ? null : it.bloc_id))} />
                </div>
              </div>
            ))}
          </div>
          <ListPaginationFooter shown={items.length} total={total} step={BLOCS_PAGE} onMore={() => q.fetchNextPage()}>
            {q.isFetchingNextPage && <span className="text-txt-dim">chargement…</span>}
          </ListPaginationFooter>
        </>
      )}

      {/* pied : tiroir « Détail et méthode » (gauche) et pont Courrier (droite) */}
      <div className="flex shrink-0 items-start justify-between gap-2">
        <details data-blocs-methode className="min-w-0 flex-1 text-xs">
          <summary className="cursor-pointer list-none py-1.5 text-[11.5px] text-txt-dim marker:hidden hover:text-mint">Détail et méthode ▾</summary>
          <div className="flex flex-col gap-1 text-[10.5px] leading-snug text-txt-dim">
            <p><b className="text-txt-mut">Le regroupement.</b> Un bloc réunit les parcelles cadastrales en
              contact (à 0,5 m près) appartenant au MÊME propriétaire personne morale (SIREN confirmé, fichiers
              des personnes morales DGFiP), à partir de 2 parcelles. La contiguïté est purement géométrique
              (PostGIS), jamais un rapprochement par nom.</p>
            <p><b className="text-txt-mut">Ce qu'il ne dit pas.</b> Les <b className="text-txt-mut">particuliers</b>
              sont hors périmètre : leur identité n'est pas stable d'une parcelle à l'autre, on ne regroupe donc
              pas leurs parcelles. Un bloc n'affirme ni la constructibilité, ni un accord de vente.</p>
            <p><b className="text-txt-mut">Les chiffres.</b> Surface, communes et zonages : Sourcés (cadastre,
              PLU). SDP résiduelle : Estimé — somme des résiduels de la fiche (enveloppe PLU moins bâti existant) ;
              une parcelle hors PLU n'a pas de résiduel connu (le compteur « résiduel sur n/N » le dit). Le tri
              suit la SDP résiduelle agrégée décroissante.</p>
            {meta?.source && <p className="text-[9.5px]">{meta.source}</p>}
          </div>
        </details>
        <button data-blocs-courrier disabled={idusCourrier.length === 0}
          onClick={() => { setCourrierPrefillIdus(idusCourrier); setModule('courriers'); pushOutilRetour({ module: 'blocs-fonciers', label: 'Blocs fonciers' }) }}
          className="mt-1.5 shrink-0 rounded-lg border border-mint/50 bg-mint/10 px-2.5 py-1 text-[11px] font-medium text-mint transition-colors duration-quick hover:bg-mint/20">
          ✉ Préparer les courriers ({idusCourrier.length}) →
        </button>
      </div>
    </div>
  )
}
