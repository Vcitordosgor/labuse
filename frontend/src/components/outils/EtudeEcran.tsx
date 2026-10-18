// IMPLANTATION-4 (LOT A) — L'ÉCRAN D'ÉTUDE DANS DOCS. L'Étude de faisabilité a quitté les Outils ; elle
// s'ouvre maintenant en overlay plein écran (patron BilanEcran), monté au niveau App et piloté par le
// drapeau `etudeIdus` du store. On y retrouve l'écran COMPLET (configuration, scénarios A/B/C, plan masse
// sur une CARTE INTÉGRÉE, sections repliables, hypothèses) — le MÊME composant M22, en mode `embedded`,
// servi par la MÊME API (POST /modules/etude). Aucun second calcul. Entrées : 9e carte Docs, tuile fiche,
// pont Assemblage, et les anciens liens #m=programme (redirigés ici par App.tsx).
import { useEffect } from 'react'
import { useApp } from '../../store/useApp'
import { Bouton } from '../ui/Bouton'
import { M22 } from './M22Programme'
import { iduComplet } from '../../lib/format'

export function EtudeEcran() {
  const etudeIdus = useApp((s) => s.etudeIdus)
  const fermerEtude = useApp((s) => s.fermerEtude)

  // Échap ferme (comme BilanEcran). Le hook est inconditionnel ; il ne fait rien quand l'overlay est fermé.
  useEffect(() => {
    if (etudeIdus == null) return
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') fermerEtude() }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [etudeIdus, fermerEtude])

  if (etudeIdus == null) return null
  const titre = etudeIdus.length === 0 ? 'Étude de faisabilité'
    : etudeIdus.length === 1 ? `Étude de faisabilité · ${iduComplet(etudeIdus[0])}`
      : `Étude de faisabilité · ${etudeIdus.length} parcelles`

  return (
    <div data-etude-ecran className="fixed inset-0 z-50 overflow-auto bg-bg" onClick={fermerEtude}>
      <div className="mx-auto my-6 flex min-h-[calc(100vh-3rem)] max-w-[1400px] flex-col rounded-lg border border-line bg-surface-1"
        onClick={(e) => e.stopPropagation()}>
        <div className="sticky top-0 z-10 flex h-14 shrink-0 items-center gap-3 border-b border-line bg-surface-2 px-5">
          <Bouton niveau="secondaire" ton="vert" onClick={fermerEtude}>← Fermer</Bouton>
          <div className="leading-tight">
            <div className="text-[16px] font-bold text-txt">{titre}</div>
            <div className="text-[12px] text-txt-mut">Pré-faisabilité collective, dessinée et contrôlée — jamais « conforme ».</div>
          </div>
        </div>
        <div className="flex min-h-0 flex-1 flex-col p-5">
          {/* clé = l'assiette : rouvrir sur une autre parcelle REMONTE M22 (état neuf, sélection locale). */}
          <M22 key={etudeIdus.join(',')} embedded initialIdus={etudeIdus} />
        </div>
      </div>
    </div>
  )
}
