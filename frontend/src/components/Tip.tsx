import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'

/** LOI-1 (revue UI/UX) — LE tooltip de l'app, tactile et stylé DA.
 *  Remplace les `title` natifs (invisibles au doigt, non stylables, absents des captures).
 *  Survol / focus clavier → apparition 150 ms ; TAP mobile → toggle (fermeture au tap
 *  extérieur ou après 4 s). Un seul dessin pour toute l'app : `.floating` + 11 px. */
export function Tip({ tip, children, side = 'top', className = '', block = false }: {
  tip: ReactNode
  children: ReactNode
  side?: 'top' | 'bottom'
  className?: string
  block?: boolean                       // true = wrapper display:flex (lignes entières)
}) {
  const [open, setOpen] = useState(false)      // tap mobile (toggle, auto-close 4 s)
  const [hover, setHover] = useState(false)    // survol / focus clavier
  const ref = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    if (!open) return
    const close = (e: PointerEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false)
    }
    window.addEventListener('pointerdown', close)
    const t = window.setTimeout(() => setOpen(false), 4000)
    return () => { window.removeEventListener('pointerdown', close); window.clearTimeout(t) }
  }, [open])

  // QA-46 (M13-C) : le tooltip n'est MONTÉ que lorsqu'il est demandé (survol / focus / tap).
  // Auparavant il était toujours dans le DOM (opacity-0) : `position:absolute` + `w-max`, il
  // gonflait le scrollWidth de tout conteneur défilant étroit (volet Couches, liste, fiche, CARTES
  // CRM) → une BARRE DE SCROLL HORIZONTALE fantôme. Monté à la demande, il n'élargit plus rien au
  // repos ; le comportement d'affichage (apparition au survol) est identique.
  const shown = open || hover
  const pos = side === 'top' ? 'bottom-full mb-1.5' : 'top-full mt-1.5'
  return (
    <span ref={ref}
      className={`relative ${block ? 'flex' : 'inline-flex'} ${className}`}
      onClick={(e) => { e.stopPropagation(); setOpen((o) => !o) }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      onFocus={() => setHover(true)}
      onBlur={() => setHover(false)}>
      {children}
      {shown && (
        <span role="tooltip"
          className={`floating pointer-events-none absolute left-1/2 z-50 w-max max-w-[260px]
            -translate-x-1/2 px-2.5 py-1.5 text-left text-[11px] font-normal normal-case leading-snug
            tracking-normal text-txt opacity-100 ${pos}`}>
          {tip}
        </span>
      )}
    </span>
  )
}
