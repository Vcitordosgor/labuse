// CalculetteFonciere — ETUDIER-BIEN-2 Lot C : l'outil « Calculette foncière » (ex-M23) restauré
// comme HÔTE MINIMAL de la Calculette PARTAGÉE (`<Calculette>` de la fiche), après le retrait de
// « Étudier un bien » qui l'hébergeait (fusion défaite). Aucune logique nouvelle, aucun moteur : le
// MÊME <Calculette> que la fiche. La clé `calculette-fonciere` reste vivante et résolvante — la fiche
// (§11, Constructibilité), RadarView et le copilote l'ouvrent via `calcPrefill` (IDU pré-rempli).
import { useEffect, useState } from 'react'
import { useApp } from '../../store/useApp'
import { EntreeParcelle, type SourceParcelle } from './EntreeParcelle'   // RECETTE-1 F2
import { Reinitialiser } from '../ui/Reinitialiser'   // RECETTE-1 F3
import { Calculette } from '../fiche/Fiche'

export function CalculetteFonciere() {
  const calcPrefill = useApp((s) => s.calcPrefill)
  const setCalcPrefill = useApp((s) => s.setCalcPrefill)
  const selectedIdu = useApp((s) => s.selectedIdu)   // RECETTE-1 F1 — la parcelle de l'outil EST celle de la fiche
  const focusParcelle = useApp((s) => s.focusParcelle)
  const select = useApp((s) => s.select)             // RECETTE-1 F1/F3 — vider la parcelle partagée (fiche)
  const [idu, setIdu] = useState<string | null>(calcPrefill ?? selectedIdu ?? null)
  // RECETTE-1 (F2) — quelle entrée a désigné la parcelle (grise l'autre dans EntreeParcelle).
  // INVARIANT (comme Taxe/Gabarit) : source='carte' UNIQUEMENT quand la parcelle vient de selectedIdu
  // (sinon l'effet F1 ci-dessous la viderait au montage). Un prefill (porte fiche/copilote) laisse
  // source=null : les deux entrées restent actives, la parcelle persiste jusqu'au Réinitialiser.
  const [source, setSource] = useState<SourceParcelle>(selectedIdu ? 'carte' : null)
  // PORTE (fiche / copilote / RadarView) : un IDU pré-rempli ouvre directement la calculette.
  useEffect(() => {
    if (calcPrefill) { setIdu(calcPrefill); setCalcPrefill(null) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [calcPrefill])
  // RECETTE-1 (F1) — un clic carte (selectedIdu) est adopté ; fermer la fiche (selectedIdu → null)
  // alors que la parcelle venait de la carte VIDE l'outil.
  useEffect(() => {
    if (selectedIdu && selectedIdu !== idu) { setIdu(selectedIdu); if (source == null) setSource('carte') }
    else if (selectedIdu == null && source === 'carte') { setIdu(null); setSource(null) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedIdu])
  // RECETTE-1 (F3) — Réinitialiser : vide la parcelle partagée (ferme la fiche) + rend les deux entrées.
  const resetAll = () => {
    if (selectedIdu) select(null)
    setIdu(null); setSource(null)
  }
  return (
    <div data-calculette-fonciere className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-1">
      <div className="flex items-start gap-1.5">
        <div className="min-w-0 flex-1">
          <h2 className="font-display text-base font-bold text-txt-hi">Calculette foncière</h2>
          <p className="mt-0.5 text-[11.5px] text-txt-mut">La charge foncière supportable d'une parcelle, par bilan à rebours — mêmes hypothèses que le document financier.</p>
        </div>
        {/* RECETTE-1 (F3) — Réinitialiser en haut à droite (dès qu'une parcelle est désignée). */}
        {idu && <Reinitialiser onReset={resetAll} />}
      </div>
      {/* RECETTE-1 (F2) — EntreeParcelle : adresse/IDU OU clic carte, l'une grise l'autre. */}
      <EntreeParcelle source={source}
        onPick={(i, src) => { setSource(src); setIdu(i); focusParcelle(i, { fiche: true }) }} />
      {idu && <Calculette idu={idu} />}
    </div>
  )
}
