// OUTIL-COMMUNES-FIX-7 LOT 3 — la case « État du PLU » du grand bandeau porte la DATE de la dernière
// pièce connue (etat_au), pas seulement le statut. Helper pur : rend la sous-ligne de la tuile.
import { fmtDateNum } from './format'

export function bandeauEtatPluSous(etatAuIso?: string | null): string {
  // LOT 3 : la case « État du PLU » du grand bandeau porte la DATE de la dernière pièce connue.
  if (!etatAuIso) return 'GPU · Sudocuh'
  // FIX-9/FIX-10 LOT 2 — le rendu de la date (mois/année/jour) vit dans `fmtDateNum` (point unique) ;
  // ici on ne choisit que la PRÉPOSITION : « en » pour une précision mois/année (« en mai 2025 »,
  // « en 2025 »), « au » pour une date au jour (« au 29/09/2025 »). Jamais un faux 1er du mois.
  const prep = /^\d{4}(-\d{2})?$/.test(etatAuIso) ? 'en' : 'au'
  return `${prep} ${fmtDateNum(etatAuIso)}`
}
