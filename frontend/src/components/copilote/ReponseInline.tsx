// M78 · 2a/2f — réponse inline QUESTION/OUTIL/VERIFICATION/PROJET/VEILLE/refus (le routeur n'a pas
// lancé de mission lourde). Le bouton de porte ouvre l'outil PRÉ-REMPLI (parcelPrefill/calcPrefill/
// pluPrefill, M-ENTREE/M60). 👍/👎 = feedback (§2f). Partagé : Copilote plein écran + surfaces embarquées (§5).
import { useState } from 'react'
import { copiloteV2Feedback, type CopiloteV2Reponse } from '../../lib/api'
import { useApp } from '../../store/useApp'

export function ReponseInline({ v2, ton = 'mint' }: { v2: CopiloteV2Reponse; ton?: 'mint' | 'violet' }) {
  const { setModule, setParcelPrefill, setCalcPrefill, setPluPrefill } = useApp()
  const mauve = ton === 'violet'
  const [pouce, setPouce] = useState<'haut' | 'bas' | null>(null)
  const [comm, setComm] = useState('')
  const [envoye, setEnvoye] = useState(false)
  const ouvrir = () => {
    if (!v2.porte) return
    if (v2.prefill_plu) setPluPrefill(v2.prefill_plu)
    else if (v2.prefill === 'calcPrefill' && v2.prefill_idu) setCalcPrefill(v2.prefill_idu)
    else if (v2.prefill_idu) setParcelPrefill(v2.prefill_idu)
    setModule(v2.porte)
  }
  const noter = (p: 'haut' | 'bas') => {
    setPouce(p)
    if (p === 'haut') void copiloteV2Feedback(v2.conversation_id ?? null, 'haut')
  }
  const bord = v2.refus && v2.refus !== 'hors_sujet' ? 'border-cp-amber/30'
    : v2.intent === 'HORS_SUJET' ? 'border-cp-line2' : mauve ? 'border-violet/30' : 'border-mint/25'
  return (
    <div data-reponse className={`rounded-2xl border ${bord} bg-cp-card px-5 py-4 text-left`}>
      <p className="whitespace-pre-wrap text-[13.5px] leading-relaxed text-cp-txt">{v2.text}</p>
      {v2.porte && (
        <button data-reponse-porte onClick={ouvrir}
          className={`mt-3 rounded-lg border px-4 py-2 font-display text-[12px] font-semibold transition-colors duration-quick ${
            mauve ? 'border-violet/40 bg-violet/10 text-violet hover:bg-violet/15'
                  : 'border-mint/40 bg-mint/10 text-mint hover:bg-mint/15'}`}>
          Ouvrir l'outil →
        </button>
      )}
      <div className="mt-2.5 flex items-center gap-3">
        {(v2.sources?.length ?? 0) > 0 && (
          <p className="flex-1 font-mono text-[10px] text-cp-faint">{v2.sources!.join(' · ')}</p>
        )}
        <div className="ml-auto flex items-center gap-1.5">
          <button data-feedback-haut onClick={() => noter('haut')}
            className={`text-[13px] transition-opacity ${pouce === 'haut' ? 'opacity-100' : 'opacity-40 hover:opacity-80'}`}
            title="Utile">👍</button>
          <button data-feedback-bas onClick={() => noter('bas')}
            className={`text-[13px] transition-opacity ${pouce === 'bas' ? 'opacity-100' : 'opacity-40 hover:opacity-80'}`}
            title="À améliorer">👎</button>
        </div>
      </div>
      {pouce === 'bas' && !envoye && (
        <div className="mt-2 flex gap-1.5">
          <input data-feedback-comm value={comm} onChange={(e) => setComm(e.target.value)}
            placeholder="Qu'est-ce qui n'allait pas ? (optionnel)"
            className="flex-1 rounded-lg border border-cp-line2 bg-cp-card2 px-3 py-1.5 text-[12px] text-cp-txt outline-none placeholder:text-cp-faint" />
          <button data-feedback-envoyer onClick={() => { void copiloteV2Feedback(v2.conversation_id ?? null, 'bas', comm); setEnvoye(true) }}
            className="rounded-lg border border-cp-line2 px-3 py-1.5 text-[12px] text-cp-muted hover:text-cp-txt">Envoyer</button>
        </div>
      )}
      {envoye && <p className="mt-2 text-[11px] text-cp-faint">Merci — c'est noté.</p>}
    </div>
  )
}
