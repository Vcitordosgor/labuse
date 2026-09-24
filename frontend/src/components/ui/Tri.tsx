// DA-FIX-3 Lot 3 (DA-027) — LE composant de tri unique (en-tête de liste).
// Groupe de boutons de tri ; le bouton actif est en vert opaque (flèche ▲▼ portée par `suffix`).
// La logique de sens (inversion surface…) reste au caller, qui fournit `isActive` et `suffix`.
export interface TriOption { key: string; label: string; suffix?: string }

export function Tri({ options, isActive, onSelect, className = '' }: {
  options: TriOption[]
  isActive: (key: string) => boolean
  onSelect: (key: string) => void
  className?: string
}) {
  return (
    <div className={`inline-flex flex-wrap items-center gap-0.5 rounded-md border border-line-2 bg-surface-2 p-0.5 ${className}`.trim()}>
      {options.map((o) => {
        const a = isActive(o.key)
        return (
          <button key={o.key} type="button" data-sort={o.key} onClick={() => onSelect(o.key)}
            className={`h-7 rounded-md px-3 text-[11px] leading-none transition-colors duration-quick focus-visible:outline-none ${
              a ? 'bg-mint font-semibold text-mint-on' : 'text-txt-mut hover:bg-surface-3 hover:text-txt'}`}>
            {o.label}{o.suffix ?? ''}
          </button>
        )
      })}
    </div>
  )
}

export default Tri
