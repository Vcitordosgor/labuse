// DONNEES-6/7 — un permis dont le dépôt est enregistré APRÈS l'autorisation est une incohérence du
// producteur (SDES/Dido, ~15 % des permis). On ne réordonne JAMAIS les dates ; on qualifie l'écart :
// au-delà d'1 MOIS c'est le plus souvent un permis modificatif ou transféré (nouveau dépôt postérieur
// sur l'autorisation d'origine — le flux open data ne porte pas le n° de modificatif, on le dit comme
// tendance) ; sous 1 mois on ne présume rien. Rend null si les dates sont cohérentes ou absentes.
// Miroir Python : src/labuse/exports/miroir.py:permis_incoherence_note (mêmes libellés, même seuil).
export function permisIncoherenceNote(dep?: string | null, aut?: string | null): string | null {
  if (!dep || !aut || aut >= dep) return null
  const gapDays = (Date.parse(dep) - Date.parse(aut)) / 86_400_000
  return gapDays > 31
    ? "Dépôt enregistré après l'autorisation — souvent un permis modificatif ou transféré"
    : 'dates incohérentes chez le producteur'
}
