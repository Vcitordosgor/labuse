/** S03-S05 (revue UI/UX) — libellés FRANÇAIS des couches de la cascade.
 *  AFFICHAGE SEULEMENT : la clé technique (`residuel_socle`…) reste la donnée,
 *  visible au survol/tap (audit) et dans la trace source_table#id. Une clé
 *  inconnue s'affiche telle quelle — jamais un libellé inventé. */

export const LAYER_LABEL: Record<string, string> = {
  // règles
  zonage_plu_gpu: 'Zonage PLU',
  prescription_plu: 'Prescriptions PLU',
  foncier_public: 'Foncier public',
  emprise_lineaire: 'Emprise linéaire',
  emprise_routiere: 'Emprise routière',
  residuel_socle: 'SDP résiduelle',
  safer: 'SAFER',
  sar: 'SAR (aménagement régional)',
  surface: 'Surface parcelle',
  parc_national: 'Parc national',
  foret_publique: 'Forêt publique',
  cinquante_pas: '50 pas géométriques',
  sup: 'Servitudes (SUP)',
  // risques
  risques: 'Risques PPR',
  sol_pollue: 'Sols pollués',
  cavite: 'Cavités',
  icpe: 'ICPE',
  mvt: 'Mouvement de terrain',
  pente: 'Pente',
  ravine: 'Ravines',
  trait_de_cote: 'Trait de côte',
  abf: 'ABF / Monuments',
  ens: 'Espace naturel sensible',
  eau: 'Eau',
  bruit_route: 'Bruit routier',
  // marché
  dvf: 'Marché DVF',
  sitadel: 'Permis SITADEL',
  amenites: 'Aménités',
  potentiel_foncier_region: 'Potentiel foncier Région',
  ocs_ge: 'Occupation du sol',
  friche: 'Friche',
  acces: 'Accès voirie',
  // proprio
  proprietaire: 'Propriétaire',
  age_dirigeant: 'Âge du dirigeant',
  bodacc: 'BODACC',
  dpe_passoire: 'DPE passoire',
  assemblage: 'Assemblage',
  // étage 0 / divers
  bati: 'Bâti',
  osm_faux_positif: 'Faux positif OSM',
}

export const layerLabel = (key: string): string => LAYER_LABEL[key] ?? key

// ─────────────────────────────────────────────────────────────────────────────
// M12 · LOT C2 — TEXTES « i » DES COUCHES (écrits pour un CLIENT, pas un
// géomaticien). Centralisés ICI (règle R3) : Vic réécrit sa voix sans toucher au
// JSX. La clé = la clé de `LayerToggles` (store useApp). Une phrase, sans jargon.
// ─────────────────────────────────────────────────────────────────────────────
export const LAYER_INFO: Record<string, string> = {
  zonage:
    'Les zones du PLU telles que déposées officiellement par la commune sur le Géoportail de l’urbanisme (source GPU) : les grands aplats de couleur, avec leurs contours d’origine — qui ne suivent pas forcément le découpage cadastral. C’est le document opposable de référence. À la différence de « Zonage PLU (par parcelle) » (qui colore chaque parcelle et affiche son code de zone au clic) et de « Colorisation par type de zonage » (qui teinte toutes les parcelles d’un coup), cette couche montre le zonage brut, non rattaché aux parcelles.',
  zonage_parcelle:
    'Chaque parcelle prend la couleur de sa zone du PLU. En zoomant, ou en cliquant une parcelle, le code exact de la zone (par ex. U1a, 1AUc) s’affiche.',
  zonage_colorise:
    'Colorie d’un coup TOUTES les parcelles selon leur type de zone (urbaine, à urbaniser, agricole, naturelle) — sans avoir à cliquer parcelle par parcelle. Une lecture d’ensemble du potentiel de constructibilité.',
  parcelles:
    'Les parcelles cadastrales, colorées selon l’avis de LABUSE (les plus prometteuses ressortent). C’est la couche de travail principale.',
  ppr:
    'Les zones exposées à un risque naturel connu (inondation, mouvement de terrain, littoral…) inscrites dans un Plan de Prévention des Risques — utile pour écarter tôt un terrain contraint.',
  parc:
    'Le périmètre du Parc national de La Réunion : à l’intérieur, l’urbanisation est très restreinte voire interdite.',
  limites:
    'Le simple tracé du contour de toutes les parcelles, sans couleur — pour lire le découpage cadastral sur le fond de carte.',
  communes:
    'Les frontières officielles entre les communes (le trait vert) — pour se repérer et savoir de quelle mairie dépend un terrain.',
  anru:
    'Les quartiers inscrits dans un programme de renouvellement urbain (ANRU) : secteurs prioritaires où des opérations d’aménagement sont soutenues par l’État.',
  cinquante_pas:
    'La bande littorale des « 50 pas géométriques » (81,20 m depuis le rivage), un régime foncier propre à l’outre-mer où la constructibilité est très encadrée.',
  equipements:
    'Les équipements du quotidien à proximité (mairie, écoles, santé, commerces, transport, sport). Sur la fiche d’une parcelle, LABUSE indique la distance en mètres jusqu’à chaque équipement le plus proche.',
}

export const layerInfo = (key: string): string | undefined => LAYER_INFO[key]
