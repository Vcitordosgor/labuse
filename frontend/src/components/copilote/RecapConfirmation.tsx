// M78-bis §2 — LE RÉCAP-CONFIRMATION avant toute mission lourde (RECHERCHE/VERIFICATION). On inverse :
// le Copilote annonce ce qu'il a compris, le client valide, PUIS ça part. Clarification = une bulle
// (≤ 3-4 suggestions, jamais 24) ; la barre principale reste utilisable (non verrouillée). Corriger →
// chips éditables + réécriture. Oui → affinage (suggestions de facettes réelles) → Lancer.
import { useState } from 'react'
import type { CopiloteV2Reponse } from '../../lib/api'
import { ChipsCompris } from './ChipsCompris'

export function RecapConfirmation({ data, brief, onReask, onLancer, onCorriger, onRepondre }: {
  data: CopiloteV2Reponse
  brief: string
  onReask: (b: string) => void        // re-interprète (option/chip retirée) → nouveau récap
  onLancer: (b: string) => void       // valide → lance la mission
  onCorriger: (b: string) => void     // réécrire : remet le brief dans la barre
  // M107 — LA RÉPONSE SE DONNE LÀ OÙ LA QUESTION EST POSÉE : envoie un message dans le même
  // fil (conversation_id) — le serveur l'interprète dans son contexte (prior_params, gate 45).
  onRepondre: (texte: string) => void
}) {
  const [etape, setEtape] = useState<'recap' | 'corriger' | 'affiner'>('recap')
  const [ajouts, setAjouts] = useState<string[]>([])
  const [libre, setLibre] = useState('')     // champ libre d'affinage (maquette : « … ou écrivez »)
  const [reponse, setReponse] = useState('')      // M107 — réponse DANS la carte Précision
  const [correction, setCorrection] = useState('')  // M107 — correction écrite directement au récap
  const mission = data.intent === 'VERIFICATION' ? 'vérification' : 'recherche'
  const envoyer = (t: string, raz: (v: string) => void) => { if (t.trim()) { onRepondre(t.trim()); raz('') } }

  // ── clarification COURTE (≤ 4 options) — M107 : le champ de réponse est DANS LA CARTE, sous
  // la question, avec autofocus. L'ancienne promesse « écrivez dans la barre » (fausse : la
  // barre gardait la demande précédente) est REMPLACÉE par le champ qui la tient. ──
  if (data.clarification_recap) {
    const cl = data.clarification_recap
    return (
      <div data-recap-clarif className="rounded-2xl border border-cp-violet/35 bg-cp-card px-5 py-4">
        <div className="mb-2 font-display text-[9.5px] uppercase tracking-[.2em] text-cp-violet">Précision</div>
        <p className="text-[13.5px] leading-snug text-cp-txt">{cl.question}</p>
        {cl.options.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {cl.options.map((o) => (
              <button key={o} data-recap-option onClick={() => onReask(`${brief} ${o}`)}
                className="rounded-xl border border-cp-line2 bg-cp-card2 px-4 py-2 font-display text-[12.5px] font-semibold text-cp-txt transition-colors duration-quick hover:border-mint hover:text-mint">
                {o}
              </button>
            ))}
          </div>
        )}
        <div className="mt-3 flex items-center gap-2">
          <input data-clarif-reponse autoFocus value={reponse} onChange={(e) => setReponse(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') envoyer(reponse, setReponse) }}
            placeholder="…ou répondez librement ici"
            className="min-w-0 flex-1 rounded-lg border border-cp-violet/30 bg-cp-card2 px-3.5 py-2 text-[13px] text-cp-txt outline-none placeholder:text-cp-faint focus:border-cp-violet" />
          <button data-clarif-envoyer disabled={!reponse.trim()} onClick={() => envoyer(reponse, setReponse)}
            className="rounded-lg border border-cp-violet/40 bg-cp-violet/10 px-3.5 py-2 font-display text-[12px] font-semibold text-cp-violet hover:bg-cp-violet/15 disabled:opacity-40">
            Répondre
          </button>
        </div>
      </div>
    )
  }

  // ── CORRIGER : les chips éditables (✕ retire → ré-interprète) + réécriture libre ──
  if (etape === 'corriger') {
    return (
      <div data-recap-corriger className="rounded-2xl border border-mint/25 bg-cp-card px-5 py-4">
        {data.brief_json && (
          <ChipsCompris briefJson={data.brief_json} onRelancer={onReask} onCorriger={onCorriger} />
        )}
        <div className="mt-1 flex gap-2">
          <button data-recap-retour onClick={() => setEtape('recap')}
            className="rounded-lg border border-cp-line2 px-4 py-2 font-display text-[12px] font-semibold text-cp-txt hover:border-mint/40">
            Retour au récap
          </button>
          <button data-recap-reecrire onClick={() => onCorriger(brief)}
            className="rounded-lg border border-cp-line2 px-4 py-2 font-display text-[12px] text-cp-muted hover:text-cp-txt">
            Réécrire dans la barre
          </button>
        </div>
      </div>
    )
  }

  // ── AFFINER : suggestions de facettes réelles (ajoutent une chip, restent ici) + Lancer ──
  if (etape === 'affiner') {
    const restantes = (data.suggestions ?? []).filter((s) => !s.ajout || !ajouts.includes(s.ajout))
    return (
      <div data-recap-affiner className="rounded-2xl border border-mint/25 bg-cp-card px-5 py-4">
        <p className="text-[13.5px] text-cp-txt">Envie d'affiner ?</p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {(data.chips ?? []).map((ch) => (
            <span key={ch} className="rounded-lg border border-mint/25 bg-mint/[0.07] px-2.5 py-1 text-[11.5px] text-cp-txt">{ch}</span>
          ))}
          {ajouts.map((a) => (
            <span key={a} className="rounded-lg border border-mint/40 bg-mint/[0.12] px-2.5 py-1 text-[11.5px] text-mint">{a}</span>
          ))}
        </div>
        {restantes.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {restantes.map((s) => (
              <button key={s.label} data-recap-suggestion
                onClick={() => (s.ajout ? setAjouts([...ajouts, s.ajout]) : onCorriger(brief))}
                className="rounded-xl border border-cp-line2 bg-cp-card2 px-3.5 py-2 font-display text-[12px] font-semibold text-cp-muted transition-colors duration-quick hover:border-mint hover:text-mint">
                + {s.label}
              </button>
            ))}
          </div>
        )}
        {/* champ libre OBLIGATOIRE (maquette étape 3) : 5 boutons ne couvrent pas tous les besoins.
             Entrée → ajoute une chip et reste ici. */}
        <input data-recap-libre value={libre} onChange={(e) => setLibre(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && libre.trim()) {
              e.preventDefault(); setAjouts([...ajouts, libre.trim()]); setLibre('')
            }
          }}
          placeholder="… ou écrivez ce que vous voulez ajouter"
          className="mt-3 w-full rounded-lg border border-cp-line2 bg-cp-card2 px-3.5 py-2.5 text-[12.5px] text-cp-txt outline-none placeholder:text-cp-faint" />
        <button data-recap-lancer onClick={() => onLancer([brief, ...ajouts, libre.trim()].filter(Boolean).join(', '))}
          className="mt-4 w-full rounded-[13px] bg-mint px-7 py-3 font-display text-[13px] font-bold uppercase tracking-wide text-mint-on shadow-[0_0_36px_rgba(74,222,128,.28)] transition-transform duration-quick hover:brightness-110">
          Lancer la {mission} →
        </button>
      </div>
    )
  }

  // ── RÉCAP : « J'ai compris : … C'est bien ça ? » + Oui / Corriger — M107 : et la possibilité
  // d'écrire DIRECTEMENT une correction, sans passer par le bouton (le geste de Vic). ──
  return (
    <div data-recap className="rounded-2xl border border-mint/30 bg-cp-card px-5 py-4">
      <p className="text-[14px] leading-relaxed text-cp-txt">{data.recap} <b className="text-cp-txt">C'est bien ça ?</b></p>
      <div className="mt-3.5 flex flex-wrap gap-2">
        <button data-recap-oui onClick={() => setEtape('affiner')}
          className="rounded-xl bg-mint px-5 py-2.5 font-display text-[12.5px] font-bold text-mint-on transition-[filter] duration-quick hover:brightness-110">
          Oui, c'est ça
        </button>
        <button data-recap-corriger onClick={() => setEtape('corriger')}
          className="rounded-xl border border-cp-line2 bg-cp-card2 px-5 py-2.5 font-display text-[12.5px] font-semibold text-cp-txt transition-colors duration-quick hover:border-mint hover:text-mint">
          Corriger
        </button>
      </div>
      <input data-recap-correction value={correction} onChange={(e) => setCorrection(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter') envoyer(correction, setCorrection) }}
        placeholder="…ou corrigez directement en écrivant ici (ex. « plutôt à Saint-Leu »)"
        className="mt-2.5 w-full rounded-lg border border-cp-line2 bg-cp-card2 px-3.5 py-2 text-[12.5px] text-cp-txt outline-none placeholder:text-cp-faint focus:border-mint/50" />
    </div>
  )
}
