/**
 * Outil « Successions » — OUTILS-MUSCLER-1 Lot A. Sert le tag radar patrimonial
 * `parcel_veille_succession` (Score V v1.3) : personne morale à SIREN confirmé dont le dirigeant
 * le plus âgé a ≥ 70 ans, ou SCI dormante (≥ 20 ans, sans mise à jour RNE depuis ≥ 5 ans).
 * DOCTRINE (A0-successions-donnee.md) : une succession PROBABLE (horizon 3-7 ans) — l'écran ne dit
 * JAMAIS « en succession » (aucun acte, aucun décès constaté). Pas de date par parcelle : le signal
 * est daté du calcul (bandeau + tiroir). Aucun badge de score (l'analyse n'a pas été demandée),
 * aucun export, aucun calcul métier au front (/modules/successions sert tout).
 * Patrons SOCLE : sélecteur CommuneScope (choix explicite), cartes empilées (Solaire piscines),
 * sélection + ponts Courrier/Comparer, « Assembler → » (Lot B), pagination 200, tiroir méthode.
 */
import { useInfiniteQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { getSuccessions, SUCCESSIONS_PAGE, type SuccessionItem } from '../../lib/api'
import { fmtInt } from '../../lib/format'
import { TOKENS } from '../../lib/tokens'
import { useApp } from '../../store/useApp'
import { ListPaginationFooter } from '../ListPagination'
import { Loading } from '../Loading'
import { ErrorState } from '../States'
import { Siren } from '../shared/Siren'
import { Tip } from '../Tip'
import { CommuneScope } from './ModulePanel'

const fmtM2 = (v: number | null | undefined) => (v == null ? '—' : `${fmtInt(v)} m²`)

// Filtre « résiduel minimum » (m² SDP) — paliers fixes (un select tient dans les 320 px ; le tri
// serveur reste résiduel décroissant, le seuil ne fait qu'écrémer la queue).
const SDP_MIN = [
  { v: 0, label: 'peu importe' },
  { v: 100, label: '≥ 100 m²' },
  { v: 200, label: '≥ 200 m²' },
  { v: 500, label: '≥ 500 m²' },
  { v: 1000, label: '≥ 1 000 m²' },
]

// Motif RÉEL du signal, par parcelle (la seule donnée datée est le calcul — servie au bandeau).
function Motif({ it }: { it: SuccessionItem }) {
  if (it.sci_dormante) return <span className="text-txt-dim">SCI dormante</span>
  if (it.dirigeant_age != null) return <span className="text-txt-dim">dirigeant {it.dirigeant_age} ans</span>
  return null
}

export function Successions() {
  const select = useApp((s) => s.select)
  const setCourrierPrefillIdus = useApp((s) => s.setCourrierPrefillIdus)
  const setParcelPrefill = useApp((s) => s.setParcelPrefill)
  const setModule = useApp((s) => s.setModule)
  const addToCompare = useApp((s) => s.addToCompare)
  const openCompare = useApp((s) => s.openCompare)
  const pushOutilRetour = useApp((s) => s.pushOutilRetour)
  const RETOUR_SUCCESSIONS = { module: 'successions', label: 'Successions' } as const

  const [commune, setCommune] = useState<string | null>(null)   // Toute l'île par défaut
  const [sdpMin, setSdpMin] = useState(0)
  const [sel, setSel] = useState<Set<string>>(new Set())

  const q = useInfiniteQuery({
    queryKey: ['successions', commune, sdpMin],
    queryFn: ({ pageParam }) => getSuccessions(commune, sdpMin, pageParam),
    initialPageParam: 0,
    getNextPageParam: (last, pages) => { const n = pages.reduce((s, p) => s + p.items.length, 0); return n < last.total ? n : undefined },
  })
  const items = q.data?.pages.flatMap((p) => p.items) ?? []
  const meta = q.data?.pages[0]
  const total = meta?.total ?? 0

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      {/* bandeau client — ce que le signal EST (et n'est pas), toujours visible (doctrine A0) */}
      <div className="rounded-lg border px-3 py-2 text-[10.5px] leading-relaxed text-txt-mut"
        style={{ borderColor: `${TOKENS.mint}4d`, background: `${TOKENS.mint}0f` }}>
        Les parcelles à potentiel dont le propriétaire <b className="text-txt">approche une succession</b> —
        dirigeant âgé (≥ 70 ans) ou SCI dormante : un <b className="text-txt">radar à 3-7 ans</b>, pas une
        succession ouverte.
        <Tip tip="Personnes morales à SIREN confirmé dont le dirigeant le plus âgé a ≥ 70 ans, ou SCI créées il y a ≥ 20 ans sans mise à jour RNE depuis ≥ 5 ans (registre RNE INPI). Aucun acte, aucun décès constaté — un signal d'état, pas un événement.">
          <span className="ml-1 cursor-help rounded-full border border-line-2 px-1 text-[8px] text-txt-dim">i</span>
        </Tip>
      </div>

      {/* entrée : périmètre EXPLICITE (Toute l'île par défaut) + filtre résiduel minimum */}
      <CommuneScope commune={commune} onChange={(c) => { setCommune(c); setSel(new Set()) }} />
      <label className="flex items-center gap-2 text-[11px] text-txt-mut">
        Résiduel minimum
        <select data-successions-sdp-min value={sdpMin}
          onChange={(e) => { setSdpMin(Number(e.target.value)); setSel(new Set()) }}
          className="rounded border border-line-2 bg-surface-3 px-1.5 py-0.5 text-txt focus:border-mint focus:outline-none">
          {SDP_MIN.map((o) => <option key={o.v} value={o.v}>{o.label}</option>)}
        </select>
        <span className="text-[10px] text-txt-dim">m² SDP</span>
      </label>

      {q.isLoading && <Loading label="Parcelles…" />}
      {q.isError && <ErrorState message="Signal momentanément indisponible — réessayez." retry={() => q.refetch()} />}
      {meta && total === 0 && (
        // ÉTAT VIDE HONNÊTE — jamais trois zéros : le périmètre, le signal et son millésime sont dits.
        <p data-successions-vide className="rounded-lg bg-surface-2 px-3 py-2 text-[11px] leading-snug text-txt-mut">
          Aucune parcelle au signal de succession probable
          {commune ? <> à <b className="text-txt">{commune}</b></> : ' sur l’île'}
          {sdpMin ? ` (résiduel ≥ ${fmtInt(sdpMin)} m²)` : ''}{meta.maj ? ` au ${meta.maj}` : ''}.
        </p>
      )}
      {meta && total > 0 && (
        <>
          {/* bandeau de tête : N parcelles · signal [source] au [millésime] */}
          <div data-successions-bandeau className="rounded-lg bg-surface-2 px-3 py-2 text-[10.5px] leading-snug text-txt-mut">
            <b data-successions-total className="tnum text-txt">{fmtInt(total)}</b> parcelle{total > 1 ? 's' : ''} ·
            signal <b className="text-txt">RNE INPI</b>{meta.maj ? ` au ${meta.maj}` : ''}
            {commune ? ` — ${commune}` : ' — toute l’île'}
          </div>

          {/* gestes sur la sélection : ponts Courrier (fil de retour) + Comparer (cap 3 côté Comparer) */}
          <div className="flex flex-wrap items-center gap-2">
            <button data-successions-courrier disabled={sel.size === 0}
              onClick={() => { setCourrierPrefillIdus([...sel]); setModule('courriers'); pushOutilRetour(RETOUR_SUCCESSIONS) }}
              className="rounded-lg border border-mint/50 bg-mint/10 px-2.5 py-1 text-[11px] font-medium text-mint transition-colors duration-quick hover:bg-mint/20 disabled:opacity-40">
              ✉ Préparer les courriers ({sel.size}) →
            </button>
            <button data-successions-comparer disabled={sel.size === 0}
              onClick={() => { [...sel].slice(0, 3).forEach(addToCompare); openCompare(); pushOutilRetour(RETOUR_SUCCESSIONS) }}
              className="rounded-lg border border-mint/50 bg-mint/10 px-2.5 py-1 text-[11px] font-medium text-mint transition-colors duration-quick hover:bg-mint/20 disabled:opacity-40">
              Comparer ({Math.min(sel.size, 3)}) →
            </button>
            {sel.size > 3 && <span className="text-[10px] text-txt-dim">Comparer se limite à 3 parcelles.</span>}
          </div>

          {/* cartes empilées (patron Solaire piscines), tri serveur = résiduel SDP décroissant */}
          <div className="flex items-center gap-2 text-[10px] uppercase tracking-wide text-txt-dim">
            <input type="checkbox" aria-label="Tout sélectionner" className="h-3 w-3 accent-mint"
              checked={items.length > 0 && items.every((i) => sel.has(i.idu))}
              onChange={(e) => setSel(e.target.checked ? new Set(items.map((i) => i.idu)) : new Set())} />
            <span>Triées par résiduel SDP décroissant</span>
          </div>
          <div className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto">
            {items.map((it) => (
              <div key={it.idu} data-successions-row
                className="hover-fill cursor-pointer rounded-lg border border-line-2 bg-surface-3 px-2.5 py-1.5"
                title="Ouvrir la fiche de la parcelle" onClick={() => select(it.idu)}>
                <div className="flex items-center gap-2">
                  <input type="checkbox" data-successions-sel className="h-3 w-3 shrink-0 accent-mint"
                    checked={sel.has(it.idu)} onClick={(e) => e.stopPropagation()}
                    onChange={() => setSel((s) => { const n = new Set(s); n.has(it.idu) ? n.delete(it.idu) : n.add(it.idu); return n })} />
                  <span className="font-mono text-[11px] text-txt-hi">{it.idu}</span>
                  <span className="ml-auto tnum text-[11px] text-txt">{fmtM2(it.sdp_residuelle_m2)}</span>
                  <span className="rounded bg-amber-500/15 px-1 text-[8.5px] font-medium text-amber-500" title="SDP résiduelle — Estimé, moteur de la fiche (enveloppe, pas une expertise)">Estimé</span>
                </div>
                <div className="mt-0.5 flex items-center gap-1.5 text-[10.5px]">
                  <span className="shrink-0 text-txt-mut">{it.commune}</span>
                  <span className="text-txt-dim">·</span>
                  <span className="shrink-0 text-txt-dim">{fmtM2(it.surface_m2)}</span>
                  {it.zone && <><span className="text-txt-dim">·</span><span className="shrink-0 text-txt-dim">{it.zone}</span></>}
                </div>
                <div className="mt-0.5 flex items-center gap-1.5 text-[10.5px]">
                  {/* PM nommée par construction (SIREN confirmé exigé) ; le repli particulier reste en ceinture */}
                  <span className="min-w-0 flex-1 truncate">
                    {it.proprio.type === 'personne_morale'
                      ? <span className="text-txt" title={it.proprio.siren ? `SIREN ${it.proprio.siren}` : undefined}>
                          {it.proprio.denomination}{it.proprio.siren ? <> · <Siren value={it.proprio.siren} className="font-mono text-[10px] text-txt-dim" /></> : null}
                        </span>
                      : <span className="italic text-txt-dim">particulier — non nommé</span>}
                  </span>
                  <Motif it={it} />
                  {/* pont Lot B : la parcelle devient le départ de l'Assemblage (voisines proposées) */}
                  <button data-successions-assembler onClick={(e) => { e.stopPropagation(); setParcelPrefill(it.idu); setModule('assemblage'); pushOutilRetour(RETOUR_SUCCESSIONS) }}
                    title="Ouvrir l'Assemblage avec cette parcelle en départ — ses voisines contiguës sont proposées"
                    className="shrink-0 text-[10px] font-medium text-mint hover:underline">Assembler →</button>
                </div>
              </div>
            ))}
          </div>
          <ListPaginationFooter shown={items.length} total={total} step={SUCCESSIONS_PAGE} onMore={() => q.fetchNextPage()}>
            {q.isFetchingNextPage && <span className="text-txt-dim">chargement…</span>}
          </ListPaginationFooter>
        </>
      )}

      {/* tiroir « Détail et méthode » — rédigé d'après A0 : ce que dit le signal, ce qu'il ne dit pas */}
      <details data-successions-methode className="shrink-0 text-xs">
        <summary className="cursor-pointer list-none py-1.5 text-[11.5px] text-txt-dim marker:hidden hover:text-mint">Détail et méthode ▾</summary>
        <div className="flex flex-col gap-1 text-[10.5px] leading-snug text-txt-dim">
          <p><b className="text-txt-mut">Le signal.</b> Le propriétaire est une personne morale à SIREN confirmé (jamais un
            rapprochement par nom) dont le dirigeant le plus âgé a ≥ 70 ans, ou une SCI créée il y a ≥ 20 ans sans mise à
            jour RNE depuis ≥ 5 ans. Source : registre RNE (INPI), fichiers des personnes morales (DGFiP).</p>
          <p><b className="text-txt-mut">Ce qu'il ne dit pas.</b> Ni une succession ouverte, ni un décès, ni une mise en
            vente : un signal d'état à horizon 3-7 ans. Aucune date « depuis » par parcelle — le registre ne publie pas
            d'historique ; le signal est daté du calcul{meta?.maj ? ` (${meta.maj}` : ''}{meta?.rne_sync ? `, RNE lu au ${meta.rne_sync})` : meta?.maj ? ')' : ''}.</p>
          <p><b className="text-txt-mut">Les chiffres.</b> Surface et zonage : Sourcés (cadastre, PLU). SDP résiduelle :
            Estimé — moteur de la fiche (enveloppe : capacité PLU moins bâti existant ; « — » = hors PLU, réellement
            inconnaissable). Le tri suit la SDP résiduelle.</p>
          {meta?.source && <p className="text-[9.5px]">{meta.source}</p>}
        </div>
      </details>
    </div>
  )
}
