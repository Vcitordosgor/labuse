import { useQuery } from '@tanstack/react-query'
import { getResults, getStats } from '../../lib/api'
import { STATUT_META, completudeColor } from '../../lib/status'
import type { ParcelResult } from '../../lib/types'
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
        <circle
          cx="9" cy="9" r={r} fill="none" stroke={completudeColor(value)} strokeWidth="2"
          strokeDasharray={c} strokeDashoffset={c * (1 - value / 100)} strokeLinecap="round"
        />
      </svg>
      <span className="font-mono text-[10px] text-txt-dim">{value}</span>
    </span>
  )
}

function ResultCard({ p }: { p: ParcelResult }) {
  const { selectedIdu, select } = useApp()
  const meta = STATUT_META[p.status]
  const on = selectedIdu === p.idu
  return (
    <button
      onClick={() => select(p.idu)}
      className={`relative flex w-full items-center overflow-hidden rounded-[10px] border bg-surface-3 py-2.5 pl-4 pr-3 text-left ${
        on ? 'border-mint' : 'border-line-2 hover:border-[#2E5A45]'
      }`}
    >
      <span className="absolute left-0 top-0 h-full w-[3px]" style={{ background: meta.color }} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-medium text-txt-hi">{p.idu.slice(8, 10)} {p.idu.slice(10)}</span>
          {p.evenement === 'rouge' && (
            <span className="rounded-full bg-[#3a1614] px-1.5 py-0.5 text-[9px] font-medium text-st-ecartee" title="Événement — procédure BODACC ouverte">
              ● ÉVÉNEMENT
            </span>
          )}
        </div>
        <div className="truncate text-[11px] text-txt-mut">
          {p.surface_m2 ? `${fmt(p.surface_m2)} m²` : '—'} · {p.lieu_dit ?? p.commune}
        </div>
      </div>
      <div className="ml-2 flex flex-col items-end gap-1">
        <span className="font-display text-[15px] font-bold" style={{ color: meta.color }}>
          {p.q_score}
        </span>
        <CompletudeRing value={p.completeness_score} />
      </div>
    </button>
  )
}

export function ResultsSection() {
  const stats = useQuery({ queryKey: ['stats'], queryFn: getStats })
  const results = useQuery({ queryKey: ['results'], queryFn: getResults })

  const s = stats.data
  const chaude = s?.chaude ?? 0
  const surveiller = s?.a_surveiller ?? 0
  const creuser = s?.a_creuser ?? 0
  const shown = results.data?.length ?? 0
  const promus = chaude + surveiller + creuser || 1

  return (
    <div className="flex min-h-0 flex-1 flex-col px-5">
      <div className="flex items-baseline justify-between">
        <p className="font-mono text-[11px] tracking-widest text-txt-dim">RÉSULTATS</p>
        <span className="text-[11px] text-txt-mut">triés par score</span>
      </div>

      {/* Compteur d'en-tête : la matrice premium, PAS « 737 opportunités » */}
      <p className="mt-2 text-xs text-txt-mut">
        <span className="font-medium text-st-chaude">{fmt(chaude)}</span> chaudes ·{' '}
        <span className="font-medium text-st-surveiller">{fmt(surveiller)}</span> à surveiller ·{' '}
        <span className="font-medium text-st-creuser">{fmt(creuser)}</span> à creuser
      </p>
      <div className="mt-2 flex h-1.5 overflow-hidden rounded-full bg-line">
        <span className="bg-st-chaude" style={{ width: `${(chaude / promus) * 100}%` }} />
        <span className="bg-st-surveiller" style={{ width: `${(surveiller / promus) * 100}%` }} />
        <span className="bg-st-creuser" style={{ width: `${(creuser / promus) * 100}%` }} />
      </div>
      <p className="mt-2 text-[11px] text-txt-dim">
        sur {fmt(s?.total ?? 0)} parcelles — filtre dur actif
      </p>

      <div className="mt-3 flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto pb-2">
        {results.isLoading && <p className="text-xs text-txt-dim">Chargement…</p>}
        {results.data?.map((p) => <ResultCard key={p.idu} p={p} />)}
      </div>

      <div className="flex items-center justify-between border-t border-line py-3">
        <span className="text-[11px] text-txt-dim">{fmt(shown)} résultats</span>
        <button className="text-xs text-mint hover:underline">Tout voir →</button>
      </div>
    </div>
  )
}
