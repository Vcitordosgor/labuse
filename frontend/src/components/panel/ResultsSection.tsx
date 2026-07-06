import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { COMMUNE, getParcelsGeojson, getStats } from '../../lib/api'
import { activeChips, matchAll, matchScope, PROMUES, type ParcelProps } from '../../lib/filters'
import { completudeColor, STATUT_META } from '../../lib/status'
import type { Statut } from '../../lib/types'
import { useApp } from '../../store/useApp'

const fmt = (n: number) => n.toLocaleString('fr-FR')

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

function ResultCard({ p }: { p: ParcelProps }) {
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
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-medium text-txt-hi">{p.idu.slice(8, 10)} {p.idu.slice(10)}</span>
          {p.evenement === 'rouge' && (
            <span className="shrink-0 rounded-full bg-[#3a1614] px-1.5 py-0.5 text-[9px] font-medium text-st-ecartee" title="Événement — procédure BODACC ouverte">
              ● ÉVÉNEMENT
            </span>
          )}
        </div>
        <div className="truncate text-[11px] text-txt-mut">{p.surface_m2 ? `${fmt(p.surface_m2)} m²` : '—'} · {COMMUNE}</div>
      </div>
      <div className="ml-2 flex shrink-0 flex-col items-end gap-1">
        <span className="font-display text-[15px] font-bold leading-none" style={{ color: meta.color }}>{p.q_score}</span>
        <CompletudeRing value={p.completeness_score} />
      </div>
    </button>
  )
}

function StatutChips({ counts, partial }: { counts: Record<Statut | 'all', number>; partial: boolean }) {
  const { filters, setFilter } = useApp()
  const items: { v: Statut | 'all'; label: string; color?: string }[] = [
    { v: 'all', label: 'Tout' },
    { v: 'chaude', label: 'Chaude', color: STATUT_META.chaude.color },
    { v: 'a_surveiller', label: 'À surveiller', color: STATUT_META.a_surveiller.color },
    { v: 'a_creuser', label: 'À creuser', color: STATUT_META.a_creuser.color },
  ]
  return (
    <div className="mt-2 flex shrink-0 flex-wrap gap-1.5" title={partial ? 'Comptes recalculés avec les filtres actifs' : 'Comptes exacts (base)'}>
      {items.map((it) => {
        const on = filters.statut === it.v
        return (
          <button key={it.v} onClick={() => setFilter('statut', it.v)}
            className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] ${
              on ? 'border-mint bg-[#0F1A14] text-txt-hi' : 'border-line-2 text-txt-mut hover:text-txt'}`}>
            {it.color && <span className="h-1.5 w-1.5 rounded-full" style={{ background: it.color }} />}
            {it.label}
            <span className="font-mono text-[10px] text-txt-dim">{fmt(counts[it.v] ?? 0)}{partial ? '*' : ''}</span>
          </button>
        )
      })}
    </div>
  )
}

const CAP = 200

export function ResultsSection() {
  const { filters, query } = useApp()
  const [showAll, setShowAll] = useState(false)
  const stats = useQuery({ queryKey: ['stats'], queryFn: getStats })
  const geo = useQuery({ queryKey: ['geojson'], queryFn: getParcelsGeojson })

  const props = useMemo(
    () => (geo.data?.features.map((f) => f.properties as unknown as ParcelProps) ?? []),
    [geo.data],
  )

  const hasScope = filters.scoreMin != null || filters.surfaceMin != null
  const qNorm = query.trim().toUpperCase().replace(/\s+/g, '')

  // Compteurs : SANS filtre → /stats (SQL-exact). AVEC filtre score/surface → recalcul client, marqué *.
  const counts = useMemo(() => {
    if (!hasScope && stats.data) {
      const s = stats.data
      return { all: s.chaude + s.a_surveiller + s.a_creuser, chaude: s.chaude, a_surveiller: s.a_surveiller, a_creuser: s.a_creuser, ecartee: s.ecartee, exclue: 0 }
    }
    const c: Record<Statut | 'all', number> = { all: 0, chaude: 0, a_surveiller: 0, a_creuser: 0, ecartee: 0, exclue: 0 }
    for (const p of props) {
      if (!matchScope(p, filters)) continue
      if (PROMUES.includes(p.status)) c.all += 1
      c[p.status] = (c[p.status] ?? 0) + 1
    }
    return c
  }, [props, filters, hasScope, stats.data])

  // Liste : filtre complet + recherche omnibox (IDU / section+numéro), promues, triées par score.
  const list = useMemo(
    () => props
      .filter((p) => matchAll(p, filters) && PROMUES.includes(p.status))
      .filter((p) => !qNorm || p.idu.toUpperCase().includes(qNorm) || p.idu.slice(8).toUpperCase().includes(qNorm))
      .sort((a, b) => b.q_score + b.a_score - (a.q_score + a.a_score)),
    [props, filters, qNorm],
  )
  const shown = showAll ? list : list.slice(0, CAP)

  const total = stats.data?.total ?? props.length
  const promus = counts.all || 1
  const chips = activeChips(filters)

  return (
    <div className="flex min-h-0 flex-1 flex-col px-5">
      <div className="flex shrink-0 items-baseline justify-between">
        <p className="font-mono text-[11px] tracking-widest text-txt-dim">RÉSULTATS</p>
        <span className="text-[11px] text-txt-mut">triés par score</span>
      </div>

      <p className="mt-2 shrink-0 text-xs text-txt-mut">
        <span className="font-medium text-st-chaude">{fmt(counts.chaude)}</span> chaudes ·{' '}
        <span className="font-medium text-st-surveiller">{fmt(counts.a_surveiller)}</span> à surveiller ·{' '}
        <span className="font-medium text-st-creuser">{fmt(counts.a_creuser)}</span> à creuser
        {hasScope && <span className="text-txt-dim"> (filtres actifs)</span>}
      </p>
      <div className="mt-2 flex h-1.5 shrink-0 overflow-hidden rounded-full bg-line">
        <span className="bg-st-chaude" style={{ width: `${(counts.chaude / promus) * 100}%` }} />
        <span className="bg-st-surveiller" style={{ width: `${(counts.a_surveiller / promus) * 100}%` }} />
        <span className="bg-st-creuser" style={{ width: `${(counts.a_creuser / promus) * 100}%` }} />
      </div>
      <p className="mt-2 shrink-0 text-[11px] text-txt-dim">
        sur {fmt(total)} parcelles — filtre dur actif{chips.length > 0 && ` · ${chips.length} filtre${chips.length > 1 ? 's' : ''}`}
      </p>

      <StatutChips counts={counts} partial={hasScope} />

      <div className="mt-3 flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto pb-2">
        {geo.isLoading && <p className="text-xs text-txt-dim">Chargement…</p>}
        {geo.isError && <p className="text-xs text-st-ecartee">Erreur de chargement — serveur à relancer ?</p>}
        {!geo.isLoading && shown.length === 0 && <p className="text-xs text-txt-dim">Aucun résultat pour ces filtres.</p>}
        {shown.map((p) => <ResultCard key={p.idu} p={p} />)}
      </div>

      <div className="flex shrink-0 items-center justify-between border-t border-line py-3">
        <span className="text-[11px] text-txt-dim">
          {fmt(shown.length)} visibles ici{list.length > shown.length ? ` / ${fmt(list.length)}` : ''}
        </span>
        {list.length > CAP && (
          <button onClick={() => setShowAll((v) => !v)} className="text-xs text-mint hover:underline">
            {showAll ? 'Réduire' : 'Tout voir →'}
          </button>
        )}
      </div>
    </div>
  )
}
