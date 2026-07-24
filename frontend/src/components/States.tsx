import type { ReactNode } from 'react'

/** LOI-2 (revue UI/UX) — les états standard de l'app : vide, erreur. Un seul dessin,
 *  digne du cockpit (jamais un « Aucun résultat » nu, jamais du JSON). Le chargement
 *  reste Loading/Skeleton (Loading.tsx). */

/* L'oiseau en filigrane — le motif signature aux endroits calmes (états vides). */
export function Oiseau({ className = 'h-6 w-auto', dim = true }: { className?: string; dim?: boolean }) {
  return (
    <svg viewBox="0 0 240 82" className={className} fill={dim ? '#1E2A23' : '#2FE0A0'} aria-hidden>
      <path d="M2 15 C58 10 100 18 120 27 C140 18 182 10 238 15 C202 29 162 40 135 46 C127 49 122 53 120 60 C118 53 113 49 105 46 C78 40 38 29 2 15 Z" />
    </svg>
  )
}

/** État VIDE : l'oiseau discret, un titre court, l'explication en dessous, une sortie
 *  si elle existe. Centré, respirant — le vide est un état de repos, pas un échec. */
export function EmptyState({ title, hint, action, className = '', mint = false }: {
  title: string
  hint?: ReactNode
  action?: ReactNode
  className?: string
  // F8 (M12) : oiseau en MENTHE (au lieu du gris de repos) — pour un vide invitant à agir
  // (ex. « Aucun projet encore »), à la couleur de l'appel « Décrivez votre opération au copilote ».
  mint?: boolean
}) {
  return (
    <div className={`flex flex-col items-center gap-2 px-6 py-10 text-center ${className}`}>
      <Oiseau className="mb-1 h-5 w-auto" dim={!mint} />
      <p className="text-sm font-medium text-txt">{title}</p>
      {hint && <p className="max-w-[340px] text-xs leading-relaxed text-txt-mut">{hint}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}

/** État ERREUR : sobre, jamais alarmiste — le message, et TOUJOURS une sortie. */
export function ErrorState({ message, retry, hint, className = '' }: {
  message: string
  retry?: () => void
  hint?: ReactNode
  className?: string
}) {
  return (
    <div className={`flex flex-col items-center gap-2 px-6 py-10 text-center ${className}`} role="alert">
      <span className="mb-1 h-1.5 w-8 rounded-full bg-st-ecartee/60" aria-hidden />
      <p className="text-sm font-medium text-txt">{message}</p>
      {hint && <p className="max-w-[340px] text-xs leading-relaxed text-txt-mut">{hint}</p>}
      {retry && (
        <button onClick={retry}
          className="mt-2 rounded-lg border border-line-2 px-3 py-1.5 text-xs font-medium text-txt transition-colors duration-quick hover:border-mint/60 hover:text-txt-hi">
          Réessayer
        </button>
      )}
    </div>
  )
}
