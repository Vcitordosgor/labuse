import { useEffect } from 'react'
import { useState } from 'react'
import { useApp } from '../../store/useApp'
import { FaisabiliteTab } from '../fiche/Fiche'
import { ParcelPicker } from './ParcelPicker'

/** M22 · FAISABILITÉ — RETOURS-15 C3 : DEUX PORTES à l'entrée (même composant .door qu'Étude de zone) :
 *  « Une parcelle » (barre adresse/IDU ou clic carte → l'onglet Faisabilité des fiches, MÊME composant
 *  FaisabiliteTab, refonte 5 blocs) · « Trouver des parcelles pour un programme » (l'ex-« Par critères »,
 *  aujourd'hui le groupe « Capacité » du panneau Filtre — compteur SQL, URL, Mes vues, veille). */

export function M22() {
  const { parcelPrefill, setParcelPrefill, setModuleMap, chercherParCapacite } = useApp()
  const [porte, setPorte] = useState<'parcelle' | 'programme' | null>(null)
  const [picked, setPicked] = useState<string | null>(null)

  // M-ENTREE — porte fiche/Densifier → Faisabilité : la parcelle amorce l'outil (motif partagé
  // parcelPrefill) ET ouvre directement la porte « Une parcelle ».
  useEffect(() => {
    if (parcelPrefill) {
      setPicked(parcelPrefill)
      setPorte('parcelle')
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

  // RETOURS-15 D1 — le panneau ne défile JAMAIS de côté : overflow-x masqué + largeur contrainte (min-w-0).
  return (
    <div className="flex min-h-0 w-full min-w-0 flex-1 flex-col gap-2 overflow-y-auto overflow-x-hidden pr-0.5">
      {porte === null ? (
        /* ACCUEIL — deux portes distinctes (même moteur FaisabiliteTab derrière la première). */
        <>
          <p className="text-[11.5px] leading-snug text-txt-mut">Que voulez-vous étudier ?</p>
          <button data-faisa-porte="parcelle" onClick={() => setPorte('parcelle')} className="door door-hot hover-fill w-full text-left">
            <div className="text-[12.5px] font-medium text-txt">Une parcelle</div>
            <div className="mt-0.5 text-[10.5px] leading-snug text-txt-dim">Ce que le PLU laisse construire sur CETTE parcelle : le verdict, les règles sourcées, la capacité estimée.</div>
          </button>
          <button data-faisa-porte="programme" onClick={() => setPorte('programme')} className="door door-hot hover-fill w-full text-left">
            <div className="text-[12.5px] font-medium text-txt">Trouver des parcelles pour un programme</div>
            <div className="mt-0.5 text-[10.5px] leading-snug text-txt-dim">Un besoin (commune + programme) → les parcelles qui l'accueillent, filtrables sur la carte.</div>
          </button>
        </>
      ) : porte === 'parcelle' ? (
        <>
          <button data-faisa-changer-porte onClick={() => { setPorte(null); setPicked(null) }} className="self-start text-[10.5px] text-mint hover:underline">← Changer</button>
          <p className="text-[11px] leading-relaxed text-txt-mut">Ce que le PLU laisse construire sur cette parcelle.</p>
          {/* DA-FIX-2 Lot 2 (DA-016) — OMNIBOX PERMANENTE : le sélecteur reste EN TÊTE ; la faisabilité
              s'affiche DESSOUS dès qu'une parcelle est désignée. Retaper = changer. */}
          <ParcelPicker onPick={setPicked} picked={picked} />
          {picked && (
            /* FaisabiliteTab rendu dans le MÊME contexte `.fiche-v6` que la fiche (aucune divergence). */
            <div data-faisa-parcelle className="fiche-v6 w-full min-w-0 overflow-x-hidden break-words pr-0.5">
              <FaisabiliteTab idu={picked} embedded />
            </div>
          )}
        </>
      ) : (
        <>
          <button data-faisa-changer-porte onClick={() => setPorte(null)} className="self-start text-[10.5px] text-mint hover:underline">← Changer</button>
          <p className="text-[11px] leading-relaxed text-txt-mut">Décrivez un programme (commune, destination, gabarit) : LABUSE liste les parcelles qui l'accueillent, filtrables et enregistrables comme une recherche.</p>
          {/* Le moteur « Par critères » vit dans le groupe « Capacité » du panneau Filtre (global :
              compteur SQL, URL, Mes vues, veille). La porte y mène — une seule implémentation. */}
          <button data-chercher-capacite onClick={() => chercherParCapacite()}
            className="self-start rounded-md border border-mint/50 bg-mint/5 px-3 py-1.5 text-[11px] font-medium text-mint transition-colors duration-quick hover:bg-mint/10">
            Décrire le programme sur la carte →
          </button>
        </>
      )}
    </div>
  )
}
