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
  // ═══ DA v3 (docs/DA-LABUSE.html §1) — miroir des tokens, synchronisé avec
  //     tailwind.config.js et :root (styles/index.css). ═══
  // surfaces et filets
  bg0: '#0A0C0B', bg1: '#0C0F0D', bg2: '#111614', bgStat: '#141A17', bg3: '#161C19',
  line: '#1A211D', line2: '#212A25', line3: '#2C3630', lineCard: '#1E2622', lineBtn: '#263029',
  // texte — 7 niveaux + labels
  txtHi: '#E8EFEA', txt: '#B8C4BC', lab: '#7C8A82',
  txtOff: '#5E6B64', txtFaint: '#4E5A53', txtGhost: '#3E4A44',
  // sémantique DA
  mintBg: '#12291D', mintOn: '#06301A', mintSub: '#0B4526',
  amber: '#E0A94F', amberBg: '#2A2113',
  // M87 — état « en retard sur sa cadence » (page Sources). Token unique, repris de DA-LABUSE.html.
  warn: '#D9873D', warnBg: 'rgba(217,135,61,.10)', warnDim: '#8a5a28',
  coral: '#E2726A', coralBg: '#2B1715',
  blue: '#8FB4F0', iris: '#8B7BD8', iris2: '#C4B5FD', irisBg: '#16121F', irisLine: '#2E2545',
  danger: '#8A5A5A', dangerLine: '#3A2626', lien: '#7FA88F',

  // — statuts matrice premium v2 (= tailwind theme.colors) —
  mint: '#4ADE80',
  violet: '#B497F0',
  violetDim: '#8b76c0',
  stChaude: '#5CE6A1',
  stSurveiller: '#4ADE96',
  stCreuser: '#E8B44C',
  stEcartee: '#E8695A',
  stNone: '#39463F',
  txtMut: '#6B776F',
  txtDim: '#8A968F',

  // — data-viz de graphe (barres marché/typologie ; hues distinctes, tokens créés O4) —
  vizCyan: '#7DE8E0',
  vizGreenDeep: '#2E6B4F',

  // — viabilité / confiance (data-viz douce, tokens dédiés) —
  viabConfirmee: '#5CE6A1', viabConfirmeeBg: '#14251E',
  viabProbable: '#8FD9B6', viabProbableBg: '#16231D',
  viabIncertaine: '#E6B15C', viabIncertaineBg: '#2A2213',
  viabLourde: '#E68A6B', viabLourdeBg: '#2A1A13',

  // — segment Renouvellement (M-RENOUV) : CUIVRE, teinte propre — ni le vert chaud des
  //   statuts, ni le violet signal ; distinct de viabIncertaine #E6B15C (ambre) et de
  //   stCreuser #E8B44C (jaune). Parcelles OCCUPÉES, potentiel de renouvellement urbain.
  renouv: '#C9834E', renouvBg: '#291D12',
} as const
