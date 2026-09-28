/**
 * M-VIA lot 1 — Bloc « Gestionnaires » (eau · assainissement · électricité).
 *
 * Contact ADMINISTRATIF uniquement — AUCUNE donnée sensible, aucun tracé de réseau.
 * Compétence eau/assainissement = EPCI depuis 2020 (loi NOTRe) ; élec = EDF SEI partout.
 * CHAQUE association datée « à jour au [date], à revérifier annuellement ». Les
 * délégations changent aux renouvellements de contrat → confidence affichée.
 * Additif : rendu depuis la charge utile de la fiche (aucun fetch).
 */
import { BlocIndisponible } from './BlocIndisponible'
import type { Gestionnaires, GestOperateur } from '../../lib/types'
import { GroupLabel, FactNote } from './primitives'
import { Badge } from '../ui/Badge'
// FICHE-FIX-5 (Lot G) — gestionnaires en Lignes courtes (opérateur · type), les paragraphes de
// méthode (bascule Runéo/Dionéo, DT-DICT) en source.
import { Lignes, Ligne } from './formes'

const CONF_META = { high: { t: 'confirmé', ton: 'vert' as const }, med: { t: 'à confirmer', ton: 'ambre' as const }, low: { t: 'incertain', ton: 'ambre' as const } }
function GestLigne({ label, op }: { label: string; op: GestOperateur | null }) {
  if (!op) return <Ligne label={label} ton="gris" valeur="non renseigné" />
  const c = op.confidence ? CONF_META[op.confidence] : null
  return (
    <Ligne label={label} title={`${op.operateur}${op.type ? ` · ${op.type}` : ''}`}
      valeur={<>{op.operateur}{op.type ? <small> · {op.type}</small> : null}{c ? <> <Badge ton={c.ton}>{c.t}</Badge></> : null}</>} />
  )
}


export function GestionnairesBlock({ g }: { g: Gestionnaires }) {
  if (g.indisponible) return <BlocIndisponible titre="Gestionnaires (raccordement)" />   // M125 — panne ≠ absence
  return (
    <div data-gestionnaires>
      {/* RETOURS-20 Z1·02 / Z3 — le titre encadré (card-elev) devient un KICKER : texte + filet,
          plus de boîte dans la boîte. Lignes, note et disclaimer inchangés (données identiques).
          M70 point 4 — la date « à jour {millésime} » reste retirée du bloc (bruit). */}
      <GroupLabel>Gestionnaires (raccordement)</GroupLabel>
      <Lignes>
        {g.epci.nom && <GestLigne label="Compétence" op={{ operateur: `${g.epci.code} — ${g.epci.nom}`, type: g.epci.contact ?? undefined }} />}
        <GestLigne label="Eau potable" op={g.eau} />
        <GestLigne label="Assainissement" op={g.assainissement} />
        {g.spanc && <GestLigne label="SPANC (ANC)" op={{ operateur: g.spanc }} />}
        {g.electricite && <GestLigne label="Électricité" op={{ operateur: g.electricite.gestionnaire, type: g.electricite.raccordement }} />}
      </Lignes>

      {/* Z3 — les paragraphes de méthode passent en NOTE 11,5 px sous les lignes (plus de plein texte). */}
      {g.note && <FactNote>{g.note}</FactNote>}
      {g.disclaimer && <FactNote>{g.disclaimer}</FactNote>}
    </div>
  )
}
