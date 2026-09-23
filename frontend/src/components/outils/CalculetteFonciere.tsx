// CalculetteFonciere — ETUDIER-BIEN-2 Lot C : l'outil « Calculette foncière » (ex-M23) restauré
// comme HÔTE MINIMAL de la Calculette PARTAGÉE (`<Calculette>` de la fiche), après le retrait de
// « Étudier un bien » qui l'hébergeait (fusion défaite). Aucune logique nouvelle, aucun moteur : le
// MÊME <Calculette> que la fiche. La clé `calculette-fonciere` reste vivante et résolvante — la fiche
// (§11, Constructibilité), RadarView et le copilote l'ouvrent via `calcPrefill` (IDU pré-rempli).
import { useEffect, useState } from 'react'
import { useApp } from '../../store/useApp'
import { ParcelInput } from '../ParcelInput'
import { Calculette } from '../fiche/Fiche'

export function CalculetteFonciere() {
  const calcPrefill = useApp((s) => s.calcPrefill)
  const setCalcPrefill = useApp((s) => s.setCalcPrefill)
  const [idu, setIdu] = useState<string | null>(calcPrefill ?? null)
  // PORTE (fiche / copilote / RadarView) : un IDU pré-rempli ouvre directement la calculette.
  useEffect(() => {
    if (calcPrefill) { setIdu(calcPrefill); setCalcPrefill(null) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [calcPrefill])
  return (
    <div data-calculette-fonciere className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-1">
      <div>
        <h2 className="font-display text-base font-bold text-txt-hi">Calculette foncière</h2>
        <p className="mt-0.5 text-[11.5px] text-txt-mut">La charge foncière supportable d'une parcelle, par bilan à rebours — mêmes hypothèses que le document financier.</p>
      </div>
      <ParcelInput onPick={(i) => setIdu(i)} placeholder="Adresse ou IDU…" dataAttr="calculette-input" />
      {idu && <Calculette idu={idu} />}
    </div>
  )
}
