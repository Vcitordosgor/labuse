import type { GabScene } from '../../lib/api'
import { fmtDec } from '../../lib/format'

export const mesure = (n: number) => fmtDec(n, Number.isInteger(n) ? 0 : 1)

export function EmpriseProjet({ regles }: { regles: GabScene['regles'] }) {
  const { plafondEmpriseM2, batiConserveM2, empriseSupplementaireM2, surfacesContinuesM2 } = regles
  const solde = plafondEmpriseM2 != null && batiConserveM2 != null && empriseSupplementaireM2 != null
  const morceaux = surfacesContinuesM2 ?? []
  if (!solde && morceaux.length < 2) return null
  return <div data-gabarit-emprise-projet className="shrink-0 space-y-1 text-xs text-txt-mut">
    {solde && <p><strong className="text-txt">Emprise supplémentaire estimée · {mesure(empriseSupplementaireM2)} m²</strong>
      <br />Plafond total {mesure(plafondEmpriseM2)} m² · bâti cartographié conservé {mesure(batiConserveM2)} m².</p>}
    {morceaux.length > 1 && <p>{morceaux.length} surfaces séparées · {mesure(morceaux[0])} m² pour la plus grande.</p>}
  </div>
}
