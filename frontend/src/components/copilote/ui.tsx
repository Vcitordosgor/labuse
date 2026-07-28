// M26-B — primitives visuelles de l'écran Copilote (tokens cp-* de la maquette B4).
import type { ReactNode } from 'react'

/** Étiquette de provenance — la CHAÎNE DU PAYLOAD, affichée telle quelle (majuscule
 *  initiale près). Jamais inventée, jamais omise (règle 1 du mandat) : si `v` est
 *  absent du payload, l'appelant n'affiche pas le chiffre. */
export function Etiquette({ v }: { v: string }) {
  const genre = v.startsWith('sourcé') ? 'source' : v.startsWith('estimé') ? 'estime' : 'absent'
  const cls = {
    source: 'border-cp-mint/25 bg-cp-mint/10 text-cp-mint',
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

/** Badge d'en-tête (exhaustivité, calibrage) — mint = nominal, ambre = dégradé. */
export function Badge({ ton, children, data }: { ton: 'mint' | 'ambre'; children: ReactNode; data?: string }) {
  return (
    <span data-badge={data}
      className={`rounded-[5px] border px-2.5 py-0.5 font-display text-[9px] font-bold uppercase tracking-[.1em] ${
        ton === 'mint' ? 'border-cp-mint/30 bg-cp-mint/10 text-cp-mint'
                       : 'border-cp-amber/35 bg-cp-amber/10 text-cp-amber'}`}>
      {children}
    </span>
  )
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

/** Pastille d'état du run (eyebrow) — Terminé / Instruction / En pause / … */
export function PillStatut({ ton, pulse, children }: { ton: 'mint' | 'violet' | 'ambre' | 'rouge'
  pulse?: boolean; children: ReactNode }) {
  const teinte = {
    mint: 'border-cp-mint/30 bg-cp-mint/10 text-cp-mint',
    violet: 'border-cp-violet/40 bg-cp-violet/10 text-cp-violet',
    ambre: 'border-cp-amber/40 bg-cp-amber/10 text-cp-amber',
    rouge: 'border-cp-red/40 bg-cp-red/10 text-cp-red',
  }[ton]
  const point = { mint: 'bg-cp-mint', violet: 'bg-cp-violet', ambre: 'bg-cp-amber', rouge: 'bg-cp-red' }[ton]
  return (
    <span data-pill-statut
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 font-display text-[9.5px] font-bold uppercase tracking-[.14em] ${teinte}`}>
      <i className={`h-1.5 w-1.5 rounded-full ${point} ${pulse ? 'animate-pulse' : ''}`} />
      {children}
    </span>
  )
}
