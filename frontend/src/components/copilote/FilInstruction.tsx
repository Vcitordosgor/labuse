// M26-B — le fil d'instruction : une ligne par étape du PLAN FIGÉ (run_started.plan),
// jamais une liste inventée. Résumés fixes par moteur (strings), données du payload
// affichées telles quelles (mention_sdp, compteurs, étiquettes).
import { fmtInt } from '../../lib/format'
import { CLIENT } from '../../lib/strings'
import type { EtapeVue } from './reduireEvenements'
import { Etiquette } from './ui'

const S = CLIENT.copilote.fil

function Point({ etat }: { etat: EtapeVue['etat'] | 'pause' }) {
  const [cls, glyphe] = {
    faite: ['border-cp-mint/45 text-cp-mint', '✓'],
    echouee: ['border-cp-red/50 text-cp-red', '!'],
    active: ['animate-pulse border-cp-violet text-cp-violet', '◌'],
    attente: ['border-dashed border-cp-line2 text-cp-faint', '·'],
    pause: ['border-cp-amber/45 text-cp-amber', '?'],
  }[etat]
  return (
    <div className={`flex h-[22px] w-[22px] shrink-0 items-center justify-center rounded-full border text-[11px] ${cls}`}>
      {glyphe}
    </div>
  )
}

function Ligne({ e }: { e: EtapeVue }) {
  const libelle = S.moteurs[e.moteur] ?? { nom: e.moteur, desc: '' }
  // la mention SDP du payload prime sur le résumé fixe (formulation du back, verbatim —
  // c'est elle qui porte « tracée par article » vs « règle générique »)
  const mention = (e.fait?.resultat as { mention_sdp?: string } | undefined)?.mention_sdp
  const resume = e.etat === 'echouee' ? e.echec?.resume : mention ?? libelle.desc
  const compteur = e.fait?.compteur
  return (
    <div data-fil-etape={e.moteur} data-etat={e.etat}
      className={`flex flex-wrap items-center gap-3 border-b border-cp-line py-3 last:border-none ${
        e.etat === 'attente' ? 'opacity-30' : ''}`}>
      <Point etat={e.etat} />
      <div className="min-w-[128px] font-display text-[12.5px] font-semibold text-cp-txt">{libelle.nom}</div>
      <div className="text-[12px] text-cp-muted">{e.etat === 'attente' ? S.enAttente : resume}</div>
      {e.fait && <Etiquette v={e.fait.etiquette} />}
      {compteur && (
        <div className="ml-auto font-display text-[11.5px] tabular-nums text-cp-faint">
          {fmtInt(compteur.avant)} → <b className="font-bold text-cp-mint">{fmtInt(compteur.apres)}</b>
        </div>
      )}
    </div>
  )
}

export function FilInstruction({ etapes, interpretation }: {
  etapes: EtapeVue[]
  /** Ligne « Interprétation » en tête de fil (états 2/3) — omise sur le fil final. */
  interpretation?: 'faite' | 'active' | 'pause'
}) {
  const SI = CLIENT.copilote.interpretation
  return (
    <div data-fil className="rounded-2xl border border-cp-line bg-cp-card px-5 py-1.5">
      {interpretation && (
        <div data-fil-etape="interpretation" data-etat={interpretation}
          className="flex flex-wrap items-center gap-3 border-b border-cp-line py-3 last:border-none">
          <Point etat={interpretation === 'faite' ? 'faite' : interpretation === 'pause' ? 'pause' : 'active'} />
          <div className="min-w-[128px] font-display text-[12.5px] font-semibold text-cp-txt">{SI.nom}</div>
          <div className="text-[12px] text-cp-muted">{SI[interpretation]}</div>
        </div>
      )}
      {etapes.map((e) => <Ligne key={e.moteur} e={e} />)}
    </div>
  )
}
