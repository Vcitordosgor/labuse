// PROJETS-V5 (E9) — LA GRILLE D'OUTILS, composant PARTAGÉ. Un seul rendu (cases icône + nom + chiffre,
// sélection au survol), servi sur la FICHE COMMUNE (passerelles) ET la FICHE PARCELLE (exports). Vic a
// validé ce rendu ; on l'extrait ici pour que les deux fiches sentent la même main.
import type { ReactNode } from 'react'

const CASE = 'flex flex-col items-center justify-center gap-0.5 rounded-lg border border-line-2 bg-surface-2 px-1 py-2.5 text-center transition-colors duration-quick hover:border-mint'

function Inner({ ic, nom, chiffre }: { ic: ReactNode; nom: string; chiffre?: ReactNode }) {
  return (
    <>
      <span className="text-[15px] text-txt-mut" aria-hidden>{ic}</span>
      <b className="text-[11px] font-medium leading-tight text-txt-hi">{nom}</b>
      {chiffre != null && chiffre !== '' && <small className="font-mono text-[9.5px] text-mint">{chiffre}</small>}
    </>
  )
}

/** Une CASE d'outil : bouton (onClick), lien (href, ouvre un onglet), ou désactivée (grisée). */
export function OutilCase({ ic, nom, chiffre, onClick, href, disabled, title, ...rest }: {
  ic: ReactNode; nom: string; chiffre?: ReactNode; onClick?: () => void; href?: string
  disabled?: boolean; title?: string
} & Record<`data-${string}`, string | undefined>) {
  const inner = <Inner ic={ic} nom={nom} chiffre={chiffre} />
  if (disabled) return <span data-outil-case={nom} aria-disabled className={`${CASE} cursor-not-allowed opacity-40`} title={title} {...rest}>{inner}</span>
  if (href) return <a data-outil-case={nom} href={href} target="_blank" rel="noreferrer" className={CASE} title={title} {...rest}>{inner}</a>
  return <button data-outil-case={nom} onClick={onClick} className={CASE} title={title} {...rest}>{inner}</button>
}

/** La GRILLE (4 colonnes) qui contient les cases. */
export function GrilleOutils({ children }: { children: ReactNode }) {
  return <div data-outils-grille className="grid grid-cols-4 gap-1.5">{children}</div>
}
