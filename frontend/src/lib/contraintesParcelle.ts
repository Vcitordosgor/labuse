import { useQuery } from '@tanstack/react-query'
import { lireJson } from './api'

export type Alerte = {
  categorie: string
  effet: string
  source: string
  date: string | null
  redhibitoire?: boolean
  statut?: 'a_verifier' | 'rouge_total' | 'rouge_partiel' | 'prescription' | null
  geometries?: GeoJSON.Geometry[]
  reglements?: string[]
  portee?: 'parcelle'
}

type Servitudes = {
  idu: string; n: number; synthese: string
  servitudes: Alerte[]
  // OUTILS-P0-1 (#2) — chaque famille prend un état parmi quatre ; l'écran rend trois listes dérivées :
  //  · verifie = « Aucune intersection détectée » (source dont la couverture de la commune est démontrée) ;
  //  · couverture_inconnue = « Couverture inconnue » (rien remonté mais couverture non démontrée) ;
  //  · lecture_indisponible = « Lecture indisponible » (lecture échouée — ex. radar PLU en panne).
  verifie?: string[]
  couverture_inconnue?: string[]
  lecture_indisponible?: string[]
  plu_radar_ok?: boolean
  // RETOURS-27 (pt 2) — procédure PLU en cours (carte dédiée) ; null si aucune n'est servie.
  procedure_plu?: { source_url?: string; libelle: string; stade?: string | null; source?: string | null; date?: string | null; date_constat?: string | null } | null
  non_couvert: string[]
}

function grouperContraintes(alertes: Alerte[]) {
  const parCategorie = new Map<string, Alerte[]>()
  for (const a of alertes) {
    const lignes = parCategorie.get(a.categorie) ?? []
    lignes.push(a)
    parCategorie.set(a.categorie, lignes)
  }
  function priorite(a: Alerte) {
    if (a.statut === 'a_verifier') return 1
    return a.redhibitoire ? 0 : 2
  }
  return [...parCategorie.values()]
    .map(lignes => lignes.sort((a, b) => priorite(a) - priorite(b)))
    .sort((a, b) => priorite(a[0]) - priorite(b[0]))
}

export function useContraintesParcelle(idu: string) {
  const id = idu.trim()
  return useQuery({
    queryKey: ['o5', id],
    queryFn: () => lireJson<Servitudes>(`/servitudes-invisibles/${id}`),
    enabled: id.length === 14,
    select: avecGroupes,
  })
}

function avecGroupes(d: Servitudes) {
  return { ...d, groupes: grouperContraintes(d.servitudes) }
}

export type ContraintesParcelle = ReturnType<typeof avecGroupes>
