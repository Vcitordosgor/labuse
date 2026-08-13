// M78 · 2a — réponse inline QUESTION/OUTIL/VERIFICATION/PROJET/VEILLE/refus (le routeur n'a pas
// lancé de mission lourde). Le bouton de porte ouvre l'outil PRÉ-REMPLI (parcelPrefill/calcPrefill/
// pluPrefill, M-ENTREE/M60). Partagé : Copilote plein écran + surfaces embarquées (§5).
// M78-quater #5 — pouces 👍/👎 RETIRÉS (ne faisaient rien de visible) ; le feedback reviendra en lien
// texte discret (BACKLOG).
import { type CopiloteV2Reponse } from '../../lib/api'
import { useApp } from '../../store/useApp'

export function ReponseInline({ v2, ton = 'mint' }: { v2: CopiloteV2Reponse; ton?: 'mint' | 'violet' }) {
  const { setModule, setParcelPrefill, setCalcPrefill, setPluPrefill } = useApp()
  const mauve = ton === 'violet'
  const ouvrir = () => {
    if (!v2.porte) return
    if (v2.prefill_plu) setPluPrefill(v2.prefill_plu)
    else if (v2.prefill === 'calcPrefill' && v2.prefill_idu) setCalcPrefill(v2.prefill_idu)
    else if (v2.prefill_idu) setParcelPrefill(v2.prefill_idu)
    setModule(v2.porte)
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
      {(v2.sources?.length ?? 0) > 0 && (
        <p className="mt-2.5 font-mono text-[10px] text-cp-faint">{v2.sources!.join(' · ')}</p>
      )}
    </div>
  )
}
