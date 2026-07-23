// A4 (ajustements post-revue) — chargement VISIBLE et affirmé : de GROS points menthe qui
// ondulent en séquence. Le critère de Vic : on doit comprendre de loin « ça charge, ce n'est
// pas cassé ». Appliqué partout où un délai est perceptible (carte, fiche, entretien, outils…).
export function Loading({ label, className = '', big = false, accent = 'mint' }:
  { label?: string; className?: string; big?: boolean; accent?: 'mint' | 'violet' }) {
  const dot = big ? 'h-3.5 w-3.5' : 'h-2.5 w-2.5'
  // accent 'violet' (#B497F0) = charte de la partie OUTILS ; 'mint' partout ailleurs (défaut).
  const tone = accent === 'violet'
    ? 'bg-violet shadow-[0_0_8px_rgba(180,151,240,0.6)]'
    : 'bg-mint shadow-[0_0_8px_rgba(92,230,161,0.6)]'
  return (
    <span className={`inline-flex items-center gap-2.5 text-txt-mut ${className}`} role="status" aria-live="polite" aria-busy="true">
      <span className="flex items-center gap-1.5" aria-hidden>
        {[0, 1, 2].map((i) => (
          <span key={i} className={`labuse-dot ${dot} rounded-full ${tone}`}
            style={{ animationDelay: `${i * 160}ms` }} />
        ))}
      </span>
      {label && <span className={big ? 'text-sm' : 'text-xs'}>{label}</span>}
    </span>
  )
}

// Bloc squelette (listes, cartes) — pulse discret, complète les gros points.
export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-surface-3 ${className}`} />
}
