import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { COMMUNE, getParcelsGeojson } from '../../lib/api'
import { activeChips, matchAll, matchScope, PROMUES, type ParcelProps } from '../../lib/filters'
import { completudeColor, STATUT_META } from '../../lib/status'
import type { Statut } from '../../lib/types'
import { useApp } from '../../store/useApp'

const fmt = (n: number) => n.toLocaleString('fr-FR')

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
    <button onClick={() => select(p.idu)}
      className={`relative flex w-full items-center overflow-hidden rounded-[10px] border bg-surface-3 py-2.5 pl-4 pr-3 text-left ${
        on ? 'border-mint' : 'border-line-2 hover:border-[#2E5A45]'}`}>
      <span className="absolute left-0 top-0 h-full w-[3px]" style={{ background: meta.color }} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-medium text-txt-hi">{p.idu.slice(8, 10)} {p.idu.slice(10)}</span>
          {p.evenement === 'rouge' && (
            <span className="rounded-full bg-[#3a1614] px-1.5 py-0.5 text-[9px] font-medium text-st-ecartee" title="Événement — procédure BODACC ouverte">● ÉVÉNEMENT</span>
          )}
        </div>
        <div className="truncate text-[11px] text-txt-mut">{p.surface_m2 ? `${fmt(p.surface_m2)} m²` : '—'} · {COMMUNE}</div>
      </div>
      <div className="ml-2 flex flex-col items-end gap-1">
        <span className="font-display text-[15px] font-bold" style={{ color: meta.color }}>{p.q_score}</span>
        <CompletudeRing value={p.completeness_score} />
      </div>
    </button>
  )
}

// Chips de statut du panneau — filtrent carte ET liste (via le store partagé).
function StatutChips({ counts }: { counts: Record<Statut | 'all', number> }) {
  const { filters, setFilter } = useApp()
  const items: { v: Statut | 'all'; label: string; color?: string }[] = [
    { v: 'all', label: 'Tout' },
    { v: 'chaude', label: 'Chaude', color: STATUT_META.chaude.color },
    { v: 'a_surveiller', label: 'À surveiller', color: STATUT_META.a_surveiller.color },
    { v: 'a_creuser', label: 'À creuser', color: STATUT_META.a_creuser.color },
  ]
  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {items.map((it) => {
        const on = filters.statut === it.v
        return (
          <button key={it.v} onClick={() => setFilter('statut', it.v)}
            className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] ${
              on ? 'border-mint bg-[#0F1A14] text-txt-hi' : 'border-line-2 text-txt-mut hover:text-txt'}`}>
            {it.color && <span className="h-1.5 w-1.5 rounded-full" style={{ background: it.color }} />}
            {it.label}
            <span className="font-mono text-[10px] text-txt-dim">{fmt(counts[it.v] ?? 0)}</span>
          </button>
        )
      })}
    </div>
  )
}

export function ResultsSection() {
  const { filters } = useApp()
  const geo = useQuery({ queryKey: ['geojson'], queryFn: getParcelsGeojson })

  const props = useMemo(
    () => (geo.data?.features.map((f) => f.properties as unknown as ParcelProps) ?? []),
    [geo.data],
  )

  // Compteurs = features matchant SCORE+SURFACE (indépendant du statut) → le breakdown reste lisible.
  const counts = useMemo(() => {
    const c: Record<Statut | 'all', number> = { all: 0, chaude: 0, a_surveiller: 0, a_creuser: 0, ecartee: 0, exclue: 0 }
    for (const p of props) {
      if (!matchScope(p, filters)) continue
      if (PROMUES.includes(p.status)) c.all += 1
      c[p.status] = (c[p.status] ?? 0) + 1
    }
    return c
  }, [props, filters])

  // Liste = filtre COMPLET (statut inclus), promues, triées par score.
  const list = useMemo(
    () => props.filter((p) => matchAll(p, filters) && PROMUES.includes(p.status))
      .sort((a, b) => b.q_score + b.a_score - (a.q_score + a.a_score)).slice(0, 500),
    [props, filters],
  )

  const total = props.length
  const promus = counts.all || 1
  const chips = activeChips(filters)

  return (
    <div className="flex min-h-0 flex-1 flex-col px-5">
      <div className="flex items-baseline justify-between">
        <p className="font-mono text-[11px] tracking-widest text-txt-dim">RÉSULTATS</p>
        <span className="text-[11px] text-txt-mut">triés par score</span>
      </div>

      <p className="mt-2 text-xs text-txt-mut">
        <span className="font-medium text-st-chaude">{fmt(counts.chaude)}</span> chaudes ·{' '}
        <span className="font-medium text-st-surveiller">{fmt(counts.a_surveiller)}</span> à surveiller ·{' '}
        <span className="font-medium text-st-creuser">{fmt(counts.a_creuser)}</span> à creuser
      </p>
      <div className="mt-2 flex h-1.5 overflow-hidden rounded-full bg-line">
        <span className="bg-st-chaude" style={{ width: `${(counts.chaude / promus) * 100}%` }} />
        <span className="bg-st-surveiller" style={{ width: `${(counts.a_surveiller / promus) * 100}%` }} />
        <span className="bg-st-creuser" style={{ width: `${(counts.a_creuser / promus) * 100}%` }} />
      </div>
      <p className="mt-2 text-[11px] text-txt-dim">
        sur {fmt(total)} parcelles — filtre dur actif
        {chips.length > 0 && ` · ${chips.length} filtre${chips.length > 1 ? 's' : ''}`}
      </p>

      <StatutChips counts={counts} />

      <div className="mt-3 flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto pb-2">
        {geo.isLoading && <p className="text-xs text-txt-dim">Chargement…</p>}
        {!geo.isLoading && list.length === 0 && <p className="text-xs text-txt-dim">Aucun résultat pour ces filtres.</p>}
        {list.map((p) => <ResultCard key={p.idu} p={p} />)}
      </div>

      <div className="flex items-center justify-between border-t border-line py-3">
        <span className="text-[11px] text-txt-dim">{fmt(list.length)} résultats</span>
        <button className="text-xs text-mint hover:underline">Tout voir →</button>
      </div>
    </div>
  )
}
