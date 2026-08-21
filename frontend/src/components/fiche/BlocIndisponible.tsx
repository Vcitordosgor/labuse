/**
 * M125 (boussole : jamais un constat non sourcé) — bloc « Donnée indisponible ».
 *
 * Quand un builder de fiche LÈVE (panne technique), le back renvoie `{ indisponible: true }`
 * plutôt que null : on rend ALORS ce message EN CLAIR, à la place du bloc — jamais un vide qui se
 * lirait comme « rien à signaler ». La cause (incident technique) est distincte d'une absence de
 * donnée. Léger (pas de carte forcée) pour tenir aussi bien en tiroir qu'en bloc autonome.
 */
import { TOKENS } from '../../lib/tokens'

export function BlocIndisponible({ titre }: { titre?: string }) {
  return (
    <div data-indisponible className="rounded-md px-2.5 py-2 text-[11.5px] leading-snug"
      style={{ backgroundColor: TOKENS.warnBg, color: TOKENS.warnDim }}>
      {titre && <span className="font-medium">{titre} — </span>}
      Donnée indisponible — erreur technique. Le calcul n’a pas abouti (incident)&nbsp;; ce n’est pas
      une absence de donnée.
    </div>
  )
}
