import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useRef, useState } from 'react'
import { csvExportUrl, getCommunes, getEntonnoir, getParcelsGeojson, getResults, getStats } from '../../lib/api'
import { hasScopeFilters, matchAll, matchScope, PROMUES, type ParcelProps } from '../../lib/filters'
import { roughCentroid } from '../../lib/geo'
import { BRULANTE_COLOR, completudeColor, STATUT_META, vBandColor } from '../../lib/status'
import type { Statut } from '../../lib/types'
import { useApp } from '../../store/useApp'

const fmt = (n: number) => n.toLocaleString('fr-FR')

// Badge V (Vendabilité) — pastille + valeur, style par bande, 🔥 pour Brûlante (chaude ∧ V≥seuil).
// V NULL (public/bailleur) → badge spécial « démarche dédiée » à la place du score.
const OWNER_BADGE: Record<string, { label: string; title: string }> = {
  public: { label: 'PUBLIC', title: 'Foncier public — démarche dédiée (V non applicable)' },
  bailleur: { label: 'BAILLEUR', title: 'Bailleur social — V non applicable' },
  copro: { label: 'COPRO', title: 'Copropriété — acquisition complexe (V calculé)' },
}

export function VBadge({ v, band, brulante }: { v: number | null | undefined; band: string | null | undefined; brulante?: boolean }) {
  if (v == null) return null
  const color = brulante ? BRULANTE_COLOR : vBandColor(band as never)
  return (
    <span className="inline-flex shrink-0 items-center gap-1 rounded-full px-1.5 py-0.5 font-mono text-[9px] font-semibold"
      style={{ background: `${color}1f`, color }}
      title={`Vendabilité V ${v}/100${brulante ? ' — 🔥 BRÛLANTE (chaude Q×A + signaux vendeur forts)' : ''} — signaux publics « raisons de vendre » (panneau fiche)`}>
      {brulante && <span aria-hidden>🔥</span>}
      V {v}
    </span>
  )
}

// Mini-anneau de complétude — exigence #1 : le score ne s'affiche JAMAIS seul.
function CompletudeRing({ value }: { value: number }) {
  const r = 7
  const c = 2 * Math.PI * r
  return (
    <span className="flex items-center gap-1" title={`Complétude ${value}%`}>
      <svg viewBox="0 0 18 18" className="h-[18px] w-[18px] -rotate-90">
        <circle cx="9" cy="9" r={r} fill="none" stroke="#1E2A23" strokeWidth="2" />
        <circle cx="9" cy="9" r={r} fill="none" stroke={completudeColor(value)} strokeWidth="2"
          strokeDasharray={c} strokeDashoffset={c * (1 - value / 100)} strokeLinecap="round" />
      </svg>
      <span className="font-mono text-[10px] text-txt-dim">{value}</span>
    </span>
  )
}

function ResultCard({ p, communeLabel }: { p: ParcelProps & { commune?: string }; communeLabel: string }) {
  const { selectedIdu, select } = useApp()
  const meta = STATUT_META[p.status]
  const on = selectedIdu === p.idu
  return (
    <button
      onClick={() => select(p.idu)}
      className={`relative flex w-full shrink-0 items-center overflow-hidden rounded-[10px] border bg-surface-3 py-2.5 pl-4 pr-3 text-left ${
        on ? 'border-mint' : 'border-line-2 hover:border-[#2E5A45]'}`}
    >
      <span className="absolute left-0 top-0 h-full w-[3px]" style={{ background: meta.color }} />
      <div className="min-w-0 flex-1">
        {/* FIX (rendu) : les badges DÉBORDAIENT sur le score/anneau à droite (chevauchement).
            La rangée passe en flex-wrap (min-w-0) et l'IDU reste sur UNE ligne (whitespace-nowrap) :
            « même proprio ×N » va à la ligne au lieu d'empiéter sur la colonne score. */}
        <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
          <span className="shrink-0 whitespace-nowrap font-mono text-xs font-medium text-txt-hi">{p.idu.slice(8, 10)} {p.idu.slice(10)}</span>
          {p.evenement === 'rouge' && (
            <span className="shrink-0 rounded-full bg-[#3a1614] px-1.5 py-0.5 text-[9px] font-medium text-st-ecartee"
              title={p.status === 'chaude' ? 'Chaude PAR ÉVÉNEMENT (procédure BODACC ouverte) — statut forcé, pas issu de la matrice Q×A' : 'Événement — procédure BODACC ouverte'}>
              {p.status === 'chaude' ? '● CHAUDE · ÉVÉNEMENT' : '● ÉVÉNEMENT'}
            </span>
          )}
          {(p.cluster ?? 0) > 1 && (
            <span className="shrink-0 rounded-full bg-[#1a2340] px-1.5 py-0.5 text-[9px] font-medium text-[#8FB4F0]"
              title={`Même propriétaire que ${(p.cluster ?? 0) - 1} autre(s) parcelle(s) chaude(s)${p.proprio ? ` — ${p.proprio}` : ''} : 1 dossier, pas ${p.cluster} lignes`}>
              même proprio ×{p.cluster}
            </span>
          )}
          {p.vue_mer === 'oui' && <span className="shrink-0 text-[10px] text-[#7DE8E0]" title="Vue mer dégagée">◠</span>}
          <VBadge v={p.v_score} band={p.v_band} brulante={p.brulante} />
          {p.owner_type && OWNER_BADGE[p.owner_type] && (
            <span className="shrink-0 rounded-full border border-line-2 px-1.5 py-0.5 text-[8.5px] font-medium text-txt-dim"
              title={OWNER_BADGE[p.owner_type].title}>
              {OWNER_BADGE[p.owner_type].label}
            </span>
          )}
        </div>
        <div className="truncate text-[11px] text-txt-mut">{p.surface_m2 ? `${fmt(p.surface_m2)} m²` : '—'} · {p.commune ?? communeLabel}</div>
      </div>
      <div className="ml-2 flex shrink-0 flex-col items-end gap-1">
        <span className="font-display text-[15px] font-bold leading-none" style={{ color: meta.color }}>{p.q_score}</span>
        <CompletudeRing value={p.completeness_score} />
      </div>
    </button>
  )
}

// Chips de statut — MULTI (cliquer = basculer l'appartenance) ; « Tout » vide la sélection.
function StatutChips({ counts, partial }: { counts: Record<Statut | 'all', number>; partial: boolean }) {
  const { filters, setFilter } = useApp()
  const items: { v: Statut | 'all'; label: string; color?: string }[] = [
    { v: 'all', label: 'Opportunités' },
    { v: 'chaude', label: 'Chaude', color: STATUT_META.chaude.color },
    { v: 'a_surveiller', label: 'À surveiller', color: STATUT_META.a_surveiller.color },
    { v: 'a_creuser', label: 'À creuser', color: STATUT_META.a_creuser.color },
    // C7 : les écartées en OPT-IN — activé, elles colorent la carte et entrent dans la liste
    { v: 'ecartee', label: 'Écartées', color: STATUT_META.ecartee.color },
  ]
  return (
    <div className="mt-2 flex shrink-0 flex-wrap gap-1.5" title={partial ? 'Comptes recalculés avec les filtres actifs' : 'Comptes exacts (SQL, base entière)'}>
      {items.map((it) => {
        const on = it.v === 'all' ? filters.statuts.length === 0 : filters.statuts.includes(it.v as Statut)
        return (
          <button
            key={it.v}
            onClick={() => {
              if (it.v === 'all') setFilter('statuts', [])
              else {
                const s = it.v as Statut
                setFilter('statuts', filters.statuts.includes(s) ? filters.statuts.filter((x) => x !== s) : [...filters.statuts, s])
              }
            }}
            className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] ${
              on ? 'border-mint bg-[#0F1A14] text-txt-hi' : 'border-line-2 text-txt-mut hover:text-txt'}`}
          >
            {it.color && <span className="h-1.5 w-1.5 rounded-full" style={{ background: it.color }} />}
            {it.label}
            <span className="font-mono text-[10px] text-txt-dim">{fmt(counts[it.v] ?? 0)}{partial ? '*' : ''}</span>
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
  const [openUp, setOpenUp] = useState(false)   // P9 : ouverture vers le HAUT si le bouton est bas
  const btnRef = useRef<HTMLButtonElement>(null)
  const commune = useApp((s) => s.commune)
  const q = useQuery({ queryKey: ['entonnoir', commune], queryFn: getEntonnoir, enabled: open })
  const toggle = () => {
    if (!open && btnRef.current) setOpenUp(btnRef.current.getBoundingClientRect().top > window.innerHeight * 0.45)
    setOpen((o) => !o)
  }
  // fermeture au clavier (Échap) — cohérent avec les autres surfaces flottantes
  useEffect(() => {
    if (!open) return
    const h = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [open])
  return (
    <div className="relative mt-2 shrink-0">
      <p className="text-[11px] text-txt-dim">
        <span className="text-txt">{fmt(total)}</span> parcelles analysées → <span className="font-medium text-mint">{fmt(opportunites)}</span> opportunités détectées{nFilters > 0 && ' · filtres appliqués'}
        <button ref={btnRef} data-entonnoir-btn onClick={toggle}
          className="ml-1.5 text-mint hover:underline" title="L'entonnoir par motif — pourquoi le reste est écarté (SQL-exact)">
          pourquoi ? {openUp && open ? '▴' : '▾'}
        </button>
      </p>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          {/* P9 (dernière passe) : popover BORNÉ + scroll interne + ouverture direction-aware
              (vers le haut si le bouton est bas) — plus jamais coupé par le bord de l'écran. */}
          <div data-entonnoir-popover className={`absolute left-0 z-20 flex max-h-[52vh] w-[300px] flex-col rounded-xl border border-line-2 bg-surface-2 p-3 shadow-2xl ${openUp ? 'bottom-full mb-1' : 'top-6'}`}>
            <p className="shrink-0 text-[11px] leading-snug text-txt">
              LABUSE a analysé <b>{fmt(q.data?.analysees ?? total)}</b> parcelles ; son avis retient
              <b className="text-mint"> {fmt(q.data?.opportunites ?? opportunites)}</b> opportunités.
              Le reste reste visible et cliquable — voici pourquoi il est écarté.
            </p>
            <p className="mt-1.5 shrink-0 font-mono text-[9.5px] tracking-widest text-txt-dim">LE RESTE, PAR MOTIF</p>
            {q.isLoading && <p className="mt-1 text-[10px] text-txt-dim">Chargement…</p>}
            <div className="mt-1 flex min-h-0 flex-1 flex-col gap-0.5 overflow-y-auto">
              {(q.data?.motifs ?? []).map((m) => (
                <div key={m.motif} className={`flex shrink-0 justify-between gap-2 text-[10.5px] ${m.motif.startsWith('écartées') ? 'font-medium text-txt border-b border-line pb-0.5 mb-0.5' : 'text-txt-mut'}`}>
                  <span className="min-w-0">{m.motif}</span>
                  <span className="shrink-0 font-mono">{fmt(m.n)}</span>
                </div>
              ))}
            </div>
            {q.data && <p className="mt-1.5 shrink-0 text-[9px] leading-snug text-txt-dim">{q.data.note}</p>}
          </div>
        </>
      )}
    </div>
  )
}

const CAP = 200

export function ResultsSection() {
  const { filters, query, zone, resetFilters, commune, setFilter } = useApp()
  const ile = commune == null   // mode « Toute l'île » : liste + compteurs servis en SQL
  const [showAll, setShowAll] = useState(false)
  // Tri par défaut de la vue chaudes : V DÉCROISSANT (Score V, Phase 4 §4) — débrayable.
  const [sortV, setSortV] = useState(true)
  // compteurs par statut sous filtres de PÉRIMÈTRE (jamais le filtre statut lui-même)
  const scopeOnly = useMemo(() => ({ ...filters, statuts: [] as Statut[] }), [filters])
  const stats = useQuery({
    queryKey: ['stats', commune, ile ? scopeOnly : null],
    queryFn: () => getStats(ile ? scopeOnly : undefined),
  })
  const geo = useQuery({ queryKey: ['geojson', commune], queryFn: getParcelsGeojson, enabled: !ile })
  const serverList = useQuery({
    queryKey: ['results', commune, filters, sortV],
    queryFn: () => getResults(filters, 500, sortV),
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
      const s = stats.data
      return { all: s.chaude + s.a_surveiller + s.a_creuser, chaude: s.chaude, a_surveiller: s.a_surveiller, a_creuser: s.a_creuser, ecartee: s.ecartee, exclue: 0 }
    }
    const c: Record<Statut | 'all', number> = { all: 0, chaude: 0, a_surveiller: 0, a_creuser: 0, ecartee: 0, exclue: 0 }
    for (const p of props) {
      if (!matchScope(p, filters, zone)) continue
      if (PROMUES.includes(p.status)) c.all += 1
      c[p.status] = (c[p.status] ?? 0) + 1
    }
    return c
  }, [props, filters, zone, scoped, ile, stats.data])

  const list = useMemo(() => {
    if (ile) {
      // serveur : déjà filtré (chips) et trié (événement d'abord, puis score)
      return ((serverList.data ?? []) as unknown as (ParcelProps & { commune?: string })[])
        .filter((p) => !qNorm || p.idu.toUpperCase().includes(qNorm) || p.idu.slice(8).toUpperCase().includes(qNorm))
    }
    return props
      .filter((p) => matchAll(p, filters, zone)
        && (PROMUES.includes(p.status) || filters.statuts.includes(p.status)))
      .filter((p) => !qNorm || p.idu.toUpperCase().includes(qNorm) || p.idu.slice(8).toUpperCase().includes(qNorm))
      .sort((a, b) => {
        // Score V : tri par défaut V décroissant (NULL en queue) — débrayable vers le tri métier.
        if (sortV) {
          const dv = (b.v_score ?? -1) - (a.v_score ?? -1)
          if (dv !== 0) return dv
        }
        // métier : l'ÉVÉNEMENT crée l'urgence de la semaine → toujours en tête, puis le score
        const ev = Number(b.evenement === 'rouge') - Number(a.evenement === 'rouge')
        return ev !== 0 ? ev : b.q_score + b.a_score - (a.q_score + a.a_score)
      })
  }, [ile, serverList.data, props, filters, zone, qNorm, sortV])
  const shown = showAll ? list : list.slice(0, CAP)

  const loading = ile ? serverList.isLoading : geo.isLoading
  const error = ile ? serverList.isError : geo.isError
  const refetch = () => (ile ? serverList.refetch() : geo.refetch())
  const total = stats.data?.total ?? props.length

  // bandeau honnête par commune (ex. Saint-Philippe = RNU) — porté par /communes
  const communesQ = useQuery({ queryKey: ['communes'], queryFn: getCommunes })
  const communeNote = commune ? communesQ.data?.find((c) => c.commune === commune)?.note : null
  const promus = counts.all || 1
  const nFilters = (filters.statuts.length ? 1 : 0) + (scoped ? 1 : 0)

  return (
    // FIX (rendu liste) : la section elle-même défile si le volet est court (laptop) — sinon
    // l'en-tête fixe (compteurs/chips) écrasait la liste (flex-1) à ~0 px. La liste garde une
    // hauteur minimale utilisable ET son scroll interne (cf. le conteneur data-results-scroll).
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-5">
      <div className="flex shrink-0 items-baseline justify-between">
        <p className="font-mono text-[11px] tracking-widest text-txt-dim">RÉSULTATS</p>
        <button onClick={() => setSortV((v) => !v)} className="text-[11px] text-txt-mut hover:text-txt"
          title="Basculer le tri : Vendabilité (V) décroissante ↔ score Q+A">
          triés par {sortV ? 'V (vendabilité) ▾' : 'score'}
        </button>
      </div>

      {communeNote && (
        <div className="mt-2 shrink-0 rounded-lg border border-st-creuser/40 bg-[#211a10] px-3 py-2 text-[10.5px] leading-snug text-st-creuser">
          ⚠ {communeNote}
        </div>
      )}
      <p className="mt-2 shrink-0 text-xs text-txt-mut"
        title={stats.data?.chaude_evenement != null ? `${fmt(stats.data.chaude)} chaudes dont ${fmt(stats.data.chaude_evenement)} par événement BODACC (bascule doctrinale)` : undefined}>
        <span className="font-medium text-st-chaude">{fmt(counts.chaude)}</span> chaudes ·{' '}
        <span className="font-medium text-st-surveiller">{fmt(counts.a_surveiller)}</span> à surveiller ·{' '}
        <span className="font-medium text-st-creuser">{fmt(counts.a_creuser)}</span> à creuser
        {scoped && <span className="text-txt-dim"> {zone ? '(dans la zone)' : '(filtres actifs)'}</span>}
      </p>
      {(stats.data?.brulantes ?? 0) > 0 && (
        <button onClick={() => setFilter('brulantes', !filters.brulantes)}
          className={`mt-1 flex w-fit shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] ${
            filters.brulantes ? 'border-[#FF6B35] text-[#FF8A50]' : 'border-line-2 text-txt-mut hover:text-txt'}`}
          title="Brûlantes 🔥 = chaudes de la matrice Q×A DONT le propriétaire cumule des signaux publics de vente (V ≥ 50) — cliquer pour filtrer">
          <span aria-hidden>🔥</span>
          <span className="font-medium" style={{ color: '#FF8A50' }}>{fmt(stats.data?.brulantes ?? 0)}</span> brûlantes
        </button>
      )}
      {stats.data?.dossiers_chaudes != null && (stats.data.chaude > 0) && (
        <p className="mt-1 shrink-0 text-[11px] text-txt-dim" title="La vraie unité de prospection : un propriétaire = un dossier, quel que soit son nombre de parcelles. Identification par SIREN (personnes morales) — les personnes physiques n'ont pas d'identité en base (doctrine).">
          soit <span className="font-medium text-txt">{fmt(stats.data.dossiers_chaudes)}</span> dossier{stats.data.dossiers_chaudes > 1 ? 's' : ''} propriétaire identifié{stats.data.dossiers_chaudes > 1 ? 's' : ''}
          {(stats.data.chaudes_sans_identite ?? 0) > 0 && <> (+{fmt(stats.data.chaudes_sans_identite ?? 0)} parcelle{(stats.data.chaudes_sans_identite ?? 0) > 1 ? 's' : ''} sans identité)</>}
        </p>
      )}
      <div className="mt-2 flex h-1.5 shrink-0 overflow-hidden rounded-full bg-line">
        <span className="bg-st-chaude" style={{ width: `${(counts.chaude / promus) * 100}%` }} />
        <span className="bg-st-surveiller" style={{ width: `${(counts.a_surveiller / promus) * 100}%` }} />
        <span className="bg-st-creuser" style={{ width: `${(counts.a_creuser / promus) * 100}%` }} />
      </div>
      <EntonnoirLine total={total} opportunites={counts.all} nFilters={nFilters} />

      <StatutChips counts={counts} partial={scoped} />

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
          <div className="rounded-lg border border-dashed border-line-2 p-4 text-center">
            <p className="text-xs text-txt-mut">Aucun résultat pour ces filtres.</p>
            <button onClick={resetFilters} className="mt-2 text-xs text-mint hover:underline">Réinitialiser les filtres</button>
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
          <a href={csvExportUrl(filters, sortV)} download
            className="text-[11px] text-txt-mut hover:text-mint"
            title="Exporter la liste filtrée en CSV (colonnes v_score, v_band, top_signaux incluses)">
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
