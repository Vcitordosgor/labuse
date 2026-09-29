/**
 * Outil « Successions à venir » — OUTILS-MUSCLER-1 Lot A (renommé 1B pt 1). Sert le tag radar
 * patrimonial `parcel_veille_succession` (Score V v1.3) : personne morale à SIREN confirmé dont le
 * dirigeant le plus âgé a ≥ 70 ans, ou SCI dormante (≥ 20 ans, sans mise à jour RNE depuis ≥ 5 ans).
 * DOCTRINE (A0-successions-donnee.md) : une succession PROBABLE (horizon 3-7 ans) — l'écran ne dit
 * JAMAIS « en succession » (aucun acte, aucun décès constaté). Pas de date par parcelle : le signal
 * est daté du calcul (bandeau + « i » de l'en-tête). Aucun badge de score (l'analyse n'a pas été
 * demandée), aucun export, aucun calcul métier au front (/modules/successions sert tout).
 * OUTILS-S2 Lot A (décisions Vic) : le pont « Préparer les courriers », les cases de sélection
 * multiple (qui ne servaient qu'à ce pont) et le tiroir « Détail et méthode » du pied sont RETIRÉS ;
 * la méthode passe intégralement dans le « i » de l'en-tête. Le signal « dirigeant âgé » est en outre
 * restreint côté serveur aux formes civiles/familiales/agricoles (VEILLE_SUCCESSION_FORMES).
 * Patron SOCLE : sélecteur CommuneScope (choix explicite), cartes empilées, pagination 200.
 */
import { useInfiniteQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { getSuccessions, SUCCESSIONS_PAGE, type SuccessionItem } from '../../lib/api'
import { fmtInt } from '../../lib/format'
import { TOKENS } from '../../lib/tokens'
import { useApp } from '../../store/useApp'
import { ListPaginationFooter } from '../ListPagination'
import { Squelette } from '../Loading'
import { ErrorState } from '../States'
import { Siren } from '../shared/Siren'
import { Tip } from '../Tip'
import { CommuneScope } from './ModulePanel'

const fmtM2 = (v: number | null | undefined) => (v == null ? '—' : `${fmtInt(v)} m²`)

// Contenu de la méthode — déplacé du pied vers le « i » de l'en-tête (OUTILS-S2 Lot A). Le texte ne
// disparaît pas, il se replie dans l'infobulle : ce qu'est le signal, ce qu'il n'est pas, les chiffres.
function methodeTip(maj?: string | null, rne?: string | null): string {
  const date = maj ? ` (calculé le ${maj}${rne ? `, RNE INPI lu au ${rne}` : ''})` : ''
  return (
    'LE SIGNAL — le propriétaire est une personne morale à SIREN confirmé (jamais un rapprochement '
    + 'par nom) dont le dirigeant le plus âgé a ≥ 70 ans, ou une SCI créée il y a ≥ 20 ans sans mise à '
    + 'jour RNE depuis ≥ 5 ans. Formes retenues pour l’âge : sociétés civiles, familiales et agricoles '
    + '(SCI, SC, SARL, SNC, GFA, SCEA, EARL, SCM) — une SA, SAS, SEM ou société d’HLM est écartée '
    + '(sa direction se renouvelle, elle ne « succède » pas). Source : registre RNE (INPI), fichiers '
    + 'des personnes morales (DGFiP).\n\n'
    + 'CE QU’IL NE DIT PAS — ni une succession ouverte, ni un décès, ni une mise en vente : un signal '
    + 'd’état à horizon 3-7 ans. Aucune date « depuis » par parcelle (le registre ne publie pas '
    + `d’historique) ; le signal est daté du calcul${date}.\n\n`
    + 'LES CHIFFRES — surface et zonage : Sourcés (cadastre, PLU). SDP résiduelle : Estimé, moteur de '
    + 'la fiche (enveloppe : capacité PLU moins bâti existant ; « — » = hors PLU, réellement '
    + 'inconnaissable). Le tri suit la SDP résiduelle décroissante.'
  )
}

export function Successions() {
  const focusParcelle = useApp((s) => s.focusParcelle)   // RETOURS-15 C8 — clic ligne → zoom + contour + fiche

  const [commune, setCommune] = useState<string | null>(null)   // Toute l'île par défaut

  const q = useInfiniteQuery({
    queryKey: ['successions', commune],
    queryFn: ({ pageParam }) => getSuccessions(commune, 0, pageParam),
    initialPageParam: 0,
    getNextPageParam: (last, pages) => { const n = pages.reduce((s, p) => s + p.items.length, 0); return n < last.total ? n : undefined },
  })
  const items = q.data?.pages.flatMap((p) => p.items) ?? []
  const meta = q.data?.pages[0]
  const total = meta?.total ?? 0

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      {/* bandeau client — ce que le signal EST (et n'est pas), toujours visible (doctrine A0). Le « i »
          porte désormais TOUTE la méthode (le tiroir du pied est retiré, OUTILS-S2 Lot A). */}
      <div className="rounded-lg border px-3 py-2 text-[10.5px] leading-relaxed text-txt-mut"
        style={{ borderColor: `${TOKENS.mint}4d`, background: `${TOKENS.mint}0f` }}>
        Les parcelles à potentiel dont le propriétaire <b className="text-txt">approche une succession</b> —
        dirigeant âgé (≥ 70 ans) ou SCI dormante : un <b className="text-txt">radar à 3-7 ans</b>, pas une
        succession ouverte.
        <Tip garder tip={methodeTip(meta?.maj, meta?.rne_sync)}>
          <span className="ml-1 cursor-help rounded-full border border-line-2 px-1 text-[8px] text-txt-dim">i</span>
        </Tip>
      </div>

      {/* entrée : périmètre EXPLICITE (Toute l'île par défaut). RETOURS-15 C8 — le filtre « Résiduel
          minimum (SDP) » est retiré (le tri serveur reste résiduel décroissant). */}
      <CommuneScope commune={commune} noteFiltre={false} onChange={(c) => setCommune(c)} />

      {q.isLoading && <Squelette lignes={6} />}
      {q.isError && <ErrorState message="Signal momentanément indisponible — réessayez." retry={() => q.refetch()} />}
      {meta && total === 0 && (
        // ÉTAT VIDE HONNÊTE — jamais trois zéros : le périmètre, le signal et son millésime sont dits.
        <p data-successions-vide className="rounded-lg bg-surface-2 px-3 py-2 text-[11px] leading-snug text-txt-mut">
          Aucune parcelle au signal de succession probable
          {commune ? <> à <b className="text-txt">{commune}</b></> : ' sur l’île'}
          {meta.maj ? ` au ${meta.maj}` : ''}.
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

          <div className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto">
            {items.map((it) => (
              <Carte key={it.idu} it={it} onOpen={() => focusParcelle(it.idu, { fiche: true })} />
            ))}
          </div>
          <ListPaginationFooter shown={items.length} total={total} step={SUCCESSIONS_PAGE} onMore={() => q.fetchNextPage()}>
            {q.isFetchingNextPage && <span className="text-txt-dim">chargement…</span>}
          </ListPaginationFooter>
        </>
      )}
    </div>
  )
}

// Carte lisible (OUTILS-S2 Lot A) : IDU · résiduel Estimé — commune · surface · zone — société · SIREN · motif.
// Plus de case de sélection (le pont Courrier est retiré) ; la carte entière ouvre la fiche.
function Carte({ it, onOpen }: { it: SuccessionItem; onOpen: () => void }) {
  return (
    <div data-successions-row
      className="hover-fill cursor-pointer rounded-lg border border-line-2 bg-surface-3 px-2.5 py-1.5"
      onClick={onOpen}>
      <div className="flex items-center gap-2">
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
  )
}

// Motif RÉEL du signal, par parcelle (la seule donnée datée est le calcul — servie au bandeau).
// DONNEES-1 lot 2.3 — le silence de dépôt de comptes BODACC (≥ 3 ans) renforce le motif « sommeil ».
function Motif({ it }: { it: SuccessionItem }) {
  // FRONT-CHIFFRES-2 (F27) — « dépôt muet » servi à plat (seuil back SEUIL_DEPOT_MUET_ANS) ; le front
  // ne recalcule plus l'ancienneté du silence de dépôt.
  const depotMuet = it.depot_comptes?.muet ?? false
  const base = it.sci_dormante ? 'SCI dormante'
    : it.dirigeant_age != null ? `dirigeant ${it.dirigeant_age} ans` : null
  if (!base && !depotMuet) return null
  return (
    <span className="shrink-0 text-txt-dim">
      {base}
      {depotMuet && <>{base ? ' · ' : ''}aucun dépôt de comptes depuis {it.depot_comptes!.depuis_ans} ans</>}
    </span>
  )
}
