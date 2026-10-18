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
  // FRONT-CHIFFRES-2 (F58) — part de propriétaires SERVIE ; le front ne recalcule plus
  // 100 × men_prop / men (même formule vit au back pour le scoring → source unique, pas de divergence).
  const partProp = f?.part_proprietaires_pct ?? null
  // RETOURS-20 Z1·02/Z3 — plus de card-elev : le titre devient un KICKER, chaque chiffre une
  // FactRow (valeur mono à droite, source datée dessous). Données/libellés/millésimes inchangés.
  return (
    <div data-marche-secteur>
      {f && (
        <>
          {/* FICHE-ORFEVRERIE-1 (Lot B, pt 17) — chaque bloc porte SON ÉCHELLE : revenus = carreau INSEE
              200 m. « Niveau de vie moyen » est VÉRIFIÉ : le champ servi est la MOYENNE du carreau
              Filosofi (nivvie_moyen_eur, CHASSE-DONNEES-FIX-1 E-70), pas la médiane — « moyen » est exact. */}
          <GroupLabel>Revenus du secteur · carreau INSEE 200 m</GroupLabel>
          <FactRow label="Niveau de vie moyen" value={eur(f.nivvie_moyen_eur)}
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
          {/* FICHE-ORFEVRERIE-1 (Lot B, pt 17) — le PARC SOCIAL (RPLS, maille COMMUNE) SORT du bloc
              « secteur » : son propre kicker d'échelle, pour qu'un chiffre communal ne se lise pas
              comme du secteur (carreau 200 m). */}
          <GroupLabel>Parc social · commune entière</GroupLabel>
          <FactRow label="Parc social" value={<>{r.nb_logements.toLocaleString('fr-FR')} <small>logements</small></>}
            src={<>{r.millesime} · maille commune</>} />
          {r.pct_qpv != null && (
            <FactRow label="En QPV — commune" value={<>{r.pct_qpv} <small>%</small></>} />
          )}
        </>
      )}
      <FactNote>Contexte informatif. Revenus et pauvreté au carreau 200 m ; parc social à la commune.</FactNote>
    </div>
  )
}
