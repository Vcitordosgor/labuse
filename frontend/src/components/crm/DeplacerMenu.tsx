// DA-FIX-5c — LE menu « Déplacer vers… » PARTAGÉ entre la carte du kanban CRM et le bloc CRM de la
// fiche parcelle. Même source de colonnes (meta.columns), même rendu, même composant : l'alternative
// au glisser-déposer. Dernière entrée « Retirer du CRM » (ton danger).
// RETOURS-18 (pt 17) — ce n'est plus un <select> NATIF (rendu système, hors DA) mais un MENU de la DA
// (déclencheur + volet .floating, lignes au survol vert), avec une FLÈCHE (chevron) qui garde sa marge.
import { useEffect, useRef, useState } from 'react'

export const RETIRER = '__retirer__'

export function DeplacerMenu({ columns, currentStatus, onMove, onRetirer, className = '' }: {
  columns: { key: string; label: string }[]
  currentStatus?: string
  onMove: (status: string) => void
  onRetirer: () => void
  className?: string
}) {
  const [open, setOpen] = useState(false)
  const wrap = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => { if (wrap.current && !wrap.current.contains(e.target as Node)) setOpen(false) }
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', onDown); document.addEventListener('keydown', onKey)
    return () => { document.removeEventListener('mousedown', onDown); document.removeEventListener('keydown', onKey) }
  }, [open])
  return (
    <div ref={wrap} className={`relative ${className}`.trim()}>
      <button data-crm-move type="button" aria-haspopup="menu" aria-expanded={open}
        aria-label="Déplacer la parcelle vers une autre colonne du CRM" onClick={() => setOpen((o) => !o)}
        className="flex min-h-[24px] w-full items-center justify-between gap-1.5 rounded-md border border-line-2 bg-surface-2 px-1.5 py-1 text-[10.5px] text-txt-dim transition-colors duration-quick hover:border-mint/50 hover:text-txt">
        <span>Déplacer</span>
        {/* RETOURS-18 (pt 17) — la FLÈCHE (chevron) garde sa MARGE (ml-1), jamais collée au bord. */}
        <svg aria-hidden viewBox="0 0 12 12" className="ml-1 h-2.5 w-2.5 shrink-0"><path d="M2.5 4.5 L6 8 L9.5 4.5" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg>
      </button>
      {open && (
        <div role="menu" className="floating absolute left-0 top-full z-30 mt-1 w-max min-w-full p-1 text-[11px]">
          {columns.map((c) => (
            <button key={c.key} role="menuitem" data-crm-move-opt={c.key} disabled={c.key === currentStatus}
              onClick={() => { onMove(c.key); setOpen(false) }}
              className="hover-fill flex w-full items-center whitespace-nowrap rounded-md px-2.5 py-1.5 text-left text-txt transition-colors duration-quick disabled:cursor-default disabled:opacity-40 disabled:hover:bg-transparent">
              {c.label}
            </button>
          ))}
          <button role="menuitem" data-crm-move-opt={RETIRER} onClick={() => { onRetirer(); setOpen(false) }}
            className="mt-0.5 flex w-full items-center whitespace-nowrap rounded-md border-t border-line/60 px-2.5 py-1.5 text-left text-danger transition-colors duration-quick hover:bg-danger/10">
            Retirer du CRM
          </button>
        </div>
      )}
    </div>
  )
}

export default DeplacerMenu
