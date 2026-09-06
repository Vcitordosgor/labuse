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

// RETOURS-20 Z2 — la confiance devient une pastille standard (tokens) : confirmé = mint,
// à confirmer / incertain = ambre. Plus de couleur composée à la main (TOKENS.viab* + alpha).
function Conf({ c }: { c?: GestOperateur['confidence'] }) {
  if (!c) return null
  const meta = { high: { t: 'confirmé', cls: 'pill-mint' }, med: { t: 'à confirmer', cls: 'pill-amber' },
                 low: { t: 'incertain', cls: 'pill-amber' } }[c]
  return <span className={`ml-1.5 ${meta.cls}`}>{meta.t}</span>
}

function Row({ icon, label, op, extra }: { icon: string; label: string; op: GestOperateur | null; extra?: string | null }) {
  return (
    <div className="flex items-baseline gap-1.5 text-[11.5px]">
      <span aria-hidden className="shrink-0 text-txt-mut">{icon}</span>
      <span className="w-24 shrink-0 text-txt-dim">{label}</span>
      <span className="text-txt">
        {op ? (<><b className="font-medium text-txt-hi">{op.operateur}</b><Conf c={op.confidence} />
          {op.type && <span className="text-txt-dim"> · {op.type}</span>}</>)
          : <span className="text-txt-mut">{extra ?? 'non renseigné'}</span>}
      </span>
    </div>
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
      <div className="mt-1 flex flex-col gap-1">
        {g.epci.nom && (
          <Row icon="◆" label="Compétence" op={{ operateur: `${g.epci.code} — ${g.epci.nom}`, type: g.epci.contact ?? undefined }} />
        )}
        <Row icon="≈" label="Eau potable" op={g.eau} />
        <Row icon="∿" label="Assainissement" op={g.assainissement} />
        {g.spanc && <Row icon="◇" label="SPANC (ANC)" op={{ operateur: g.spanc }} />}
        {g.electricite && (
          <Row icon="↯" label="Électricité" op={{ operateur: g.electricite.gestionnaire, type: g.electricite.raccordement }} />
        )}
      </div>

      {/* Z3 — les paragraphes de méthode passent en NOTE 11,5 px sous les lignes (plus de plein texte). */}
      {g.note && <FactNote>{g.note}</FactNote>}
      {g.disclaimer && <FactNote>{g.disclaimer}</FactNote>}
    </div>
  )
}
