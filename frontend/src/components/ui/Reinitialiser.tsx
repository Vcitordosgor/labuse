// RECETTE-1 (F3, Vic 04/10) — LE bouton « Réinitialiser » unique des outils. En haut à droite du corps
// de l'outil, même composant partout : un Chip secondaire (ton neutre) avec l'icône ↻. Il vide les
// champs, le résultat, la surbrillance carte et l'état LOCAL de l'outil (via `onReset`) et REND les deux
// entrées de `EntreeParcelle` (F2) — il NE change PAS de chemin (pas un retour). Remplace « Nouvelle
// étude » (Étude de zone) et tous les « Recommencer »/« Nouveau » faits à la main.
import type { ReactNode } from 'react'
import { Chip } from './Chip'

export function Reinitialiser({ onReset, label = 'Réinitialiser', className = '', aide }: {
  onReset: () => void; label?: string; className?: string
  // RECETTE-2 (T3) — texte d'explication OPTIONNEL. Fourni → mise en page canonique T3 : le bouton est
  // SEUL sur sa ligne (en haut à droite), l'aide vient EN DESSOUS, pleine largeur (jamais côte à côte).
  // Les appelants qui juxtaposaient un <p> au bouton passent désormais ce texte en `aide`.
  aide?: ReactNode
}) {
  const chip = (
    <Chip ton="neutre" data-reinitialiser onClick={onReset}
      className={`shrink-0 ${className}`.trim()} title="Vider les champs et le résultat (reste dans l'outil)">
      <svg aria-hidden="true" viewBox="0 0 16 16" className="h-3.5 w-3.5 shrink-0" fill="none"
        stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <path d="M13.5 8a5.5 5.5 0 1 1-1.6-3.9" />
        <path d="M13.5 2.5V5h-2.5" />
      </svg>
      {label}
    </Chip>
  )
  if (aide == null) return chip
  return (
    <div data-reinitialiser-bloc className="flex flex-col gap-1">
      <div className="flex justify-end">{chip}</div>
      <p className="text-[10.5px] leading-snug text-txt-mut">{aide}</p>
    </div>
  )
}

export default Reinitialiser
