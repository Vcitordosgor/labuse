import { useEffect, useState } from 'react'
import { useApp } from '../../store/useApp'
import { M15 } from './moteurs'
import { PluAnnuaire } from './PluAnnuaire'
import { VerifProcedure } from './VerifProcedure'

// M137-P — OUTIL PLU UNIFIÉ : les 3 anciens outils (Annuaire PLU, Vérif procédure, Changement PLU /
// simulplu) fusionnent en UN. La page 1 propose les 3 voies ; chacune MONTE le composant existant
// inchangé (aucun calcul ne change — c'est la navigation qui est refondue). Le hub s'ouvre directement
// sur une vue quand la fiche/le Copilote le demande (pluVue), ou sur l'Annuaire si une zone est
// pré-remplie (pluPrefill).
type Vue = 'accueil' | 'annuaire' | 'procedure' | 'changement'

const VOIES: { vue: Exclude<Vue, 'accueil'>; titre: string; sous: string }[] = [
  { vue: 'annuaire', titre: 'Annuaire PLU',
    sous: 'Tous les PLU des 24 communes au même endroit — à télécharger ou à interroger' },
  { vue: 'procedure', titre: 'Procédure PLU',
    sous: 'Une procédure PLU est-elle en cours sur votre parcelle ? (sursis à statuer, veille AU)' },
  { vue: 'changement', titre: 'Changement PLU',
    sous: 'Et si cette zone AU devenait constructible ? Simulez la bascule' },
]

export function Plu() {
  const pluVue = useApp((s) => s.pluVue)
  const setPluVue = useApp((s) => s.setPluVue)
  const pluPrefill = useApp((s) => s.pluPrefill)
  // Ouverture directe : une vue explicite (fiche → procédure) prime ; sinon une zone pré-remplie ouvre
  // l'Annuaire ; sinon la page d'accueil des 3 voies.
  const [vue, setVue] = useState<Vue>(() => pluVue ?? (pluPrefill ? 'annuaire' : 'accueil'))
  useEffect(() => { if (pluVue) { setVue(pluVue); setPluVue(null) } }, [pluVue, setPluVue])

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
      {vue === 'procedure' && <VerifProcedure />}
      {vue === 'changement' && <M15 />}
    </div>
  )
}
