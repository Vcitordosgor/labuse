// CIRCUIT-P — types partagés de la page Circuit. Le backend est la vérité : ces types décrivent ce
// que `/admin/circuit` (+ détail + journal) renvoie. Les états portent toujours [couleur, libellé].
export type Couleur = 'mint' | 'ambre' | 'rouge' | 'gris' | 'mauve'
export type Etat = [Couleur, string]

export type CibleType = 'reservoir' | 'robinet' | 'pompe' | 'compteur'
export type Cible = { type: CibleType; ids: (number | string)[] }
export type Ligne = { n: number; couleur: Couleur; titre: string; phrase: string; verbe: string; cible: Cible }
export type Kpi = { valeur: number | string; sur?: number; libelle: string; candidat?: string | null; detail?: string }
export type Resume = { total: number; kpis: Kpi[]; groupes: { titre: string; lignes: Ligne[] }[]; reste: { reservoirs: number; robinets: number; chiffres: number } }

export type Reservoir = {
  id: number; nom: string; producteur: string; famille: string; slug: string | null
  millesime: string | null; ingere_le: string | null; mode: string
  cadence_jours: number | null; cadence_statut: string | null; a_verifier: boolean
  dernier_controle: string | null; etat: Etat; ko: boolean; taps: string[]; chiffres_ids: string[]
  vanne: { type: string; label?: string; motif?: string }
  veille: any | null; filtre: any
}
export type Robinet = {
  id: string; categorie: string; nom: string; parent: string | null; route: string
  chiffres: string[]; hors_registre: string | null; etat: Etat; ko: boolean; hors_moteur: number
}
export type Famille = { nom: string; ids: number[] }
export type Categorie = { slug: string; nom: string; ids: string[] }

export type CircuitData = {
  run_servi: string; candidat: string | null; manifeste: any
  reservoirs: Reservoir[]; robinets: Robinet[]; chiffres: Record<string, any>
  familles: Famille[]; categories: Categorie[]; resume: Resume
  aretes: { reservoir_vers_chiffre: [string, string][]; chiffre_vers_robinet: [string, string][] }
  fuites: any[]; eau_ancienne: any[]; dernier_controle: any | null
  journal: any[]; runs: any[]; residuel: any; compteurs: Record<string, number>
  // DASHBOARD-4 D1 — les compteurs tels que les verrous les comptent (source unique).
  compteurs_coherence?: { sources_vitrine: number | null; couches: number | null; donnees: number | null; verrous: number; garanties: number | null }
  // DASHBOARD-4 D7 — plafond des agents (0 = aucun agent ne tourne) + crédit API (non exposé → lien).
  agents?: { plafond_eur: number; actif: boolean; cle_env: string; credit_eur: number | null; credit_url: string }
  garanties?: { id: string; phrase: string; verdict: string; preuve: string; details: string[] }[] | null
}

// DASHBOARD-4 D2 — une tâche « verrous » détachée : progression + résultat persistant (30 lignes).
export type VerrouLigne = { id: string; phrase: string; verdict: string; preuve: string; details: string[]; avertissement?: boolean }
export type VerrousTache = {
  etat: 'en_cours' | 'termine' | 'echec'; fait?: number; total?: number; message?: string; maj?: string; par?: string
  resultat?: { lignes: VerrouLigne[]; casses: string[]; bloquants: string[]; joues: number; verrous: number; garanties: number }
} | null

// La cible d'une ligne du résumé, portée vers l'onglet Circuit : ouvrir un détail (une seule cible)
// ou déplier le circuit sur des ids (plusieurs).
export type Focus =
  | { kind: 'detail'; type: 'reservoir' | 'robinet' | 'pompe' | 'compteur'; id: number | string }
  | { kind: 'groupe'; type: 'reservoir' | 'robinet'; ids: (number | string)[] }
  | null

export function focusDeCible(c: Cible): Focus {
  if (c.type === 'pompe') return { kind: 'detail', type: 'pompe', id: 'pompe' }
  if (c.type === 'compteur') return { kind: 'detail', type: 'compteur', id: 'compteur' }
  if (c.ids.length === 1) return { kind: 'detail', type: c.type, id: c.ids[0] }
  return { kind: 'groupe', type: c.type, ids: c.ids }
}
