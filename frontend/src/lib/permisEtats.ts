// RETOURS-17 W2/W3 — SOURCE UNIQUE des couleurs et libellés des états de permis, partagée par le
// panneau (pastilles + lignes filtrantes), la carte (couleur du point) et la légende. Une seule liste,
// jamais deux : la couleur d'un état est la MÊME sur la pastille et sur la carte (constat Vic 05/09 :
// la carte peignait tout en vert alors que les compteurs disaient trois choses).
//
// La base Sitadel se PARTITIONNE en quatre états dont la somme fait le total (mesuré en W1 le 05/09,
// base locale q_v11_m137 : Récent 5 580 · Dormant 15 466 · Achevé 20 534 · Autre 8 964 = 50 544) :
//   • Récent  — autorisé dans les 24 derniers mois (fenêtre de veille) ;
//   • Dormant — PC ancien (> 36 mois) sans achèvement déclaré, parcelle toujours non bâtie (opportunité) ;
//   • Achevé  — travaux déclarés terminés (DAACT) — le gros du reste, 40 % de la base ;
//   • Autre   — ni récent, ni dormant, ni achevé (natures DP/PA/PD, permis non rattachés, période 24-36 mois).
//
// Sur la CARTE, Achevé et Autre partagent le même GRIS neutre (décision Vic 05/09 : la carte répond
// « où sont les récents et les dormants », le reste est un fond neutre) — trois couleurs à l'écran,
// quatre lignes au panneau. `carteEtat` réduit un état de panneau à sa couleur de carte.
import { TOKENS } from './tokens'

export type PermisEtat = 'recent' | 'dormant' | 'acheve' | 'autre'
/** MINI-CORRECTIONS-2 (pt 16) — QUATRE couleurs distinctes désormais (Achevé et Autre ne sont plus
 *  fondus) : la carte et la légende répondent « récent / dormant / achevé / autre » d'un coup d'œil. */
export type PermisEtatCarte = 'recent' | 'dormant' | 'acheve' | 'autre'

export const PERMIS_ETAT_COLOR: Record<PermisEtatCarte, string> = {
  recent: TOKENS.blue,        // bleu #8FB4F0 — Récents (demande Vic)
  dormant: TOKENS.coral,      // corail/rouge #E2726A — Dormants
  acheve: TOKENS.stExclue,    // gris neutre #6B7A72 — Achevés
  autre: TOKENS.amber,        // orange #E0A94F — Autres
}

/** Couleur de carte d'un état de panneau : identité (4 ↔ 4) depuis MINI-CORRECTIONS-2 (pt 16). */
export const carteEtat = (e: PermisEtat): PermisEtatCarte => e

/** Couleur de la pastille d'un état de panneau. */
export const etatColor = (e: PermisEtat): string => PERMIS_ETAT_COLOR[carteEtat(e)]

// Légende de carte — QUATRE entrées, l'ordre du cycle de vie, mêmes couleurs que les points.
export const PERMIS_LEGENDE: { key: PermisEtatCarte; color: string; label: string }[] = [
  { key: 'recent', color: PERMIS_ETAT_COLOR.recent, label: 'Récent (autorisé ≤ 24 mois)' },
  { key: 'dormant', color: PERMIS_ETAT_COLOR.dormant, label: 'Dormant (ancien PC sans achèvement)' },
  { key: 'acheve', color: PERMIS_ETAT_COLOR.acheve, label: 'Achevé (travaux déclarés)' },
  { key: 'autre', color: PERMIS_ETAT_COLOR.autre, label: 'Autre' },
]
