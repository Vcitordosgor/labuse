// DA-FIX-3 Lot 2 (DA-026) — LE composant case à cocher unique.
// Carré 16 px, rayon 4, contour vert ; cochée = aplat vert plein + coche sombre. L'input natif reste
// à l'intérieur (masqué, `sr-only`) pour le clavier et l'accessibilité. Désactivé = règle globale.
import type { InputHTMLAttributes, ReactNode } from 'react'

export interface CaseProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  /** libellé optionnel rendu à droite de la case. */
  label?: ReactNode
}

export function Case({ label, className = '', disabled, ...rest }: CaseProps) {
  return (
    <label className={`inline-flex items-center gap-2 ${disabled ? 'cursor-not-allowed opacity-40' : 'cursor-pointer'} ${className}`.trim()}>
      <span className="relative inline-flex h-4 w-4 shrink-0 items-center justify-center">
        <input type="checkbox" disabled={disabled}
          className="peer sr-only" {...rest} />
        <span aria-hidden="true"
          className="pointer-events-none absolute inset-0 rounded-[4px] border border-mint bg-transparent transition-colors duration-quick peer-checked:bg-mint peer-focus-visible:border-mint" />
        <svg aria-hidden="true" viewBox="0 0 12 12"
          className="pointer-events-none relative h-2.5 w-2.5 opacity-0 transition-opacity duration-quick peer-checked:opacity-100"
          style={{ color: 'var(--mint-on)' }}>
          <polyline points="2.5,6.5 5,9 9.5,3.5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
      {label != null && <span className="text-[12px] text-txt">{label}</span>}
    </label>
  )
}

export default Case
