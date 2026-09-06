/**
 * M125-2 — Contexte socio-économique du secteur (Filosofi 200 m au centroïde + parc social RPLS
 * de la commune). Contexte informatif, HORS scoring. Chaque sous-bloc porte SON millésime (daté,
 * jamais un millésime unique). Rendu seulement si au moins une source est présente.
 */
import type { MarcheSecteur } from '../../lib/types'
import { GroupLabel, FactRow, FactNote } from './primitives'

function eur(n: number | null): string {
  return n == null ? '—' : `${Math.round(n).toLocaleString('fr-FR')} €`
}

export function MarcheSecteurBlock({ ms }: { ms: MarcheSecteur }) {
  const f = ms.filosofi_200m
  const r = ms.rpls_commune
  if (!f && !r) return null
  const partProp = f && f.men > 0 ? Math.round((100 * f.men_prop) / f.men) : null
  // RETOURS-20 Z1·02/Z3 — plus de card-elev : le titre devient un KICKER, chaque chiffre une
  // FactRow (valeur mono à droite, source datée dessous). Données/libellés/millésimes inchangés.
  return (
    <div data-marche-secteur>
      <GroupLabel>Contexte socio-économique (secteur)</GroupLabel>
      {f && (
        <>
          {/* RETOURS-11F4 F9 — Filosofi = carreau INSEE 200 m : Sourcé (jamais « estimé »). */}
          <FactRow label="Niveau de vie médian" value={eur(f.nivvie_moyen_eur)}
            src={<><span className="b s">sourcé</span>{f.millesime}</>} />
          {partProp != null && (
            <FactRow label="Propriétaires" value={<>{partProp} <small>%</small></>} />
          )}
          {f.taux_pauvrete_pct != null && (
            <FactRow label="Pauvreté" value={<>{f.taux_pauvrete_pct} <small>%</small></>} />
          )}
        </>
      )}
      {r && (
        <>
          <FactRow label="Parc social" value={<>{r.nb_logements.toLocaleString('fr-FR')} <small>logements</small></>}
            src={r.millesime} />
          {r.pct_qpv != null && (
            <FactRow label="En QPV" value={<>{r.pct_qpv} <small>%</small></>} />
          )}
        </>
      )}
      <FactNote>Contexte informatif — hors scoring.</FactNote>
    </div>
  )
}
