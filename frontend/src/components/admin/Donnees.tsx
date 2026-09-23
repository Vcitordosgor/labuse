// CIRCUIT-P2 (lot 1.1) — la page « Données » EST le Circuit, rien d'autre : il porte lui-même ses
// onglets (À faire · Sources · Circuit · Journal) et ses deux boutons.
// CIRCUIT-P5 — « Destinations » (le calibrage du moteur plu_destinations, commune × état) n'a plus
// de lien EN BAS de la page : son détail complet s'ouvre depuis la page de détail de la SOURCE GPU
// (Sources → « Urbanisme PLU/GPU » → « Voir le calibrage complet par commune »). Le composant
// DestinationsDetail est inchangé — il est simplement atteint autrement (via le détail de la source).
import { CircuitSection } from './circuit/Circuit'

export function DonneesSection() {
  return <CircuitSection />
}
