/**
 * M125-2 — Copropriété(s) immatriculée(s) (RNIC) rattachée(s) à la parcelle.
 * Signal informatif (cible bailleur / acquisition en copropriété), jamais un verdict. Rendu
 * seulement si au moins une copropriété est rattachée. Aucun fetch (charge utile de la fiche).
 */
import type { Copropriete } from '../../lib/types'

function detail(c: Copropriete): string {
  const bouts: string[] = []
  if (c.nb_lots_total != null) {
    let lots = `${c.nb_lots_total} lot${c.nb_lots_total > 1 ? 's' : ''}`
    if (c.nb_lots_habitation != null) lots += ` (dont ${c.nb_lots_habitation} hab.)`
    bouts.push(lots)
  }
  if (c.periode_construction) bouts.push(c.periode_construction)
  if (c.syndic_nom || c.syndic_type) {
    bouts.push(`syndic ${[c.syndic_type, c.syndic_nom].filter(Boolean).join(' · ')}`)
  }
  return bouts.join(' · ')
}

export function CoproprietesBlock({ copros }: { copros: Copropriete[] }) {
  if (!copros || copros.length === 0) return null
  return (
    <div data-coproprietes className="card-elev px-3 py-2.5">
      <span className="text-xs font-medium text-txt-hi">
        Copropriété{copros.length > 1 ? 's' : ''} rattachée{copros.length > 1 ? 's' : ''}
      </span>
      <div className="mt-2 flex flex-col gap-1.5">
        {copros.map((c) => (
          <div key={c.numero_immatriculation} className="text-[11px] leading-snug text-txt">
            <b className="font-medium text-txt-hi">{c.nom_usage || c.numero_immatriculation}</b>
            {detail(c) && <span className="text-txt-mut"> · {detail(c)}</span>}
            {c.adresse && <div className="text-[10.5px] text-txt-dim">{c.adresse}</div>}
          </div>
        ))}
      </div>
      <p className="mt-2 text-[10.5px] leading-snug text-txt-dim">
        Source : RNIC (registre national des copropriétés) — information, jamais un verdict.
      </p>
    </div>
  )
}
