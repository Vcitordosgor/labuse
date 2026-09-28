// FRONT-CHIFFRES-2 (F13/F29) — LE HOOK des paliers servis (jeton DA + ton + libellés). Chargé une
// fois, mis en cache long (le vocabulaire ne change qu'à une bascule de run). La pastille (Projets)
// et le badge (Outils) l'utilisent pour NE PLUS coder la correspondance palier→couleur : à q_v15
// (bandes A/B/C/D) seul le back change. Tant que la carte n'est pas chargée / si l'endpoint échoue,
// l'appelant rend un ton neutre — jamais une couleur inventée au front.
import { useQuery } from '@tanstack/react-query'

import { getPaliersDA, type PalierDA } from './api'
import { codePalier } from './status'

export function usePaliersDA(): Record<string, PalierDA> | undefined {
  const q = useQuery({ queryKey: ['vocabulaire-paliers'], queryFn: getPaliersDA, staleTime: 60 * 60 * 1000 })
  return q.data?.paliers
}

/** la DA du palier canonique d'un tier (jeton + ton + chip), ou undefined si non résolu/non chargé. */
export function palierDe(tier: string | null | undefined, paliers: Record<string, PalierDA> | undefined): PalierDA | undefined {
  const code = codePalier(tier)
  return code && paliers ? paliers[code] : undefined
}
