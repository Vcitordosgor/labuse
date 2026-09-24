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
  sans_millesime?: string | null   // CIRCUIT-P6 : la raison écrite du « à jour par construction »
}
export type Robinet = {
  id: string; categorie: string; nom: string; parent: string | null; route: string
  chiffres: string[]; hors_registre: string | null; etat: Etat; ko: boolean; hors_moteur: number
}
export type Famille = { nom: string; ids: number[] }
export type Categorie = { slug: string; nom: string; ids: string[] }

// CIRCUIT-P4 (lot 2) — l'onglet « À faire » : une liste ordonnée de cinq types de gestes.
export type AFaireType = 'injecter' | 'deposer' | 'calculer' | 'basculer' | 'decider'
export type AFaireBouton = {
  label: string; action: string; source?: number; candidat?: string; verrou?: string
  vanne?: string | null; disabled?: boolean; raison?: string | null
}
export type AFaireLigne = {
  type: AFaireType; couleur: Couleur; titre: string; phrase: string
  bouton: AFaireBouton; ghost?: { label: string; action: string; candidat?: string }; cible?: Cible
}
export type AFaire = {
  total: number; lignes: AFaireLigne[]; contexte: string | null
  // CIRCUIT-P7 (lot 4) — trois dates sous le titre (sonde · contrôle du circuit · agents).
  dates?: { sonde: string | null; controle: string | null; agents: string | null }
  calme: { nouvelles: number; pannes: number; jamais?: number; vitrine: number; derniere_bascule: string | null }
}
// CIRCUIT-P4 (lot 1) — le compte par état (pastilles de l'onglet Sources).
export type EtatsSources = {
  'à jour': number; 'nouvelle version': number; 'échue': number
  'jamais vérifiée': number; 'sonde en panne': number; total: number
}
// CIRCUIT-P4 (lot 3) — une source HORS vitrine, avec sa raison en clair et la date de la décision.
export type HorsVitrine = {
  id: number; nom: string; famille: string; statut: string; statut_label: string
  raison: string; depuis: string | null
}

export type CircuitData = {
  run_servi: string; candidat: string | null; manifeste: any
  reservoirs: Reservoir[]; robinets: Robinet[]; chiffres: Record<string, any>
  familles: Famille[]; categories: Categorie[]; resume: Resume
  a_faire?: AFaire; etats_sources?: EtatsSources   // CIRCUIT-P4 (lots 1-2)
  hors_vitrine?: HorsVitrine[]   // CIRCUIT-P4 (lot 3)
  aretes: { reservoir_vers_chiffre: [string, string][]; chiffre_vers_robinet: [string, string][] }
  fuites: any[]; eau_ancienne: any[]; dernier_controle: any | null
  journal: any[]; runs: any[]; residuel: any; compteurs: Record<string, number>
  // DASHBOARD-4 D1 — les compteurs tels que les verrous les comptent (source unique).
  compteurs_coherence?: { sources_vitrine: number | null; couches: number | null; donnees: number | null; verrous: number; garanties: number | null }
  // DASHBOARD-4 D7 / CIRCUIT-P7 (lot 1) — la carte Agents : plafond + dernier passage (coût du ledger,
  // nouvelles trouvées), prochain dimanche, et les portées du menu (jamais / g8 / vitrine + coût estimé).
  agents?: {
    plafond_eur: number; actif: boolean; cle_env: string; credit_eur: number | null; credit_url: string
    dernier_passage?: string | null; sources?: number; cout_eur?: number | null; nouvelles?: number
    prochain_dimanche?: string | null; jamais?: number; g8?: number; vitrine?: number; cout_estime_tous?: number | null
  }
  // CIRCUIT-P7 (lot 1) — la carte Sonde de nuit (cadence, dernier passage, interrogées / en panne / nouvelles).
  sonde?: {
    cadence: string; interrogeables: number; dernier_passage: string | null
    interrogees: number; en_panne: number; nouvelles: number
  }
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
