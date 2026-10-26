import { useEffect } from 'react'
import { useApp } from '../../store/useApp'
import { PluAnnuaire } from './PluAnnuaire'

// RECETTE-OUTILS-2 (R4) — la voie « Procédure & changement » est SUPPRIMÉE (décision Vic : le
// simulateur d'ouverture est une ANALOGIE — densité médiane des zones U appliquée à une zone AU —,
// pas une information fiable). L'outil PLU n'a donc plus qu'une voie : l'Annuaire, ouvert DIRECTEMENT
// (plus de hub à 2 cartes). Les anciens deep-links (pluVue 'procedure'/'changement', fiche/Copilote)
// retombent sans 404 sur l'Annuaire. L'info « procédure PLU en cours » (Sudocuh) reste servie sur la
// fiche commune et la fiche parcelle (hors de cet outil). Le composant ProcedureChangement et les
// endpoints back restent au dépôt, simplement non câblés ici.
export function Plu() {
  const pluVue = useApp((s) => s.pluVue)
  const setPluVue = useApp((s) => s.setPluVue)
  // on consomme l'ancien contrat (procedure/changement/annuaire) sans effet : tout mène à l'Annuaire.
  useEffect(() => { if (pluVue) setPluVue(null) }, [pluVue, setPluVue])

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-hidden">
      <PluAnnuaire />
    </div>
  )
}
