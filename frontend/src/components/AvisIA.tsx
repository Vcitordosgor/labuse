import { CLIENT } from '../lib/strings'

/** EXPRESS-01 · Volet B — avis IA posé en tête de TOUTE surface où l'IA s'exprime.
 *  Cartouche sobre, TOUJOURS visible, jamais repliable, jamais derrière un tooltip ;
 *  ni alerte rouge ni encart pub. Le texte vient d'une source unique (CLIENT.avisIa) —
 *  jamais recopié. `className` permet d'accorder les couleurs à la DA de chaque surface
 *  (par défaut : cartouche neutre sur fond sombre standard). */
export function AvisIA({ className = 'mb-3 border-line-2 bg-surface-2 text-txt-mut' }: { className?: string }) {
  return (
    <p data-avis-ia className={`rounded-lg border px-3 py-2 text-[11px] leading-snug ${className}`}>
      {CLIENT.avisIa}
    </p>
  )
}
