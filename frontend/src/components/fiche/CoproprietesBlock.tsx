/**
 * M125-2 — Copropriété(s) immatriculée(s) (RNIC) rattachée(s) à la parcelle.
 * Signal informatif (cible bailleur / acquisition en copropriété), jamais un verdict. Rendu
 * seulement si au moins une copropriété est rattachée. Aucun fetch (charge utile de la fiche).
 */
import type { Copropriete } from '../../lib/types'
import { GroupLabel, FactNote } from './primitives'

// CHIRURGICAL-FIX-1 (E100) — la période de construction RNIC est une ÉNUMÉRATION brute
// (« DE_2001_A_2010 », « AVANT_1949 », « A_COMPTER_DE_2011 »…). On la rend LISIBLE pour le client
// (« 2001–2010 », « avant 1949 », « à compter de 2011 ») au lieu d'afficher le code tel quel.
function periodeLisible(code: string | null | undefined): string | null {
  if (!code) return null
  const c = code.trim()
  if (/^NON_CONNUE$/i.test(c) || /non renseign/i.test(c)) return null
  let m = c.match(/^DE_(\d{4})_A_(\d{4})$/i)
  if (m) return `${m[1]}–${m[2]}`
  m = c.match(/^AVANT_(\d{4})$/i)
  if (m) return `avant ${m[1]}`
  m = c.match(/^A_COMPTER_DE_(\d{4})$/i)
  if (m) return `à compter de ${m[1]}`
  return c.replace(/_/g, ' ').toLowerCase()   // repli : jamais le code brut à deux-points/soulignés
}

function detail(c: Copropriete): string {
  const bouts: string[] = []
  if (c.nb_lots_total != null) {
    let lots = `${c.nb_lots_total} lot${c.nb_lots_total > 1 ? 's' : ''}`
    if (c.nb_lots_habitation != null) lots += ` (dont ${c.nb_lots_habitation} hab.)`
    // SOURCES-4 lot 1 — lots de stationnement et de commerce/bureaux (RNIC/ANAH, jusque-là dans raw).
    if (c.nb_lots_stationnement != null && c.nb_lots_stationnement > 0)
      lots += `, ${c.nb_lots_stationnement} stationnement`
    if (c.nb_lots_hab_bur_com) lots += `, ${c.nb_lots_hab_bur_com} hab./bur./com.`
    bouts.push(lots)
  }
  { const per = periodeLisible(c.periode_construction); if (per) bouts.push(per) }
  if (c.residence_service === 'oui') bouts.push('résidence-service')
  if (c.syndicat_cooperatif === 'oui') bouts.push('syndicat coopératif')
  if (c.syndic_nom || c.syndic_type) {
    // SOURCES-4 lot 1 — SIRET du syndic surfacé (colonne en base, jamais servie).
    const syndic = [c.syndic_type, c.syndic_nom, c.syndic_siret && `SIRET ${c.syndic_siret}`]
      .filter(Boolean).join(' · ')
    bouts.push(`syndic ${syndic}`)
  }
  return bouts.join(' · ')
}

// CHIRURGICAL-FIX-1 (LOT H pt5) — une copropriété rattachée « proche_20m » est À PROXIMITÉ (dans un
// rayon de 20 m), PAS sur la parcelle : BW2635 (au 2 rue d'Allemagne) affichait les copros des 4 et 6
// comme les siennes. On distingue le rattachement cadastre/géocode (sur la parcelle) du voisinage.
const estProche = (c: Copropriete) => c.rattachement === 'proche_20m'

export function CoproprietesBlock({ copros }: { copros: Copropriete[] }) {
  if (!copros || copros.length === 0) return null
  const toutesProches = copros.every(estProche)
  const pl = copros.length > 1 ? 's' : ''
  return (
    <div data-coproprietes>
      {/* RETOURS-23 Z3 — plus de card-elev : kicker + faits à plat. */}
      <GroupLabel>Copropriété{pl} {toutesProches ? 'à proximité' : `rattachée${pl}`}</GroupLabel>
      <div className="mt-1 flex flex-col gap-1.5">
        {copros.map((c) => (
          <div key={c.numero_immatriculation} className="text-[11px] leading-snug text-txt">
            <b className="font-medium text-txt-hi">{c.nom_usage || c.numero_immatriculation}</b>
            {estProche(c) && <span className="ml-1 rounded-full border border-line-2 px-1.5 py-0.5 text-[9.5px] text-txt-mut">à proximité</span>}
            {detail(c) && <span className="text-txt-mut"> · {detail(c)}</span>}
            {c.adresse && <div className="text-[10.5px] text-txt-dim">{c.adresse}{estProche(c) ? ' — à proximité (≤ 20 m), pas sur la parcelle' : ''}</div>}
          </div>
        ))}
      </div>
      <FactNote>Source : RNIC (registre national des copropriétés) — information, jamais un verdict.</FactNote>
    </div>
  )
}
