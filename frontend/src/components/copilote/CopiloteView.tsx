// M26-B — écran Copilote (vue de premier niveau). PROJECTION de l'event log M26-A :
// aucune logique métier, aucun recalcul. Design : maquette B4 de référence
// (docs/mandats/copilote_maquette_B4_reference_M26B.html), tokens cp-*.
// Point B : l'état 1 (instruction terminée) est complet ; pendant l'instruction on
// n'affiche AUCUN résultat partiel (règle 5) — les états 2 à 5 viennent après la
// validation visuelle de Vic (les rendus transitoires ci-dessous restent sobres).
import { useState } from 'react'
import type { MissionActive } from '../../lib/copilote'
import { CLIENT } from '../../lib/strings'
import { BlocLivrable } from './BlocLivrable'
import { Entonnoir } from './Entonnoir'
import { FilInstruction } from './FilInstruction'
import { Resultats, type EtiquettesMoteurs } from './Resultats'
import { PillStatut, SecHead } from './ui'
import { useCopiloteRun } from './useCopiloteRun'
import type { VueCopilote } from './reduireEvenements'

const S = CLIENT.copilote

// halo discret de la maquette (radial mint en haut à droite, violet en bas à gauche)
const FOND = {
  backgroundImage:
    'radial-gradient(ellipse 900px 460px at 78% -10%, rgba(99,242,184,.06), transparent 62%), ' +
    'radial-gradient(ellipse 700px 460px at 5% 105%, rgba(180,151,240,.05), transparent 62%)',
}

const TON_STATUT: Record<string, 'mint' | 'violet' | 'ambre' | 'rouge'> = {
  interpreting: 'violet', running: 'violet', awaiting_user: 'ambre', paused: 'ambre',
  done: 'mint', failed: 'rouge', cancelled: 'rouge',
}

function Missions({ mission, setMission, verrouille }: {
  mission: MissionActive
  setMission: (m: MissionActive) => void
  verrouille: boolean
}) {
  return (
    <div data-missions className="mt-3 flex flex-wrap items-center gap-2">
      {S.missions.map((m) => m.actif ? (
        <button key={m.key} data-mission={m.key} disabled={verrouille}
          onClick={() => setMission(m.key as MissionActive)}
          className={`rounded-lg border px-3 py-1.5 font-display text-[11px] font-semibold transition-colors duration-quick ${
            mission === m.key
              ? 'border-cp-mint/50 bg-cp-mint/10 text-cp-mint'
              : 'border-cp-line2 bg-cp-card2 text-cp-muted hover:border-cp-mint/40'} ${
            verrouille ? 'cursor-default opacity-60' : ''}`}>
          {m.label}
        </button>
      ) : (
        <span key={m.key} data-mission={m.key} data-mission-bientot
          className="flex items-center gap-1.5 rounded-lg border border-cp-line px-3 py-1.5 font-display text-[11px] font-semibold text-cp-faint opacity-60">
          {m.label}
          <span className="rounded border border-cp-line2 px-1 py-px text-[8.5px] uppercase tracking-[.1em]">{S.bientot}</span>
        </span>
      ))}
    </div>
  )
}

/** Étiquette produite par chaque moteur, lue dans le fil (payload, jamais inventée). */
const etiquettesDe = (vue: VueCopilote): EtiquettesMoteurs => {
  const de = (m: string) => vue.etapes.find((e) => e.moteur === m)?.fait?.etiquette ?? null
  return { criblage: de('criblage'), faisabilite: de('faisabilite'),
           marche_dvf: de('marche_dvf'), risques: de('risques') }
}

function Journal({ evenements, fermer }: {
  evenements: ReturnType<typeof useCopiloteRun>['evenements']; fermer: () => void
}) {
  return (
    <div data-journal className="mt-4 rounded-2xl border border-cp-line bg-cp-card px-5 py-4">
      <div className="mb-3 flex items-baseline gap-3">
        <h3 className="font-display text-[13.5px] font-semibold text-cp-txt">{S.journal.titre}</h3>
        <p className="text-[11px] text-cp-faint">{S.journal.sousTitre}</p>
        <button onClick={fermer} className="ml-auto text-[11px] text-cp-muted hover:text-cp-txt">
          {S.journal.fermer} ✕
        </button>
      </div>
      <div className="max-h-[420px] overflow-y-auto font-mono text-[10.5px] leading-relaxed text-cp-muted">
        {evenements.map((e) => (
          <div key={e.seq} className="border-b border-cp-line py-1.5 last:border-none">
            <span className="text-cp-faint">#{e.seq}</span>{' '}
            <span className="font-semibold text-cp-txt">{e.kind}</span>{' '}
            <span className="break-all">{JSON.stringify(e.payload)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export function CopiloteView() {
  const run = useCopiloteRun()
  const { vue } = run
  const [brief, setBrief] = useState('')
  const [mission, setMission] = useState<MissionActive>('instruire')
  const [reponse, setReponse] = useState('')
  const [journalOuvert, setJournalOuvert] = useState(false)

  const actif = run.runId != null
  const terminal = vue.statut === 'done' || vue.statut === 'failed' || vue.statut === 'cancelled'
  const enInstruction = actif && !terminal && vue.statut !== 'awaiting_user'
  const fini = vue.statut === 'done' && vue.recap != null
  const communes = (vue.briefJson?.communes as string[] | undefined) ?? null
  const nLogements = (vue.briefJson?.programme as { logements?: number } | undefined)?.logements

  const lancer = () => {
    if (brief.trim() && !enInstruction && !run.enCreation) void run.instruire(mission, brief)
  }

  return (
    <div data-copilote className="min-h-0 flex-1 overflow-y-auto bg-cp-bg font-sans text-[13px] text-cp-txt" style={FOND}>
      <div className="mx-auto max-w-[1000px] px-6 pb-12 pt-9">
        <div className="mb-4 flex items-center gap-3">
          <span className="font-display text-[10.5px] uppercase tracking-[.24em] text-cp-muted">{S.crumb}</span>
          {actif && (
            <PillStatut ton={TON_STATUT[vue.statut] ?? 'violet'}
              pulse={vue.statut === 'running' || vue.statut === 'interpreting'}>
              {S.statuts[vue.statut] ?? vue.statut}
            </PillStatut>
          )}
          {run.fluxInterrompu && (
            <span data-flux-interrompu className="text-[10.5px] text-cp-amber">{S.fluxInterrompu}</span>
          )}
        </div>

        <h1 className="font-display text-[clamp(30px,5vw,44px)] font-bold leading-[1.05] tracking-tight text-cp-txt">
          {S.h1Ligne1}<br />{S.h1Ligne2Avant}<em className="not-italic text-cp-mint">{S.h1Ligne2Em}</em>{S.h1Ligne2Apres}
        </h1>
        <p className="mb-6 mt-3 max-w-[600px] text-[13.5px] text-cp-muted">
          {S.lede}<b className="font-medium text-cp-txt">{S.ledeFort}</b>
        </p>

        <div className={`flex flex-wrap items-start gap-5 rounded-[18px] border border-cp-mint/35 bg-gradient-to-b from-cp-mint/5 to-white/[0.015] p-5 shadow-[0_0_60px_rgba(99,242,184,.06)] ${
          enInstruction ? 'opacity-65' : ''}`}>
          <div className="min-w-[250px] flex-1">
            <textarea data-brief value={brief} onChange={(e) => setBrief(e.target.value)}
              readOnly={enInstruction} placeholder={S.placeholder} rows={2}
              className="w-full resize-none bg-transparent font-sans text-base leading-normal text-cp-txt outline-none placeholder:text-cp-faint" />
          </div>
          <div className="flex flex-col items-end gap-2">
            {enInstruction ? (
              <button data-annuler onClick={() => void run.annuler()}
                className="rounded-[13px] border border-cp-line2 px-6 py-3.5 font-display text-[13px] font-bold uppercase tracking-wide text-cp-muted">
                {S.annuler}
              </button>
            ) : (
              <button data-instruire onClick={lancer} disabled={!brief.trim() || run.enCreation}
                className="rounded-[13px] bg-cp-mint px-7 py-3.5 font-display text-[13px] font-bold uppercase tracking-wide text-[#08130E] shadow-[0_0_36px_rgba(99,242,184,.28)] transition-transform duration-quick hover:brightness-110 disabled:opacity-40">
                {S.instruire} →
              </button>
            )}
            <div className="flex items-center gap-2 text-[10.5px] text-cp-faint">
              <i className="h-1 w-1 rounded-full bg-cp-mint" />{S.serment}
            </div>
          </div>
        </div>
        <Missions mission={mission} setMission={setMission} verrouille={enInstruction} />

        {run.quota && (
          <p data-quota className="mt-5 rounded-xl border border-cp-red/30 bg-cp-red/10 px-4 py-3 text-[12px] text-cp-red">
            {run.quota.detail}
          </p>
        )}
        {run.erreur && (
          <p data-erreur className="mt-5 rounded-xl border border-cp-red/30 bg-cp-red/10 px-4 py-3 text-[12px] text-cp-red">
            {run.erreur}
          </p>
        )}

        {/* règle 5 : AUCUN résultat partiel pendant l'instruction — rendu transitoire
            sobre ; le fil vivant (état 2) vient après validation du Point B */}
        {actif && !terminal && vue.statut !== 'awaiting_user' && (
          <div data-en-cours className="mt-9 rounded-2xl border border-dashed border-cp-line2 bg-cp-card px-8 py-9 text-center text-[12.5px] text-cp-faint">
            {vue.statut === 'interpreting' ? S.interpretationEnCours : S.enCours}
            <br />{S.enCoursNote}
          </div>
        )}

        {/* clarification — gabarit provisoire (état 3 complet après validation du B) :
            fonctionnel pour ne pas bloquer un run réel, sans prétendre au design final */}
        {vue.statut === 'awaiting_user' && vue.clarification && (
          <div data-clarification className="mt-9 rounded-2xl border border-cp-violet/35 bg-cp-card px-6 py-5">
            <div className="mb-2.5 font-display text-[9.5px] uppercase tracking-[.2em] text-cp-violet">{S.precisionTitre}</div>
            <h3 className="font-display text-lg font-semibold text-cp-txt">{vue.clarification.question}</h3>
            <div className="mt-4 flex flex-wrap gap-2">
              {(vue.clarification.options ?? []).map((o) => (
                <button key={o} onClick={() => void run.repondre(o)}
                  className="rounded-xl border border-cp-line2 bg-cp-card2 px-4 py-2.5 font-display text-[12.5px] font-semibold text-cp-txt hover:border-cp-mint hover:text-cp-mint">
                  {o}
                </button>
              ))}
            </div>
            <div className="mt-3.5 flex gap-2 rounded-[13px] border border-cp-line2 bg-cp-card2 p-1.5">
              <input value={reponse} onChange={(e) => setReponse(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && reponse.trim()) void run.repondre(reponse) }}
                placeholder={S.precisionPlaceholder}
                className="flex-1 bg-transparent px-3 py-2.5 text-[13px] text-cp-txt outline-none placeholder:text-cp-faint" />
              <button disabled={!reponse.trim()} onClick={() => void run.repondre(reponse)}
                className="rounded-[10px] bg-cp-violet px-5 py-2.5 font-display text-[12px] font-bold text-[#150E22] disabled:opacity-40">
                {S.precisionReprendre}
              </button>
            </div>
          </div>
        )}

        {vue.statut === 'cancelled' && (
          <p data-annulee className="mt-9 rounded-2xl border border-cp-line2 bg-cp-card px-6 py-5 text-[12.5px] text-cp-muted">
            {S.annulee}{vue.motifAnnulation ? ` — ${vue.motifAnnulation}` : ''}
          </p>
        )}
        {vue.statut === 'failed' && vue.echec && (
          <p data-echec className="mt-9 rounded-2xl border border-cp-red/30 bg-cp-red/[0.06] px-6 py-5 text-[12.5px] leading-relaxed text-cp-txt">
            {vue.echec.message}{vue.echec.detail ? <span className="text-cp-muted"> ({vue.echec.detail})</span> : null}
          </p>
        )}

        {/* ── état 1 : instruction terminée ─────────────────────────────────── */}
        {fini && vue.recap && (
          <>
            <SecHead titre={S.entonnoir.titre} sousTitre={S.entonnoir.sousTitre} />
            <Entonnoir recap={vue.recap} communes={communes} dureeMs={vue.final?.duree_totale_ms ?? null} />

            <SecHead titre={S.fil.titre} meta={S.fil.meta(vue.etapes.length)} />
            <FilInstruction etapes={vue.etapes} />

            <SecHead titre={S.resultats.titre(vue.recap.n_restituees)}
              meta={S.resultats.meta(vue.recap.n_retenues)} />
            {vue.recap.n_restituees > 0 ? (
              <Resultats recap={vue.recap} etiquettes={etiquettesDe(vue)}
                titre={[communes?.join(', '), nLogements != null ? `${nLogements} logements` : null]
                  .filter(Boolean).join(' · ')} />
            ) : (
              // zéro n'est PAS une erreur (règle 6) — panneau complet de l'état 4 après le B
              <div data-zero className="rounded-2xl border border-cp-line2 bg-cp-card px-8 py-9 text-center">
                <h3 className="font-display text-[17px] font-semibold text-cp-txt">{S.resultats.zeroTitre}</h3>
                <p className="mt-2 text-[12px] text-cp-muted">{S.resultats.zeroNote}</p>
              </div>
            )}
            <BlocLivrable recap={vue.recap} nMoteurs={vue.etapes.length}
              ouvrirJournal={() => setJournalOuvert(true)} />
            {journalOuvert && <Journal evenements={run.evenements} fermer={() => setJournalOuvert(false)} />}
          </>
        )}
      </div>
    </div>
  )
}
