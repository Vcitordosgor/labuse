import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { csvExportUrl, getCommunes, getFiltre, getParcelsGeojson, getResults, type SortKey } from '../../lib/api'
import { hasScopeFilters, matchAll, matchScope, type ParcelProps } from '../../lib/filters'
import { roughCentroid } from '../../lib/geo'
import { fmtInt as fmt } from '../../lib/format'
import { ALL_TIER_META, effectiveTier, TIER_V2_META, verdictMeta, type TierV2 } from '../../lib/status'
import { CLIENT } from '../../lib/strings'
import { Tip } from '../Tip'
import { EmptyState } from '../States'
import { useApp } from '../../store/useApp'


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
      <button onClick={() => select(p.idu)}
        className={`relative flex w-full shrink-0 items-center overflow-hidden rounded-[10px] border bg-surface-3 py-2.5 px-4 text-left ${
          on ? 'border-mint' : 'border-line-2 hover:border-[#2E5A45]'}`}>
        <div className="min-w-0 flex-1">
          <span title={`Référence complète : ${p.idu}`} className="shrink-0 cursor-help whitespace-nowrap font-mono text-xs font-medium text-txt-hi">{p.idu.slice(8, 10)} {p.idu.slice(10)}</span>
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
      className={`relative flex w-full shrink-0 items-center overflow-hidden rounded-[10px] border bg-surface-3 py-2.5 pl-4 pr-3 text-left ${
        on ? 'border-mint' : 'border-line-2 hover:border-[#2E5A45]'}`}
    >
      <span className="absolute left-0 top-0 h-full w-[3px]" style={{ background: meta.color }} />
      <div className="min-w-0 flex-1">
        <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
          <span title={`Référence complète : ${p.idu}`} className="shrink-0 cursor-help whitespace-nowrap font-mono text-xs font-medium text-txt-hi">{p.idu.slice(8, 10)} {p.idu.slice(10)}</span>
          <Tip tip={`Verdict scoring (P×C)${p.rang_v2 != null ? ` — rang ${p.rang_v2} hors copro` : ''}${p.mult_v2 != null ? ` · ×${p.mult_v2.toFixed(1)} vs moyenne du parc` : ''}${p.etage0 ? ' — exclusion dure (étage 0 du run servi)' : ''}`}
            className="shrink-0">
            <span data-tier-chip className="rounded-full px-1.5 py-0.5 text-[9px] font-semibold"
              style={{ background: `${meta.color}1f`, color: meta.color }}>
              {meta.label}{p.rang_v2 != null && !p.etage0 ? ` · ${p.rang_v2}` : ''}
            </span>
          </Tip>
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
        {/* B2 : ×N (affichage produit du scoring v2). JAMAIS le nombre nu — l'unité de sens
            « plus probable » vit juste dessous, et l'infobulle porte le détail. Calcul inchangé (A3). */}
        <Tip tip={p.mult_v2 != null ? CLIENT.tri.multBadge(p.mult_v2.toFixed(1)) : CLIENT.mult.absent}>
          <span data-mult-tip className="font-display text-[15px] font-bold leading-none tnum" style={{ color: meta.color }}>
            {p.mult_v2 != null ? `×${p.mult_v2.toFixed(1)}` : '—'}
          </span>
        </Tip>
        {p.mult_v2 != null && (
          <span className="mt-0.5 text-[8.5px] leading-none text-txt-dim">{CLIENT.mult.unite}</span>
        )}
      </div>
    </button>
  )
}

// E2 (M12) : le composant TierChips (chips de verdict du bandeau) a été RETIRÉ — doublon avec
// le bloc « Verdict · Scoring v2 (multi) » du panneau « + Filtre » (point d'entrée unique).

// C4 + P2 (revue Vic n°3) : LABUSE MONTRE son analyse (avis argumenté), il ne décide pas à
// votre place. M55-G point 4 : le lien DIT où il mène — « comprendre le classement → » ouvre
// la MÊME modale que le bouton du bandeau (AlgoExplainer, état partagé store.algoOpen) : une
// étiquette, une destination. L'ancien « pourquoi ? » (entonnoir par motif en flux, cible
// muette) est retiré ; les motifs de déclassement restent accessibles par les chips
// « Déclassées · motif » du panneau Filtres, et chaque écartée garde son motif en fiche.
function LigneClassement({ total, opportunites, nFilters }: { total: number; opportunites: number; nFilters: number }) {
  const setAlgoOpen = useApp((s) => s.setAlgoOpen)
  return (
    <p className="mt-2 shrink-0 text-[11px] text-txt-dim"
      title="Opportunités détectées = brûlantes + chaudes (scoring P×C, hors étage 0 du run servi)">
      <span className="text-txt">{fmt(total)}</span> parcelles analysées → <span className="font-medium text-mint">{fmt(opportunites)}</span> opportunités détectées{nFilters > 0 && ' · filtres appliqués'}
      <button data-comprendre-btn onClick={() => setAlgoOpen(true)}
        className="ml-1.5 text-mint hover:underline"
        title="Ce que le classement mesure, sur quoi il est entraîné, ce qu'il ne dit pas">
        {CLIENT.algo.lien}
      </button>
    </p>
  )
}

const CAP = 200          // slice client — mode commune uniquement (le GeoJSON est déjà complet)
const RESULTS_PAGE = 200  // E3 : taille de page de la pagination île (offset serveur)

//: tris (M5.1 lot 1.3) — rang P par défaut ; le tri par V a disparu du sélecteur.
// B3 (M12) : libellés client centralisés (CLIENT.tri) ; « rang P » → « classement ».
// M13-F3 (QA-57) : « commune » RETIRÉ (demande Vic) ; ×N → « mutation ×N » ; chaque
// bouton porte son propre title explicatif.
// M55-G suite point 8 : `dir` = le SENS du tri, affiché sur la pill ACTIVE.
// M55-H point 4 : le tri Surface a ses DEUX sens — re-clic sur la pill active = inversion
// (« Surface ↓ » ↔ « Surface ↑ », clé serveur surface / surface_asc), dans les deux modes.
const SORTS: { key: SortKey; label: string; tip: string; dir?: string }[] = [
  { key: 'rang', label: CLIENT.tri.rang, tip: CLIENT.tri.rangTip },
  { key: 'mult', label: CLIENT.tri.mult, tip: CLIENT.tri.multTip, dir: '↓' },
  { key: 'surface', label: CLIENT.tri.surface, tip: CLIENT.tri.surfaceTip, dir: '↓' },
]

const TIER_ZERO: Record<TierV2 | 'all', number> = {
  all: 0, brulante: 0, chaude: 0, reserve_fonciere: 0, a_creuser: 0, ecartee: 0,
}

export function ResultsSection() {
  const { filters, query, zone, resetFilters, commune, setCommune } = useApp()
  const ile = commune == null   // mode « Toute l'île » : liste + compteurs servis en SQL
  const [showAll, setShowAll] = useState(false)
  // M55-G point 8 — décision Vic : sans analyse demandée, l'avis LABUSE ne s'affiche pas.
  // Mode FACTUEL (analyse OFF) : liste neutre, tri Surface seul, aucune ventilation d'opinion.
  const analyse = filters.analyseLabuse
  // Tri par défaut (M5.1) : RANG P croissant — ×N / surface en options (analyse) ;
  // factuel : Surface seul (les deux tris d'opinion sont retirés de ce mode).
  const [sort, setSort] = useState<SortKey>(analyse ? 'rang' : 'surface')
  const sorts = analyse ? SORTS : SORTS.filter((s) => s.key === 'surface')
  useEffect(() => { setSort(analyse ? 'rang' : 'surface') }, [analyse])
  // M55-F point 1 — POINT UNIQUE : compteurs (ventilation, total, opportunités) dérivent du
  // MÊME getFiltre(filters) que la Révélation et le compteur vivant (stage 8) — mêmes critères
  // (communes, terrain, signaux, tiers, interrupteur), mêmes nombres, fini les trois récits.
  // Retiré : getStats(scopeOnly) [tiers retirés] et getStats(undefined) [mode commune = aucun
  // filtre → l'origine du « 431 663 → 98 » décorrélé, mesuré 10/08].
  const uni = useQuery({
    queryKey: ['results-unifie', commune, filters],
    queryFn: () => getFiltre(filters, 0),
  })
  const geo = useQuery({ queryKey: ['geojson', commune], queryFn: getParcelsGeojson, enabled: !ile })
  // E3 (M12) : la liste île n'est plus plafonnée à 500. Pagination par offset (le back la
  // supporte nativement, A2) — pages de 200, « Charger plus » accumule. Tri `rang` = index top-N
  // (quasi-gratuit) ; les autres tris paginent aussi (coût croissant en profondeur, assumé).
  const serverList = useInfiniteQuery({
    queryKey: ['results', commune, filters, sort],
    queryFn: ({ pageParam }) => getResults(filters, RESULTS_PAGE, sort, pageParam),
    initialPageParam: 0,
    getNextPageParam: (last: unknown[], pages) => (last.length === RESULTS_PAGE ? pages.length * RESULTS_PAGE : undefined),
    enabled: ile,
  })
  const serverRows = useMemo(
    () => (serverList.data?.pages ?? []).flat() as unknown as (ParcelProps & { commune?: string })[],
    [serverList.data],
  )

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

  // Compteurs : SANS filtre de périmètre → /stats (SQL-exact). AVEC → île : /stats FILTRÉ
  // (SQL-exact aussi) ; commune : recalcul client marqué *.
  const counts = useMemo(() => {
    if (uni.data) {
      const t = uni.data.tiers
      return { all: t.brulante + t.chaude + t.reserve_fonciere + t.a_creuser,
               brulante: t.brulante, chaude: t.chaude, reserve_fonciere: t.reserve_fonciere,
               a_creuser: t.a_creuser, ecartee: t.ecartee }
    }
    // fallback client (mode commune, réponse serveur pas encore là) — jamais un vide
    const c: Record<TierV2 | 'all', number> = { ...TIER_ZERO }
    for (const p of props) {
      if (!matchScope(p, filters, zone)) continue
      const t = effectiveTier(p.tier_v2, p.etage0)
      if (!t) continue
      if (t !== 'ecartee') c.all += 1
      c[t] += 1
    }
    return c
  }, [props, filters, zone, uni.data])

  const list = useMemo(() => {
    if (ile) {
      // serveur : déjà filtré (chips) et trié (rang P par défaut), accumulé par pages (E3)
      return serverRows
        .filter((p) => !qNorm || p.idu.toUpperCase().includes(qNorm) || p.idu.slice(8).toUpperCase().includes(qNorm))
    }
    return props
      .filter((p) => matchAll(p, filters, zone))
      .filter((p) => !qNorm || p.idu.toUpperCase().includes(qNorm) || p.idu.slice(8).toUpperCase().includes(qNorm))
      .sort((a, b) => {
        // même sémantique que le serveur : rang P (copros/sans rang en queue), ×N, surface, commune
        if (sort === 'mult') return (b.mult_v2 ?? -1) - (a.mult_v2 ?? -1)
        if (sort === 'surface') return (b.surface_m2 ?? -1) - (a.surface_m2 ?? -1)
        if (sort === 'surface_asc') return (a.surface_m2 ?? Infinity) - (b.surface_m2 ?? Infinity)
        if (sort === 'commune') return String((a as { commune?: string }).commune ?? '').localeCompare(String((b as { commune?: string }).commune ?? ''))
        const ra = a.rang_v2 ?? Infinity
        const rb = b.rang_v2 ?? Infinity
        if (ra !== rb) return ra - rb
        return (b.mult_v2 ?? -1) - (a.mult_v2 ?? -1)
      })
  }, [ile, serverRows, props, filters, zone, qNorm, sort])
  // E3 : en mode île, la liste paginée est déjà bornée par ce qui a été chargé → tout afficher.
  // En mode commune, le GeoJSON est complet → on garde le slice client + « Tout voir ».
  const shown = ile || showAll ? list : list.slice(0, CAP)

  const loading = ile ? serverList.isLoading : geo.isLoading
  const error = ile ? serverList.isError : geo.isError
  const refetch = () => (ile ? serverList.refetch() : geo.refetch())
  // Total analysé du périmètre courant (point unique) — retenues + écartées ; fallback client.
  const total = uni.data?.total ?? props.length

  // bandeau honnête par commune (ex. Saint-Philippe = RNU) — porté par /communes
  const communesQ = useQuery({ queryKey: ['communes'], queryFn: getCommunes })
  const communeNote = commune ? communesQ.data?.find((c) => c.commune === commune)?.note : null
  const promus = counts.all || 1
  const nFilters = (filters.tiers.length ? 1 : 0) + (scoped ? 1 : 0)
  const opportunites = uni.data?.opportunites ?? counts.brulante + counts.chaude

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
        <p className="font-mono text-[11px] tracking-widest text-txt-dim">RÉSULTATS</p>
        {/* QA-46 (M13-C) : la barre de tri S'EMPILE (flex-wrap) au lieu de déborder — les 4 options
            de tri ne tiennent pas sur la largeur du volet (~300 px) et étaient rognées. Le libellé
            « Trier » et le contrôle segmenté passent à la ligne, le pilule wrappe ses boutons. */}
        {/* M55-G point 3 — segmented control PRO : pills nettes (rayon suivi conteneur/bouton),
            padding constant px-3/py-1, état actif FRANC (rempli mint, texte encre — plus le
            mint/15 flottant), « i » aligné sur la ligne de base du libellé TRIER. */}
        <div data-tri-bar className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1.5">
          <span className="flex h-[15px] shrink-0 items-center gap-1.5 text-[10px] uppercase tracking-wide text-txt-dim">Trier
            {/* M55-F point 6 : le « i » des deux lunettes (opportunité globale vs probabilité seule) */}
            <Tip side="top" tip={CLIENT.tri.lunettes}>
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
                    actif ? 'bg-mint font-semibold text-mint-ink' : 'text-txt-mut hover:bg-surface-3 hover:text-txt'}`}
                  title={s.key === 'surface' && actif ? `${s.tip} — re-cliquer pour inverser le sens` : s.tip}>
                  {s.label}{fleche}
                </button>
              )
            })}
          </div>
        </div>
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
          <p className="mt-3 shrink-0 border-t border-line pt-2.5 text-xs text-txt-mut"
            title={uni.data ? `${fmt(uni.data.opportunites)} opportunités (brûlantes + chaudes) dont ${fmt(uni.data.opportunites_evenement)} avec événement BODACC ouvert` : undefined}>
            <span className="font-medium" style={{ color: TIER_V2_META.brulante.color }}>{fmt(counts.brulante)}</span> brûlantes ·{' '}
            <span className="font-medium" style={{ color: TIER_V2_META.chaude.color }}>{fmt(counts.chaude)}</span> chaudes ·{' '}
            <span className="font-medium" style={{ color: TIER_V2_META.reserve_fonciere.color }}>{fmt(counts.reserve_fonciere)}</span> potentiel long terme
            {scoped && <span className="text-txt-dim"> {zone ? '(dans la zone)' : '(filtres actifs)'}</span>}
          </p>
          {/* M55-G point 5 (décision Vic) : la ligne « soit N parcelles avec dossier propriétaire ·
              N personnes physiques » a QUITTÉ la zone résultats — l'info vit en fiche (tiroir
              Propriétaire), rien n'est perdu. Champs API (opportunites_avec_dossier…) inchangés. */}
          <div className="mt-2 flex h-1.5 shrink-0 overflow-hidden rounded-full bg-line">
            <span style={{ background: TIER_V2_META.brulante.color, width: `${(counts.brulante / promus) * 100}%` }} />
            <span style={{ background: TIER_V2_META.chaude.color, width: `${(counts.chaude / promus) * 100}%` }} />
            <span style={{ background: TIER_V2_META.reserve_fonciere.color, width: `${(counts.reserve_fonciere / promus) * 100}%` }} />
            <span style={{ background: TIER_V2_META.a_creuser.color, width: `${(counts.a_creuser / promus) * 100}%` }} />
          </div>
          <LigneClassement total={total} opportunites={opportunites} nFilters={nFilters} />
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
        {!loading && !error && shown.length === 0 && (
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
        {shown.map((p) => <ResultCard key={p.idu} p={p} communeLabel={commune ?? ''} factual={!analyse} />)}
      </div>

      <div className="flex shrink-0 items-center justify-between gap-2 border-t border-line py-3">
        <span className="min-w-0 text-[11px] text-txt-dim">
          {/* E3 : plus de « 500 premiers » — on affiche le nombre réellement chargé, sur le total. */}
          {fmt(shown.length)} affichée{shown.length > 1 ? 's' : ''}
          {!ile && list.length > shown.length ? ` / ${fmt(list.length)}` : ''}
          {ile && total > 0 && <span className="text-txt-dim"> / {fmt(total)} au total</span>}
        </span>
        <span className="flex shrink-0 items-center gap-2">
          <a href={csvExportUrl(filters, sort)} download
            className="text-[11px] text-txt-mut hover:text-mint"
            title="Exporter la liste filtrée en CSV (verdict, rang, ×N — mêmes filtres, même tri)">
            ⬇ CSV
          </a>
          {/* E3 : île → pagination serveur (Charger plus) ; commune → slice client (Tout voir). */}
          {ile ? (
            serverList.hasNextPage && (
              <button onClick={() => serverList.fetchNextPage()} disabled={serverList.isFetchingNextPage}
                className="text-xs text-mint hover:underline disabled:opacity-50">
                {serverList.isFetchingNextPage ? 'Chargement…' : 'Charger plus →'}
              </button>
            )
          ) : (
            list.length > CAP && (
              <button onClick={() => setShowAll((v) => !v)} className="text-xs text-mint hover:underline">
                {showAll ? 'Réduire' : 'Tout voir →'}
              </button>
            )
          )}
        </span>
      </div>
    </div>
  )
}
