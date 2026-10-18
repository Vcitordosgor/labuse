// IMPLANTATION-4 — L'ÉCRAN D'ÉTUDE DANS DOCS. L'Étude de faisabilité a quitté les Outils ; elle s'ouvre
// en overlay plein écran (patron BilanEcran), monté au niveau App et piloté par le drapeau `etudeIdus`.
// Depuis la suite v4, l'écran est SANS CARTE : EtudeEcran n'est plus qu'une COQUILLE d'overlay (cadre +
// fermeture + Échap + pont Bilan). Tout l'écran (en-tête ← Fermer / Réinitialiser, configuration,
// scénarios, chiffres clés, PLAN MASSE DESSINÉ, sections) est rendu par le MÊME composant M22 en mode
// `embedded`, servi par la MÊME API (POST /modules/etude). Aucun second calcul. Entrées : 9e carte Docs,
// tuile fiche, pont Assemblage, et les anciens liens #m=programme (redirigés ici par App.tsx).
import { useEffect, useState } from 'react'
import { useApp } from '../../store/useApp'
import { M22, type EtudeProgramme } from './M22Programme'
import { BilanEcran } from '../fiche/BilanEcran'

export function EtudeEcran() {
  const etudeIdus = useApp((s) => s.etudeIdus)
  const fermerEtude = useApp((s) => s.fermerEtude)
  // IMPLANTATION-4 (LOT B) — pont « Bilan de ce scénario » : ouvre le Bilan (par-dessus l'Étude)
  // pré-rempli avec le programme du scénario affiché (logements par type + SDP), étiqueté « depuis
  // l'Étude ». Le Bilan porte sur la 1ʳᵉ parcelle de l'assiette (modèle de bilan par parcelle).
  const [bilanProg, setBilanProg] = useState<EtudeProgramme | null>(null)

  // Échap ferme (comme BilanEcran). Le hook est inconditionnel ; il ne fait rien quand l'overlay est fermé.
  useEffect(() => {
    if (etudeIdus == null) return
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') fermerEtude() }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [etudeIdus, fermerEtude])

  if (etudeIdus == null) return null

  return (
    <div data-etude-ecran className="fixed inset-0 z-50 overflow-auto bg-bg" onClick={fermerEtude}>
      <div className="mx-auto my-6 flex min-h-[calc(100vh-3rem)] max-w-[1400px] flex-col overflow-hidden rounded-lg border border-line bg-surface-1"
        onClick={(e) => e.stopPropagation()}>
        {/* clé = l'assiette : rouvrir sur une autre parcelle REMONTE M22 (état neuf, sélection locale).
            M22 (embedded) rend l'écran COMPLET, en-tête compris (← Fermer → onClose / Réinitialiser). */}
        <M22 key={etudeIdus.join(',')} embedded initialIdus={etudeIdus} onBilan={setBilanProg} onClose={fermerEtude} />
      </div>

      {/* Bilan de ce scénario — par-dessus l'Étude (son propre overlay fixed inset-0). */}
      {bilanProg && etudeIdus[0] && (
        <div onClick={(e) => e.stopPropagation()}>
          <BilanEcran idu={etudeIdus[0]} depuisEtude={bilanProg} onClose={() => setBilanProg(null)} />
        </div>
      )}
    </div>
  )
}
