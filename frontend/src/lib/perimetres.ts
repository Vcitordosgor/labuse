// OUTILS-2 (O2-5) — VOCABULAIRE UNIQUE des périmètres de capacité constructible.
//
// Sur une parcelle bâtie, deux chiffres coexistent et se CONTREDISENT en apparence :
//  • le RÉSIDUEL (bâti conservé) — ce qu'on peut ajouter SANS démolir l'existant (parcel_residuel,
//    servi par Pièges & risques / le potentiel de transformation de la fiche) ;
//  • le POTENTIEL (terrain libéré) — la capacité au gabarit PLU si le terrain est LIBÉRÉ (Faisabilité,
//    SHAB vendable).
// Un client les lit comme une erreur si aucun ne porte son périmètre. On étiquette donc CHAQUE chiffre,
// partout où il apparaît (fiche, Pièges, Faisabilité, Comparaison, Étudier un bien), avec un vocabulaire
// UNIQUE défini ICI — un seul endroit à changer, jamais deux libellés qui divergent.
export const PERIM_RESIDUEL = 'résiduel, bâti conservé'
export const PERIM_POTENTIEL = 'potentiel, terrain libéré'
// Formes COURTES — le « périmètre en un mot » à accoler à un libellé métier déjà nommé (« SDP
// résiduelle · bâti conservé », « SHAB vendable · terrain libéré »). Même source, un seul endroit.
export const PERIM_RESIDUEL_COURT = 'bâti conservé'
export const PERIM_POTENTIEL_COURT = 'terrain libéré'
