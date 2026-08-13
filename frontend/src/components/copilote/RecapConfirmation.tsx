// M78-bis §2 — LE RÉCAP-CONFIRMATION avant toute mission lourde (RECHERCHE/VERIFICATION). On inverse :
// le Copilote annonce ce qu'il a compris, le client valide, PUIS ça part. Clarification = une bulle
// (≤ 3-4 suggestions, jamais 24) ; la barre principale reste utilisable (non verrouillée). Corriger →
// chips éditables + réécriture. Oui → affinage (suggestions de facettes réelles) → Lancer.
import { useState } from 'react'
import type { CopiloteV2Reponse } from '../../lib/api'
import { ChipsCompris } from './ChipsCompris'

export function RecapConfirmation({ data, brief, onReask, onLancer, onCorriger }: {
  data: CopiloteV2Reponse
  brief: string
  onReask: (b: string) => void        // re-interprète (option/chip retirée) → nouveau récap
  onLancer: (b: string) => void       // valide → lance la mission
  onCorriger: (b: string) => void     // réécrire : remet le brief dans la barre
}) {
  const [etape, setEtape] = useState<'recap' | 'corriger' | 'affiner'>('recap')
  const [ajouts, setAjouts] = useState<string[]>([])
  const mission = data.intent === 'VERIFICATION' ? 'vérification' : 'recherche'
  const finalBrief = [brief, ...ajouts].join(', ')

  // ── clarification COURTE (≤ 4 options) — la barre reste utilisable (non verrouillée) ──
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
        <p className="mt-3 text-[11px] text-cp-faint">…ou écrivez librement votre réponse dans la barre — le Copilote comprend.</p>
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
        <button data-recap-lancer onClick={() => onLancer(finalBrief)}
          className="mt-4 rounded-[13px] bg-mint px-7 py-3 font-display text-[13px] font-bold uppercase tracking-wide text-mint-on shadow-[0_0_36px_rgba(74,222,128,.28)] transition-transform duration-quick hover:brightness-110">
          Lancer la {mission} →
        </button>
      </div>
    )
  }

  // ── RÉCAP : « J'ai compris : … C'est bien ça ? » + Oui / Corriger ──
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
    </div>
  )
}
