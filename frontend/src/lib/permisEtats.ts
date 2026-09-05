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
/** Trois valeurs peintes sur la carte (Achevé + Autre → gris). */
export type PermisEtatCarte = 'recent' | 'dormant' | 'gris'

export const PERMIS_ETAT_COLOR: Record<PermisEtatCarte, string> = {
  recent: TOKENS.mint,        // vert de marque #4ADE80
  dormant: TOKENS.coral,      // corail #E2726A (couleur historique du dormant, inchangée)
  gris: TOKENS.stExclue,      // gris neutre existant #6B7A72 (Achevé + Autre)
}

/** Réduit un état de panneau (4) à sa couleur de carte (3). */
export const carteEtat = (e: PermisEtat): PermisEtatCarte =>
  e === 'recent' ? 'recent' : e === 'dormant' ? 'dormant' : 'gris'

/** Couleur de la pastille d'un état de panneau. */
export const etatColor = (e: PermisEtat): string => PERMIS_ETAT_COLOR[carteEtat(e)]

// Légende de carte (W3) — trois entrées, l'ordre du cycle de vie. Achevé et Autre fondus en « gris ».
export const PERMIS_LEGENDE: { key: PermisEtatCarte; color: string; label: string }[] = [
  { key: 'recent', color: PERMIS_ETAT_COLOR.recent, label: 'Récent (autorisé ≤ 24 mois)' },
  { key: 'dormant', color: PERMIS_ETAT_COLOR.dormant, label: 'Dormant (ancien PC sans achèvement)' },
  { key: 'gris', color: PERMIS_ETAT_COLOR.gris, label: 'Achevé ou autre' },
]
