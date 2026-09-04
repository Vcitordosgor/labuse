// RETOURS-11 T6 (03/09) — référentiel UNIQUE de l'affichage des noms de commune.
// Décision Vic : trois communes gardent leur article partout (« Le Port », « Le Tampon »,
// « La Possession ») ; les 21 autres restent EXACTEMENT comme aujourd'hui — c'est-à-dire que
// l'article n'est élidé QUE sur les pastilles de la carte (où il l'était déjà pour toutes).
// Un seul endroit décide : la carte, les listes et les tables passent par ces fonctions.

export const COMMUNES_ARTICLE_GARDE = new Set(['Le Port', 'Le Tampon', 'La Possession'])

const ARTICLE = /^(Les|Le|La|L')\s?/

/** Nom affiché sur les pastilles de la carte : article élidé SAUF pour les trois retenues. */
export function communePastille(nom: string): string {
  if (COMMUNES_ARTICLE_GARDE.has(nom)) return nom
  return nom.replace(ARTICLE, '')
}

/** Clé de tri qui ignore l'article (comme l'annuaire PLU) : « Le Port » se range à « P ». */
export function communeSortKey(nom: string): string {
  return nom.replace(ARTICLE, '')
}

/** Tri alphabétique français des communes, article ignoré. */
export function trierCommunes<T>(items: T[], nomDe: (x: T) => string): T[] {
  return [...items].sort((a, b) => communeSortKey(nomDe(a)).localeCompare(communeSortKey(nomDe(b)), 'fr'))
}
