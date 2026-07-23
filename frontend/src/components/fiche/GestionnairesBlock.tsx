/**
 * M-VIA lot 1 — Bloc « Gestionnaires » (eau · assainissement · électricité).
 *
 * Contact ADMINISTRATIF uniquement — AUCUNE donnée sensible, aucun tracé de réseau.
 * Compétence eau/assainissement = EPCI depuis 2020 (loi NOTRe) ; élec = EDF SEI partout.
 * CHAQUE association datée « à jour au [date], à revérifier annuellement ». Les
 * délégations changent aux renouvellements de contrat → confidence affichée.
 * Additif : rendu depuis la charge utile de la fiche (aucun fetch).
 */
import { TOKENS } from '../../lib/tokens'
import type { Gestionnaires, GestOperateur } from '../../lib/types'
import { Tip } from '../Tip'

function Conf({ c }: { c?: GestOperateur['confidence'] }) {
  if (!c) return null
  const meta = { high: { t: 'confirmé', color: TOKENS.viabConfirmee }, med: { t: 'à confirmer', color: TOKENS.viabIncertaine },
                 low: { t: 'incertain', color: TOKENS.viabLourde } }[c]
  return <span className="ml-1.5 rounded-full px-1.5 py-0.5 text-[9.5px]"
    style={{ backgroundColor: `${meta.color}1A`, color: meta.color }}>{meta.t}</span>
}

function Row({ icon, label, op, extra }: { icon: string; label: string; op: GestOperateur | null; extra?: string | null }) {
  return (
    <div className="flex items-baseline gap-2 text-[11.5px]">
      <span aria-hidden className="w-4 shrink-0 text-center text-txt-mut">{icon}</span>
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
  return (
    <div data-gestionnaires className="card-elev px-3 py-2.5">
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-txt-hi">Gestionnaires (raccordement)</span>
        {g.a_jour_au && (
          <Tip tip="Les délégations changent aux renouvellements de contrat — à revérifier annuellement" className="ml-auto">
            <span className="rounded-full bg-line-2 px-2 py-0.5 text-[10px] text-txt-dim">
              à jour {g.a_jour_au}
            </span>
          </Tip>
        )}
      </div>

      <div className="mt-2 flex flex-col gap-1">
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

      {g.note && <p className="mt-2 text-[11px] leading-snug text-st-creuser">{g.note}</p>}
      {g.disclaimer && <p className="mt-1.5 text-[10.5px] leading-snug text-txt-dim">{g.disclaimer}</p>}
    </div>
  )
}
