import { useQuery } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { getParcelsGeojson } from '../../lib/api'
import { activeChips } from '../../lib/filters'
import { STATUT_META } from '../../lib/status'
import type { Statut } from '../../lib/types'
import { useApp } from '../../store/useApp'

function Omnibox() {
  const { query, setQuery, select, setView } = useApp()
  const ref = useRef<HTMLInputElement>(null)
  const geo = useQuery({ queryKey: ['geojson'], queryFn: getParcelsGeojson })

  // raccourci « / » → focus (comme indiqué par le kbd)
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key === '/' && document.activeElement?.tagName !== 'INPUT') {
        e.preventDefault()
        ref.current?.focus()
      }
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [])

  // Entrée : premier IDU correspondant → ouvre sa fiche (recherche = filtre live de la liste)
  const onEnter = () => {
    const qn = query.trim().toUpperCase().replace(/\s+/g, '')
    if (!qn || !geo.data) return
    const hit = geo.data.features.find((f) => {
      const idu = String(f.properties?.idu ?? '').toUpperCase()
      return idu.includes(qn) || idu.slice(8).includes(qn)
    })
    if (hit) {
      setView('cartes')
      select(String(hit.properties?.idu))
    }
  }

  return (
    <div className="flex h-8 w-[360px] items-center gap-2 rounded-lg border border-line-2 bg-surface-3 px-3 focus-within:border-[#2E6B4F]">
      <svg viewBox="0 0 20 20" className="h-4 w-4 shrink-0 text-txt-mut">
        <circle cx="9" cy="9" r="5.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
        <line x1="13" y1="13" x2="17" y2="17" stroke="currentColor" strokeWidth="1.5" />
      </svg>
      <input ref={ref} value={query} onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && onEnter()}
        placeholder="Rechercher un IDU : AB 0234, DE0805…"
        title="Filtre la liste des résultats ; Entrée ouvre la première fiche correspondante"
        className="min-w-0 flex-1 bg-transparent text-xs text-txt placeholder:text-txt-mut focus:outline-none" />
      <kbd className="shrink-0 rounded border border-line-2 px-1 font-mono text-[11px] text-txt-dim">/</kbd>
    </div>
  )
}

// Popover d'ajout de filtre : statut, score Q, surface.
function AddFilter() {
  const { filters, setFilter } = useApp()
  const [open, setOpen] = useState(false)
  const STATUTS: (Statut | 'all')[] = ['all', 'chaude', 'a_surveiller', 'a_creuser', 'ecartee']
  return (
    <div className="relative">
      <button onClick={() => setOpen((o) => !o)}
        className={`flex h-[26px] items-center gap-1 rounded-full border border-dashed px-3 text-xs ${
          open ? 'border-mint text-mint' : 'border-line-2 text-txt-mut hover:text-txt'}`}>+ Filtre</button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute left-0 top-9 z-20 w-64 rounded-xl border border-line-2 bg-surface-2 p-4 shadow-2xl">
            <label className="font-mono text-[11px] tracking-widest text-txt-dim">STATUT</label>
            <div className="mb-3 mt-2 flex flex-wrap gap-1.5">
              {STATUTS.map((s) => (
                <button key={s} onClick={() => setFilter('statut', s)}
                  className={`rounded-full border px-2 py-0.5 text-[11px] ${
                    filters.statut === s ? 'border-mint text-txt-hi' : 'border-line-2 text-txt-mut'}`}>
                  {s === 'all' ? 'Tout' : STATUT_META[s].label}
                </button>
              ))}
            </div>
            <label className="font-mono text-[11px] tracking-widest text-txt-dim">SCORE Q ≥</label>
            <input type="number" min={0} max={100} value={filters.scoreMin ?? ''} placeholder="ex. 70"
              onChange={(e) => setFilter('scoreMin', e.target.value === '' ? null : Number(e.target.value))}
              className="mb-3 mt-2 w-full rounded-lg border border-line-2 bg-surface-3 px-2 py-1 text-xs text-txt focus:border-mint focus:outline-none" />
            <label className="font-mono text-[11px] tracking-widest text-txt-dim">SURFACE ≥ (m²)</label>
            <input type="number" min={0} value={filters.surfaceMin ?? ''} placeholder="ex. 1000"
              onChange={(e) => setFilter('surfaceMin', e.target.value === '' ? null : Number(e.target.value))}
              className="mt-2 w-full rounded-lg border border-line-2 bg-surface-3 px-2 py-1 text-xs text-txt focus:border-mint focus:outline-none" />
          </div>
        </>
      )}
    </div>
  )
}

function FilterChips() {
  const { filters, clearFilter } = useApp()
  const chips = activeChips(filters)
  return (
    <div className="flex items-center gap-2">
      {/* périmètre fixe (Brique 1 = Saint-Paul) */}
      <span className="flex h-[26px] items-center gap-1.5 rounded-full border border-line-2 bg-surface-3 px-3 text-xs text-txt">
        <span className="h-1.5 w-1.5 rounded-full bg-mint" /> Saint-Paul
      </span>
      {chips.map((c) => (
        <span key={c.key} className="flex h-[26px] items-center gap-2 rounded-full border border-line-2 bg-surface-3 px-3 text-xs text-txt">
          {c.label}
          <button onClick={() => clearFilter(c.key)} className="text-txt-dim hover:text-txt-hi" title="Retirer">×</button>
        </span>
      ))}
      <AddFilter />
    </div>
  )
}

function VerdictToggle() {
  const { mode, setMode } = useApp()
  return (
    <div className="flex items-center gap-0.5 rounded-lg border border-line-2 bg-surface-2 p-1">
      {(['verdict', 'mutabilite'] as const).map((m) => (
        <button key={m} onClick={() => setMode(m)}
          className={`rounded-md px-3 py-1 text-xs ${m === mode ? 'bg-mint font-medium text-mint-ink' : 'text-txt-mut hover:text-txt'}`}>
          {m === 'verdict' ? 'Verdict' : 'Mutabilité'}
        </button>
      ))}
    </div>
  )
}

function NotifBell() {
  const [open, setOpen] = useState(false)
  return (
    <div className="relative">
      <button onClick={() => setOpen((o) => !o)} title="Notifications"
        className="flex h-9 w-9 items-center justify-center rounded-full border border-line-2 bg-surface-3 text-txt-mut hover:text-txt">
        <svg viewBox="0 0 20 20" className="h-[18px] w-[18px]">
          <path d="M10 3 a4 4 0 0 1 4 4 v3 l1.5 2.5 h-11 L6 10 V7 a4 4 0 0 1 4-4Z" fill="none" stroke="currentColor" strokeWidth="1.4" />
          <path d="M8.5 15 a1.5 1.5 0 0 0 3 0" fill="none" stroke="currentColor" strokeWidth="1.4" />
        </svg>
      </button>
      {open && (
        <div className="absolute right-0 top-11 z-20 w-64 rounded-lg border border-line-2 bg-surface-2 p-4 text-xs shadow-xl">
          <p className="font-mono text-[11px] tracking-widest text-txt-dim">NOTIFICATIONS</p>
          <p className="mt-3 text-txt-dim">Aucune notification pour l'instant.</p>
        </div>
      )}
    </div>
  )
}

export function Header() {
  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-line bg-bg px-4">
      <Omnibox />
      <FilterChips />
      <div className="ml-auto flex items-center gap-3">
        <VerdictToggle />
        <NotifBell />
        <span className="flex h-8 w-8 items-center justify-center rounded-full border border-line-2 bg-surface-3 font-mono text-[11px] text-mint">VL</span>
      </div>
    </header>
  )
}
