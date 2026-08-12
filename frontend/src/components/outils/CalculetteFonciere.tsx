import { useEffect, useState } from 'react'
import { Calculette } from '../fiche/Fiche'
import { ParcelPicker } from './ParcelPicker'
import { useApp } from '../../store/useApp'
import { iduComplet } from '../../lib/format'

/** M15-C2 — Calculette foncière autonome : la calculette de charge foncière DES FICHES, portée dans
 *  un outil. Sortie strictement IDENTIQUE à la fiche (même composant, même moteur /charge — zéro
 *  recalcul, zéro divergence). Le seul ajout = l'entrée : 2 modes (barre IDU/adresse + clic carte).
 *  M60 P1a — DEPUIS LA FICHE : une porte pose `calcPrefill` (IDU) → on saute le ParcelPicker et on
 *  ouvre pré-rempli, IDU EN TÊTE. DEPUIS OUTILS (sans prefill) : le ParcelPicker (champ IDU/adresse). */
export function CalculetteFonciere() {
  const calcPrefill = useApp((s) => s.calcPrefill)
  const setCalcPrefill = useApp((s) => s.setCalcPrefill)
  const [picked, setPicked] = useState<string | null>(calcPrefill)
  useEffect(() => {
    if (calcPrefill) { setPicked(calcPrefill); setCalcPrefill(null) }
  }, [calcPrefill, setCalcPrefill])
  return (
    <>
      <div className="rounded-lg border border-violet/40 bg-violet/[0.07] px-3 py-2 text-[10.5px] leading-relaxed text-txt-mut">
        Ce qu'un terrain peut <b>supporter</b> selon VOS hypothèses (coût, marge). LABUSE affiche le
        sourcé (SDP, prix de sortie) ; vous saisissez vos hypothèses ; le moteur calcule —
        <b> le même calcul que la fiche</b>.
      </div>
      {!picked ? (
        <ParcelPicker onPick={setPicked} picked={picked} />
      ) : (
        <>
          {/* M60 P1a — IDU EN TÊTE (complet), avec « changer » pour repasser au ParcelPicker. */}
          <div className="flex items-center gap-2 text-[11px] text-txt-mut">
            <span>Parcelle <b className="font-mono text-txt">{iduComplet(picked) || picked}</b></span>
            <button data-calc-changer onClick={() => setPicked(null)}
              className="ml-auto rounded border border-line-2 px-2 py-0.5 text-[10.5px] text-txt-dim transition-colors duration-quick hover:text-txt">changer</button>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto pr-0.5">
            <Calculette idu={picked} />
          </div>
        </>
      )}
    </>
  )
}
