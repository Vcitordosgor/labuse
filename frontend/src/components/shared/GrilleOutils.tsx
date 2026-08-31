// PROJETS-V5 (E9) — LA GRILLE D'OUTILS, composant PARTAGÉ. Un seul rendu (cases icône + nom + chiffre,
// sélection au survol), servi sur la FICHE COMMUNE (passerelles) ET la FICHE PARCELLE (exports). Vic a
// validé ce rendu ; on l'extrait ici pour que les deux fiches sentent la même main.
import type { ReactNode } from 'react'

// RETOURS-4 S3 — survol PLEIN (aplat `--mint`, contenu inversé en encre sombre) sur les cases cliquables
// (tuiles d'export de la fiche parcelle + passerelles de la fiche commune). `group` + group-hover inversent
// icône, nom et chiffre. Les cases DÉSACTIVÉES gardent le gabarit sans le survol (CASE_BASE).
const CASE_BASE = 'group flex flex-col items-center justify-center gap-0.5 rounded-lg border border-line-2 bg-surface-2 px-1 py-2.5 text-center transition-colors duration-quick'
const CASE = `${CASE_BASE} hover:border-mint hover:bg-mint`

function Inner({ ic, nom, chiffre }: { ic: ReactNode; nom: string; chiffre?: ReactNode }) {
  return (
    <>
      <span className="text-[15px] text-txt-mut group-hover:text-mint-on" aria-hidden>{ic}</span>
      <b className="text-[11px] font-medium leading-tight text-txt-hi group-hover:text-mint-on">{nom}</b>
      {chiffre != null && chiffre !== '' && <small className="font-mono text-[9.5px] text-mint group-hover:text-mint-on">{chiffre}</small>}
    </>
  )
}

/** Une CASE d'outil : bouton (onClick), lien (href, ouvre un onglet), ou désactivée (grisée). */
export function OutilCase({ ic, nom, chiffre, onClick, href, disabled, title, ...rest }: {
  ic: ReactNode; nom: string; chiffre?: ReactNode; onClick?: () => void; href?: string
  disabled?: boolean; title?: string
} & Record<`data-${string}`, string | undefined>) {
  const inner = <Inner ic={ic} nom={nom} chiffre={chiffre} />
  if (disabled) return <span data-outil-case={nom} aria-disabled className={`${CASE_BASE} cursor-not-allowed opacity-40`} title={title} {...rest}>{inner}</span>
  if (href) return <a data-outil-case={nom} href={href} target="_blank" rel="noreferrer" className={CASE} title={title} {...rest}>{inner}</a>
  return <button data-outil-case={nom} onClick={onClick} className={CASE} title={title} {...rest}>{inner}</button>
}

/** La GRILLE (4 colonnes) qui contient les cases. */
export function GrilleOutils({ children }: { children: ReactNode }) {
  return <div data-outils-grille className="grid grid-cols-4 gap-1.5">{children}</div>
}
