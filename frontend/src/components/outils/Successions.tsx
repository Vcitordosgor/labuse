/**
 * Outil « Successions à venir » — OUTILS-MUSCLER-1 Lot A (renommé 1B pt 1). Sert le tag radar
 * patrimonial `parcel_veille_succession` (Score V v1.3) : personne morale à SIREN confirmé dont le
 * dirigeant le plus âgé a ≥ 70 ans, ou SCI dormante (≥ 20 ans, sans mise à jour RNE depuis ≥ 5 ans).
 * DOCTRINE (A0-successions-donnee.md) : une succession PROBABLE (horizon 3-7 ans) — l'écran ne dit
 * JAMAIS « en succession » (aucun acte, aucun décès constaté). Pas de date par parcelle : le signal
 * est daté du calcul (bandeau + tiroir). Aucun badge de score (l'analyse n'a pas été demandée),
 * aucun export, aucun calcul métier au front (/modules/successions sert tout).
 * Patrons SOCLE : sélecteur CommuneScope (choix explicite), cartes empilées (Solaire piscines),
 * pagination 200, tiroir méthode. La sélection sert le pont Courrier (déplacé en pied, 1B pt 6).
 * OUTILS-MUSCLER-1B : ponts « Assembler → » (pt 2) et « Comparer » (pt 3) retirés de cet écran ;
 * mentions du tri (pt 4) et du filtre (pt 5) masquées, tri et filtre inchangés.
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
// DONNEES-1 lot 2.3 — le silence de dépôt de comptes BODACC (≥ 3 ans) renforce le motif « sommeil ».
function Motif({ it }: { it: SuccessionItem }) {
  const depotMuet = it.depot_comptes != null && it.depot_comptes.depuis_ans != null && it.depot_comptes.depuis_ans >= 3
  const base = it.sci_dormante ? 'SCI dormante'
    : it.dirigeant_age != null ? `dirigeant ${it.dirigeant_age} ans` : null
  if (!base && !depotMuet) return null
  return (
    <span className="text-txt-dim">
      {base}
      {depotMuet && <>{base ? ' · ' : ''}aucun dépôt de comptes depuis {it.depot_comptes!.depuis_ans} ans</>}
    </span>
  )
}

export function Successions() {
  const select = useApp((s) => s.select)
  const setCourrierPrefillIdus = useApp((s) => s.setCourrierPrefillIdus)
  const setModule = useApp((s) => s.setModule)
  const pushOutilRetour = useApp((s) => s.pushOutilRetour)
  const RETOUR_SUCCESSIONS = { module: 'successions', label: 'Successions à venir' } as const

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
        <Tip garder tip="Personnes morales à SIREN confirmé dont le dirigeant le plus âgé a ≥ 70 ans, ou SCI créées il y a ≥ 20 ans sans mise à jour RNE depuis ≥ 5 ans (registre RNE INPI). Aucun acte, aucun décès constaté — un signal d'état, pas un événement.">
          <span className="ml-1 cursor-help rounded-full border border-line-2 px-1 text-[8px] text-txt-dim">i</span>
        </Tip>
      </div>

      {/* entrée : périmètre EXPLICITE (Toute l'île par défaut) + filtre résiduel minimum */}
      <CommuneScope commune={commune} noteFiltre={false} onChange={(c) => { setCommune(c); setSel(new Set()) }} />
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

          {/* case « tout sélectionner » — la sélection sert le pont Courrier déplacé en pied (1B pt 6).
              Le tri serveur reste résiduel SDP décroissant ; seule l'étiquette du tri est retirée (1B pt 4). */}
          <div className="flex items-center gap-2 text-[10px] uppercase tracking-wide text-txt-dim">
            <input type="checkbox" aria-label="Tout sélectionner" className="h-3 w-3 accent-mint"
              checked={items.length > 0 && items.every((i) => sel.has(i.idu))}
              onChange={(e) => setSel(e.target.checked ? new Set(items.map((i) => i.idu)) : new Set())} />
            <span>Tout sélectionner</span>
          </div>
          <div className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto">
            {items.map((it) => (
              <div key={it.idu} data-successions-row
                className="hover-fill cursor-pointer rounded-lg border border-line-2 bg-surface-3 px-2.5 py-1.5"
                onClick={() => select(it.idu)}>{/* RECETTE-1 R28 — infobulle « Ouvrir la fiche » retirée */}
                <div className="flex items-center gap-2">
                  <input type="checkbox" data-successions-sel className="h-3 w-3 shrink-0 accent-mint"
                    checked={sel.has(it.idu)} onClick={(e) => e.stopPropagation()}
                    onChange={() => setSel((s) => { const n = new Set(s); n.has(it.idu) ? n.delete(it.idu) : n.add(it.idu); return n })} />
                  <span className="font-mono text-[11px] text-txt-hi">{it.idu}</span>
                  <span className="ml-auto tnum text-[11px] text-txt">{fmtM2(it.sdp_residuelle_m2)}</span>
                  <span className="rounded bg-amber-500/15 px-1 text-[8.5px] font-medium text-amber-500">Estimé</span>
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
                      ? <span className="text-txt">
                          {it.proprio.denomination}{it.proprio.siren ? <> · <Siren value={it.proprio.siren} className="font-mono text-[10px] text-txt-dim" /></> : null}
                        </span>
                      : <span className="italic text-txt-dim">particulier — non nommé</span>}
                  </span>
                  <Motif it={it} />
                </div>
              </div>
            ))}
          </div>
          <ListPaginationFooter shown={items.length} total={total} step={SUCCESSIONS_PAGE} onMore={() => q.fetchNextPage()}>
            {q.isFetchingNextPage && <span className="text-txt-dim">chargement…</span>}
          </ListPaginationFooter>
        </>
      )}

      {/* pied de panneau : tiroir « Détail et méthode » (gauche) et pont Courrier (droite, même ligne —
          1B pt 6). `items-start` maintient le bouton sur la ligne du résumé quand le tiroir s'ouvre. */}
      <div className="flex shrink-0 items-start justify-between gap-2">
      <details data-successions-methode className="min-w-0 flex-1 text-xs">
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
        <button data-successions-courrier disabled={sel.size === 0}
          onClick={() => { setCourrierPrefillIdus([...sel]); setModule('courriers'); pushOutilRetour(RETOUR_SUCCESSIONS) }}
          className="mt-1.5 shrink-0 rounded-lg border border-mint/50 bg-mint/10 px-2.5 py-1 text-[11px] font-medium text-mint transition-colors duration-quick hover:bg-mint/20">
          ✉ Préparer les courriers ({sel.size}) →
        </button>
      </div>
    </div>
  )
}
