import { useEffect, useState } from 'react'
import { useApp } from '../../store/useApp'
import { PluAnnuaire } from './PluAnnuaire'
import { ProcedureChangement } from './ProcedureChangement'

// M137-P — OUTIL PLU UNIFIÉ. M137-Q : les voies « Procédure » et « Changement » (qui s'ignoraient)
// fusionnent en UNE — « Procédure & changement » : les communes en procédure en tête, chacune reliée
// à sa simulation AU→U préremplie (ProcedureChangement). Le hub passe donc à 2 voies. Chaque voie
// MONTE le composant existant (aucun calcul ne change). Ouverture directe possible depuis la fiche /
// le Copilote (pluVue), ou sur l'Annuaire si une zone est pré-remplie (pluPrefill).
type Vue = 'accueil' | 'annuaire' | 'procchg'

// M137-Q — les anciennes vues 'procedure'/'changement' (contrat store, portes fiche/Copilote)
// pointent désormais vers la voie fusionnée.
const mapVue = (v: 'annuaire' | 'procedure' | 'changement'): Exclude<Vue, 'accueil'> =>
  v === 'annuaire' ? 'annuaire' : 'procchg'

const VOIES: { vue: Exclude<Vue, 'accueil'>; titre: string; sous: string }[] = [
  { vue: 'annuaire', titre: 'Annuaire PLU',
    sous: 'Tous les PLU des 24 communes au même endroit — à télécharger ou à interroger' },
  { vue: 'procchg', titre: 'Procédure & changement',
    sous: 'Où le PLU est en révision — et simulez ce que la bascule d’une zone AU en U changerait' },
]

export function Plu() {
  const pluVue = useApp((s) => s.pluVue)
  const setPluVue = useApp((s) => s.setPluVue)
  const pluPrefill = useApp((s) => s.pluPrefill)
  // Ouverture directe : une vue explicite (fiche → procédure/changement) prime ; sinon une zone
  // pré-remplie ouvre l'Annuaire ; sinon la page d'accueil des 2 voies.
  const [vue, setVue] = useState<Vue>(() => (pluVue ? mapVue(pluVue) : pluPrefill ? 'annuaire' : 'accueil'))
  useEffect(() => { if (pluVue) { setVue(mapVue(pluVue)); setPluVue(null) } }, [pluVue, setPluVue])

  if (vue === 'accueil') {
    return (
      <div data-plu-accueil className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
        {VOIES.map((v) => (
          <button key={v.vue} data-plu-voie={v.vue} onClick={() => setVue(v.vue)}
            className="flex flex-col gap-0.5 rounded-lg border border-line-2 bg-surface-2 px-3.5 py-3 text-left transition-colors duration-quick hover:border-mint/50">
            <span className="text-[13px] font-medium text-txt-hi">{v.titre}</span>
            <span className="text-[10.5px] leading-snug text-txt-dim">{v.sous}</span>
          </button>
        ))}
      </div>
    )
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-hidden">
      <button data-plu-hub-retour onClick={() => setVue('accueil')}
        className="shrink-0 self-start text-[11px] text-mint hover:underline">‹ Choix PLU</button>
      {vue === 'annuaire' && <PluAnnuaire />}
      {vue === 'procchg' && <ProcedureChangement />}
    </div>
  )
}
