/** FIX-PRIX-ET-OPPORTUNITES (lot 3) — la capacité constructible est un MAXIMUM réglementaire.
 *
 *  Miroir TypeScript de `src/labuse/capacite_max.py` (à garder synchrone). Suite de VERITE-TERRAIN-2
 *  volet D : face à 6 601 permis réels post-PLU, la capacité servie (SDP max, logements) est un PLAFOND
 *  — les projets déposés en utilisent en médiane ~la moitié (ratio médian 0,46 en surface, 0,40 en
 *  logements). Partout où une capacité est affichée, on le dit : maximum réglementaire, pas le programme
 *  qui sera déposé. */

export const CAPACITE_RATIO_MEDIAN_SDP = 0.46
export const CAPACITE_RATIO_MEDIAN_LOGEMENTS = 0.4

/** mention complète (survol / détail). */
export const CAPACITE_MAX_MENTION =
  'Maximum réglementaire (gabarit) : le total que la parcelle peut porter selon les règles, pas le ' +
  'programme qui sera déposé. Face aux permis réellement autorisés (volet D VERITE-TERRAIN-2), les ' +
  'projets en utilisent en médiane environ la moitié (0,46 en surface, 0,40 en logements).'

/** mention courte (chip / inline). */
export const CAPACITE_MAX_MENTION_COURTE =
  'maximum réglementaire — les permis réels en utilisent ~½ en médiane (volet D)'
