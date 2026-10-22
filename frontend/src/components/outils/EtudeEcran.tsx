// IMPLANTATION-4 — L'ÉCRAN D'ÉTUDE DANS DOCS. L'Étude de faisabilité a quitté les Outils ; elle s'ouvre
// en overlay plein écran (patron BilanEcran), monté au niveau App et piloté par le drapeau `etudeIdus`.
// Depuis la suite v4, l'écran est SANS CARTE : EtudeEcran n'est plus qu'une COQUILLE d'overlay (cadre +
// fermeture + Échap + pont Bilan). Tout l'écran (en-tête ← Fermer / Réinitialiser, configuration,
// scénarios, chiffres clés, PLAN MASSE DESSINÉ, sections) est rendu par le MÊME composant M22 en mode
// `embedded`, servi par la MÊME API (POST /modules/etude). Aucun second calcul. Entrées : 9e carte Docs,
// tuile fiche, pont Assemblage, et les anciens liens #m=programme (redirigés ici par App.tsx).
import { useEffect, useState } from 'react'
import { useApp } from '../../store/useApp'
import { EtudeV6 } from './EtudeV6'
import type { EtudeProgramme } from './M22Programme'
import { BilanEcran } from '../fiche/BilanEcran'

// ETUDE-V6 — l'overlay Docs monte le parcours en 3 étapes (EtudeV6). M22 reste pour son mode outil et
// ses tests. Lot B : le pont « Bilan de ce scénario » est recâblé depuis le RÉSULTAT (la variante
// affichée transmet son programme au Bilan existant — pas de refonte du Bilan).
export function EtudeEcran() {
  const etudeIdus = useApp((s) => s.etudeIdus)
  const fermerEtude = useApp((s) => s.fermerEtude)
  const [bilanProg, setBilanProg] = useState<EtudeProgramme | null>(null)

  // Échap ferme. Le hook est inconditionnel ; il ne fait rien quand l'overlay est fermé.
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
        {/* clé = l'assiette : rouvrir sur une autre parcelle REMONTE le wizard (état neuf). */}
        <EtudeV6 key={etudeIdus.join(',')} initialIdus={etudeIdus} onClose={fermerEtude} onBilan={setBilanProg} />
      </div>

      {/* Bilan de ce scénario — par-dessus l'Étude (son propre overlay). Le Bilan porte sur la 1ʳᵉ parcelle. */}
      {bilanProg && etudeIdus[0] && (
        <div onClick={(e) => e.stopPropagation()}>
          <BilanEcran idu={etudeIdus[0]} depuisEtude={bilanProg} onClose={() => setBilanProg(null)} />
        </div>
      )}
    </div>
  )
}
