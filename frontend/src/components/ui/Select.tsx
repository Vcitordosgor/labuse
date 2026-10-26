// U3 (RECETTE-OUTILS-4) — menu déroulant PARTAGÉ de l'app. La flèche native (dont la position varie
// selon le navigateur et restait collée au bord) est remplacée par un chevron de la charte posé à
// 16 px EXACTEMENT du bord droit (`right-4`), avec un padding droit (`pr-9` = 36 px) qui garantit que
// le texte de l'option ne passe JAMAIS dessous. Tous les menus de l'app consomment ce composant →
// ils sont rigoureusement identiques (Activité, Périmètre, filtres…).
//
// Le <select> reste natif (accessibilité, clavier, ouverture système conservés) ; `className` le
// stylise comme avant (bordure, fond, hauteur, texte) MOINS le padding droit, désormais géré ici.
// `wrapClassName` porte la mise en page du conteneur (ex. `w-full`, marges) quand le menu doit
// s'étirer — sans quoi le conteneur `inline-flex` se réduit à la largeur de l'option.
import { forwardRef, type SelectHTMLAttributes } from 'react'

export const Select = forwardRef<
  HTMLSelectElement,
  SelectHTMLAttributes<HTMLSelectElement> & { wrapClassName?: string }
>(function Select({ className = '', wrapClassName = '', children, ...props }, ref) {
  return (
    <span className={`relative inline-flex items-center ${wrapClassName}`}>
      <select ref={ref} {...props} className={`appearance-none bg-none !pr-9 ${className}`}>
        {children}
      </select>
      <svg
        aria-hidden
        viewBox="0 0 12 12"
        className="pointer-events-none absolute right-4 top-1/2 h-2.5 w-2.5 -translate-y-1/2 text-txt-mut"
      >
        <path d="M2.5 4.5 6 8l3.5-3.5" fill="none" stroke="currentColor" strokeWidth="1.5"
          strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </span>
  )
})
