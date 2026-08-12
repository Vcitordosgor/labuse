// M26-B — écran Copilote (vue de premier niveau). PROJECTION de l'event log M26-A :
// aucune logique métier, aucun recalcul. Design : maquette B4 de référence
// (docs/mandats/copilote_maquette_B4_reference_M26B.html), tokens cp-*.
// Les 5 états : 1 terminé · 2 en cours (AUCUN résultat partiel — règle 5) · 3 précision
// (le run REPREND, ne redémarre pas) · 4 zéro retenue (honnête, relances non chiffrées)
// · 5 quota (aucun run créé). Un rafraîchissement en plein run retombe sur le même fil
// (run épinglé + rejeu after_seq).
import { useEffect, useRef, useState } from 'react'
import type { MissionActive } from '../../lib/copilote'
import { CLIENT } from '../../lib/strings'
import { BlocLivrable } from './BlocLivrable'
import { Entonnoir } from './Entonnoir'
import { FilInstruction } from './FilInstruction'
import { Resultats, type EtiquettesMoteurs } from './Resultats'
import { PillStatut, SecHead } from './ui'
import { runEpingle, useCopiloteRun } from './useCopiloteRun'
import { calibrageConnu, entonnoirEnCours, etatInterpretation, type VueCopilote } from './reduireEvenements'
import { AvisIA } from '../AvisIA'
import { useApp } from '../../store/useApp'

const S = CLIENT.copilote

// halo discret de la maquette (radial mint en haut à droite, violet en bas à gauche)
const FOND = {
  backgroundImage:
    'radial-gradient(ellipse 900px 460px at 78% -10%, rgba(74,222,128,.06), transparent 62%), ' +
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
              ? 'border-mint/50 bg-mint/10 text-mint'
              : 'border-cp-line2 bg-cp-card2 text-cp-muted hover:border-mint/40'} ${
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

/** Secondes écoulées depuis le premier événement du run (affichage seulement). */
function useChrono(depuis: string | null, actif: boolean): number | null {
  const [, retick] = useState(0)
  useEffect(() => {
    if (!actif) return
    const t = setInterval(() => retick((n) => n + 1), 1000)
    return () => clearInterval(t)
  }, [actif])
  if (!depuis) return null
  const s = Math.max(0, Math.round((Date.now() - new Date(depuis).getTime()) / 1000))
  return Number.isFinite(s) ? s : null
}

export function CopiloteView() {
  const run = useCopiloteRun()
  const { vue } = run
  const [brief, setBrief] = useState('')
  const [mission, setMission] = useState<MissionActive>('instruire')
  const [reponse, setReponse] = useState('')
  const [journalOuvert, setJournalOuvert] = useState(false)
  const briefRef = useRef<HTMLTextAreaElement | null>(null)

  // rafraîchissement en plein run : on recharge le run épinglé, le SSE rejoue le fil
  const { charger } = run
  useEffect(() => {
    const id = runEpingle()
    if (id) charger(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // M65 P4 — « Décrire un projet » (liste Projets) arme `entretienDirect` puis navigue ici :
  // l'amorce prend place dans le brief (ancien flux IAStub → ProjetEntretien, désormais absorbé
  // par le Copilote). Consommée une fois, puis effacée. Ne pas écraser un brief déjà saisi.
  const { entretienDirect, clearEntretienDirect } = useApp()
  useEffect(() => {
    if (entretienDirect === null) return
    setBrief((b) => b.trim() ? b : (entretienDirect || 'je veux monter une opération immobilière'))
    briefRef.current?.focus()
    clearEntretienDirect()
  }, [entretienDirect, clearEntretienDirect])

  const actif = run.runId != null
  const terminal = vue.statut === 'done' || vue.statut === 'failed' || vue.statut === 'cancelled'
  const enAttente = vue.statut === 'awaiting_user'
  const enInstruction = actif && !terminal && !enAttente
  const fini = vue.statut === 'done' && vue.recap != null
  const communes = (vue.briefJson?.communes as string[] | undefined) ?? null
  const nLogements = (vue.briefJson?.programme as { logements?: number } | undefined)?.logements
  const nFaits = vue.etapes.filter((e) => e.etat === 'faite' || e.etat === 'echouee').length
  const chrono = useChrono(run.evenements[0]?.created_at ?? null, enInstruction)

  const lancer = () => {
    if (brief.trim() && !enInstruction && !enAttente && !run.enCreation)
      void run.instruire(mission, brief)
  }
  // relances de l'état 4 — NON CHIFFRÉES : le brief d'origine revient en console,
  // l'utilisateur ajuste lui-même (aucun chiffre inventé par l'écran)
  const relancer = () => {
    setBrief(vue.briefRaw ?? brief)
    briefRef.current?.focus()
    briefRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'center' })
  }

  const pill = run.quota != null
    ? <PillStatut ton="rouge">{S.quota.pill}</PillStatut>
    : actif
      ? <PillStatut ton={TON_STATUT[vue.statut] ?? 'violet'}
          pulse={vue.statut === 'running' || vue.statut === 'interpreting'}>
          {S.statuts[vue.statut] ?? vue.statut}
          {enInstruction && chrono != null ? ` · ${chrono} s` : ''}
        </PillStatut>
      : null

  return (
    <div data-copilote className="min-h-0 flex-1 overflow-y-auto bg-cp-bg font-sans text-[13px] text-cp-txt" style={FOND}>
      <div className="mx-auto max-w-[1000px] px-6 pb-12 pt-9">
        <div className="mb-4 flex items-center gap-3">
          <span className="font-display text-[10.5px] uppercase tracking-[.24em] text-cp-muted">{S.crumb}</span>
          {pill}
          {run.fluxInterrompu && (
            <span data-flux-interrompu className="text-[10.5px] text-cp-amber">{S.fluxInterrompu}</span>
          )}
        </div>

        <h1 className="font-display text-[clamp(30px,5vw,44px)] font-bold leading-[1.05] tracking-tight text-cp-txt">
          {S.h1Ligne1}<br />{S.h1Ligne2Avant}<em className="not-italic text-mint">{S.h1Ligne2Em}</em>{S.h1Ligne2Apres}
        </h1>
        <p className="mb-6 mt-3 max-w-[600px] text-[13.5px] text-cp-muted">
          {S.lede}<b className="font-medium text-cp-txt">{S.ledeFort}</b>
        </p>

        <AvisIA className="mb-5 border-cp-faint/40 bg-white/[0.02] text-cp-muted" />

        <div className={`flex flex-wrap items-start gap-5 rounded-[18px] border bg-gradient-to-b from-mint/5 to-white/[0.015] p-5 shadow-[0_0_60px_rgba(74,222,128,.06)] ${
          run.quota != null ? 'border-cp-red/30 opacity-50'
          : enInstruction || enAttente ? 'border-mint/35 opacity-65' : 'border-mint/35'}`}>
          <div className="min-w-[250px] flex-1">
            <textarea data-brief ref={briefRef} value={brief} onChange={(e) => setBrief(e.target.value)}
              readOnly={enInstruction || enAttente} placeholder={S.placeholder} rows={2}
              className="w-full resize-none bg-transparent font-sans text-base leading-normal text-cp-txt outline-none placeholder:text-cp-faint focus:outline-none" />
          </div>
          <div className="flex flex-col items-end gap-2">
            {enInstruction ? (
              <button data-annuler onClick={() => void run.annuler()}
                className="rounded-[13px] border border-cp-line2 px-6 py-3.5 font-display text-[13px] font-bold uppercase tracking-wide text-cp-muted">
                {S.annuler}
              </button>
            ) : enAttente ? (
              <button data-en-attente disabled
                className="cursor-default rounded-[13px] border border-cp-line2 px-6 py-3.5 font-display text-[13px] font-bold uppercase tracking-wide text-cp-muted">
                {S.enAttenteBouton}
              </button>
            ) : (
              <button data-instruire onClick={lancer}
                disabled={!brief.trim() || run.enCreation || run.quota != null}
                className="rounded-[13px] bg-mint px-7 py-3.5 font-display text-[13px] font-bold uppercase tracking-wide text-mint-on shadow-[0_0_36px_rgba(74,222,128,.28)] transition-transform duration-quick hover:brightness-110 disabled:opacity-40">
                {S.instruire} →
              </button>
            )}
            <div className={`flex items-center gap-2 text-[10.5px] ${run.quota != null ? 'text-cp-red' : 'text-cp-faint'}`}>
              <i className={`h-1 w-1 rounded-full ${run.quota != null ? 'bg-cp-red' : 'bg-mint'}`} />
              {run.quota != null ? S.quota.pill
                : enInstruction ? S.enCoursSerment(nFaits, vue.plan.length || 6)
                : enAttente ? S.suspendue
                : S.serment}
            </div>
          </div>
        </div>
        <Missions mission={mission} setMission={setMission} verrouille={enInstruction || enAttente} />

        {/* ── état 5 · quota atteint AVANT création — aucun run, aucun moteur ── */}
        {run.quota && (
          <div data-quota-panel
            className="mt-9 rounded-2xl border border-cp-red/30 bg-gradient-to-br from-cp-red/10 to-cp-red/[0.02] px-6 py-7 text-center">
            <div className="mx-auto mb-3.5 flex h-11 w-11 items-center justify-center rounded-full border border-cp-red/45 text-cp-red">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
                <circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" />
              </svg>
            </div>
            <h3 className="font-display text-[19px] font-semibold tracking-tight text-cp-txt">
              {S.quota.titre(run.quota.quota)}
            </h3>
            {/* le corps du 429, verbatim — c'est lui qui dit quand ça repart */}
            <p data-quota-detail className="mx-auto mt-2 max-w-[62ch] text-[13px] text-cp-muted">{run.quota.detail}</p>
            <p className="mx-auto mt-1.5 max-w-[62ch] text-[13px] text-cp-muted">{S.quota.aucunRun}</p>
            <p className="mx-auto mt-3 max-w-[62ch] text-[12px] text-cp-faint">{S.quota.distinct}</p>
          </div>
        )}
        {run.erreur && (
          <p data-erreur className="mt-5 rounded-xl border border-cp-red/30 bg-cp-red/10 px-4 py-3 text-[12px] text-cp-red">
            {run.erreur}
          </p>
        )}

        {/* ── état 3 · demande de précision — le run REPREND, il ne redémarre pas ── */}
        {enAttente && vue.clarification && (
          <div data-clarification className="mt-9 rounded-2xl border border-cp-violet/35 bg-cp-card px-6 py-5">
            <div className="mb-2.5 font-display text-[9.5px] uppercase tracking-[.2em] text-cp-violet">{S.precisionTitre}</div>
            <h3 className="font-display text-lg font-semibold tracking-tight text-cp-txt">{vue.clarification.question}</h3>
            {(vue.clarification.options?.length ?? 0) > 0 && (
              <div className="mb-3.5 mt-4 flex flex-wrap gap-2">
                {(vue.clarification.options ?? []).map((o) => (
                  <button key={o} data-clarif-option onClick={() => void run.repondre(o)}
                    className="rounded-xl border border-cp-line2 bg-cp-card2 px-4 py-2.5 font-display text-[12.5px] font-semibold text-cp-txt transition-colors duration-quick hover:border-mint hover:text-mint">
                    {o}
                  </button>
                ))}
              </div>
            )}
            <div className="mt-3.5 flex gap-1.5 rounded-[13px] border border-cp-line2 bg-cp-card2 p-1.5">
              <input data-clarif-libre value={reponse} onChange={(e) => setReponse(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && reponse.trim()) void run.repondre(reponse) }}
                placeholder={S.precisionPlaceholder}
                className="flex-1 bg-transparent px-3 py-2.5 text-[13px] text-cp-txt outline-none placeholder:text-cp-faint focus:outline-none" />
              <button data-clarif-reprendre disabled={!reponse.trim()} onClick={() => void run.repondre(reponse)}
                className="rounded-[10px] bg-cp-violet px-5 py-2.5 font-display text-[12px] font-bold text-[#150E22] disabled:opacity-40">
                {S.precisionReprendre}
              </button>
            </div>
          </div>
        )}
        {enAttente && vue.plan.length > 0 && (
          <>
            <SecHead titre={S.fil.titre} meta={S.fil.metaPause} />
            <FilInstruction etapes={vue.etapes} interpretation={etatInterpretation(vue)} />
          </>
        )}

        {/* ── état 2 · instruction en cours — AUCUN résultat partiel (règle 5) ── */}
        {enInstruction && vue.plan.length > 0 && (
          <>
            <SecHead titre={S.entonnoir.titre} sousTitre={S.entonnoir.sousTitreEnCours} />
            <Entonnoir etages={entonnoirEnCours(vue)} communes={communes}
              calibrage={calibrageConnu(vue)} enCours />
            <SecHead titre={S.fil.titre}
              meta={S.fil.metaEtape(Math.min(nFaits + 1, vue.plan.length), vue.plan.length)} />
            <FilInstruction etapes={vue.etapes} interpretation={etatInterpretation(vue)} />
            <SecHead titre={S.resultats.titreEnCours} />
            <div data-en-cours
              className="rounded-2xl border border-dashed border-cp-line2 bg-cp-card px-8 py-9 text-center text-[12.5px] leading-relaxed text-cp-faint">
              {S.enCours}<br />{S.enCoursNote}
            </div>
          </>
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

        {/* ── états 1 & 4 · instruction terminée (zéro n'est PAS une erreur — règle 6) ── */}
        {fini && vue.recap && (
          <>
            <SecHead titre={S.entonnoir.titre} sousTitre={S.entonnoir.sousTitre} />
            <Entonnoir etages={vue.recap.entonnoir} communes={communes}
              dureeMs={vue.final?.duree_totale_ms ?? null}
              exhaustif={vue.recap.exhaustif} calibrage={vue.recap.calibrage}
              requalification={vue.recap.requalification ?? null} />

            <SecHead titre={S.fil.titre} meta={S.fil.meta(vue.etapes.length)} />
            <FilInstruction etapes={vue.etapes} />

            <SecHead titre={S.resultats.titre(vue.recap.n_restituees)}
              meta={S.resultats.meta(vue.recap.n_retenues)} />
            {vue.recap.n_restituees > 0 ? (
              <Resultats recap={vue.recap} etiquettes={etiquettesDe(vue)}
                titre={[communes?.join(', '), nLogements != null ? `${nLogements} logements` : null]
                  .filter(Boolean).join(' · ')} />
            ) : (
              <div data-zero className="rounded-2xl border border-cp-line2 bg-cp-card px-8 py-8 text-center">
                <div className="mx-auto mb-3.5 flex h-11 w-11 items-center justify-center rounded-full border border-cp-line2 text-cp-muted">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" />
                  </svg>
                </div>
                <h3 className="font-display text-[19px] font-semibold tracking-tight text-cp-txt">{S.resultats.zeroTitre}</h3>
                <p className="mx-auto mt-2 max-w-[62ch] text-[13px] text-cp-muted">{S.resultats.zeroNote}</p>
                <div className="mt-4 flex flex-wrap justify-center gap-2.5">
                  <button data-relance onClick={relancer}
                    className="rounded-xl bg-mint px-5 py-3 font-display text-[12px] font-bold text-mint-on">
                    {S.resultats.relanceBudget}
                  </button>
                  <button data-relance onClick={relancer}
                    className="rounded-xl border border-cp-line2 bg-cp-card2 px-5 py-3 font-display text-[12px] font-bold text-cp-txt">
                    {S.resultats.relanceCommunes}
                  </button>
                </div>
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
