// OUTIL-COMMUNES-FIX-7 LOT 3 — la case « État du PLU » du grand bandeau porte la DATE de la dernière
// pièce connue (etat_au), pas seulement le statut. Helper pur : rend la sous-ligne de la tuile.
import { fmtDateNum } from './format'

export function bandeauEtatPluSous(etatAuIso?: string | null): string {
  // LOT 3 : la case « État du PLU » du grand bandeau porte la DATE de la dernière pièce connue.
  return etatAuIso ? `au ${fmtDateNum(etatAuIso)}` : 'GPU · Sudocuh'
}
