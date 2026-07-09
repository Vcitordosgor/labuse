// B1 (mandat calculette) — animation de chargement DISCRÈTE : des points qui pulsent, pour
// qu'un délai ne ressemble jamais à un écran figé (« on ne doit jamais craindre un bug »).
export function Loading({ label, className = '' }: { label?: string; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-1.5 text-txt-dim ${className}`} role="status" aria-live="polite">
      {label && <span className="text-xs">{label}</span>}
      <span className="flex gap-0.5" aria-hidden>
        {[0, 1, 2].map((i) => (
          <span key={i} className="h-1 w-1 animate-pulse rounded-full bg-current"
            style={{ animationDelay: `${i * 160}ms`, animationDuration: '1s' }} />
        ))}
      </span>
    </span>
  )
}

// Barre / bloc squelette (listes, cartes) — même langage visuel (pulse menthe-neutre).
export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-surface-3 ${className}`} />
}
