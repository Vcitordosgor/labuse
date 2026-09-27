import { useEffect } from 'react'
import { useState } from 'react'
import { useApp } from '../../store/useApp'
import { FaisabiliteTab } from '../fiche/Fiche'
import { ParcelPicker } from './ParcelPicker'

/** M22 · FAISABILITÉ — UN SEUL MODE (FAISABILITE-1 lot C).
 *  On désigne UNE parcelle (IDU / adresse / clic carte) et on voit sa faisabilité — exactement
 *  l'onglet Faisabilité des fiches, porté dans l'outil (aucune divergence).
 *  L'ancien mode « Par critères » (SENS 2 : décrire un programme → parcelles) est retiré : il est
 *  remplacé par le groupe « Capacité » du panneau Filtre (carte), plus global (compteur SQL, entre
 *  dans l'URL/Mes vues/veille). Le lien discret ci-dessous y mène (fil de retour). */

export function M22() {
  const { parcelPrefill, setParcelPrefill, setModuleMap, chercherParCapacite } = useApp()
  const [picked, setPicked] = useState<string | null>(null)

  // M-ENTREE — porte fiche/Densifier → Faisabilité : la parcelle amorce l'outil (motif partagé
  // parcelPrefill, consommation-puis-reset).
  useEffect(() => {
    if (parcelPrefill) {
      setPicked(parcelPrefill)
      setParcelPrefill(null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [parcelPrefill])

  // carte : la parcelle désignée (surlignée) ; nettoyée au démontage.
  useEffect(() => {
    setModuleMap({ idus: picked ? [picked] : [], extra: null })
    return () => setModuleMap({ idus: [], extra: null })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [picked])

  // RETOURS-15 D1 — le panneau ne défile JAMAIS de côté : overflow-x masqué + largeur contrainte
  // (min-w-0) ; le verdict et les chips qui débordaient vont désormais à la ligne.
  return (
    <div className="flex min-h-0 w-full min-w-0 flex-1 flex-col gap-2 overflow-y-auto overflow-x-hidden pr-0.5">
      {/* Sous-titre : la promesse de l'outil, une parcelle à la fois. */}
      <p className="text-[11px] leading-relaxed text-txt-mut">
        Ce que le PLU laisse construire sur cette parcelle.
      </p>
      {/* DA-FIX-2 Lot 2 (DA-016) — OMNIBOX PERMANENTE : le sélecteur de parcelle reste EN TÊTE ;
          la faisabilité s'affiche DESSOUS dès qu'une parcelle est désignée. Retaper = changer. */}
      <ParcelPicker onPick={setPicked} picked={picked} />
      {picked ? (
        /* OUTILS-FIX-3 A1 — FaisabiliteTab rendu dans le MÊME contexte `.fiche-v6` que la fiche.
           `embedded` cantonne l'IA (explication du calcul) à la fiche parcelle. */
        <div data-faisa-parcelle className="fiche-v6 w-full min-w-0 overflow-x-hidden break-words pr-0.5">
          <FaisabiliteTab idu={picked} embedded />
        </div>
      ) : (
        /* Fil de retour vers le groupe « Capacité » du panneau Filtre (l'ex-« Par critères »,
           désormais global). Lien discret : la saisie de parcelle reste l'action principale. */
        <button data-chercher-capacite onClick={() => chercherParCapacite()}
          className="self-start text-[11px] text-txt-dim underline decoration-txt-dim/40 underline-offset-2 transition-colors duration-quick hover:text-mint">
          Chercher des parcelles par capacité →
        </button>
      )}
    </div>
  )
}
