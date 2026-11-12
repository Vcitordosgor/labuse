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
import { useApp } from '../../store/useApp'
import { ListPaginationFooter } from '../ListPagination'
import { Squelette } from '../Loading'
import { ErrorState } from '../States'
import { Siren } from '../shared/Siren'
import { Bouton } from '../ui/Bouton'
import { CommuneScope } from './ModulePanel'

const fmtM2 = (v: number | null | undefined) => (v == null ? '—' : `${fmtInt(v)} m²`)

// RETOURS-25 (pt 12) — `methodeTip` (contenu du « i » méthode) retiré avec la section explicative.

export function Successions() {
  const focusParcelle = useApp((s) => s.focusParcelle)   // RETOURS-15 C8 — clic ligne → zoom + contour + fiche
  const select = useApp((s) => s.select)                  // RECETTE-1 F3 — fermer la fiche ouverte par une ligne
  const selectedIdu = useApp((s) => s.selectedIdu)

  const [commune, setCommune] = useState<string | null>(null)   // Toute l'île par défaut
  // RECETTE-1 (F3) — Réinitialiser : revient à « toute l'île » + ferme la fiche éventuellement ouverte.
  const resetAll = () => { setCommune(null); if (selectedIdu) select(null) }

  const q = useInfiniteQuery({
    queryKey: ['successions', commune],
    queryFn: ({ pageParam }) => getSuccessions(commune, 0, pageParam),
    initialPageParam: 0,
    getNextPageParam: (last, pages) => { const n = pages.reduce((s, p) => s + p.items.length, 0); return n < last.total ? n : undefined },
  })
  const items = q.data?.pages.flatMap((p) => p.items) ?? []
  const meta = q.data?.pages[0]
  const total = meta?.total ?? 0
  // OUTILS-P1-1 (pt 1) — parcelles écartées (âge dirigeant ≥ 100 ans, donnée amont invraisemblable) :
  // comptées, jamais écartées en silence ; la date de la donnée RNE est dite au bandeau et à l'état vide.
  const ageEcarte = meta?.n_age_ecarte ?? 0
  const rne = meta?.rne_sync

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      {/* RETOURS-25 (pt 12) — section explicative (« Les parcelles … approche une succession » + « i »
          méthode) retirée. */}

      {/* entrée : périmètre EXPLICITE (Toute l'île par défaut). RETOURS-15 C8 — le filtre « Résiduel
          minimum (SDP) » est retiré (le tri serveur reste résiduel décroissant). */}
      <div className="flex flex-col gap-1">
        <div className="min-w-0 flex-1"><CommuneScope commune={commune} noteFiltre={false} onChange={(c) => setCommune(c)} /></div>
        {/* RECETTE-OUTILS-1 (T5) — « Réinitialiser les filtres » DANS le bloc filtre, visible seulement
            quand le périmètre diffère du défaut (Toute l'île). Plus de « Réinitialiser » en tête. */}
        {commune && (
          /* RETOURS-25 — « Réinitialiser les filtres » en VERT (cohérent avec Blocs). */
          <Bouton niveau="lien" ton="vert" data-successions-reset-filtres onClick={resetAll} className="self-start">
            Réinitialiser les filtres
          </Bouton>
        )}
      </div>

      {q.isLoading && <Squelette lignes={6} />}
      {q.isError && <ErrorState message="Signal momentanément indisponible — réessayez." retry={() => q.refetch()} />}
      {meta && total === 0 && (
        // ÉTAT VIDE HONNÊTE — jamais trois zéros : le périmètre, le signal et son millésime sont dits.
        <p data-successions-vide className="rounded-lg bg-surface-2 px-3 py-2 text-[11px] leading-snug text-txt-mut">
          Aucune parcelle au signal de succession probable
          {commune ? <> à <b className="text-txt">{commune}</b></> : ' sur l’île'}.
          {/* OUTILS-P1-1 (pt 1) — la date de la donnée RNE est affichée. */}
          {rne && <> Donnée RNE au <b className="text-txt">{rne}</b>.</>}
          {ageEcarte > 0 && <> {fmtInt(ageEcarte)} parcelle{ageEcarte > 1 ? 's' : ''} écartée{ageEcarte > 1 ? 's' : ''} : âge du dirigeant ≥ 100 ans (donnée amont à vérifier).</>}
        </p>
      )}
      {meta && total > 0 && (
        <>
          {/* bandeau de tête : N parcelles · signal [source] — périmètre · donnée RNE au [millésime] */}
          <div data-successions-bandeau className="rounded-lg bg-surface-2 px-3 py-2 text-[10.5px] leading-snug text-txt-mut">
            <b data-successions-total className="tnum text-txt">{fmtInt(total)}</b> parcelle{total > 1 ? 's' : ''} ·
            signal <b className="text-txt">RNE INPI</b>{commune ? ` — ${commune}` : ' — toute l’île'}
            {/* OUTILS-P1-1 (pt 1) — date de la donnée RNE rétablie (le nom et l'âge en viennent). */}
            {rne && <> · donnée RNE au <b className="text-txt">{rne}</b></>}
            {/* OUTILS-P1-1 (pt 1) — les âges ≥ 100 ans sont sortis de la liste ET comptés ici. */}
            {ageEcarte > 0 && (
              <div data-successions-age-ecarte className="mt-0.5 text-txt-dim">
                {fmtInt(ageEcarte)} parcelle{ageEcarte > 1 ? 's' : ''} écartée{ageEcarte > 1 ? 's' : ''} : âge du dirigeant ≥ 100 ans (donnée amont à vérifier).
              </div>
            )}
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
      <div className="mt-0.5 flex flex-wrap items-baseline gap-x-1.5 gap-y-0.5 text-[10.5px]">
        {/* PM nommée par construction (SIREN confirmé exigé) ; le repli particulier reste en ceinture */}
        {/* RECETTE-OUTILS-1 (pt 43) — dénomination + SIREN jamais tronqués : repli sur une 2e ligne au besoin */}
        <span className="min-w-0">
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
  // OUTILS-P1-1 (pt 1) — libellé FACTUEL, sans pronostic : « Nom · N ans » quand le dirigeant est nommé
  // (nom ET âge du même millésime RNE), sinon « Dirigeant de N ans » (jamais « dirigeant · » orphelin).
  const base = it.sci_dormante ? 'SCI dormante'
    : it.dirigeant_age != null
      ? (it.dirigeant_nom ? `${it.dirigeant_nom} · ${it.dirigeant_age} ans` : `Dirigeant de ${it.dirigeant_age} ans`)
      : null
  if (!base && !depotMuet) return null
  // RECETTE-OUTILS-2 (R23) — plus de troncature (« aucun dépôt de compt… ») : le texte PEUT PASSER à la
  // ligne (`break-words`, plus de `shrink-0`), et la mention de dépôt descend sur SA ligne (« Nom · âge »,
  // puis « aucun dépôt de comptes » dessous), comme le demande le mandat.
  return (
    <span className="min-w-0 break-words text-txt-dim">
      {base}
      {depotMuet && (
        <span className="block">aucun dépôt de comptes depuis {it.depot_comptes!.depuis_ans} ans</span>
      )}
    </span>
  )
}
