import { useQuery } from '@tanstack/react-query'
import { getCommunes, getResults, getStats } from './api'
import type { Statut } from './types'
import { EMPTY_FILTERS, useApp, type Filters } from '../store/useApp'

/** Filtres (forme FILTER_SCHEMA serveur) → objet Filters du store. Pur, déterministe.
 *  La commune n'est PAS ici : c'est un filtre de périmètre géré par le geste d'application. */
export function filtresToFilters(f: Record<string, unknown>): Filters {
  return {
    ...EMPTY_FILTERS,
    statuts: (f.statuts as Statut[]) ?? [],
    scoreMin: (f.scoreMin as number | null) ?? null,
    surfaceMin: (f.surfaceMin as number | null) ?? null,
    surfaceMax: (f.surfaceMax as number | null) ?? null,
    sdpMin: (f.sdpMin as number | null) ?? null,
    evenement: !!f.evenement,
    vueMer: !!f.vueMer,
    flags: (f.flags as string[]) ?? [],
    flagsExclus: (f.flagsExclus as string[]) ?? [],
    communes: (f.communes as string[]) ?? [],
  }
}

/** La chorégraphie d'application PARTAGÉE (copilote R2 ET « ouvrir un projet » = rejouer) :
 *  périmètre → filtres → verdict allumé → vol caméra → restitution (compteur + top 3). Les
 *  chiffres viennent du SERVEUR (getStats/getResults) — jamais calculés côté client. */
export function useApplySearch() {
  const communesQ = useQuery({ queryKey: ['communes'], queryFn: getCommunes })
  const { setFilters, setView, setCommune, setVerdict, setFlyTo, setIaRestitution } = useApp()

  return async (raw: Record<string, unknown>, phrase = 'parcelles correspondent — voici les 3 meilleures') => {
    // la commune est un filtre de PÉRIMÈTRE : un secteur d'UNE commune = la commune elle-même
    let communes = (raw.communes as string[]) ?? []
    let communeSeule = typeof raw.commune === 'string' && raw.commune ? raw.commune : null
    if (communes.length === 1) { communeSeule = communes[0]; communes = [] }
    if (communes.length > 0) setCommune(null)
    else if (communeSeule) setCommune(communeSeule)

    const next = filtresToFilters({ ...raw, communes })
    setFilters(next)
    setVerdict(true)          // le tri est ALLUMÉ — mise en scène cohérente avec R1
    setView('cartes')

    // vol de caméra vers le périmètre (bbox commune, union du secteur, ou île)
    const infos = communesQ.data ?? []
    const cible = communes.length ? communes : (communeSeule ? [communeSeule] : [])
    const boxes = infos.filter((c) => cible.includes(c.commune)).map((c) => c.bbox)
    if (boxes.length) {
      const x1 = Math.min(...boxes.map((b) => b[0])), y1 = Math.min(...boxes.map((b) => b[1]))
      const x2 = Math.max(...boxes.map((b) => b[2])), y2 = Math.max(...boxes.map((b) => b[3]))
      setFlyTo({ center: [(x1 + x2) / 2, (y1 + y2) / 2], zoom: boxes.length > 1 ? 10.2 : 11.5 })
    } else {
      setFlyTo({ center: [55.53, -21.13], zoom: 9.7 })
    }

    // restitution : compteur + les 3 meilleures, cliquables (best-effort — filtres déjà posés)
    try {
      // top 3 seulement → limite basse (20) : sous contention de tuiles « tout », une réponse
      // légère revient bien plus vite qu'un /parcels?limit=500 (la restitution est un flourish)
      const [st, top] = await Promise.all([getStats(next), getResults(next, 20)])
      setIaRestitution({
        n: st.chaude + st.a_surveiller + st.a_creuser,
        phrase,
        top: top.slice(0, 3).map((t) => ({ idu: t.idu, commune: t.commune, q_score: t.q_score })),
      })
    } catch { /* restitution best-effort — les filtres sont déjà posés */ }
  }
}
