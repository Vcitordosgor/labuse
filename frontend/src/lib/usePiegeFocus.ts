// FIX-NU3-2 (M-A04) — PIÈGE DE FOCUS réutilisable pour les modales/tiroirs. Généralise le patron
// exemplaire d'AccueilCopilote (brief) : quand la modale est ouverte, Tab/Shift+Tab bouclent À
// L'INTÉRIEUR, Échap ferme, le focus initial va dans le panneau, et À LA FERMETURE le focus est
// RENDU à l'élément déclencheur. WCAG 2.1.2 (pas de piège inverse) / 2.4.3 (ordre de focus).
import { useEffect, type RefObject } from 'react'

const SELECTEUR_FOCUSABLE =
  'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), ' +
  'textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

/**
 * @param actif  la modale est-elle ouverte ?
 * @param ref    conteneur de la modale (reçoit/piège le focus)
 * @param onClose appelé sur Échap
 */
export function usePiegeFocus(
  actif: boolean,
  ref: RefObject<HTMLElement | null>,
  onClose: () => void,
): void {
  useEffect(() => {
    if (!actif) return
    const declencheur = document.activeElement as HTMLElement | null
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { onClose(); return }
      if (e.key === 'Tab' && ref.current) {
        const foc = Array.from(ref.current.querySelectorAll<HTMLElement>(SELECTEUR_FOCUSABLE))
          .filter((el) => el.offsetParent !== null || el === document.activeElement)
        if (!foc.length) return
        const first = foc[0], last = foc[foc.length - 1]
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
      }
    }
    document.addEventListener('keydown', onKey)
    // focus initial : le 1ᵉʳ élément focusable du panneau (sinon le panneau lui-même).
    const t = window.setTimeout(() => {
      const cible = ref.current?.querySelector<HTMLElement>(SELECTEUR_FOCUSABLE)
      ;(cible ?? ref.current)?.focus?.()
    }, 0)
    return () => {
      document.removeEventListener('keydown', onKey)
      window.clearTimeout(t)
      declencheur?.focus?.()   // restitution au déclencheur
    }
  }, [actif, ref, onClose])
}
