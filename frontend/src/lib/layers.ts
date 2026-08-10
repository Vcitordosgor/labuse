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
  // M55-A item 6 : chaque « i » dit désormais CE QUE montre la couche, SA source, et SA
  // couverture (partielle → dite franchement). Les trois « i » du zonage PLU sont traités à part
  // (item 1, en attente d'arbitrage Vic sur le renommage) et restés en l'état pour l'instant.
  parcelles:
    'Les 431 663 parcelles cadastrales de l’île (source DGFiP), colorées selon l’avis de LABUSE : les plus prometteuses ressortent. C’est la couche de travail principale — présente sur les 24 communes.',
  ppr:
    'Les zones exposées à un risque naturel connu (inondation, mouvement de terrain, littoral…) inscrites dans un Plan de Prévention des Risques. Source : la DEAL (via Géorisques). Couverture : les 24 communes de l’île. Utile pour écarter tôt un terrain contraint.',
  parc:
    'Le périmètre du Parc national de La Réunion (source : l’établissement public du Parc) : à l’intérieur, l’urbanisation est très restreinte voire interdite. Il couvre surtout les Hauts et le centre de l’île — il est donc normalement absent du littoral urbanisé.',
  limites:
    'Le simple tracé du contour de toutes les parcelles cadastrales (source DGFiP), sans couleur — pour lire le découpage sur le fond de carte. Toute l’île.',
  communes:
    'Les frontières officielles entre les 24 communes (le trait vert, source IGN / geo.api.gouv) — pour se repérer et savoir de quelle mairie dépend un terrain.',
  anru:
    'Les quartiers inscrits dans un programme de renouvellement urbain (NPNRU, source ANRU) : secteurs prioritaires soutenus par l’État. Dispositif ciblé — présent sur 6 communes seulement (Le Port, Saint-André, Saint-Benoît, Saint-Denis, Saint-Louis, Saint-Pierre) ; ailleurs la couche est vide, et LABUSE vous le signale.',
  cinquante_pas:
    'La bande littorale des « 50 pas géométriques » (81,20 m depuis le rivage), un régime foncier propre à l’outre-mer où la constructibilité est très encadrée (source : cadastre). Elle ne longe que le rivage — normalement absente des communes sans littoral (les Hauts).',
  equipements:
    'Les équipements du quotidien à proximité, relevés dans OpenStreetMap (les 24 communes) : mairie, écoles (école, collège), santé (pharmacie, hôpital, clinique, médecin), commerces (supermarché, supérette, boulangerie, centre commercial — pas toutes les boutiques), transport (arrêts de bus), police / gendarmerie, sport (terrains, gymnases, stades, piscines). Sur la fiche d’une parcelle, LABUSE indique la distance jusqu’à chaque équipement le plus proche.',
  renouv:
    'Des parcelles déjà occupées (bâties) mais en zone constructible avec une vraie capacité restante : un potentiel de renouvellement urbain (densifier, diviser, reconstruire). Segment calculé par LABUSE (68 445 parcelles sur l’île) — pas une opportunité qualifiée, et rien ne dit qu’elles se vendront.',
}

export const layerInfo = (key: string): string | undefined => LAYER_INFO[key]
