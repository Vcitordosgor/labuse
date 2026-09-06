// CIRCUIT-P (lot 3) — la logique du diagramme SANS le DOM : quels chemins s'allument au survol,
// combien de tuyaux. Testable sans navigateur.
// CIRCUIT-P3 (lot 3.1) — « à regarder » n'est PLUS reclassé ici : le serveur décide (`ko` sur
// chaque réservoir/robinet, via circuit_etats.ko_*), le front le lit. Un seul juge, jamais deux.
import type { CircuitData, Reservoir, Robinet } from './types'

export type Maps = {
  reservoirById: Map<number, Reservoir>
  robinetById: Map<string, Robinet>
  famDeReservoir: Map<number, string>
  reservoirsDeRobinet: Map<string, number[]>
}

export function construireMaps(d: CircuitData): Maps {
  const reservoirById = new Map(d.reservoirs.map((r) => [r.id, r]))
  const robinetById = new Map(d.robinets.map((r) => [r.id, r]))
  const famDeReservoir = new Map<number, string>()
  for (const f of d.familles) for (const id of f.ids) famDeReservoir.set(id, f.nom)
  const reservoirsDeRobinet = new Map<string, number[]>()
  for (const r of d.reservoirs) {
    for (const t of r.taps || []) {
      const l = reservoirsDeRobinet.get(t) || []
      l.push(r.id); reservoirsDeRobinet.set(t, l)
    }
  }
  return { reservoirById, robinetById, famDeReservoir, reservoirsDeRobinet }
}

// Le nombre de tuyaux : un stub par bloc famille + un stub par bloc catégorie + 2 (le collecteur
// rejoint la pompe d'un trait, le distributeur aussi). = familles + catégories + 2 (règle 3.3).
export const nbConduits = (nFamilles: number, nCategories: number) => nFamilles + nCategories + 2

// Le survol d'une ligne allume son chemin : famille → pompe → catégories (règle 3).
export function cheminsAllumes(
  hover: { type: 'reservoir'; id: number } | { type: 'robinet'; id: string } | null,
  maps: Maps,
): { familles: Set<string>; categories: Set<string> } {
  const familles = new Set<string>()
  const categories = new Set<string>()
  if (!hover) return { familles, categories }
  if (hover.type === 'reservoir') {
    const fam = maps.famDeReservoir.get(hover.id)
    if (fam) familles.add(fam)
    const r = maps.reservoirById.get(hover.id)
    for (const t of r?.taps || []) {
      const rob = maps.robinetById.get(t)
      if (rob) categories.add(rob.categorie)
    }
  } else {
    const rob = maps.robinetById.get(hover.id)
    if (rob) categories.add(rob.categorie)
    for (const rid of maps.reservoirsDeRobinet.get(hover.id) || []) {
      const fam = maps.famDeReservoir.get(rid)
      if (fam) familles.add(fam)
    }
  }
  return { familles, categories }
}
