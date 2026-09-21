// CIRCUIT-P2 (lot 1.1) — la page « Données » EST le Circuit, rien d'autre. L'ancien enrobage
// (bandeau « Mes données sont-elles à jour ? », onglets Catalogue / Circuit / CRON, paragraphes
// « Qui fait quoi » et « Les autres onglets sont des vues ») a disparu : le Circuit porte lui-même
// ses trois onglets (Résumé · Circuit · Journal) et ses deux boutons.
// DASHBOARD-2 (Lot 7) — « Destinations » a quitté le rail : sa calibration est désormais le DÉTAIL
// du réservoir `plu_destinations`, ouvert par un lien depuis ici (la donnée destination coule dans
// le Circuit comme les autres). Le CRON reste une page à part (lien dans Pilotage).
import { useState } from 'react'
import { CircuitSection } from './circuit/Circuit'
import { DestinationsDetail } from './Destinations'

export function DonneesSection() {
  const [vue, setVue] = useState<'circuit' | 'destinations'>('circuit')
  if (vue === 'destinations') return <DestinationsDetail onBack={() => setVue('circuit')} />
  // DASHBOARD-4 (D6) — « Destinations PLU » : entrée EN BAS du Circuit (détail du réservoir
  // plu_destinations), pas en tête. La donnée destination coule dans le Circuit comme les autres.
  return (
    <div className="flex flex-col gap-3">
      <CircuitSection />
      <div className="mt-1 border-t border-line pt-3 text-[13px]">
        <button onClick={() => setVue('destinations')} className="text-mint hover:underline">
          Destinations PLU — le détail du réservoir <span className="font-mono">plu_destinations</span> (calibrage par commune) →
        </button>
      </div>
    </div>
  )
}
