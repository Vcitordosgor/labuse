import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { csvExportUrl, getCommunes, getEntonnoir, getParcelsGeojson, getResults, getStats, type SortKey } from '../../lib/api'
import { hasScopeFilters, matchAll, matchScope, type ParcelProps } from '../../lib/filters'
import { roughCentroid } from '../../lib/geo'
import { fmtInt as fmt } from '../../lib/format'
import { effectiveTier, TIER_V2_META, verdictMeta, type TierV2 } from '../../lib/status'
import { CLIENT } from '../../lib/strings'
import { Loading } from '../Loading'
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

function ResultCard({ p, communeLabel }: { p: ParcelProps & { commune?: string }; communeLabel: string }) {
  const { selectedIdu, select } = useApp()
  // M5.1 : le VERDICT v2 pilote la carte de résultat — chip tier EN PREMIER (couleur
  // verdictMeta), rang + ×N ; l'étage 0 du run servi prime.
  const meta = verdictMeta(p.status, p.tier_v2, p.etage0)
  const on = selectedIdu === p.idu
  return (
    <button
      onClick={() => select(p.idu)}
      className={`relative flex w-full shrink-0 items-center overflow-hidden rounded-[10px] border bg-surface-3 py-2.5 pl-4 pr-3 text-left ${
        on ? 'border-mint' : 'border-line-2 hover:border-[#2E5A45]'}`}
    >
      <span className="absolute left-0 top-0 h-full w-[3px]" style={{ background: meta.color }} />
      <div className="min-w-0 flex-1">
        <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
          <span className="shrink-0 whitespace-nowrap font-mono text-xs font-medium text-txt-hi">{p.idu.slice(8, 10)} {p.idu.slice(10)}</span>
          <Tip tip={`Verdict scoring v2 (P×C)${p.rang_v2 != null ? ` — rang ${p.rang_v2} hors copro` : ''}${p.mult_v2 != null ? ` · ×${p.mult_v2.toFixed(1)} vs moyenne du parc` : ''}${p.etage0 ? ' — exclusion dure (étage 0 du run servi)' : ''}`}
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
        <Tip tip={p.mult_v2 != null ? CLIENT.mult.tip(p.mult_v2.toFixed(1)) : CLIENT.mult.absent}>
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
// votre place. Le popover expose l'entonnoir PAR MOTIF (SQL-exact) : le reste reste visible et
// cliquable, chaque écartée motivée — vous pouvez contredire.
function EntonnoirLine({ total, opportunites, nFilters }: { total: number; opportunites: number; nFilters: number }) {
  const [open, setOpen] = useState(false)
  const commune = useApp((s) => s.commune)
  const q = useQuery({ queryKey: ['entonnoir', commune], queryFn: getEntonnoir, enabled: open })
  // fermeture au clavier (Échap)
  useEffect(() => {
    if (!open) return
    const h = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [open])
  return (
    <div className="mt-2 shrink-0">
      <p className="text-[11px] text-txt-dim"
        title="Opportunités détectées = brûlantes v2 + chaudes v2 (scoring P×C, hors étage 0 du run servi)">
        <span className="text-txt">{fmt(total)}</span> parcelles analysées → <span className="font-medium text-mint">{fmt(opportunites)}</span> opportunités détectées{nFilters > 0 && ' · filtres appliqués'}
        <button data-entonnoir-btn onClick={() => setOpen((o) => !o)}
          className="ml-1.5 text-mint hover:underline" title="L'entonnoir par motif — pourquoi le reste est écarté (SQL-exact)">
          pourquoi ? {open ? '▴' : '▾'}
        </button>
      </p>
      {/* Point 8 : l'explication s'ouvre EN FLUX (plus un popover flottant clippé/modal) → elle est
          entièrement lisible ET la liste des parcelles reste scrollable en dessous (la section défile
          naturellement). Plus de fond modal qui bloquait le scroll vers les parcelles. */}
      {open && (
        <div data-entonnoir-panel className="card-elev mt-1.5 p-3">
          <p className="text-[11px] leading-snug text-txt">
            LABUSE a analysé <b>{fmt(q.data?.analysees ?? total)}</b> parcelles ; son avis retient
            <b className="text-mint"> {fmt(q.data?.opportunites ?? opportunites)}</b> opportunités
            (brûlantes v2 + chaudes v2). Le reste reste visible et cliquable — voici pourquoi il est écarté.
          </p>
          {q.data?.tiers && (
            <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5">
              {(['brulante', 'chaude', 'reserve_fonciere', 'a_creuser', 'ecartee'] as TierV2[]).map((t) => (
                <span key={t} className="flex items-center gap-1 text-[10px] text-txt-mut">
                  <span className="h-1.5 w-1.5 rounded-full" style={{ background: TIER_V2_META[t].color }} />
                  {TIER_V2_META[t].label} <span className="font-mono">{fmt(q.data!.tiers![t])}</span>
                </span>
              ))}
            </div>
          )}
          <p className="label-caps mt-1.5 text-[9.5px]">Le reste, par motif</p>
          {q.isLoading && <Loading className="mt-1 text-[11px]" label="Décompte par motif" />}
          {q.data && (q.data.motifs ?? []).length === 0 && (
            <p className="mt-1 text-[10.5px] text-txt-dim">Détail par motif non disponible sur ce périmètre.</p>
          )}
          <div className="mt-1 flex flex-col gap-0.5">
            {(q.data?.motifs ?? []).map((m) => (
              <div key={m.motif} className={`flex justify-between gap-2 text-[10.5px] ${m.motif.startsWith('écartées') ? 'font-medium text-txt border-b border-line pb-0.5 mb-0.5' : 'text-txt-mut'}`}>
                <span className="min-w-0">{m.motif}</span>
                <span className="tnum shrink-0 font-mono">{fmt(m.n)}</span>
              </div>
            ))}
          </div>
          {q.data && <p className="mt-1.5 text-[9px] leading-snug text-txt-dim">{q.data.note}</p>}
        </div>
      )}
    </div>
  )
}

const CAP = 200          // slice client — mode commune uniquement (le GeoJSON est déjà complet)
const RESULTS_PAGE = 200  // E3 : taille de page de la pagination île (offset serveur)

//: tris (M5.1 lot 1.3) — rang P par défaut ; le tri par V a disparu du sélecteur.
// B3 (M12) : libellés client centralisés (CLIENT.tri) ; « rang P » → « classement ».
const SORTS: { key: SortKey; label: string }[] = [
  { key: 'rang', label: CLIENT.tri.rang },
  { key: 'mult', label: CLIENT.tri.mult },
  { key: 'surface', label: CLIENT.tri.surface },
  { key: 'commune', label: CLIENT.tri.commune },
]

const TIER_ZERO: Record<TierV2 | 'all', number> = {
  all: 0, brulante: 0, chaude: 0, reserve_fonciere: 0, a_creuser: 0, ecartee: 0,
}

export function ResultsSection() {
  const { filters, query, zone, resetFilters, commune, setCommune } = useApp()
  const ile = commune == null   // mode « Toute l'île » : liste + compteurs servis en SQL
  const [showAll, setShowAll] = useState(false)
  // Tri par défaut (M5.1) : RANG P croissant — ×N / surface / commune en options.
  const [sort, setSort] = useState<SortKey>('rang')
  // compteurs par tier sous filtres de PÉRIMÈTRE (jamais le filtre tier lui-même)
  const scopeOnly = useMemo(() => ({ ...filters, tiers: [] as TierV2[] }), [filters])
  const stats = useQuery({
    queryKey: ['stats', commune, ile ? scopeOnly : null],
    queryFn: () => getStats(ile ? scopeOnly : undefined),
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
    if ((!scoped || ile) && stats.data) {
      const t = stats.data.tiers
      return { all: t.brulante + t.chaude + t.reserve_fonciere + t.a_creuser,
               brulante: t.brulante, chaude: t.chaude, reserve_fonciere: t.reserve_fonciere,
               a_creuser: t.a_creuser, ecartee: t.ecartee }
    }
    const c: Record<TierV2 | 'all', number> = { ...TIER_ZERO }
    for (const p of props) {
      if (!matchScope(p, filters, zone)) continue
      const t = effectiveTier(p.tier_v2, p.etage0)
      if (!t) continue
      if (t !== 'ecartee') c.all += 1
      c[t] += 1
    }
    return c
  }, [props, filters, zone, scoped, ile, stats.data])

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
  const total = stats.data?.total ?? props.length

  // bandeau honnête par commune (ex. Saint-Philippe = RNU) — porté par /communes
  const communesQ = useQuery({ queryKey: ['communes'], queryFn: getCommunes })
  const communeNote = commune ? communesQ.data?.find((c) => c.commune === commune)?.note : null
  const promus = counts.all || 1
  const nFilters = (filters.tiers.length ? 1 : 0) + (scoped ? 1 : 0)
  const opportunites = ile && stats.data ? stats.data.opportunites : counts.brulante + counts.chaude

  return (
    // FIX (rendu liste) : la section elle-même défile si le volet est court (laptop) — sinon
    // l'en-tête fixe (compteurs/chips) écrasait la liste (flex-1) à ~0 px. La liste garde une
    // hauteur minimale utilisable ET son scroll interne (cf. le conteneur data-results-scroll).
    <div data-results-panel className="flex min-h-0 flex-1 flex-col overflow-y-auto overflow-x-clip px-5">
      {/* Fix cosmétique (point 3) : ligne de tri LISIBLE et alignée (contrôle segmenté), au lieu
          des options qui flottaient collées à droite sans hiérarchie. Fonction inchangée. */}
      <div className="shrink-0">
        <p className="font-mono text-[11px] tracking-widest text-txt-dim">RÉSULTATS</p>
        {/* QA-46 (M13-C) : la barre de tri S'EMPILE (flex-wrap) au lieu de déborder — les 4 options
            de tri ne tiennent pas sur la largeur du volet (~300 px) et étaient rognées. Le libellé
            « Trier » et le contrôle segmenté passent à la ligne, le pilule wrappe ses boutons. */}
        <div data-tri-bar className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1.5">
          <span className="shrink-0 text-[10px] uppercase tracking-wide text-txt-dim">Trier</span>
          {/* B3 : espacement régulier entre les 4 options (gap-1 + px-2.5 uniformes) */}
          <div className="flex flex-wrap items-center gap-1 rounded-full border border-line-2 bg-surface-2 p-1">
            {SORTS.map((s) => (
              <button key={s.key} data-sort={s.key} onClick={() => setSort(s.key)}
                className={`rounded-full px-2.5 py-0.5 text-[11px] transition-colors ${sort === s.key ? 'bg-mint/15 font-medium text-mint' : 'text-txt-mut hover:text-txt'}`}
                title={s.key === 'rang' ? CLIENT.tri.rangTip : `Trier par ${s.label}`}>
                {s.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {communeNote && (
        <div className="mt-2 shrink-0 rounded-lg border border-st-creuser/40 bg-st-creuser/10 px-3 py-2 text-[10.5px] leading-snug text-st-creuser">
          ▲ {communeNote}
        </div>
      )}
      <p className="mt-3 shrink-0 border-t border-line pt-2.5 text-xs text-txt-mut"
        title={ile && stats.data ? `${fmt(stats.data.opportunites)} opportunités (brûlantes v2 + chaudes v2) dont ${fmt(stats.data.opportunites_evenement)} avec événement BODACC ouvert` : undefined}>
        <span className="font-medium" style={{ color: TIER_V2_META.brulante.color }}>{fmt(counts.brulante)}</span> brûlantes v2 ·{' '}
        <span className="font-medium" style={{ color: TIER_V2_META.chaude.color }}>{fmt(counts.chaude)}</span> chaudes ·{' '}
        <span className="font-medium" style={{ color: TIER_V2_META.reserve_fonciere.color }}>{fmt(counts.reserve_fonciere)}</span> réserve foncière
        {scoped && <span className="text-txt-dim"> {zone ? '(dans la zone)' : '(filtres actifs)'}</span>}
      </p>
      {/* CRED-3 (revue externe 12/07) : les PARCELLES sont l'unité de la somme — avec dossier +
          personnes physiques = les opportunités affichées juste au-dessus. */}
      {ile && stats.data != null && stats.data.opportunites > 0 && (
        <p data-dossiers-detail className="mt-1 shrink-0 text-[11px] leading-snug text-txt-dim"
          title="Un propriétaire = un dossier, quel que soit son nombre de parcelles (identification par SIREN, personnes morales DGFiP). Les personnes physiques n'ont pas d'identité en open data — doctrine RGPD : jamais de donnée nominative en base.">
          soit <span className="font-medium text-txt">{fmt(stats.data.opportunites_avec_dossier)}</span> parcelle{stats.data.opportunites_avec_dossier > 1 ? 's' : ''} avec
          dossier propriétaire ({fmt(stats.data.dossiers_opportunites)} propriétaire{stats.data.dossiers_opportunites > 1 ? 's' : ''} identifié{stats.data.dossiers_opportunites > 1 ? 's' : ''})
          {stats.data.opportunites_sans_identite > 0 && (
            <> · <span className="font-medium text-txt">{fmt(stats.data.opportunites_sans_identite)}</span> personnes
            physiques — non couvertes par l'open data</>
          )}
        </p>
      )}
      <div className="mt-2 flex h-1.5 shrink-0 overflow-hidden rounded-full bg-line">
        <span style={{ background: TIER_V2_META.brulante.color, width: `${(counts.brulante / promus) * 100}%` }} />
        <span style={{ background: TIER_V2_META.chaude.color, width: `${(counts.chaude / promus) * 100}%` }} />
        <span style={{ background: TIER_V2_META.reserve_fonciere.color, width: `${(counts.reserve_fonciere / promus) * 100}%` }} />
        <span style={{ background: TIER_V2_META.a_creuser.color, width: `${(counts.a_creuser / promus) * 100}%` }} />
      </div>
      <EntonnoirLine total={total} opportunites={opportunites} nFilters={nFilters} />

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
                  ? TIER_V2_META[filters.tiers[0]].label.toLowerCase()
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
        {shown.map((p) => <ResultCard key={p.idu} p={p} communeLabel={commune ?? ''} />)}
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
            title="Exporter la liste filtrée en CSV (tier v2, rang, ×N — mêmes filtres, même tri)">
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
