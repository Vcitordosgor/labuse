// M26-B — primitives visuelles de l'écran Copilote (tokens cp-* de la maquette B4).
import type { ReactNode } from 'react'
import { Badge as UiBadge, type BadgeTon } from '../ui/Badge'

/** Étiquette de provenance — la CHAÎNE DU PAYLOAD, affichée telle quelle (majuscule
 *  initiale près). Jamais inventée, jamais omise (règle 1 du mandat) : si `v` est
 *  absent du payload, l'appelant n'affiche pas le chiffre. */
export function Etiquette({ v }: { v: string }) {
  const genre = v.startsWith('sourcé') ? 'source' : v.startsWith('estimé') ? 'estime' : 'absent'
  const cls = {
    source: 'border-cp-ia/25 bg-cp-ia/10 text-cp-ia',
    estime: 'border-cp-amber/25 bg-cp-amber/10 text-cp-amber',
    absent: 'border-cp-line2 bg-cp-muted/10 text-cp-muted',
  }[genre]
  return (
    <span data-etiquette={v}
      className={`rounded-[5px] border px-2 py-0.5 font-display text-[9px] font-bold uppercase tracking-[.1em] ${cls}`}>
      {v.charAt(0).toUpperCase() + v.slice(1)}
    </span>
  )
}

/** Badge d'en-tête (exhaustivité, calibrage) — DA-034 : délègue au Badge partagé. mint = nominal
 *  (→ vert), ambre = dégradé (→ ambre). Même nom d'export, même API. */
export function Badge({ ton, children, data }: { ton: 'mint' | 'ambre'; children: ReactNode; data?: string }) {
  return <UiBadge data-badge={data} ton={ton === 'mint' ? 'vert' : 'ambre'}>{children}</UiBadge>
}

export function SecHead({ titre, sousTitre, meta }: { titre: string; sousTitre?: string; meta?: ReactNode }) {
  return (
    <div className={`mb-3 mt-9 ${meta != null ? 'flex items-baseline gap-3' : ''}`}>
      <h2 className="font-display text-[15px] font-semibold text-cp-txt">{titre}</h2>
      {sousTitre && <p className="mt-0.5 text-[11.5px] text-cp-faint">{sousTitre}</p>}
      {meta != null && <div className="ml-auto text-[11px] tabular-nums text-cp-faint">{meta}</div>}
    </div>
  )
}

/** Pastille d'état du run (eyebrow) — Terminé / Instruction / En pause / … DA-034 : délègue au
 *  Badge partagé (avec point). Mapping 4→3 tons : mint→vert, ambre→ambre, rouge→ambre (pas de 4ᵉ
 *  ton), violet→neutre (le mauve « IA » n'a pas de ton Badge dédié). Le `pulse` n'est plus rendu
 *  (le Badge partagé n'a pas de pastille pulsante). */
export function PillStatut({ ton, children }: { ton: 'mint' | 'violet' | 'ambre' | 'rouge'
  pulse?: boolean; children: ReactNode }) {
  const t: BadgeTon = ton === 'mint' ? 'vert' : ton === 'violet' ? 'neutre' : 'ambre'
  return <UiBadge data-pill-statut="" point ton={t}>{children}</UiBadge>
}

// M102 P1.1 — INDICATEUR DE TRAITEMENT (surface IA → mauve légitime). SOBRE : trois points en
// pulsation + une phrase — JAMAIS une barre de progression (elle prétendrait savoir où elle en
// est). Affiché pendant que le routeur/les outils travaillent, retiré à la réponse.
export function TraitementEnCours() {
  return (
    <div data-traitement className="rounded-2xl border border-violet/25 bg-cp-card px-5 py-4 text-left"
      role="status" aria-live="polite">
      <span className="inline-flex items-center gap-2 text-[13px] text-cp-muted">
        <span className="inline-flex gap-1" aria-hidden>
          <i className="h-1.5 w-1.5 animate-pulse rounded-full bg-cp-violet" />
          <i className="h-1.5 w-1.5 animate-pulse rounded-full bg-cp-violet [animation-delay:150ms]" />
          <i className="h-1.5 w-1.5 animate-pulse rounded-full bg-cp-violet [animation-delay:300ms]" />
        </span>
        Le Copilote cherche votre réponse…
      </span>
    </div>
  )
}
