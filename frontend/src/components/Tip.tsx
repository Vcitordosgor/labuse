import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { ReactNode } from 'react'

/** LOI-1 (revue UI/UX) — LE tooltip de l'app, tactile et stylé DA.
 *  Remplace les `title` natifs (invisibles au doigt, non stylables, absents des captures).
 *  Survol / focus clavier → apparition ; TAP mobile → toggle (fermeture au tap
 *  extérieur ou après 4 s). Un seul dessin pour toute l'app : `.floating` + 11 px.
 *
 *  M13 D2 (QA-48) — la bulle est rendue dans un PORTAL sur <body>, en position `fixed`,
 *  AU-DESSUS de tout (z ultra-haut) : elle n'est plus rognée par le bord du panneau ni par un
 *  conteneur `overflow:auto`. Repositionnement automatique si elle déborde d'un bord de l'écran
 *  (bascule haut↔bas, recentrage horizontal borné). La largeur max reste 260 px. */
export function Tip({ tip, children, side = 'top', className = '', block = false }: {
  tip: ReactNode
  children: ReactNode
  side?: 'top' | 'bottom'
  className?: string
  block?: boolean                       // true = wrapper display:flex (lignes entières)
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLSpanElement>(null)
  const bubbleRef = useRef<HTMLSpanElement>(null)
  const [pos, setPos] = useState<{ left: number; top: number; place: 'top' | 'bottom' } | null>(null)

  // Fermeture : tap extérieur (mobile toggle) OU minuterie 4 s.
  useEffect(() => {
    if (!open) return
    const close = (e: PointerEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false)
    }
    window.addEventListener('pointerdown', close)
    const t = window.setTimeout(() => setOpen(false), 4000)
    return () => { window.removeEventListener('pointerdown', close); window.clearTimeout(t) }
  }, [open])

  // Positionnement : ancré sur le déclencheur, en coordonnées viewport (`fixed`), avec
  // repositionnement auto si la bulle touche un bord (bascule côté + recentrage horizontal borné).
  useLayoutEffect(() => {
    if (!open) { setPos(null); return }
    const compute = () => {
      const trig = ref.current?.getBoundingClientRect()
      const bub = bubbleRef.current?.getBoundingClientRect()
      if (!trig) return
      const M = 8                              // marge de sécurité au bord de l'écran
      const bw = bub?.width ?? 240
      const bh = bub?.height ?? 44
      const cx = trig.left + trig.width / 2
      // horizontal : centré, borné à l'écran
      let left = cx - bw / 2
      left = Math.max(M, Math.min(left, window.innerWidth - bw - M))
      // vertical : côté demandé, bascule si ça déborde
      let place: 'top' | 'bottom' = side
      if (place === 'top' && trig.top - bh - 6 < M) place = 'bottom'
      else if (place === 'bottom' && trig.bottom + bh + 6 > window.innerHeight - M) place = 'top'
      const top = place === 'top' ? trig.top - bh - 6 : trig.bottom + 6
      setPos({ left, top, place })
    }
    compute()
    // 2e passe une fois la bulle mesurée (largeur réelle), puis suivi scroll/resize.
    const raf = requestAnimationFrame(compute)
    window.addEventListener('scroll', compute, true)
    window.addEventListener('resize', compute)
    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('scroll', compute, true)
      window.removeEventListener('resize', compute)
    }
  }, [open, side, tip])

  return (
    <span ref={ref}
      className={`${block ? 'flex' : 'inline-flex'} ${className}`}
      onPointerEnter={(e) => { if (e.pointerType !== 'touch') setOpen(true) }}
      onPointerLeave={(e) => { if (e.pointerType !== 'touch') setOpen(false) }}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
      onClick={(e) => { e.stopPropagation(); setOpen((o) => !o) }}>
      {children}
      {open && createPortal(
        <span role="tooltip" ref={bubbleRef}
          style={{ left: pos?.left ?? 0, top: pos?.top ?? 0, visibility: pos ? 'visible' : 'hidden' }}
          className="floating pointer-events-none fixed z-[9999] w-max max-w-[260px]
            px-2.5 py-1.5 text-left text-[11px] font-normal normal-case leading-snug
            tracking-normal text-txt">
          {tip}
        </span>,
        document.body,
      )}
    </span>
  )
}
