// RECETTE-1 (F3, Vic 04/10) — LE bouton « Réinitialiser » unique des outils. En haut à droite du corps
// de l'outil, même composant partout : un Chip secondaire (ton neutre) avec l'icône ↻. Il vide les
// champs, le résultat, la surbrillance carte et l'état LOCAL de l'outil (via `onReset`) et REND les deux
// entrées de `EntreeParcelle` (F2) — il NE change PAS de chemin (pas un retour). Remplace « Nouvelle
// étude » (Étude de zone) et tous les « Recommencer »/« Nouveau » faits à la main.
import { Chip } from './Chip'

export function Reinitialiser({ onReset, label = 'Réinitialiser', className = '' }: {
  onReset: () => void; label?: string; className?: string
}) {
  return (
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
}

export default Reinitialiser
