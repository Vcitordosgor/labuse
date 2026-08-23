import { useEffect, useState, type ReactNode } from 'react'
import { fmtInt } from '../lib/format'

// SOCLE (refonte 13 outils) — PAGINATION DE LISTE PARTAGÉE. Un seul pied de liste pour PLU (04),
// Densifier (12) et Faisabilité (02). Doctrine : le compteur « n / total affichées » est TOUJOURS
// visible et EXACT (jamais tronqué), la liste se charge par paquets de 400 jusqu'à épuisement, et un
// « Tout charger (total) » optionnel sert les pressés. Le slot `children` accueille les actions
// propres à l'outil (ex. « Exporter CSV » de Densifier) sans dupliquer le pied.
//
// Deux morceaux, à composer :
//   • usePagination(total) : gère la FENÊTRE visible (nombre de lignes affichées) — pour une liste
//     déjà chargée en mémoire qu'on tranche côté client (Densifier, PLU en mode caché).
//   • ListPaginationFooter : le rendu du pied — réutilisable AUSSI avec une pagination serveur
//     (on lui passe alors shown/total/onMore issus de useInfiniteQuery ou d'un offset).

export const PAGE_SIZE = 400

export interface Pagination {
  shown: number
  hasMore: boolean
  more: () => void
  all: () => void
  reset: () => void
  step: number
}

// Fenêtre visible bornée à `total`. Se réinitialise à UNE page quand le jeu change (nouvelle
// requête → `total` bouge) ; à `total` inchangé (re-tri client), la fenêtre agrandie est préservée
// (deps stables, l'effet ne refire pas).
export function usePagination(total: number, step: number = PAGE_SIZE): Pagination {
  const [shown, setShown] = useState(() => Math.min(step, total))
  useEffect(() => { setShown(Math.min(step, total)) }, [total, step])
  return {
    shown,
    hasMore: shown < total,
    more: () => setShown((s) => Math.min(s + step, total)),
    all: () => setShown(total),
    reset: () => setShown(Math.min(step, total)),
    step,
  }
}

export function ListPaginationFooter({
  shown, total, step = PAGE_SIZE, onMore, onAll, allLabel, children, className,
}: {
  shown: number
  total: number
  step?: number
  onMore: () => void
  onAll?: () => void          // absent = pas de bouton « tout charger »
  allLabel?: string           // défaut « Tout charger (N) »
  children?: ReactNode        // actions additionnelles (ex. Densifier : « Exporter CSV »)
  className?: string
}) {
  const remaining = Math.max(0, total - shown)
  const hasMore = remaining > 0
  // Honnête sur la dernière page : « Voir 137 de plus », pas « Voir 400 de plus » quand il en reste 137.
  const nextChunk = Math.min(step, remaining)
  return (
    <div
      data-pagination
      className={className ?? 'flex flex-wrap items-center gap-3 border-t border-line pt-2 text-[11px] text-txt-mut'}
    >
      {/* compteur TOUJOURS rendu, valeurs exactes */}
      <span data-pagination-count>
        <b className="text-txt">{fmtInt(shown)} / {fmtInt(total)}</b> affichées
      </span>
      {hasMore && (
        <button data-pagination-more onClick={onMore} className="text-mint hover:underline">
          Voir {fmtInt(nextChunk)} de plus
        </button>
      )}
      {hasMore && onAll && (
        <button data-pagination-all onClick={onAll} className="text-txt-mut hover:text-mint">
          {allLabel ?? `Tout charger (${fmtInt(total)})`}
        </button>
      )}
      {children}
    </div>
  )
}
