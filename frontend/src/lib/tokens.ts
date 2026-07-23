/** LOI-0 — miroir JS de la palette Tailwind (tailwind.config.js) : LA source des couleurs
 *  appliquées en `style` inline, là où une classe utilitaire n'est PAS applicable (valeur hex
 *  requise, notamment l'astuce d'opacité `${c}22` qui suffixe l'alpha au hex 6 chiffres).
 *  Aucune couleur en dur dans les composants : on passe par ici.
 *
 *  Les valeurs des STATUTS sont IDENTIQUES aux tokens Tailwind → rendu pixel-identique.
 *  La palette « viabilité / confiance » est une data-viz douce DISTINCTE des statuts
 *  (#E6B15C ≠ st-creuser #E8B44C, #E68A6B ≠ st-ecartee #E8695A) : tokens créés en O4 pour ne
 *  jamais approximer sur un token de statut. */
export const TOKENS = {
  // — statuts matrice premium v2 (= tailwind theme.colors) —
  mint: '#5CE6A1',
  violet: '#B497F0',
  violetDim: '#8b76c0',
  stChaude: '#5CE6A1',
  stSurveiller: '#4ADE96',
  stCreuser: '#E8B44C',
  stEcartee: '#E8695A',
  stNone: '#39463F',
  txtMut: '#8FA69A',
  txtDim: '#5C7268',

  // — data-viz de graphe (barres marché/typologie ; hues distinctes, tokens créés O4) —
  vizCyan: '#7DE8E0',
  vizGreenDeep: '#2E6B4F',

  // — viabilité / confiance (data-viz douce, tokens dédiés) —
  viabConfirmee: '#5CE6A1', viabConfirmeeBg: '#14251E',
  viabProbable: '#8FD9B6', viabProbableBg: '#16231D',
  viabIncertaine: '#E6B15C', viabIncertaineBg: '#2A2213',
  viabLourde: '#E68A6B', viabLourdeBg: '#2A1A13',
} as const
