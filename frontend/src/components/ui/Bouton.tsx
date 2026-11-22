// DA-FIX-1 Lot 4 (DA-019, DA-021, DA-022, DA-023) — LE composant bouton unique de l'app.
// Trois niveaux, trois tons. Invariants de la charte (§2) appliqués une seule fois ici :
//   • hauteur 32 px · rayon 6 · padding-x 14 · police 13 px / 500 ;
//   • icône seule → carré 32×32 ;
//   • :focus-visible = EXACTEMENT le rendu du survol, sans anneau (DA-019) ;
//   • désactivé : hérite de la règle globale index.css (opacity .4 + not-allowed, Lot 2).
// Les trois niveaux (primaire / secondaire / lien) et les trois tons (vert / ambre / ia-mauve)
// remplacent .btn/.b-pri/.b-sec/.p-on/.cta/.act/.ia-btn, les `btnPlein` inline et les
// <div>/<span onClick> qui faisaient office de bouton. NE PAS réintroduire de bouton stylé à la main.
import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Chargement } from '../Loading'

export type BoutonNiveau = 'primaire' | 'secondaire' | 'lien'
export type BoutonTon = 'vert' | 'ambre' | 'ia' | 'danger'

export interface BoutonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  niveau?: BoutonNiveau
  ton?: BoutonTon
  /** icône seule → carré 32×32 (pas de padding horizontal). */
  icone?: boolean
  /** MINI-CORRECTIONS-2 (pt 12) — état de chargement LISIBLE, porté par le composant Bouton donc
   *  identique partout : points + libellé en `currentColor` (la couleur de texte du bouton), bouton
   *  désactivé et `aria-busy`. `loadingLabel` remplace le texte le temps du chargement (sinon on garde
   *  les enfants). Fini le gris illisible sur le vert. */
  loading?: boolean
  loadingLabel?: string
  children?: ReactNode
}

// Par ton : aplat (fond opaque + encre sombre), et contour (bord + texte de la couleur).
// L'encre sombre du ton vert = token --mint-on ; ambre/ia/danger = encres sombres dédiées.
// DA-FIX-2 Lot 0 (décision Vic 24/09) — ton `danger` (corail/rouge de l'app) RÉSERVÉ aux actions
// destructrices : Supprimer, Écarter, et les boutons st-ecartee. Jamais pour une action neutre.
// RETOURS-21 — règle de focus UNIQUE : le focus clavier = SEULEMENT le contour vert global
// (`*:focus-visible`), plus d'aplat de focus (`focus-visible:bg/text`). Le survol garde son aplat.
const TON = {
  vert:   { fill: 'bg-mint text-mint-on',       line: 'border-mint text-mint',        hover: 'hover:bg-mint hover:text-mint-on' },
  ambre:  { fill: 'bg-amber text-[#241a06]',    line: 'border-amber text-amber',      hover: 'hover:bg-amber hover:text-[#241a06]' },
  ia:     { fill: 'bg-violet text-[#14091f]',   line: 'border-violet text-violet',    hover: 'hover:bg-violet hover:text-[#14091f]' },
  danger: { fill: 'bg-coral text-[#2b1512]',    line: 'border-coral text-coral',      hover: 'hover:bg-coral hover:text-[#2b1512]' },
} as const

const BASE =
  'inline-flex items-center justify-center gap-2 h-8 rounded-md text-[13px] font-medium leading-none ' +
  'transition-colors duration-quick focus-visible:outline-none disabled:pointer-events-auto'

export function Bouton({ niveau = 'secondaire', ton = 'vert', icone = false, loading = false, loadingLabel, className = '', type, disabled, children, ...rest }: BoutonProps) {
  const t = TON[ton]
  const pad = icone ? 'w-8 px-0 shrink-0' : 'px-[14px]'
  let variant: string
  if (niveau === 'primaire') {
    // Fond opaque de sa couleur, encre sombre — au repos comme au survol/focus.
    variant = `${t.fill} border border-transparent`
  } else if (niveau === 'secondaire') {
    // Contour + fond transparent ; survol/focus = aplat opaque, contenu inversé.
    variant = `bg-transparent border ${t.line} ${t.hover}`
  } else {
    // Lien : souligné, sans contour ; survol/focus = texte vert (quel que soit le ton).
    variant = `bg-transparent border-0 underline underline-offset-2 ${t.line.split(' ').pop()} hover:text-mint`
  }
  return (
    <button type={type ?? 'button'} disabled={disabled || loading} aria-busy={loading || undefined}
      className={`${BASE} ${pad} ${variant} ${className}`.trim()} {...rest}>
      {loading
        ? <Chargement variant="inline" accent="courant" delai={0} label={loadingLabel ?? (typeof children === 'string' ? children : undefined)} />
        : children}
    </button>
  )
}

export default Bouton
