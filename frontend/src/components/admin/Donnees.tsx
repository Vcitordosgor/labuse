// CIRCUIT-P2 (lot 1.1) — la page « Données » EST le Circuit, rien d'autre. L'ancien enrobage
// (bandeau « Mes données sont-elles à jour ? », onglets Catalogue / Circuit / CRON, paragraphes
// « Qui fait quoi » et « Les autres onglets sont des vues ») a disparu : le Circuit porte lui-même
// ses trois onglets (Résumé · Circuit · Journal) et ses deux boutons. Le Catalogue n'existe plus
// (le Circuit avec « tout afficher » + les pages de détail le remplacent ; la page Sources côté
// client reste). Le CRON a quitté Données : son lien vit dans Pilotage, la page /admin/cron est
// inchangée.
import { CircuitSection } from './circuit/Circuit'

export function DonneesSection() {
  return <CircuitSection />
}
