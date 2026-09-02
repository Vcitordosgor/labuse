import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { getCommunes, getFiltre, getParcelsGeojson, getResults, type SortKey } from '../../lib/api'
import { hasScopeFilters, matchAll, matchScope, type ParcelProps } from '../../lib/filters'
import { roughCentroid } from '../../lib/geo'
import { fmtInt as fmt } from '../../lib/format'
import { ALL_TIER_META, effectiveTier, etatBienMeta, TIER_V2_META, verdictMeta, type TierV2 } from '../../lib/status'
import { raisonDominante } from '../../lib/raison'
import { CLIENT } from '../../lib/strings'
import { Tip } from '../Tip'
import { EmptyState } from '../States'
import { useApp } from '../../store/useApp'
import { usePagination } from '../ListPagination'


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
          on ? 'border-mint' : 'border-line-2 hover:border-mint/60'}`}>
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
      className={`relative flex w-full shrink-0 items-center overflow-hidden rounded-[10px] border bg-surface-3 py-2.5 pl-4 pr-3 text-left ${
        on ? 'border-mint' : 'border-line-2 hover:border-mint/60'}`}
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

// M55-H point 5 (décision Vic) — ordre des GROUPES de la liste d'analyse (identique au CASE
// SQL du serveur) : 4 tiers d'opportunité, puis potentiel épuisé (declasse_*), puis écartées.
const GROUPE_ORDER = (p: Pick<ParcelProps, 'etage0' | 'tier_v2'>): number => {
  if (p.etage0) return 6
  const t = p.tier_v2 ?? ''
  if (t === 'brulante') return 0
  if (t === 'chaude') return 1
  if (t === 'reserve_fonciere') return 2
  if (t === 'a_creuser') return 3
  if (t.startsWith('declasse')) return 4
  return 5
}

// M69 A — comparateur de la liste EXTRAIT en fonction pure (testable). Le GROUPEMENT par tier
// n'est appliqué QUE si `groupes` (tri « Probabilité de vente »/rang en mode analyse) ; les tris
// de COLONNE (Surface ↓/↑) s'appliquent GLOBALEMENT → ordre monotone garanti sur tout le jeu.
// Même sémantique que le serveur (_q_v2_list) : un seul comportement de tri, client et serveur.
export type SortableRow = Pick<ParcelProps, 'etage0' | 'tier_v2' | 'mult_v2' | 'surface_m2' | 'rang_v2'> & { commune?: string }
export function sortRows<T extends SortableRow>(rows: T[], sort: SortKey, groupes: boolean): T[] {
  return rows.slice().sort((a, b) => {
    if (groupes) {
      const ga = GROUPE_ORDER(a)
      const gb = GROUPE_ORDER(b)
      if (ga !== gb) return ga - gb
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

// M55-H point 10 : couleur de la famille « potentiel épuisé » — la terre éteinte des
// verdicts declasse_* (source unique ALL_TIER_META, jamais un littéral recopié).
const EPUISE_COLOR = ALL_TIER_META['declasse_bati_sature'].color

const TIER_ZERO: Record<TierV2 | 'all', number> = {
  all: 0, brulante: 0, chaude: 0, reserve_fonciere: 0, a_creuser: 0, ecartee: 0,
}

export function ResultsSection() {
  const { filters, query, zone, resetFilters, commune, setCommune } = useApp()
  const ile = commune == null   // mode « Toute l'île » : liste + compteurs servis en SQL
  // M55-G point 8 — décision Vic : sans analyse demandée, l'avis LABUSE ne s'affiche pas.
  // Mode FACTUEL (analyse OFF) : liste neutre, tri Surface seul, aucune ventilation d'opinion.
  const analyse = filters.analyseLabuse
  // Tri par défaut (M5.1) : RANG P croissant — ×N / surface en options (analyse) ;
  // factuel : Surface seul (les deux tris d'opinion sont retirés de ce mode).
  const [sort, setSort] = useState<SortKey>(analyse ? 'rang' : 'surface')
  const sorts = analyse ? SORTS : SORTS.filter((s) => s.key === 'surface')
  useEffect(() => { setSort(analyse ? 'rang' : 'surface') }, [analyse])
  // M69 A — GROUPEMENT PAR TIER : appliqué UNIQUEMENT pour le tri par défaut « Probabilité de
  // vente » (rang) en mode analyse (M55-H p5). Un tri de COLONNE (Surface) doit produire un ordre
  // GLOBAL monotone → on lève le groupement. Ce booléen pilote client ET serveur (un seul point).
  const groupes = analyse && sort === 'rang'
  // M55-F point 1 — POINT UNIQUE : compteurs (ventilation, total, opportunités) dérivent du
  // MÊME getFiltre(filters) que la Révélation et le compteur vivant (stage 8) — mêmes critères
  // (communes, terrain, signaux, tiers, interrupteur), mêmes nombres, fini les trois récits.
  // Retiré : getStats(scopeOnly) [tiers retirés] et getStats(undefined) [mode commune = aucun
  // filtre → l'origine du « 431 663 → 98 » décorrélé, mesuré 10/08].
  const uni = useQuery({
    queryKey: ['results-unifie', commune, filters],
    queryFn: () => getFiltre(filters, 0),
  })
  const trameQ = useQuery({
    queryKey: ['filtre', filters, false],
    queryFn: () => getFiltre({ ...filters, analyseLabuse: false }, 0),
    enabled: analyse,
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

  const loading = ile ? serverList.isLoading : geo.isLoading
  const error = ile ? serverList.isError : geo.isError
  const refetch = () => (ile ? serverList.refetch() : geo.refetch())
  // Total analysé du périmètre courant (point unique) — retenues + écartées ; fallback client.
  const total = uni.data?.total ?? props.length

  // bandeau honnête par commune (ex. Saint-Philippe = RNU) — porté par /communes
  const communesQ = useQuery({ queryKey: ['communes'], queryFn: getCommunes })
  const communeNote = commune ? communesQ.data?.find((c) => c.commune === commune)?.note : null
  const promus = counts.all || 1
  // M55-K point 1 : `nFilters` et la var locale `opportunites` sont retirés avec la ligne de
  // synthèse (0-caller). Le tooltip de la ventilation lit toujours `uni.data.opportunites`.
  // M55-H point 10 — l'arithmétique de la Révélation, ICI AUSSI (source unique getFiltre) :
  // potentiel épuisé = retenues − 4 tiers vivants ; écartées = trame analysée − retenues.
  // trameQ partage la queryKey de FiltreLabuse (['filtre', filters, false]) → cache commun.
  const vent4 = counts.brulante + counts.chaude + counts.reserve_fonciere + counts.a_creuser
  const epuise = uni.data ? Math.max(0, uni.data.compte - vent4) : 0
  const ecartees = uni.data && trameQ.data ? Math.max(0, trameQ.data.compte - uni.data.compte) : null

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
          {/* M69 A — état du groupement : dit que la liste est groupée par tier quand le tri par
              défaut (Probabilité de vente) est actif (lève le malentendu « pourquoi non monotone »). */}
          {groupes && (
            <span data-tri-groupe className="basis-full text-[10px] leading-tight text-txt-dim">Liste {CLIENT.tri.groupe}</span>
          )}
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
          {/* M55-H point 10 : la ventilation ENTIÈRE — 4 tiers + potentiel épuisé + écartées,
              MÊMES nombres que la phrase de Révélation (source unique getFiltre :
              épuisé = retenues − 4 tiers ; écartées = trame analysée − retenues). Le « i »
              raconte les trois familles. */}
          <p className="mt-3 shrink-0 border-t border-line pt-2.5 text-xs leading-relaxed text-txt-mut"
            title={uni.data ? `${fmt(uni.data.opportunites)} opportunités (priorité + à suivre) dont ${fmt(uni.data.opportunites_evenement)} avec événement BODACC ouvert` : undefined}>
            {/* M135 — bande de résumé : MÊMES NOMBRES, échelle d'action (labels de status.ts, jamais en dur) */}
            <span className="font-medium" style={{ color: TIER_V2_META.brulante.color }}>{fmt(counts.brulante)}</span> {TIER_V2_META.brulante.label.toLowerCase()} ·{' '}
            <span className="font-medium" style={{ color: TIER_V2_META.chaude.color }}>{fmt(counts.chaude)}</span> {TIER_V2_META.chaude.label.toLowerCase()} ·{' '}
            <span className="font-medium" style={{ color: TIER_V2_META.reserve_fonciere.color }}>{fmt(counts.reserve_fonciere)}</span> {TIER_V2_META.reserve_fonciere.label.toLowerCase()} ·{' '}
            <span className="font-medium" style={{ color: TIER_V2_META.a_creuser.color }}>{fmt(counts.a_creuser)}</span> {TIER_V2_META.a_creuser.label.toLowerCase()} ·{' '}
            <span className="font-medium" style={{ color: EPUISE_COLOR }}>{fmt(epuise)}</span> faible
            {ecartees != null && (
              <> · <span className="font-medium text-txt-dim">{fmt(ecartees)}</span> écartées</>
            )}
            {/* M55-K point 1 : « (filtres actifs) » retiré (la ventilation EST déjà filtrée —
                mention redondante). « (dans la zone) » conservé : un polygone dessiné n'est
                pas visible autrement dans le panneau, c'est un signal distinct, non redondant. */}
            {zone && <span className="text-txt-dim"> (dans la zone)</span>}
            <Tip side="top" tip={CLIENT.ventilation.familles} className="ml-1.5 inline-flex align-middle">
              <span data-ventilation-info role="button" tabIndex={0} aria-label="Comprendre les trois familles"
                className="flex h-[13px] w-[13px] items-center justify-center rounded-full border border-line-2 text-[8px] font-bold leading-none text-txt-dim hover:border-mint hover:text-mint">i</span>
            </Tip>
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
        {/* RETOURS-7 Z11 — compteur SUR UNE SEULE LIGNE : « 200 / 430 813 » (affichées / total). */}
        <span className="min-w-0 text-[11px] text-txt-dim tnum">
          {fmt(shown.length)}{total > 0 || !ile ? ` / ${fmt(ile ? total : (list.length || total))}` : ''}
        </span>
        <span className="flex shrink-0 items-center gap-2">
          {/* RETOURS-7 Z11 — export CSV RETIRÉ de la liste (décision Vic). SUITE-1 S7 : l'endpoint
              /parcels/export.csv et `csvExportUrl` ont été supprimés (code mort sans appelant). */}
          {/* RETOURS-10 (T3) — UN SEUL geste « Voir 200 de plus » (jamais « Tout voir ») : île → page
              serveur suivante ; commune → fenêtre client +200. Jamais de chargement massif. */}
          {ile ? (
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
