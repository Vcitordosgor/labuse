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
