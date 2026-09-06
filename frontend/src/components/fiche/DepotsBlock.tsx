/**
 * M38 — Activité de DÉPÔT (Sitadel3 `date_depot`). Informatif seul : redate l'activité sur le
 * dépôt (~9 mois avant l'autorisation servie), ne touche NI tier NI verdict.
 *
 * Deux lignes HIÉRARCHISÉES et DISTINCTES (arbitrage Vic Phase 0 §3), jamais fusionnées :
 *  - « sur cette parcelle » — dépôts rattachés (IDU) à la parcelle consultée ;
 *  - « sur le secteur »     — dépôts de la section cadastrale, activité alentour.
 * Étiquette d'honnêteté obligatoire : permis AUTORISÉS datés au dépôt, jamais « en instance ».
 * Le bloc n'est pas rendu hors couverture (payload `depots` = null).
 */
import { BlocIndisponible } from './BlocIndisponible'
import { GroupLabel, FactNote } from './primitives'

type Ligne = { count: number; dernier: string | null; maille?: string }
type Depots = {
  indisponible?: boolean   // M125 — panne technique (≠ absence)
  raison?: string
  fenetre_mois: number
  source: string
  sourcage: string
  millesime: string | null
  libelle: string
  granularite: string
  parcelle: Ligne | null
  secteur: Ligne | null
}

export function DepotsBlock({ d }: { d: Depots }) {
  if (d?.indisponible) return <BlocIndisponible titre="Activité de dépôt (Sitadel)" />   // M125 — panne ≠ absence
  if (!d || (!d.parcelle && !d.secteur)) return null
  const mois = d.fenetre_mois
  return (
    <div data-depots>
      {/* Z1·02 / Z3 — la boîte (card-elev) devient un KICKER + badge de source à droite ; plus de
          boîte dans la boîte. Les deux lignes et la note de méthode (→ FactNote) sont inchangées. */}
      <GroupLabel right={
        <span className="rounded-full border border-mint/40 bg-mint/10 px-2 py-0.5 text-[10px] font-semibold text-mint">
          {d.sourcage} {d.source}
        </span>
      }>Activité de dépôt de permis</GroupLabel>
      <div className="mt-1 flex flex-col gap-1">
        {d.parcelle && (
          <p className="text-[11px] leading-snug text-txt">
            <span className="text-txt-dim">Sur cette parcelle :</span>{' '}
            <b>{d.parcelle.count}</b> dépôt{d.parcelle.count > 1 ? 's' : ''} sur {mois} mois
            {d.parcelle.dernier && <span className="text-txt-mut"> · dernier {d.parcelle.dernier}</span>}
          </p>
        )}
        {d.secteur && (
          <p className="text-[11px] leading-snug text-txt">
            <span className="text-txt-dim">Sur le secteur :</span>{' '}
            <b>{d.secteur.count}</b> dépôt{d.secteur.count > 1 ? 's' : ''} sur {mois} mois
            <span className="text-txt-mut"> · {d.secteur.maille}</span>
            {d.secteur.dernier && <span className="text-txt-mut"> · dernier {d.secteur.dernier}</span>}
          </p>
        )}
      </div>
      <FactNote>{d.libelle}.</FactNote>
    </div>
  )
}
