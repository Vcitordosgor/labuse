// DA-FIX-2 Lot 1 (DA-011 → DA-016) — LE composant retour unique de l'app.
// Toujours en haut à gauche du panneau, rendu `Bouton niveau="secondaire"` (DA-FIX-5 P4, décision Vic
// 24/09) : contour vert, 32 px, rayon 6, survol vert plein — jamais un lien souligné. Glyphe `←` + nom
// de la destination. Il remplace les trois mécanismes historiques (fil « ← Outils », RetourOutil
// post-pont, retours d'étape locaux) ET les retours faits à la main (texte gris « ← Mes projets »,
// `‹`…). Glyphe UNIQUE `←` — jamais `‹`, jamais « Retour » nu, jamais une croix (la croix ✕ ferme le
// panneau, elle ne recule pas). Libellés : « Outils » à l'écran 1, le nom de l'étape précédente dans
// une étape, le nom de l'outil/écran de départ après un pont.
import type { ButtonHTMLAttributes } from 'react'
import { Bouton } from './Bouton'

// RECETTE-OUTILS-2 (R3) — `shrink-0` : dans le CORPS d'un outil (colonne flex qui déborde), le Bouton
// h-8 était écrasé par flex-shrink (hauteur ~15 px, contour fin, hors DA) — le « ← Outils » de l'en-tête
// (conteneur shrink-0) y échappait seul. Avec shrink-0, TOUS les « Retour » gardent la hauteur 32 px /
// contour / rayon / padding de la charte.
export function Retour({ label, onClick, className = '', ...rest }: { label: string; onClick: () => void; className?: string } & Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'onClick'>) {
  return (
    <Bouton niveau="secondaire" ton="vert" data-retour onClick={onClick} className={`shrink-0 self-start ${className}`.trim()} {...rest}>
      <span aria-hidden="true">←</span> {label}
    </Bouton>
  )
}

export default Retour
