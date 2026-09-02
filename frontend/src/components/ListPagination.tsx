import { useEffect, useState, type ReactNode } from 'react'
import { fmtInt } from '../lib/format'

// SOCLE (refonte 13 outils) — PAGINATION DE LISTE PARTAGÉE, l'UNIQUE pied de liste de l'app. Doctrine :
// le compteur « n / total affichées » est TOUJOURS visible et EXACT (jamais tronqué), la liste se charge
// par paquets de 200 avec un seul bouton « Voir N de plus ». Le slot `children` accueille les actions
// propres à l'outil (ex. « Exporter CSV » de Densifier) sans dupliquer le pied.
//
// RETOURS-10 (T3) — DEUX changements de doctrine : (1) la page passe de 400 à **200** partout ; (2) le
// bouton « Tout charger (total) » DISPARAÎT — jamais de chargement massif d'un coup (c'est lui qui figeait
// l'app en tirant 33 910 lignes). Il ne reste que « Voir 200 de plus ». La position de défilement est
// conservée : on APPEND à la liste (le conteneur parent, en overflow, garde son scroll — on ne remonte
// jamais en tête).
//
// Deux morceaux, à composer :
//   • usePagination(total) : gère la FENÊTRE visible (nombre de lignes affichées) — pour une liste
//     déjà chargée en mémoire qu'on tranche côté client (liste de parcelles en mode commune, Projets…).
//   • ListPaginationFooter : le rendu du pied — réutilisable AUSSI avec une pagination serveur
//     (on lui passe alors shown/total/onMore issus de useInfiniteQuery ou d'un offset).

export const PAGE_SIZE = 200

export interface Pagination {
  shown: number
  hasMore: boolean
  more: () => void
  reset: () => void
  step: number
}

// Fenêtre visible bornée à `total`. Se réinitialise à UNE page quand le jeu change (nouvelle
// requête → `total` bouge) ; à `total` inchangé (re-tri client), la fenêtre agrandie est préservée
// (deps stables, l'effet ne refire pas) → la position de défilement tient.
export function usePagination(total: number, step: number = PAGE_SIZE): Pagination {
  const [shown, setShown] = useState(() => Math.min(step, total))
  useEffect(() => { setShown(Math.min(step, total)) }, [total, step])
  return {
    shown,
    hasMore: shown < total,
    more: () => setShown((s) => Math.min(s + step, total)),
    reset: () => setShown(Math.min(step, total)),
    step,
  }
}

export function ListPaginationFooter({
  shown, total, step = PAGE_SIZE, onMore, children, className,
}: {
  shown: number
  total: number
  step?: number
  onMore: () => void
  children?: ReactNode        // actions additionnelles (ex. Densifier : « Exporter CSV »)
  className?: string
}) {
  const remaining = Math.max(0, total - shown)
  const hasMore = remaining > 0
  // Honnête sur la dernière page : « Voir 137 de plus », pas « Voir 200 de plus » quand il en reste 137.
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
      {children}
    </div>
  )
}
