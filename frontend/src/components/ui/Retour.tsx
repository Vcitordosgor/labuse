// DA-FIX-2 Lot 1 (DA-011 → DA-016) — LE composant retour unique de l'app.
// Toujours en haut à gauche du panneau, rendu `Bouton niveau="lien"` : glyphe `←` + nom de la
// destination. Il remplace les trois mécanismes historiques (fil « ← Outils », RetourOutil post-pont,
// retours d'étape locaux). Glyphe UNIQUE `←` — jamais `‹`, jamais « Retour » nu, jamais une croix
// (la croix ✕ ferme le panneau, elle ne recule pas). Libellés : « Outils » à l'écran 1, le nom de
// l'étape précédente dans une étape, le nom de l'outil de départ après un pont.
import type { ButtonHTMLAttributes } from 'react'
import { Bouton } from './Bouton'

export function Retour({ label, onClick, className = '', ...rest }: { label: string; onClick: () => void; className?: string } & Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'onClick'>) {
  return (
    <Bouton niveau="lien" ton="vert" data-retour onClick={onClick} className={`self-start ${className}`.trim()} {...rest}>
      <span aria-hidden="true">←</span> {label}
    </Bouton>
  )
}

export default Retour
