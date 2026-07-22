import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { csvExportUrl, getCommunes, getEntonnoir, getParcelsGeojson, getResults, getStats, type SortKey } from '../../lib/api'
import { hasScopeFilters, matchAll, matchScope, type ParcelProps } from '../../lib/filters'
import { roughCentroid } from '../../lib/geo'
import { completudeColor, effectiveTier, TIER_V2_META, verdictMeta, type TierV2 } from '../../lib/status'
import { Tip } from '../Tip'
import { EmptyState } from '../States'
import { useApp } from '../../store/useApp'

const fmt = (n: number) => n.toLocaleString('fr-FR')

// M5.1 : le badge « V nn » a disparu de la liste (le dossier propriétaire reste dans la
// fiche) ; les badges secondaires conservés : même proprio ×N, événement daté, veille
// succession, propriétaire spécial.
const OWNER_BADGE: Record<string, { label: string; title: string }> = {
  public: { label: 'PUBLIC', title: 'Foncier public — démarche dédiée' },
  bailleur: { label: 'BAILLEUR', title: 'Bailleur social — démarche dédiée' },
  copro: { label: 'COPRO', title: 'Copropriété — acquisition complexe (hors classement foncier)' },
}

// Mini-anneau de complétude — exigence #1 : le score ne s'affiche JAMAIS seul.
function CompletudeRing({ value }: { value: number }) {
  const r = 7
  const c = 2 * Math.PI * r
  return (
    <Tip tip={`Complétude des données : ${value}/100 — part des sources disponibles pour cette parcelle. N'est PAS une note de qualité du terrain.`}
      className="items-center gap-1">
      <svg viewBox="0 0 18 18" className="h-[18px] w-[18px] -rotate-90">
        <circle cx="9" cy="9" r={r} fill="none" stroke="#1E2A23" strokeWidth="2" />
        <circle cx="9" cy="9" r={r} fill="none" stroke={completudeColor(value)} strokeWidth="2"
          strokeDasharray={c} strokeDashoffset={c * (1 - value / 100)} strokeLinecap="round" />
      </svg>
      <span className="font-mono text-[11px] text-txt-dim tnum">{value}</span>
    </Tip>
  )
}

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
            <span className="shrink-0 rounded-full bg-[#2a2138] px-1.5 py-0.5 text-[9px] font-medium text-[#B497F0]"
              title="Veille succession — radar patrimonial (signal d'état, pas un événement daté)">
              veille succession
            </span>
          )}
          {p.owner_type && OWNER_BADGE[p.owner_type] && (
            <span className="shrink-0 rounded-full border border-line-2 px-1.5 py-0.5 text-[8.5px] font-medium text-txt-dim"
              title={OWNER_BADGE[p.owner_type].title}>
              {OWNER_BADGE[p.owner_type].label}
            </span>
          )}
        </div>
        {/* M6 2a (§1.8) : adresse postale BAN sur la carte de résultat — jamais un vide */}
        <div data-card-adresse className={`truncate text-[10.5px] text-txt-dim ${p.adresse ? '' : 'opacity-60'}`}>
          {p.adresse ?? 'Adresse non disponible'}
        </div>
        <div className="truncate text-[11px] text-txt-mut">{p.surface_m2 ? `${fmt(p.surface_m2)} m²` : '—'} · {p.commune ?? communeLabel}</div>
      </div>
      <div className="ml-2 flex shrink-0 flex-col items-end gap-1">
        {/* ×N = l'affichage produit du scoring v2 (probabilité relative de mutation) */}
        <Tip tip={p.mult_v2 != null ? `Multiplicateur de rang — cette parcelle est classée ${p.mult_v2.toFixed(1)} fois au-dessus de la moyenne de l'univers analysé.` : 'Scoring v2 non disponible'}>
          <span data-mult-tip className="font-display text-[15px] font-bold leading-none tnum" style={{ color: meta.color }}>
            {p.mult_v2 != null ? `×${p.mult_v2.toFixed(1)}` : '—'}
          </span>
        </Tip>
        <CompletudeRing value={p.completeness_score} />
      </div>
    </button>
  )
}

// Chips de tier v2 — MULTI (cliquer = basculer l'appartenance) ; « Tout » vide la sélection
// (périmètre par défaut = univers v2 hors étage 0 servi). « Écartées » (opt-in) = étage 0 dur.
function TierChips({ counts, partial }: { counts: Record<TierV2 | 'all', number>; partial: boolean }) {
  const { filters, setFilter } = useApp()
  const items: { v: TierV2 | 'all'; label: string; color?: string }[] = [
    { v: 'all', label: 'Tout' },
    { v: 'brulante', label: 'Brûlantes v2', color: TIER_V2_META.brulante.color },
    { v: 'chaude', label: 'Chaudes v2', color: TIER_V2_META.chaude.color },
    { v: 'reserve_fonciere', label: 'Réserve foncière', color: TIER_V2_META.reserve_fonciere.color },
    { v: 'a_creuser', label: 'À creuser', color: TIER_V2_META.a_creuser.color },
    // opt-in : les exclusions dures de l'étage 0 (run servi) — motifs dans l'entonnoir
    { v: 'ecartee', label: 'Écartées', color: TIER_V2_META.ecartee.color },
  ]
  return (
    <div className="mt-2 flex shrink-0 flex-wrap gap-1.5" title={partial ? 'Comptes recalculés avec les filtres actifs' : 'Comptes exacts (SQL, base entière)'}>
      {items.map((it) => {
        const on = it.v === 'all' ? filters.tiers.length === 0 : filters.tiers.includes(it.v as TierV2)
        return (
          <button
            key={it.v}
            onClick={() => {
              if (it.v === 'all') setFilter('tiers', [])
              else {
                const t = it.v as TierV2
                setFilter('tiers', filters.tiers.includes(t) ? filters.tiers.filter((x) => x !== t) : [...filters.tiers, t])
              }
            }}
            className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] ${
              on ? 'border-mint bg-[#0F1A14] text-txt-hi' : 'border-line-2 text-txt-mut hover:text-txt'}`}
          >
            {it.color && <span className="h-1.5 w-1.5 rounded-full" style={{ background: it.color }} />}
            {it.label}
            <span className="font-mono text-[11px] text-txt-dim">{fmt(counts[it.v] ?? 0)}{partial ? '*' : ''}</span>
          </button>
        )
      })}
    </div>
  )
}

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
        <div data-entonnoir-panel className="mt-1.5 rounded-xl border border-line-2 bg-surface-2 p-3">
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
          <p className="mt-1.5 font-mono text-[9.5px] tracking-widest text-txt-dim">LE RESTE, PAR MOTIF</p>
          {q.isLoading && <p className="mt-1 text-[11px] text-txt-dim">Chargement…</p>}
          {q.data && (q.data.motifs ?? []).length === 0 && (
            <p className="mt-1 text-[10.5px] text-txt-dim">Détail par motif non disponible sur ce périmètre.</p>
          )}
          <div className="mt-1 flex flex-col gap-0.5">
            {(q.data?.motifs ?? []).map((m) => (
              <div key={m.motif} className={`flex justify-between gap-2 text-[10.5px] ${m.motif.startsWith('écartées') ? 'font-medium text-txt border-b border-line pb-0.5 mb-0.5' : 'text-txt-mut'}`}>
                <span className="min-w-0">{m.motif}</span>
                <span className="shrink-0 font-mono">{fmt(m.n)}</span>
              </div>
            ))}
          </div>
          {q.data && <p className="mt-1.5 text-[9px] leading-snug text-txt-dim">{q.data.note}</p>}
        </div>
      )}
    </div>
  )
}

const CAP = 200

//: tris (M5.1 lot 1.3) — rang P par défaut ; le tri par V a disparu du sélecteur.
const SORTS: { key: SortKey; label: string }[] = [
  { key: 'rang', label: 'rang P' },
  { key: 'mult', label: '×N' },
  { key: 'surface', label: 'surface' },
  { key: 'commune', label: 'commune' },
]

const TIER_ZERO: Record<TierV2 | 'all', number> = {
  all: 0, brulante: 0, chaude: 0, reserve_fonciere: 0, a_creuser: 0, ecartee: 0,
}

export function ResultsSection() {
  const { filters, query, zone, resetFilters, commune, setCommune, setFilter } = useApp()
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
  const serverList = useQuery({
    queryKey: ['results', commune, filters, sort],
    queryFn: () => getResults(filters, 500, sort),
    enabled: ile,
  })

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
      // serveur : déjà filtré (chips) et trié (rang P par défaut)
      return ((serverList.data ?? []) as unknown as (ParcelProps & { commune?: string })[])
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
  }, [ile, serverList.data, props, filters, zone, qNorm, sort])
  const shown = showAll ? list : list.slice(0, CAP)

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
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-5">
      {/* Fix cosmétique (point 3) : ligne de tri LISIBLE et alignée (contrôle segmenté), au lieu
          des options qui flottaient collées à droite sans hiérarchie. Fonction inchangée. */}
      <div className="shrink-0">
        <p className="font-mono text-[11px] tracking-widest text-txt-dim">RÉSULTATS</p>
        <div className="mt-1.5 flex items-center gap-2">
          <span className="shrink-0 text-[10px] uppercase tracking-wide text-txt-dim">Trier</span>
          <div className="flex items-center gap-0.5 rounded-full border border-line-2 bg-surface-2 p-0.5">
            {SORTS.map((s) => (
              <button key={s.key} data-sort={s.key} onClick={() => setSort(s.key)}
                className={`rounded-full px-2 py-0.5 text-[11px] transition-colors ${sort === s.key ? 'bg-mint/15 font-medium text-mint' : 'text-txt-mut hover:text-txt'}`}
                title={s.key === 'rang' ? 'Rang P (scoring v2) — copropriétés en queue' : `Trier par ${s.label}`}>
                {s.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {communeNote && (
        <div className="mt-2 shrink-0 rounded-lg border border-st-creuser/40 bg-[#211a10] px-3 py-2 text-[10.5px] leading-snug text-st-creuser">
          ⚠ {communeNote}
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

      <TierChips counts={counts} partial={scoped} />

      {/* toggle copro (M5.1 lot 1.5) — les copropriétés restent visibles par défaut (badge COPRO) */}
      <label className="mt-1.5 flex w-fit shrink-0 cursor-pointer items-center gap-1.5 text-[11px] text-txt-mut hover:text-txt"
        title="Les copropriétés sont hors classement foncier (rang) mais restent dans l'univers — cocher pour les masquer">
        <input data-toggle-copro type="checkbox" checked={filters.horsCopro}
          onChange={(e) => setFilter('horsCopro', e.target.checked)} className="h-3 w-3" />
        masquer les copropriétés
      </label>

      <div data-results-scroll className="mt-3 flex min-h-[200px] flex-1 flex-col gap-2 overflow-y-auto pb-2">
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
          {fmt(shown.length)} visibles ici{list.length > shown.length ? ` / ${fmt(list.length)}` : ''}
          {ile && (serverList.data?.length ?? 0) >= 500 && ' · 500 premiers (île) — affinez les filtres'}
        </span>
        <span className="flex shrink-0 items-center gap-2">
          <a href={csvExportUrl(filters, sort)} download
            className="text-[11px] text-txt-mut hover:text-mint"
            title="Exporter la liste filtrée en CSV (tier v2, rang, ×N — mêmes filtres, même tri)">
            ⬇ CSV
          </a>
          {list.length > CAP && (
            <button onClick={() => setShowAll((v) => !v)} className="text-xs text-mint hover:underline">
              {showAll ? 'Réduire' : 'Tout voir →'}
            </button>
          )}
        </span>
      </div>
    </div>
  )
}
