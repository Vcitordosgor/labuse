import { useState } from 'react'
import { useApp } from '../../store/useApp'

function Omnibox() {
  const { query, setQuery } = useApp()
  return (
    <div className="flex h-8 w-[380px] items-center gap-2 rounded-lg border border-line-2 bg-surface-3 px-3">
      <svg viewBox="0 0 20 20" className="h-4 w-4 text-txt-mut">
        <circle cx="9" cy="9" r="5.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
        <line x1="13" y1="13" x2="17" y2="17" stroke="currentColor" strokeWidth="1.5" />
      </svg>
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Rechercher : adresse, AB 0234, lieu-dit…"
        className="flex-1 bg-transparent text-xs text-txt placeholder:text-txt-mut focus:outline-none"
      />
      <kbd className="rounded border border-line-2 px-1 font-mono text-[11px] text-txt-dim">/</kbd>
    </div>
  )
}

function Chip({ label, dashed }: { label: string; dashed?: boolean }) {
  return (
    <span
      className={`flex h-[26px] items-center gap-2 rounded-full px-3 text-xs ${
        dashed ? 'border border-dashed border-line-2 text-txt-mut' : 'border border-line-2 bg-surface-3 text-txt'
      }`}
    >
      {label}
      {!dashed && <span className="text-txt-dim">×</span>}
    </span>
  )
}

function VerdictToggle() {
  const { mode, setMode } = useApp()
  return (
    <div className="flex items-center gap-0.5 rounded-lg border border-line-2 bg-surface-2 p-1">
      {(['verdict', 'mutabilite'] as const).map((m) => (
        <button
          key={m}
          onClick={() => setMode(m)}
          className={`rounded-md px-3 py-1 text-xs capitalize ${
            mode === m ? 'bg-mint font-medium text-mint-ink' : 'text-txt-mut hover:text-txt'
          }`}
        >
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
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex h-9 w-9 items-center justify-center rounded-full border border-line-2 bg-surface-3 text-txt-mut hover:text-txt"
        title="Notifications"
      >
        <svg viewBox="0 0 20 20" className="h-[18px] w-[18px]">
          <path d="M10 3 a4 4 0 0 1 4 4 v3 l1.5 2.5 h-11 L6 10 V7 a4 4 0 0 1 4-4Z" fill="none" stroke="currentColor" strokeWidth="1.4" />
          <path d="M8.5 15 a1.5 1.5 0 0 0 3 0" fill="none" stroke="currentColor" strokeWidth="1.4" />
        </svg>
      </button>
      {open && (
        <div className="absolute right-0 top-11 z-20 w-64 rounded-lg border border-line-2 bg-surface-2 p-4 text-xs text-txt-mut shadow-xl">
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
      <div className="flex items-center gap-2">
        <Chip label="Saint-Paul" />
        <Chip label="Zone U" />
        <Chip label="Score ≥ 70" />
        <Chip label="+ Filtre" dashed />
      </div>
      <div className="ml-auto flex items-center gap-3">
        <VerdictToggle />
        <NotifBell />
        <span className="flex h-8 w-8 items-center justify-center rounded-full border border-line-2 bg-surface-3 font-mono text-[11px] text-mint">
          VL
        </span>
      </div>
    </header>
  )
}
