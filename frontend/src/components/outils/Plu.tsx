import { useEffect, useState } from 'react'
import { useApp } from '../../store/useApp'
import { PluAnnuaire } from './PluAnnuaire'
import { VerifProcedure } from './VerifProcedure'

// RECETTE-OUTILS-2 (R4) — l'ancien SIMULATEUR D'OUVERTURE (« Procédure & changement », analogie
// densité médiane) est retiré : il n'était pas fiable. L'Annuaire reste la voie par défaut.
// OUTIL-COMMUNES-FIX-13 LOT 3 — MAIS le bouton « Vérif procédure » de la fiche (Fiche.tsx:1927) pose
// pluVue='procedure' : il doit ouvrir l'OUTIL DE VÉRIFICATION (radar sourcé, point de calcul unique —
// stade / débat PADD / sursis), PAS l'Annuaire. L'audit ASTRA-10 n°3 arrivait sur « PLU — Le règlement
// d'urbanisme… » (l'Annuaire) : le deep-link était silencieusement jeté. On AIGUILLE désormais sur
// VerifProcedure (amorcé sur selectedIdu = la commune de la parcelle). On fige la vue à l'ouverture
// puis on NEUTRALISE le drapeau au store, pour que la prochaine ouverture par le menu reparte sur
// l'Annuaire (défaut). Le simulateur (ProcedureChangement) reste au dépôt, non câblé.
export function Plu() {
  const pluVue = useApp((s) => s.pluVue)
  const setPluVue = useApp((s) => s.setPluVue)
  const [vue] = useState(pluVue)   // vue demandée à l'ouverture (déduite du deep-link du bouton)
  useEffect(() => { if (pluVue) setPluVue(null) }, [])   // consommé une fois

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-hidden">
      {vue === 'procedure' ? <VerifProcedure /> : <PluAnnuaire />}
    </div>
  )
}
