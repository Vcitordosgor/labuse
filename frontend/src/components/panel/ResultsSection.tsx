import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import { Fragment, useEffect, useMemo, useState } from 'react'
import { getAnalyse, getAnalyseStats, getCommunes, getFiltre, getParcelsGeojson, getResults, type BandeGroupe, type QualiteKey, type SignalNiveauKey, type SortKey } from '../../lib/api'
import { hasScopeFilters, matchAll, type ParcelProps } from '../../lib/filters'
import { roughCentroid } from '../../lib/geo'
import { fmtInt as fmt } from '../../lib/format'
import { ALL_TIER_META, BANDE_META, bandeMeta, etatBienMeta, signalMeta, type Bande, verdictMeta } from '../../lib/status'
import { raisonDominante } from '../../lib/raison'
import { CLIENT } from '../../lib/strings'
import { Tip } from '../Tip'
import { EmptyState } from '../States'
import { useApp, type Filters } from '../../store/useApp'
import { usePagination, ListPaginationFooter } from '../ListPagination'


// M5.1 : le badge « V nn » a disparu de la liste (le dossier propriétaire reste dans la
// fiche) ; les badges secondaires conservés : même proprio ×N, événement daté, veille
// succession, propriétaire spécial.
const OWNER_BADGE: Record<string, { label: string; title: string }> = {
  public: { label: 'PUBLIC', title: 'Foncier public — démarche dédiée' },
  bailleur: { label: 'BAILLEUR', title: 'Bailleur social — démarche dédiée' },
  copro: { label: 'COPRO', title: 'Copropriété — acquisition complexe (hors classement foncier)' },
}

// B2 (M12) : le mini-anneau de complétude (le « 92 » des cartes) a QUITTÉ la liste — il était
// présent sur toutes les cartes, sans valeur discriminante. Il ne vit plus que sur la fiche
// parcelle ouverte (Fiche.tsx). La liste garde le seul chiffre qui trie : le ×N.


function ResultCard({ p, communeLabel, factual = false }: { p: ParcelProps & { commune?: string }; communeLabel: string; factual?: boolean }) {
  const { selectedIdu, select } = useApp()
  // M5.1 : le VERDICT v2 pilote la carte de résultat — chip tier EN PREMIER (couleur
  // verdictMeta), rang + ×N ; l'étage 0 du run servi prime.
  const meta = verdictMeta(p.status, p.tier_v2, p.etage0)
  const on = selectedIdu === p.idu
  // M55-G point 8 — MODE FACTUEL : carte NEUTRE (référence, adresse, surface, commune),
  // sans badge de tier, sans ×N, sans liseré de couleur d'opinion. La FICHE ouverte au clic
  // reste complète (verdict inclus) — rien n'est caché, rien n'est imposé.
  if (factual) {
    return (
      // RECETTE-1 R32 — survol vert opaque (hover-fill) sur les lignes du listing, comme le reste de l'app.
      <button onClick={() => select(p.idu)}
        className={`hover-fill relative flex w-full shrink-0 items-center overflow-hidden rounded-[10px] border bg-surface-3 py-2.5 px-4 text-left ${
          on ? 'border-mint' : 'border-line-2'}`}>
        <div className="min-w-0 flex-1">
          <span className="shrink-0 whitespace-nowrap font-mono text-[11.5px] font-medium tracking-tight text-txt-hi">{p.idu}</span>
          <div data-card-adresse className={`truncate text-[10.5px] text-txt-dim ${p.adresse ? '' : 'opacity-60'}`}>
            {p.adresse ?? 'Adresse non disponible'}
          </div>
          <div className="truncate text-[11px] text-txt-mut tnum">{p.surface_m2 ? `${fmt(p.surface_m2)} m²` : '—'} · {p.commune ?? communeLabel}</div>
        </div>
      </button>
    )
  }
  return (
    <button
      onClick={() => select(p.idu)}
      className={`hover-fill relative flex w-full shrink-0 items-center overflow-hidden rounded-[10px] border bg-surface-3 py-2.5 pl-4 pr-3 text-left ${
        on ? 'border-mint' : 'border-line-2'}`}
    >
      <span className="absolute left-0 top-0 h-full w-[3px]" style={{ background: meta.color }} />
      <div className="min-w-0 flex-1">
        <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
          <span className="shrink-0 whitespace-nowrap font-mono text-[11.5px] font-medium tracking-tight text-txt-hi">{p.idu}</span>
          {/* M55-I point 5 (décision Vic) : le RANG quitte le badge (« Brûlante · 59 » →
              « Priorité ») — les ex æquo massifs du v8 (15 valeurs distinctes dans le
              top 500) ne portent pas cette précision, et la liste est déjà ordonnée. Restent
              le tier + le ×N (colonne droite, son tooltip). Le rang COMPLET avec dénominateur
              (rang N / total) reste en fiche parcelle et dans les exports (inchangés). */}
          <Tip tip={`${meta.long}${p.fraction ? ` · ${p.fraction} de vente sous 1 an` : ''}${p.etage0 ? ' — exclusion dure (écartée d’office du classement)' : ''}`}
            className="shrink-0">
            <span data-tier-chip className="rounded-full px-1.5 py-0.5 text-[9px] font-semibold"
              style={{ background: `${meta.color}1f`, color: meta.color }}>
              {meta.label}
            </span>
          </Tip>
          {/* M135 P3 — LA RAISON DOMINANTE (reason code n°1, chip court). Un seul badge par carte.
              Liste île : `raison` servie (Python) ; carte commune (geojson) : dérivée de top5 au front. */}
          {(() => { const raison = p.raison ?? raisonDominante(p.top5 as Parameters<typeof raisonDominante>[0]); return raison && (
            <Tip tip={`Raison principale de ce classement — ${raison}. Le détail (2-3 raisons) est en fiche.`} className="shrink-0">
              <span data-raison className="rounded-full border border-mint/40 bg-mint/10 px-1.5 py-0.5 text-[9px] font-medium text-mint">
                {raison}
              </span>
            </Tip>
          ) })()}
          {/* M131 P3 — badge d'état du bien (affichage pur du fait M125/M129-D) */}
          {etatBienMeta(p.etat_bien) && (
            <Tip tip={etatBienMeta(p.etat_bien)!.label} className="shrink-0">
              <span data-etat-bien={p.etat_bien} className="rounded-full border px-1.5 py-0.5 text-[9px] font-medium"
                style={{ borderColor: `${etatBienMeta(p.etat_bien)!.color}55`, color: etatBienMeta(p.etat_bien)!.color }}>
                {etatBienMeta(p.etat_bien)!.short}
              </span>
            </Tip>
          )}
          {p.evenement === 'rouge' && (
            <Tip tip={`Événement — procédure BODACC ouverte${p.evenement_date ? ` (${new Date(p.evenement_date).toLocaleDateString('fr-FR')})` : ''}`}
              className="shrink-0">
              <span className="rounded-full bg-[#3a1614] px-1.5 py-0.5 text-[9px] font-medium text-st-ecartee">
                ● ÉVÉNEMENT{p.evenement_date ? ` · ${new Date(p.evenement_date).toLocaleDateString('fr-FR')}` : ''}
              </span>
            </Tip>
          )}
          {(p.cluster ?? 0) > 1 && (
            <Tip tip={`Même propriétaire que ${(p.cluster ?? 0) - 1} autre(s) opportunité(s)${p.proprio ? ` — ${p.proprio}` : ''} : 1 dossier, pas ${p.cluster} lignes`}
              className="shrink-0">
              <span className="rounded-full bg-[#1a2340] px-1.5 py-0.5 text-[9px] font-medium text-[#8FB4F0]">
                même proprio ×{p.cluster}
              </span>
            </Tip>
          )}
          {p.veille && (
            <Tip tip="Veille succession — radar patrimonial (signal d'état, pas un événement daté)" className="shrink-0">
              <span className="rounded-full bg-[#2a2138] px-1.5 py-0.5 text-[9px] font-medium text-[#B497F0]">
                veille succession
              </span>
            </Tip>
          )}
          {p.owner_type && OWNER_BADGE[p.owner_type] && (
            <Tip tip={OWNER_BADGE[p.owner_type].title} className="shrink-0">
              <span className="rounded-full border border-line-2 px-1.5 py-0.5 text-[8.5px] font-medium text-txt-dim">
                {OWNER_BADGE[p.owner_type].label}
              </span>
            </Tip>
          )}
        </div>
        {/* M6 2a (§1.8) : adresse postale BAN sur la carte de résultat — jamais un vide */}
        <div data-card-adresse className={`truncate text-[10.5px] text-txt-dim ${p.adresse ? '' : 'opacity-60'}`}>
          {p.adresse ?? 'Adresse non disponible'}
        </div>
        <div className="truncate text-[11px] text-txt-mut tnum">{p.surface_m2 ? `${fmt(p.surface_m2)} m²` : '—'} · {p.commune ?? communeLabel}</div>
      </div>
      <div className="ml-2 flex shrink-0 flex-col items-end">
        {/* M135 P2 — la PROBABILITÉ en FRACTION humaine (« 1/5 sous 1 an »), jamais un « ×N ».
            Servie depuis la proba calibrée (p) ; « — / peu probable » sous 1/50. Calcul inchangé. */}
        <Tip tip={p.fraction ? CLIENT.mult.fractionBadge(p.fraction) : CLIENT.mult.absent}>
          <span data-fraction className="font-display text-[15px] font-bold leading-none tnum" style={{ color: meta.color }}>
            {p.fraction ?? '—'}
          </span>
        </Tip>
        <span className="mt-0.5 text-[8.5px] leading-none text-txt-dim">{p.fraction ? CLIENT.mult.unite : CLIENT.mult.faible}</span>
      </div>
    </button>
  )
}

// E2 (M12) : le composant TierChips (chips de verdict du bandeau) a été RETIRÉ — doublon avec
// le bloc « Verdict · Scoring v2 (multi) » du panneau « + Filtre » (point d'entrée unique).

// C4 + P2 (revue Vic n°3) : LABUSE MONTRE son analyse (avis argumenté), il ne décide pas à
// votre place. L'ancien « pourquoi ? » (entonnoir par motif) est retiré ; les motifs de
// déclassement restent accessibles par les chips « Potentiel épuisé · motif » et chaque écartée
// garde son motif en fiche.
// M55-K point 1 : la ligne de synthèse « N parcelles analysées → M opportunités détectées ·
// filtres appliqués » (ex-LigneClassement) est RETIRÉE — entièrement dérivable de la ventilation
// (total = somme des paliers), et la mention du filtrage y faisait doublon avec « (filtres
// actifs) ». Le concept « opportunités » (brûlantes + chaudes) reste vivant : tooltip de la
// ventilation (uni.data.opportunites) + champ API /filtre + outil blocB (autre endpoint).

const RESULTS_PAGE = 200  // E3 : taille de page de la pagination île (offset serveur) — RETOURS-10 T3 : 200 partout

//: tris (M5.1 lot 1.3) — rang P par défaut ; le tri par V a disparu du sélecteur.
// B3 (M12) : libellés client centralisés (CLIENT.tri) ; « rang P » → « classement ».
// M13-F3 (QA-57) : « commune » RETIRÉ (demande Vic) ; ×N → « mutation ×N » ; chaque
// bouton porte son propre title explicatif.
// M55-G suite point 8 : `dir` = le SENS du tri, affiché sur la pill ACTIVE.
// M55-H point 4 : le tri Surface a ses DEUX sens — re-clic sur la pill active = inversion
// (« Surface ↓ » ↔ « Surface ↑ », clé serveur surface / surface_asc), dans les deux modes.
// M55-I point 3 (arbitrage Vic) : le tri « Mutation » (clé 'mult') est RETIRÉ (doublon prouvé
// du classement). Restent « Probabilité de vente » (rang) et « Surface » (inversible). La clé
// serveur 'mult' reste valide côté API mais n'est plus atteignable depuis la barre.
const SORTS: { key: SortKey; label: string; tip: string; dir?: string }[] = [
  { key: 'rang', label: CLIENT.tri.rang, tip: CLIENT.tri.rangTip },
  { key: 'surface', label: CLIENT.tri.surface, tip: CLIENT.tri.surfaceTip, dir: '↓' },
]
// RECETTE-5 (V2, décision Vic) — le listing FACTUEL : « Adresse » par défaut (adressées d'abord,
// puis SURFACE décroissante) — que du fait cadastral. Le tri « Potentiel » (SDP résiduelle = calcul
// LABUSE) est RETIRÉ de la vue factuelle : une vue qui s'annonce « sans analyse » ne sert pas une
// opinion de LABUSE. Le potentiel reste dans l'analyse, nulle part ailleurs. Surface reste en second
// (inversible). [RECETTE-3 (T3) : l'ancien défaut était « Potentiel ».]
// RECETTE-6 (A1, décision Vic) — le BOUTON « Adresse » est RETIRÉ de la barre : le tri « adressées
// d'abord » reste le DÉFAUT (en arrière-plan, cf. le `useState`/`useEffect` ci-dessous qui garde
// 'adresse'), il ne s'affiche simplement plus comme bouton. Seule « Surface » reste cliquable.
const FACTUAL_SORTS: { key: SortKey; label: string; tip: string; dir?: string }[] = [
  { key: 'surface', label: CLIENT.tri.surface, tip: CLIENT.tri.surfaceTip, dir: '↓' },
]

// M55-H point 5 (décision Vic) — ordre des GROUPES de la liste d'analyse (identique au CASE
// SQL du serveur) : 4 tiers d'opportunité, puis potentiel épuisé (declasse_*), puis écartées.
const GROUPE_ORDER = (p: Pick<ParcelProps, 'etage0' | 'tier_v2'>): number => {
  if (p.etage0) return 6
  const t = p.tier_v2 ?? ''
  // PALIERS-1 — les DEUX vocabulaires : servi (brulante/chaude/…) + q_v14 (priorite/a_suivre/sans_signal)
  if (t === 'brulante' || t === 'priorite') return 0
  if (t === 'chaude' || t === 'a_suivre') return 1
  if (t === 'reserve_fonciere') return 2
  if (t === 'a_creuser' || t === 'sans_signal') return 3
  if (t.startsWith('declasse')) return 4
  return 5
}

// M69 A — comparateur de la liste EXTRAIT en fonction pure (testable). Le GROUPEMENT par tier
// n'est appliqué QUE si `groupes` (tri « Probabilité de vente »/rang en mode analyse) ; les tris
// de COLONNE (Surface ↓/↑) s'appliquent GLOBALEMENT → ordre monotone garanti sur tout le jeu.
// Même sémantique que le serveur (_q_v2_list) : un seul comportement de tri, client et serveur.
export type SortableRow = Pick<ParcelProps, 'etage0' | 'tier_v2' | 'mult_v2' | 'surface_m2' | 'rang_v2'>
  & { commune?: string; adresse?: string | null; sdp_residuelle_m2?: number | null }
export function sortRows<T extends SortableRow>(rows: T[], sort: SortKey, groupes: boolean): T[] {
  return rows.slice().sort((a, b) => {
    if (groupes) {
      const ga = GROUPE_ORDER(a)
      const gb = GROUPE_ORDER(b)
      if (ga !== gb) return ga - gb
    }
    // RECETTE-5 (V2) — « Adresse » (défaut factuel) : adressées d'abord, puis SURFACE décroissante.
    // Que du fait cadastral — aucune SDP résiduelle (calcul LABUSE) ici. Le geojson porte adresse+surface.
    if (sort === 'adresse') {
      const aa = a.adresse ? 1 : 0, ba = b.adresse ? 1 : 0
      if (aa !== ba) return ba - aa
      return (b.surface_m2 ?? -1) - (a.surface_m2 ?? -1)
    }
    // RECETTE-3 (T3) — « Potentiel » (analyse seulement désormais) : adressées d'abord, puis SDP
    // résiduelle, puis surface. Même sémantique que le serveur (_Q_V2_ORDERS['potentiel']).
    if (sort === 'potentiel') {
      const aa = a.adresse ? 1 : 0, ba = b.adresse ? 1 : 0
      if (aa !== ba) return ba - aa
      const as = a.sdp_residuelle_m2 ?? 0, bs = b.sdp_residuelle_m2 ?? 0
      if (as !== bs) return bs - as
      return (b.surface_m2 ?? -1) - (a.surface_m2 ?? -1)
    }
    if (sort === 'mult') return (b.mult_v2 ?? -1) - (a.mult_v2 ?? -1)
    if (sort === 'surface') return (b.surface_m2 ?? -1) - (a.surface_m2 ?? -1)
    if (sort === 'surface_asc') return (a.surface_m2 ?? Infinity) - (b.surface_m2 ?? Infinity)
    if (sort === 'commune') return String(a.commune ?? '').localeCompare(String(b.commune ?? ''))
    const ra = a.rang_v2 ?? Infinity
    const rb = b.rang_v2 ?? Infinity
    if (ra !== rb) return ra - rb
    return (b.mult_v2 ?? -1) - (a.mult_v2 ?? -1)
  })
}


// RECETTE-3 (T4, décision Vic) — les QUATRE SEGMENTS du listing d'analyse, dans CET ordre. Chaque
// parcelle garde son palier (chips ResultCard) ; la segmentation est une SECONDE lecture, par nature
// du bien. Un pro qui a obtenu un permis PRIME sur l'état du bien (segment 1).
// RECETTE-10 T7 — le segment est une SECONDE LECTURE (nature du bien), calculée EN DIRECT sur Sitadel
// (permis OBTENU dans les 36 mois, hors du run de score) ; le palier vient du run et prédit la VENTE.
// Les deux sont ORTHOGONAUX : un permis pro signale un AMÉNAGEMENT en cours, pas une vente imminente —
// c'est même souvent l'inverse (le terrain se construit, il ne revient pas au marché). Empiriquement,
// la majorité des parcelles « permis pro » sont « Sans signal » de vente : ce n'est PAS une
// contradiction. Le libellé et l'info-bulle disent donc EXACTEMENT ce que le segment regroupe, et ne
// prétendent plus qu'il s'agit du « signal le plus fort du modèle » (le modèle prédit la vente).
// ANALYSE-1 — la SEGMENTATION par nature du bien (permis pro / terrain nu / bâti densifier / reste) a
// QUITTÉ l'écran Analyse : le nouveau moteur rend UNE liste unique classée par bande de Score puis
// Signal de mutation. `SegKey`/`segmentOf`/`SegmentList` restent (exportés, tests + usages tiers) ;
// la constante SEGMENTS et le composant AnalyseSegment (rendu de segment) sont retirés (morts ici).
type SegKey = 'permis_pro' | 'terrain_nu' | 'bati_densifier' | 'reste'
export function segmentOf(p: Pick<ParcelProps, 'permis_pro' | 'etat_bien'>): SegKey {
  if (p.permis_pro) return 'permis_pro'
  if (p.etat_bien === 'nu') return 'terrain_nu'
  if (p.etat_bien === 'bati_encore') return 'bati_densifier'
  return 'reste'
}

// RECETTE-11 C1 — LA liste d'UN segment de l'Analyse, paginée par la règle PARTAGÉE (200) sur SES
// PROPRES lignes (jamais la fenêtre globale). Sous 200 : tout s'affiche, AUCUN « charger plus » ;
// au-delà : 200 puis « Voir 200 de plus » (pied partagé). En mode île, si le serveur a encore des
// pages non chargées (segRows < total serveur ET fenêtre client épuisée), on offre de charger plus.
// RECETTE-11 C1 — LA règle : un segment n'offre « charger plus » (serveur) QUE si sa fenêtre client
// est épuisée ET que le serveur a d'autres lignes du segment non chargées. Corollaire testé : un
// segment de MOINS de 200 lignes entièrement chargé (segLen === serverTotal) n'offre JAMAIS de
// « charger plus » — et sous 200, la fenêtre client (usePagination) montre tout sans « Voir de plus ».
export function segmentOffreChargerPlus(
  shownClient: number, segLen: number, serverTotal: number, serverHasMore: boolean): boolean {
  return shownClient >= segLen && segLen < serverTotal && serverHasMore
}

export function SegmentList({ segKey, rows, serverTotal, commune, serverHasMore, serverLoading, onServerMore, serverPaged = false }: {
  segKey: SegKey; rows: (ParcelProps & { commune?: string })[]; serverTotal: number; commune: string
  serverHasMore: boolean; serverLoading: boolean; onServerMore: () => void
  // RECETTE-12 B2 — `serverPaged` : les lignes sont DÉJÀ paginées par le serveur (param `segment`,
  // 200/page) → on affiche TOUT ce qui est chargé (pas de re-fenêtrage client qui retomberait à 200)
  // et un seul pied « N sur total · Voir 200 de plus ». Sans ce flag (mode commune : liste complète
  // en mémoire), on garde le fenêtrage client 200 d'origine (aucune régression des tests C1).
  serverPaged?: boolean
}) {
  const pg = usePagination(rows.length)
  if (rows.length === 0) {
    return (
      <div className="mt-2 flex flex-col gap-2">
        <p className="px-3 py-1.5 text-[10.5px] text-txt-dim">
          {serverTotal > 0 ? 'Chargez plus de résultats pour voir ces parcelles →' : 'Aucune parcelle dans ce segment.'}
        </p>
        {serverTotal > 0 && serverHasMore && (
          <button data-segment-more={segKey} onClick={onServerMore} disabled={serverLoading}
            className="px-3 py-1.5 text-left text-[10.5px] text-txt-dim hover:text-mint disabled:opacity-60">
            0 sur {fmt(serverTotal)} affichées — charger plus de résultats →
          </button>
        )}
      </div>
    )
  }
  if (serverPaged) {
    // pagination SERVEUR pure : tout le chargé s'affiche ; compteur exact « N sur total » toujours
    // visible ; « Voir 200 de plus » seulement si le serveur a d'autres lignes de CE segment.
    return (
      <div className="mt-2 flex flex-col gap-2">
        {rows.map((p) => <ResultCard key={p.idu} p={p} communeLabel={commune} />)}
        <div data-pagination className="flex flex-wrap items-center gap-3 border-t border-line pt-2 text-[11px] text-txt-mut">
          <span data-pagination-count><b className="text-txt">{fmt(rows.length)} sur {fmt(serverTotal)}</b> affichées</span>
          {serverHasMore && (
            <button data-segment-more={segKey} onClick={onServerMore} disabled={serverLoading}
              className="text-mint hover:underline disabled:opacity-60">
              {serverLoading ? 'Chargement…' : `Voir ${fmt(Math.min(RESULTS_PAGE, serverTotal - rows.length))} de plus`}
            </button>
          )}
        </div>
      </div>
    )
  }
  const shown = rows.slice(0, pg.shown)
  return (
    <div className="mt-2 flex flex-col gap-2">
      {shown.map((p) => <ResultCard key={p.idu} p={p} communeLabel={commune} />)}
      {/* règle 200 partagée sur les lignes DU segment (jamais de « charger plus » sous 200) */}
      {pg.hasMore && <ListPaginationFooter shown={pg.shown} total={rows.length} onMore={pg.more} />}
      {/* mode île : la fenêtre client est épuisée mais le serveur a d'autres pages du segment */}
      {segmentOffreChargerPlus(pg.shown, rows.length, serverTotal, serverHasMore) && (
        <button data-segment-more={segKey} onClick={onServerMore} disabled={serverLoading}
          className="px-3 py-1.5 text-left text-[10.5px] text-txt-dim hover:text-mint disabled:opacity-60">
          {fmt(rows.length)} sur {fmt(serverTotal)} affichées — charger plus de résultats →
        </button>
      )}
    </div>
  )
}

// ══════════════════ ANALYSE-1 — LE NOUVEAU MOTEUR À L'ÉCRAN ══════════════════
// Filtre PROPRE à l'Analyse (mandat §1.4) : le Signal de mutation (Fort / Moyen / Faible). « Tous »
// toujours EN DERNIER (règle DA). Le filtre narrreowit la liste ; il ne re-classe rien.
const SIGNALS_FILTRE: { key: SignalNiveauKey | 'tous'; label: string }[] = [
  { key: 'fort', label: 'Fort' }, { key: 'moyen', label: 'Moyen' },
  { key: 'faible', label: 'Faible' }, { key: 'tous', label: 'Tous' },
]
// ANALYSE-2 — le filtre CLASSEMENT : les 4 bandes de qualité (libellés gravés) + « Tous » en DERNIER.
// « Non retenue » et « Analyse incomplète » ne sont PAS des choix de classement (catégories à part) —
// elles restent accessibles par leurs groupes de fin de liste.
const CLASSEMENT_FILTRE: { key: QualiteKey | 'tous'; label: string }[] = [
  { key: 'A', label: BANDE_META.A.label }, { key: 'B', label: BANDE_META.B.label },
  { key: 'C', label: BANDE_META.C.label }, { key: 'D', label: BANDE_META.D.label },
  { key: 'tous', label: 'Tous' },
]
//: les 5 catégories de l'ENCART (4 bandes + Non retenue) — « Analyse incomplète » (NC) est à part.
const BANDE_ENCART: Bande[] = ['A', 'B', 'C', 'D', '0']

// Les 2-3 contributions FR les plus fortes, telles que le moteur les produit — ce qui MONTE (▲) et ce
// qui BAISSE (▼) le Score. Aucun chiffre de score : juste la phrase du moteur.
function ContributionsRow({ contributions }: { contributions?: ParcelProps['contributions'] }) {
  const list = (contributions ?? []).slice(0, 3)
  if (!list.length) return null
  return (
    <div data-contributions className="mt-1 flex flex-col gap-0.5">
      {list.map((c, i) => {
        const up = c.sens === 'hausse'
        return (
          <span key={i} className="inline-flex items-start gap-1 text-[10px] leading-snug" style={{ color: up ? '#5CE6A1' : '#C08A6E' }}>
            <span aria-hidden className="mt-[1px] shrink-0 text-[8px] font-bold">{up ? '▲' : '▼'}</span>
            <span className="text-txt-dim">{c.libelle}</span>
          </span>
        )
      })}
    </div>
  )
}

// LA LIGNE d'analyse : référence + commune · BANDE (mot + couleur, dominante) · badge Signal
// (SECONDAIRE) · surface · zone · 2-3 contributions. « Analyse incomplète » (NC) montre sa CAUSE et
// n'affiche ni signal ni contributions (elle n'est pas une parcelle « mauvaise », juste incomplète).
function AnalyseCard({ p, communeLabel }: { p: ParcelProps & { commune?: string }; communeLabel: string }) {
  const { selectedIdu, select } = useApp()
  const bm = bandeMeta(p.bande)
  const sm = signalMeta(p.signal_niveau)
  const on = selectedIdu === p.idu
  const nc = p.bande === 'NC'
  return (
    <button onClick={() => select(p.idu)}
      className={`hover-fill relative flex w-full shrink-0 items-start overflow-hidden rounded-[10px] border bg-surface-3 py-2.5 pl-4 pr-3 text-left ${on ? 'border-mint' : 'border-line-2'}`}>
      {bm && <span className="absolute left-0 top-0 h-full w-[3px]" style={{ background: bm.color }} />}
      <div className="min-w-0 flex-1">
        <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
          <span className="shrink-0 whitespace-nowrap font-mono text-[11.5px] font-medium tracking-tight text-txt-hi">{p.idu}</span>
          {bm && (
            <Tip tip={bm.long} className="shrink-0">
              <span data-bande={p.bande} className="rounded-full px-2 py-0.5 text-[9.5px] font-bold" style={{ background: `${bm.color}26`, color: bm.color }}>{bm.label}</span>
            </Tip>
          )}
          {sm && !nc && (
            <Tip tip={sm.long} className="shrink-0">
              <span data-signal={p.signal_niveau} className="rounded-full border px-1.5 py-0.5 text-[8.5px] font-medium" style={{ borderColor: `${sm.color}66`, color: sm.color }}>{sm.label}</span>
            </Tip>
          )}
          {p.zone_fam && (
            <span data-zone className="shrink-0 rounded-full border border-line-2 px-1.5 py-0.5 text-[8.5px] font-medium text-txt-dim">zone {p.zone_fam}</span>
          )}
        </div>
        <div data-card-adresse className={`truncate text-[10.5px] text-txt-dim ${p.adresse ? '' : 'opacity-60'}`}>{p.adresse ?? 'Adresse non disponible'}</div>
        <div className="truncate text-[11px] text-txt-mut tnum">{p.surface_m2 ? `${fmt(p.surface_m2)} m²` : '—'} · {p.commune ?? communeLabel}</div>
        {nc && p.cause && <div data-cause className="mt-1 text-[10px] leading-snug" style={{ color: BANDE_META.NC.color }}>Analyse incomplète — {p.cause}.</div>}
        {!nc && <ContributionsRow contributions={p.contributions} />}
      </div>
    </button>
  )
}

// UN groupe de fin de liste (« Analyse incomplète » NC, puis « Sans potentiel constructible » 0) :
// repliable, son COMPTE dans l'en-tête, lignes chargées à l'ouverture (jamais masqué — mandat §5).
function AnalyseBandeGroup({ groupe, label, color, total, filters, commune, signal }: {
  groupe: BandeGroupe; label: string; color: string; total: number
  filters: Filters; commune: string; signal?: SignalNiveauKey
}) {
  const [open, setOpen] = useState(false)
  const q = useInfiniteQuery({
    queryKey: ['analyse-groupe', groupe, filters, signal],
    queryFn: ({ pageParam }) => getAnalyse(filters, groupe, { limit: RESULTS_PAGE, offset: pageParam as number, signal }),
    initialPageParam: 0,
    getNextPageParam: (last: unknown[], pages) => (last.length === RESULTS_PAGE ? pages.length * RESULTS_PAGE : undefined),
    enabled: open,
  })
  const rows = useMemo(() => (q.data?.pages ?? []).flat() as unknown as (ParcelProps & { commune?: string })[], [q.data])
  return (
    <div className="shrink-0">
      <button data-bande-groupe={groupe} onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-2 rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-left hover:border-mint/50">
        <span className="flex min-w-0 items-center gap-2">
          <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.5"
            className={`shrink-0 text-txt-dim transition-transform ${open ? 'rotate-90' : ''}`}><path d="m9 18 6-6-6-6" /></svg>
          <span className="inline-flex h-2 w-2 shrink-0 rounded-full" style={{ background: color }} />
          <span className="truncate text-[12px] font-medium text-txt">{label}</span>
        </span>
        <span className="shrink-0 tnum text-[11px] text-txt-dim">{fmt(total)}</span>
      </button>
      {open && (
        <div className="mt-2 flex flex-col gap-2">
          {q.isLoading && rows.length === 0 && <p className="px-3 py-1.5 text-[10.5px] text-txt-dim">Chargement…</p>}
          {rows.map((p) => <AnalyseCard key={p.idu} p={p} communeLabel={commune} />)}
          {(q.hasNextPage ?? false) && (
            <div data-pagination className="flex flex-wrap items-center gap-3 border-t border-line pt-2 text-[11px] text-txt-mut">
              <span><b className="text-txt">{fmt(rows.length)} sur {fmt(total)}</b> affichées</span>
              <button onClick={() => q.fetchNextPage()} disabled={q.isFetchingNextPage} className="text-mint hover:underline disabled:opacity-60">
                {q.isFetchingNextPage ? 'Chargement…' : `Voir ${fmt(Math.min(RESULTS_PAGE, total - rows.length))} de plus`}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// En-tête de bande dans la liste unique de qualité (A → B → C → D) : inséré quand la bande change
// (le serveur ordonne déjà par bande). Une pastille couleur + le mot ; jamais un chiffre de score.
function BandeHeader({ bande }: { bande: Bande }) {
  const bm = BANDE_META[bande]
  return (
    <div data-bande-header={bande} className="mt-1 flex shrink-0 items-center gap-2 px-1 pt-1">
      <span className="inline-flex h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: bm.color }} />
      <span className="text-[11px] font-semibold uppercase tracking-wide" style={{ color: bm.color }}>{bm.label}</span>
    </div>
  )
}

export function ResultsSection() {
  const { filters, query, zone, resetFilters, commune, setCommune } = useApp()
  const ile = commune == null   // mode « Toute l'île » : liste + compteurs servis en SQL
  // M55-G point 8 — décision Vic : sans analyse demandée, l'avis LABUSE ne s'affiche pas.
  // Mode FACTUEL (analyse OFF) : liste neutre, tri Surface seul, aucune ventilation d'opinion.
  const analyse = filters.analyseLabuse
  // Tri par défaut : analyse = RANG P (groupé par tier) ; factuel = ADRESSE (RECETTE-5 V2, décision
  // Vic) — adressées d'abord puis SURFACE décroissante, que du fait cadastral (l'ancien défaut
  // « Potentiel » servait une SDP résiduelle = calcul LABUSE, retirée de la vue factuelle). Surface
  // reste en second (inversible) dans les deux modes.
  const [sort, setSort] = useState<SortKey>(analyse ? 'rang' : 'adresse')
  const sorts = analyse ? SORTS : FACTUAL_SORTS
  useEffect(() => { setSort(analyse ? 'rang' : 'adresse') }, [analyse])
  // M69 A — GROUPEMENT PAR TIER : appliqué UNIQUEMENT pour le tri par défaut « Probabilité de
  // vente » (rang) en mode analyse (M55-H p5). Un tri de COLONNE (Surface) doit produire un ordre
  // GLOBAL monotone → on lève le groupement. Ce booléen pilote client ET serveur (un seul point).
  const groupes = analyse && sort === 'rang'
  // M55-F point 1 — POINT UNIQUE : compteurs (ventilation, total, opportunités) dérivent du
  // MÊME getFiltre(filters) que la Révélation et le compteur vivant (stage 8) — mêmes critères
  // (communes, terrain, signaux, tiers, interrupteur), mêmes nombres, fini les trois récits.
  // Retiré : getStats(scopeOnly) [tiers retirés] et getStats(undefined) [mode commune = aucun
  // filtre → l'origine du « 431 663 → 98 » décorrélé, mesuré 10/08].
  // ANALYSE-1 — `uni` sert désormais le mode FACTUEL (total du périmètre). En analyse, la ventilation
  // et le total viennent de `bandesQ` (getAnalyseStats, ventilation par bande du nouveau moteur).
  const uni = useQuery({
    queryKey: ['results-unifie', commune, filters],
    queryFn: () => getFiltre(filters, 0),
    enabled: !analyse,
  })
  const geo = useQuery({ queryKey: ['geojson', commune], queryFn: getParcelsGeojson, enabled: !ile })
  // E3 (M12) : la liste île n'est plus plafonnée à 500. Pagination par offset (le back la
  // supporte nativement, A2) — pages de 200, « Charger plus » accumule. Tri `rang` = index top-N
  // (quasi-gratuit) ; les autres tris paginent aussi (coût croissant en profondeur, assumé).
  // M55-H point 5 : en mode ANALYSE la liste se groupe par tier côté serveur (groupes=1) —
  // le tri choisi s'applique DANS chaque groupe. Le mode factuel reste plat.
  const serverList = useInfiniteQuery({
    queryKey: ['results', commune, filters, sort, groupes],
    queryFn: ({ pageParam }) => getResults(filters, RESULTS_PAGE, sort, pageParam, groupes),
    initialPageParam: 0,
    getNextPageParam: (last: unknown[], pages) => (last.length === RESULTS_PAGE ? pages.length * RESULTS_PAGE : undefined),
    enabled: ile && !analyse,   // ANALYSE-1 : en analyse, la liste vient de `analyseList` (getAnalyse)
  })
  const serverRows = useMemo(
    () => (serverList.data?.pages ?? []).flat() as unknown as (ParcelProps & { commune?: string })[],
    [serverList.data],
  )

  // ── ANALYSE-1 — le NOUVEAU moteur (Score LABUSE + Signal de mutation), lu sur le run candidat ──
  // Filtre PROPRE à l'Analyse : le Signal de mutation (Fort / Moyen / Faible / Tous). Il narreowit la
  // liste, il ne re-classe rien (la bande vient du moteur telle quelle).
  // ANALYSE-2 — DEUX filtres INDÉPENDANTS et combinables (ET) : le CLASSEMENT (bande de qualité, ou
  // Tous) et le SIGNAL de mutation (ou Tous). « Tous » toujours en DERNIER (règle DA). Ils narrowissent
  // la liste, ils ne re-classent rien (la bande vient du moteur telle quelle).
  const [classementFiltre, setClassementFiltre] = useState<QualiteKey | 'tous'>('tous')
  const [signalFiltre, setSignalFiltre] = useState<SignalNiveauKey | 'tous'>('tous')
  const signalParam = signalFiltre === 'tous' ? undefined : signalFiltre
  // param serveur `bande` : une bande PRÉCISE (A/B/C/D) ou `qualite` (les 4) quand Classement = Tous.
  const bandeParam: BandeGroupe = classementFiltre === 'tous' ? 'qualite' : classementFiltre
  useEffect(() => { if (!analyse) { setSignalFiltre('tous'); setClassementFiltre('tous') } }, [analyse])
  // la LISTE UNIQUE (bandes ordonnées par bande puis Signal côté serveur), servie par /filtre en mode
  // `labuse` — TOUJOURS côté serveur (le geojson commune ne porte pas la bande). Filtrée par les DEUX.
  const analyseList = useInfiniteQuery({
    queryKey: ['analyse-qualite', commune, filters, bandeParam, signalParam],
    queryFn: ({ pageParam }) => getAnalyse(filters, bandeParam, { limit: RESULTS_PAGE, offset: pageParam as number, signal: signalParam }),
    initialPageParam: 0,
    getNextPageParam: (last: unknown[], pages) => (last.length === RESULTS_PAGE ? pages.length * RESULTS_PAGE : undefined),
    enabled: analyse,
  })
  const analyseRows = useMemo(
    () => (analyseList.data?.pages ?? []).flat() as unknown as (ParcelProps & { commune?: string })[],
    [analyseList.data],
  )
  // ventilation par BANDE + croisement bande × Signal du périmètre (récapitulatif) — filtres globaux
  // SANS tier ni bande. Le crosstab donne le compteur FILTRÉ cohérent (« N correspondent à vos filtres »).
  const bandesQ = useQuery({
    queryKey: ['analyse-bandes', commune, filters],
    queryFn: () => getAnalyseStats(filters),
    enabled: analyse,
  })
  const bandes = bandesQ.data?.bandes ?? { A: 0, B: 0, C: 0, D: 0, '0': 0, NC: 0 }
  const xtab = bandesQ.data?.bandes_signal
  // ANALYSE-2 — N parcelles pour le couple (Classement, Signal) courant, dérivé du SEUL crosstab :
  // somme sur les bandes sélectionnées × les signaux sélectionnés. Par construction, somme des 4 bandes
  // = total, et Fort+Moyen+Faible = Tous (le compteur ne peut pas mentir, il vient d'un unique GROUP BY).
  const filtreCount = useMemo(() => {
    if (!xtab) return 0
    const bs: QualiteKey[] = classementFiltre === 'tous' ? ['A', 'B', 'C', 'D'] : [classementFiltre]
    const ss: SignalNiveauKey[] = signalFiltre === 'tous' ? ['fort', 'moyen', 'faible'] : [signalFiltre]
    return bs.reduce((a, b) => a + ss.reduce((x, s) => x + (xtab[b]?.[s] ?? 0), 0), 0)
  }, [xtab, classementFiltre, signalFiltre])
  // ANALYSE-3 — le compteur de chaque BANDE affiché dans l'ENCART (les 5 pastilles), CROSS-FILTRÉ par le
  // Signal courant : Signal = Tous → total de la bande (le chiffre « d'aujourd'hui ») ; Signal = Fort →
  // le nombre de cette bande à signal Fort. Lu sur le crosstab (toutes bandes, y compris Non retenue).
  const bandeSignalCount = (b: Bande) => {
    if (!xtab) return bandes[b] ?? 0
    const ss: SignalNiveauKey[] = signalFiltre === 'tous' ? ['fort', 'moyen', 'faible'] : [signalFiltre]
    return ss.reduce((a, s) => a + (xtab[b]?.[s] ?? 0), 0)
  }
  // total « analysé » de l'encart = les 5 catégories montrées (4 bandes + Non retenue) ; « Analyse
  // incomplète » (NC) est à part (l'analyse n'a PAS pu conclure), surfacée dans son groupe de fin.
  const encartTotal = bandes.A + bandes.B + bandes.C + bandes.D + bandes['0']
  const bandeTotal = bandesQ.data?.bande_total ?? 0
  // groupes de fin (Non retenue / Analyse incomplète) : montrés seulement quand Classement = Tous
  // (sinon on a demandé une bande précise, ces catégories n'en font pas partie).
  const showEndGroups = classementFiltre === 'tous'

  // props + centroïde (calculé UNE fois — sert au filtre de zone) — mode commune uniquement
  const props = useMemo(
    () => (geo.data?.features ?? []).map((f) => {
      const p = f.properties as unknown as ParcelProps
      p.centroid = roughCentroid(f.geometry)
      return p
    }),
    [geo.data],
  )

  const scoped = hasScopeFilters(filters, zone)
  const qNorm = query.trim().toUpperCase().replace(/\s+/g, '')

  const list = useMemo(() => {
    if (ile) {
      // serveur : déjà filtré (chips) et trié (rang P par défaut), accumulé par pages (E3)
      return serverRows
        .filter((p) => !qNorm || p.idu.toUpperCase().includes(qNorm) || p.idu.slice(8).toUpperCase().includes(qNorm))
    }
    // M69 A — tri client (mode commune) via la fonction pure `sortRows` : GLOBAL pour Surface,
    // groupé par tier seulement pour rang (cf. `groupes`). Même comportement que le serveur.
    const filtered = props
      .filter((p) => matchAll(p, filters, zone))
      .filter((p) => !qNorm || p.idu.toUpperCase().includes(qNorm) || p.idu.slice(8).toUpperCase().includes(qNorm))
    return sortRows(filtered, sort, groupes)
  }, [ile, serverRows, props, filters, zone, qNorm, sort, groupes])
  // RETOURS-10 (T3) — mode commune : le GeoJSON est complet en mémoire, mais on ne le déverse JAMAIS d'un
  // coup (« Tout voir » figeait l'app). Fenêtre de 200, « Voir 200 de plus » incrémental (usePagination),
  // position de défilement conservée (on APPEND). Mode île : la pagination serveur (200/page) borne déjà.
  const pg = usePagination(list.length)
  const shown = ile ? list : list.slice(0, pg.shown)

  const loading = analyse ? analyseList.isLoading : ile ? serverList.isLoading : geo.isLoading
  const error = analyse ? analyseList.isError : ile ? serverList.isError : geo.isError
  const refetch = () => (analyse ? analyseList.refetch() : ile ? serverList.refetch() : geo.refetch())
  // Total analysé du périmètre courant (point unique) — retenues + écartées ; fallback client.
  const total = uni.data?.total ?? props.length

  // bandeau honnête par commune (ex. Saint-Philippe = RNU) — porté par /communes
  const communesQ = useQuery({ queryKey: ['communes'], queryFn: getCommunes })
  const communeNote = commune ? communesQ.data?.find((c) => c.commune === commune)?.note : null

  return (
    // FIX (rendu liste) : la section elle-même défile si le volet est court (laptop) — sinon
    // l'en-tête fixe (compteurs/chips) écrasait la liste (flex-1) à ~0 px. La liste garde une
    // hauteur minimale utilisable ET son scroll interne (cf. le conteneur data-results-scroll).
    <div data-results-panel className="flex min-h-0 flex-1 flex-col overflow-y-auto overflow-x-clip px-5">
      {/* M55-D stage 3 : les FILTRES (FiltreLabuse) ont quitté la liste de résultats pour la section
          repliable « Filtres » du panneau gauche (« Tous les filtres → »). Ici : la liste seule. */}
      {/* Fix cosmétique (point 3) : ligne de tri LISIBLE et alignée (contrôle segmenté), au lieu
          des options qui flottaient collées à droite sans hiérarchie. Fonction inchangée. */}
      <div className="shrink-0">
        {/* ANALYSE-3 (§1) — le titre « RÉSULTATS » est retiré en mode analyse (l'encart qui suit dit
            déjà ce que c'est) ; il reste en mode factuel, au-dessus de la barre de tri. */}
        {!analyse && <p className="font-mono text-[11px] tracking-widest text-txt-dim">RÉSULTATS</p>}
        {/* QA-46 (M13-C) : la barre de tri S'EMPILE (flex-wrap) au lieu de déborder — les 4 options
            de tri ne tiennent pas sur la largeur du volet (~300 px) et étaient rognées. Le libellé
            « Trier » et le contrôle segmenté passent à la ligne, le pilule wrappe ses boutons. */}
        {/* M55-G point 3 — segmented control PRO : pills nettes (rayon suivi conteneur/bouton),
            padding constant px-3/py-1, état actif FRANC (rempli mint, texte encre — plus le
            mint/15 flottant), « i » aligné sur la ligne de base du libellé TRIER. */}
        {/* ANALYSE-1 — la barre de tri ne s'affiche QU'EN mode factuel : l'Analyse a UN ordre fixe
            (bande de Score puis Signal de mutation, lexicographique), jamais un tri chiffré au choix. */}
        {!analyse && <div data-tri-bar className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1.5">
          <span className="flex h-[15px] shrink-0 items-center gap-1.5 text-[10px] uppercase tracking-wide text-txt-dim">Trier
            {/* M55-F point 6 : le « i » des deux lunettes (opportunité globale vs probabilité seule) */}
            <Tip garder side="top" tip={CLIENT.tri.lunettes}>
              <span data-tri-info role="button" tabIndex={0} aria-label="Comprendre les deux tris"
                className="flex h-[15px] w-[15px] items-center justify-center rounded-full border border-line-2 text-[9px] font-bold normal-case leading-none text-txt-dim hover:border-mint hover:text-mint">i</span>
            </Tip>
          </span>
          <div className="inline-flex flex-wrap items-center gap-0.5 rounded-lg border border-line-2 bg-surface-2 p-0.5">
            {sorts.map((s) => {
              // M55-H point 4 : la pill Surface couvre ses DEUX sens — re-clic = inversion
              const actif = sort === s.key || (s.key === 'surface' && sort === 'surface_asc')
              const fleche = s.key === 'surface' && actif ? (sort === 'surface' ? ' ↓' : ' ↑')
                : actif && s.dir ? ` ${s.dir}` : ''
              return (
                <button key={s.key} data-sort={s.key}
                  onClick={() => setSort(s.key === 'surface' && sort === 'surface' ? 'surface_asc' : s.key)}
                  className={`rounded-md px-3 py-1 text-[11px] transition-colors duration-quick ${
                    actif ? 'bg-mint font-semibold text-mint-ink' : 'text-txt-mut hover:bg-surface-3 hover:text-txt'}`}>
                  {s.label}{fleche}
                </button>
              )
            })}
          </div>
          {/* RECETTE-1 R25 — la ligne « Liste groupée par priorité d'action … · trier par Surface »
              est RETIRÉE (demande Vic). Le groupement reste actif ; on ne l'explique plus par ce texte. */}
        </div>}
      </div>

      {communeNote && (
        <div className="mt-2 shrink-0 rounded-lg border border-st-creuser/40 bg-st-creuser/10 px-3 py-2 text-[10.5px] leading-snug text-st-creuser">
          ▲ {communeNote}
        </div>
      )}
      {/* M55-G point 8 : la ventilation par tier, la barre et la ligne « analysées →
          opportunités » sont des affichages d'OPINION — mode analyse seulement. En factuel,
          seul reste le compte total (pied de liste) ; le bandeau « Tri factuel — sans
          analyse » (VerdictHero) dit le mode. */}
      {analyse && (
        <>
          {/* ANALYSE-3 (révision) — l'ENCART DE SYNTHÈSE porte les compteurs : la phrase + les 5 pastilles
              chiffrées (4 bandes + Non retenue) + la barre colorée. Les pastilles ET la barre sont
              CROSS-FILTRÉES par le Signal courant (Signal = Tous → totaux ; Signal = Fort → le sous-total
              Fort de chaque bande) — lu sur le crosstab. La phrase « analysé N » reste le total (fait). */}
          <div data-encart className="mt-2 shrink-0 rounded-lg border border-line-2 bg-surface-2/50 px-3 py-1.5">
            <p className="text-[11.5px] leading-snug text-txt-mut">
              <b className="text-txt">LABUSE</b> a analysé les <b className="tabular-nums text-txt">{fmt(encartTotal)}</b> parcelles{zone ? ' de la zone' : commune ? ` de ${commune}` : ' de votre sélection'}.
            </p>
            <div data-ventilation-bande className="mt-1 flex flex-wrap gap-x-2.5 gap-y-0.5 text-[11px] leading-snug">
              {BANDE_ENCART.map((b) => (
                <span key={b} className="inline-flex items-center gap-1">
                  <span className="inline-flex h-2 w-2 rounded-full" style={{ background: BANDE_META[b].color }} />
                  <b className="tabular-nums" style={{ color: BANDE_META[b].color }}>{fmt(bandeSignalCount(b))}</b>
                  <span className="text-txt-dim">{BANDE_META[b].label}</span>
                </span>
              ))}
            </div>
            {(() => {
              const vals = BANDE_ENCART.map((b) => bandeSignalCount(b))
              const tot = Math.max(1, vals.reduce((a, v) => a + v, 0))
              return (
                <div className="mt-1 flex h-1.5 overflow-hidden rounded-full bg-line">
                  {BANDE_ENCART.map((b, i) => vals[i] > 0 && (
                    <span key={b} style={{ background: BANDE_META[b].color, width: `${(vals[i] / tot) * 100}%` }} />
                  ))}
                </div>
              )
            })()}
          </div>

          {/* ANALYSE-3 (révision) — les DEUX filtres, deux lignes. La puce ne porte QUE le MOT ENTIER, sur
              UNE ligne, JAMAIS tronqué, JAMAIS d'info réservée au survol. « Tous » en dernier. Actif = vert
              opaque. Le compteur est revenu dans l'encart. Les libellés « Classement »/« Signal » inline
              ont été retirés : à la largeur de colonne, 5 mots entiers + libellé ne tiennent pas sur une
              ligne — les deux rangées restent distinctes par leur contenu (bandes de qualité vs Fort/
              Moyen/Faible). Rangée 1 = le classement (bande), rangée 2 = le signal de mutation. */}
          <div data-filtres className="mt-2 flex shrink-0 flex-col gap-1 rounded-lg border border-line-2 bg-surface-2/50 px-2 py-1.5">
            <div data-classement-filtre className="flex min-w-0 flex-nowrap items-center gap-0.5">
              {CLASSEMENT_FILTRE.map((c) => {
                const actif = classementFiltre === c.key
                return (
                  <button key={c.key} data-classement-pill={c.key} onClick={() => setClassementFiltre(c.key)}
                    className={`whitespace-nowrap rounded-md px-1 py-1 text-[10px] leading-none transition-colors duration-quick ${
                      actif ? 'bg-mint font-semibold text-mint-ink' : 'text-txt-mut hover:bg-surface-3 hover:text-txt'}`}>
                    {c.label}
                  </button>
                )
              })}
            </div>
            <div data-signal-filtre className="flex min-w-0 flex-nowrap items-center gap-0.5">
              {SIGNALS_FILTRE.map((s) => {
                const actif = signalFiltre === s.key
                return (
                  <button key={s.key} data-signal-pill={s.key} onClick={() => setSignalFiltre(s.key)}
                    className={`whitespace-nowrap rounded-md px-1 py-1 text-[10px] leading-none transition-colors duration-quick ${
                      actif ? 'bg-mint font-semibold text-mint-ink' : 'text-txt-mut hover:bg-surface-3 hover:text-txt'}`}>
                    {s.label}
                  </button>
                )
              })}
            </div>
          </div>

          {/* ANALYSE-3 (§4) — la ligne de résultats : « N parcelles correspondent à vos filtres » SEULE,
              sur une seule ligne. « Trier par potentiel » retiré (l'ordre est fixe, le libellé débordait). */}
          <div data-filtre-resume className="mt-2 shrink-0 truncate border-t border-line pt-1.5 text-[11px] text-txt-mut">
            <b className="tabular-nums text-txt">{fmt(filtreCount)}</b> parcelle{filtreCount > 1 ? 's' : ''} correspondent à vos filtres
          </div>
        </>
      )}

      {/* E2 (M12) : les chips de verdict (Tout / Brûlantes / Chaudes / Réserve / À creuser /
          Écartées) ET le toggle « masquer les copropriétés » ont été RETIRÉS d'ici — ils
          faisaient doublon avec le bloc « Verdict · Scoring v2 (multi) » du panneau « + Filtre »
          (point d'entrée unique). Les CHIFFRES restent affichés juste au-dessus, en info non
          cliquable (barre + ligne brûlantes/chaudes/réserve). A4 : ces compteurs sont cohérents. */}

      <div data-results-scroll className="mt-3 flex min-h-[200px] flex-1 flex-col gap-2 overflow-y-auto overflow-x-clip pb-2">
        {loading && (
          <>
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-[52px] shrink-0 animate-pulse rounded-[10px] border border-line-2 bg-surface-3" />
            ))}
          </>
        )}
        {error && (
          <div className="rounded-lg border border-[#5a2420] bg-[#2a1210] p-3 text-xs">
            <p className="text-st-ecartee">Erreur de chargement des parcelles.</p>
            <button onClick={refetch} className="mt-2 rounded border border-line-2 px-2 py-1 text-txt hover:text-txt-hi">Réessayer</button>
          </div>
        )}
        {!loading && !error && (analyse ? bandeTotal === 0 : shown.length === 0) && (
          /* Item 4 (UX V1) : état vide EXPLICITE — dit où on est et comment en sortir
             (élargir à l'île / réinitialiser), aligné sur le #map-empty historique. */
          <div data-liste-vide>
            <EmptyState className="py-6"
              title="Aucune parcelle ici"
              hint={commune ? (
                <>Aucune parcelle {filters.tiers.length === 1
                  ? ALL_TIER_META[filters.tiers[0]].label.toLowerCase()
                  : scoped || filters.tiers.length ? 'correspondante' : ''} à {commune} —
                  élargissez à l'île ou ajustez les filtres.</>
              ) : (
                <>Aucune parcelle ne correspond à ces filtres sur l'île — retirez un critère.</>
              )}
              action={
                <span className="flex items-center justify-center gap-4">
                  {commune && (
                    <button data-vide-ile onClick={() => setCommune(null)} className="text-xs text-mint hover:underline">
                      Élargir à toute l'île
                    </button>
                  )}
                  <button onClick={resetFilters} className="text-xs text-mint hover:underline">Réinitialiser les filtres</button>
                </span>
              } />
          </div>
        )}
        {/* ANALYSE-1 — mode ANALYSE : UNE liste unique, classée par bande de Score puis par Signal de
            mutation (serveur, lexicographique). Un en-tête de bande est inséré à chaque changement de
            bande. Puis, EN FIN de liste et jamais masqués, deux groupes repliables avec leur compte :
            « Analyse incomplète » (au-dessus, jamais reléguée comme mauvaise) et « Sans potentiel
            constructible » (tout en bas). Mode FACTUEL : liste plate (neutre). */}
        {!loading && !error && analyse && bandeTotal > 0 && (
          <>
          {analyseRows.map((p, i) => (
            <Fragment key={p.idu}>
              {(i === 0 || p.bande !== analyseRows[i - 1].bande) && p.bande && <BandeHeader bande={p.bande as Bande} />}
              <AnalyseCard p={p} communeLabel={commune ?? ''} />
            </Fragment>
          ))}
          {analyseList.isLoading && analyseRows.length === 0 && (
            <p className="px-3 py-1.5 text-[10.5px] text-txt-dim">Chargement…</p>
          )}
          {/* ANALYSE-2 — vide HONNÊTE : quand le couple (Classement, Signal) ne matche AUCUNE parcelle,
              on le DIT clairement (ce n'est pas une panne), en nommant le filtre — plus jamais un
              « 0 / 2 216 » muet. Les groupes de fin restent accessibles (si Classement = Tous). */}
          {!analyseList.isLoading && analyseRows.length === 0 && filtreCount === 0 && (
            <p data-filtre-vide className="px-3 py-2 text-[11px] leading-snug text-txt-dim">
              Aucune parcelle {classementFiltre !== 'tous'
                ? <>« <b style={{ color: BANDE_META[classementFiltre].color }}>{BANDE_META[classementFiltre].label}</b> »</>
                : 'constructible'}{signalParam ? <> à signal <b>{signalParam}</b></> : ''} dans cette sélection.
              {showEndGroups ? ' Les parcelles Non retenue et Analyse incomplète restent consultables ci-dessous.' : ''}
            </p>
          )}
          {/* ANALYSE-2 — groupes de fin montrés seulement quand Classement = Tous (une bande précise
              demandée n'inclut pas ces catégories à part). Jamais masqués sinon. */}
          {showEndGroups && (bandes.NC ?? 0) > 0 && (
            <AnalyseBandeGroup groupe="nc" label={BANDE_META.NC.label} color={BANDE_META.NC.color}
              total={bandes.NC ?? 0} filters={filters} commune={commune ?? ''} />
          )}
          {showEndGroups && (bandes['0'] ?? 0) > 0 && (
            <AnalyseBandeGroup groupe="zero" label={BANDE_META['0'].label} color={BANDE_META['0'].color}
              total={bandes['0'] ?? 0} filters={filters} commune={commune ?? ''} />
          )}
          </>
        )}
        {!loading && !error && !analyse && (
          shown.map((p) => <ResultCard key={p.idu} p={p} communeLabel={commune ?? ''} factual={true} />)
        )}
      </div>

      <div className="flex shrink-0 items-center justify-between gap-2 border-t border-line py-3">
        {/* RETOURS-7 Z11 — compteur SUR UNE SEULE LIGNE. ANALYSE-1 : en analyse, le compteur porte les
            parcelles CONSTRUCTIBLES affichées / total (les groupes NC et Sans potentiel ont leur propre
            compte dans leur en-tête). */}
        <span className="min-w-0 text-[11px] text-txt-dim tnum">
          {analyse
            ? `${fmt(analyseRows.length)} / ${fmt(filtreCount)} constructibles`
            : `${fmt(shown.length)}${total > 0 || !ile ? ` / ${fmt(ile ? total : (list.length || total))}` : ''}`}
        </span>
        <span className="flex shrink-0 items-center gap-2">
          {/* RETOURS-10 (T3) — UN SEUL geste « Voir 200 de plus » (jamais « Tout voir »). */}
          {analyse ? (
            (analyseList.hasNextPage ?? false) && (
              <button data-results-more onClick={() => analyseList.fetchNextPage()} disabled={analyseList.isFetchingNextPage}
                className="text-xs text-mint hover:underline disabled:opacity-50">
                {analyseList.isFetchingNextPage ? 'Chargement…' : `Voir ${fmt(RESULTS_PAGE)} de plus →`}
              </button>
            )
          ) : ile ? (
            serverList.hasNextPage && (
              <button data-results-more onClick={() => serverList.fetchNextPage()} disabled={serverList.isFetchingNextPage}
                className="text-xs text-mint hover:underline disabled:opacity-50">
                {serverList.isFetchingNextPage ? 'Chargement…' : `Voir ${fmt(RESULTS_PAGE)} de plus →`}
              </button>
            )
          ) : (
            pg.hasMore && (
              <button data-results-more onClick={pg.more} className="text-xs text-mint hover:underline">
                Voir {fmt(Math.min(pg.step, list.length - pg.shown))} de plus →
              </button>
            )
          )}
        </span>
      </div>
    </div>
  )
}
