import type { ReactNode } from 'react'

/**
 * RETOURS-11 T2 — tuile d'icône unique, réutilisable (« pas de copies »).
 * Rendue à l'intérieur d'une carte cliquable qui porte `.hover-fill` (vert) ou
 * `.hover-fill-ia` (mauve). Au repos : tuile teintée. Au survol de la carte : fond
 * sombre, glyphe et contour de la couleur (vert, ou mauve si `ia`). Toute la
 * mécanique de survol vit dans la classe CSS `.itile` (styles/index.css), pas ici.
 */
export function IconTile({ children, ia = false, className = '' }: {
  children: ReactNode
  ia?: boolean
  className?: string
}) {
  return <span className={`itile${ia ? ' ia' : ''}${className ? ' ' + className : ''}`}>{children}</span>
}

export default IconTile
