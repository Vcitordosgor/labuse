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
  safer: 'Parcelle déclarée agricole (RPG)',
  sar: 'Potentiel foncier Région (indicatif)',
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
  trait_de_cote: 'Indicateur d\'érosion côtière (Cerema)',
  abf: 'ABF / Monuments',
  ens: 'Espace protégé réglementaire (INPN)',
  eau: 'Eau',
  bruit_route: 'Bruit routier',
  // marché
  dvf: 'Marché DVF',
  sitadel: 'Permis SITADEL',
  amenites: 'Commerces et services à proximité',
  potentiel_foncier_region: 'Potentiel foncier Région',
  ocs_ge: 'Occupation du sol (BD CARTO V5 — grain grossier)',
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
  // M55-A (fusion A) : DEUX couches de zonage seulement. La couche PARCELLAIRE (calibrée) fait tout —
  // colorer d'ensemble + code au zoom/clic ; la couche OFFICIELLE montre le document GPU brut.
  zonage:
    'Les zones du PLU telles que déposées par la commune sur le Géoportail de l’urbanisme (flux GPU) : les aplats bruts du document opposable, avec leurs contours d’origine. Non rattachés au cadastre : ils couvrent AUSSI l’espace non parcellaire (voirie, ravines, domaine public), d’où des couleurs là où la couche « par parcelle » n’en montre pas. Couverture : 23 des 24 communes — Saint-Philippe, au RNU, n’a pas de PLU numérisé.',
  zonage_parcelle:
    'La couche de zonage à utiliser au quotidien : chaque parcelle prend d’emblée la couleur de sa famille de zone (U urbaine, AU à urbaniser, A agricole, N naturelle), calée sur le cadastre par LABUSE — une lecture d’ensemble de la constructibilité, sans cliquer. En zoomant, ou en cliquant une parcelle, le code exact (U1a, 1AUc…) s’affiche. Comme elle colore la couche « Parcelles », celle-ci s’active automatiquement avec elle. Couverture : 99 % des parcelles ; absente là où la commune est au RNU (Saint-Philippe).',
  // M55-A item 6 : chaque « i » dit désormais CE QUE montre la couche, SA source, et SA
  // couverture (partielle → dite franchement).
  parcelles:
    'Les 431 663 parcelles cadastrales de l’île (source DGFiP) en APLAT COLORÉ PAR STATUT / TIER de LABUSE (Priorité → Écartée) : chaque parcelle est REMPLIE de la couleur de son avis, les plus prometteuses ressortent d’un coup d’œil. C’est ce qui la distingue de « Limites parcelles », qui n’affiche que le contour gris du découpage, sans couleur. C’est la couche de travail principale — présente sur les 24 communes.',
  ppr:
    'Les zones exposées à un risque naturel connu (inondation, mouvement de terrain, littoral…) inscrites dans un Plan de Prévention des Risques. Source : la DEAL (via Géorisques). Couverture : les 24 communes de l’île. Utile pour écarter tôt un terrain contraint.',
  // M106 P1 : les aléas DEAL séparés. La séparation inondation / mouvement de terrain n'existe
  // pas dans le zonage réglementaire PPR (un document multirisque ne dit pas quel aléa commande
  // chaque zone) — elle vit dans la cartographie d'aléas, qui la porte nativement.
  alea_inondation:
    'Les secteurs exposés à l’aléa inondation, avec leur niveau (faible, moyen, fort), d’après la cartographie des aléas de la DEAL Réunion. À distinguer du zonage PPR : ici c’est l’exposition au phénomène, pas la règle d’urbanisme. Couverture : les 24 communes.',
  alea_mvt:
    'Les secteurs exposés à l’aléa mouvement de terrain (glissements, chutes de blocs…), avec leur niveau (faible, moyen, fort), d’après la cartographie des aléas de la DEAL Réunion. À distinguer du zonage PPR : ici c’est l’exposition au phénomène, pas la règle d’urbanisme. Couverture : 23 communes (Saint-Denis non couverte par ce flux).',
  parc:
    'Le périmètre du Parc national de La Réunion (source : l’établissement public du Parc) : à l’intérieur, l’urbanisation est très restreinte voire interdite. Il couvre surtout les Hauts et le centre de l’île — il est donc normalement absent du littoral urbanisé.',
  limites:
    'Le simple tracé du contour de toutes les parcelles cadastrales (source DGFiP), sans couleur — pour lire le découpage sur le fond de carte. Toute l’île.',
  communes:
    'Les frontières officielles entre les 24 communes (le trait vert, source IGN / geo.api.gouv) — pour se repérer et savoir de quelle mairie dépend un terrain.',
  anru:
    'Les quartiers inscrits dans un programme national de renouvellement urbain (NPNRU, piloté par l’ANRU) : des secteurs soutenus par l’État pour rénover l’habitat et l’espace public. Ce que ça change pour un projet : maîtrise foncière publique active, opérations d’aménagement en cours, environnement immédiat en transformation. Dispositif ciblé — 8 emprises sur 6 communes (Le Port, Saint-André, Saint-Benoît, Saint-Denis, Saint-Louis, Saint-Pierre) ; ailleurs la couche est vide, et LABUSE vous le signale. Source : DEAL Réunion / ANCT.',
  // M134 — couche « Dispositifs et périmètres ». Chaque « i » : ce que c'est · ce que ça change
  // (le FAIT, jamais un conseil chiffré personnalisé) · la source et son millésime.
  qpv:
    'Les quartiers prioritaires de la politique de la ville (QPV) : les secteurs les plus fragiles, cibles des aides publiques à l’aménagement et à la rénovation. Ce que ça change pour un projet : un logement neuf destiné à l’accession y ouvre la TVA réduite (accession sociale, sous conditions de ressources de l’acquéreur), et le quartier concentre les crédits d’aménagement. Source : ANCT — quartiers de génération 2024, 57 quartiers sur 13 communes.',
  tva_primo:
    'La bande des 500 mètres autour des quartiers prioritaires : le périmètre où la TVA réduite pour l’accession sociale s’étend AU-DELÀ du quartier lui-même. PÉRIMÈTRE DÉRIVÉ, calculé par LABUSE à partir des QPV (Estimé) — ce n’est pas une source officielle : la limite exacte se vérifie au cas par cas. Le quartier lui-même est la couche « QPV — quartier prioritaire ».',
  zfang:
    'La zone franche d’activité nouvelle génération (ZFANG) : un régime fiscal de plein droit dans les DOM qui allège l’imposition des entreprises implantées dans la commune. Maille COMMUNE ENTIÈRE (pas un périmètre fin). Régime standard : abattements d’environ 50 %. Régime RENFORCÉ (6 communes de l’Est, HACHURÉE sur la carte) : abattements majorés — 80 % sur les bénéfices et la taxe foncière bâtie, 100 % sur la CFE, jusqu’en 2030. Taux légaux du dispositif (art. 44 quaterdecies CGI · décret n° 2026-421 du 29 mai 2026), pas un calcul de votre avantage.',
  frr:
    'France Ruralités Revitalisation (FRR, ex-ZRR) : un régime d’exonérations fiscales et sociales pour soutenir les communes rurales. Maille COMMUNE ENTIÈRE. Une commune est classée en TOTALITÉ (aplat plein) ou EN PARTIE seulement (HACHURÉE sur la carte) — la zone spéciale d’action rurale des Hauts est infra-communale, la situation dépend alors de la localisation exacte du terrain. Source : art. 44 quindecies A CGI · zone spéciale d’action rurale (décret n° 78-690), FRR depuis le 1er juillet 2024.',
  cinquante_pas:
    'La bande littorale des « 50 pas géométriques » (81,20 m depuis le rivage), un régime foncier propre à l’outre-mer où la constructibilité est très encadrée (source : cadastre). Elle ne longe que le rivage — normalement absente des communes sans littoral (les Hauts).',
  // SECTEUR-2 (T4) — prix du logement neuf (VEFA acté DVF), aplat commune.
  vefa_neuf:
    'Le prix du logement NEUF, à la maille COMMUNE : la médiane du prix au m² bâti des ventes « en l’état futur d’achèvement » (VEFA) réellement actées, source geo-DVF (DGFiP), sur une fenêtre de 36 mois glissants. La commune est peinte (rampe jaune → magenta) si au moins 10 ventes VEFA soutiennent la médiane ; sous ce seuil elle est HACHURÉE en gris (« moins de 10 ventes »), jamais vide. Un clic sur une commune ouvre son détail : médiane et n, tendance sur 12 mois, répartition appartements/maisons, et l’offre engagée Sitadel (logements collectifs autorisés sur 24 mois — ce qui arrive en face). La médiane par taille (T2/T3/T4) n’est pas servie : DVF au 974 ne porte pas le nombre de pièces. Le STOCK du neuf relève de l’enquête ECLN (SDES), métropole seulement — hors champ La Réunion. Rien n’est extrapolé.',
  equipements:
    'Les équipements du quotidien à proximité, relevés dans OpenStreetMap (les 24 communes) : mairie, écoles primaires, collège / lycée, crèche, santé (pharmacie, hôpital, clinique, médecin), commerces — c’est-à-dire supermarché, supérette, boulangerie et centre commercial (pas toutes les boutiques) — marché forain, police / gendarmerie et sport (stades, gymnases, piscines, complexes sportifs — les terrains isolés ne sont plus affichés). Les arrêts de bus sont désormais servis par la couche dédiée « Transport public » (GTFS). Couverture OSM PARTIELLE pour crèche, marché, santé et services (mairie, police) — l’absence n’est pas une preuve ; la couche « Équipements (INSEE BPE) » est plus complète sur ces familles. Ce sont ces points OSM qui nourrissent le MODÈLE LABUSE (amenités du scoring) ; les distances « À proximité » de la fiche d’une parcelle viennent, elles, de l’INSEE BPE (l’autre couche) — chaque lecture dit sa source.',
  // M137-U — 2e source d'équipements, SÉPARÉE d'OSM (jamais fusionnée → l'utilisateur voit la provenance).
  equipements_bpe:
    'Les équipements et services recensés par l’INSEE (Base Permanente des Équipements, BPE) : commerces, santé, enseignement, services aux particuliers, sport et loisirs, transports, tourisme. Source statistique officielle, distincte d’OpenStreetMap (l’autre couche « Équipements ») — LABUSE ne fusionne pas les deux, vous voyez d’où vient chaque point. C’est la BPE qui nourrit la ligne « À proximité » de la fiche d’une parcelle (école, commerces, santé, arrêt — distances à vol d’oiseau) ; le modèle LABUSE, lui, s’appuie sur OpenStreetMap. Source : INSEE, BPE millésime 2025, 35 546 équipements géolocalisés sur les 24 communes.',
  // M137-U — ZNIEFF : contrainte, avec la distinction type I / type II (ils ne pèsent pas pareil).
  znieff:
    'L’inventaire des Zones Naturelles d’Intérêt Écologique, Faunistique et Floristique (ZNIEFF) — le porter à connaissance du patrimoine naturel. Type I : un secteur de fort intérêt biologique, plus restreint et plus sensible ; type II : un grand ensemble naturel riche et peu modifié (les deux ne pèsent pas pareil en instruction). Ce que ça change pour un projet : ce n’est PAS une interdiction de construire, mais un signal fort — l’étude d’impact y est renforcée et le risque de recours contentieux plus élevé. Source : INPN / MNHN (PatriNat), inventaire continental type I et II, mise à jour 2025. Les ZNIEFF marines (en mer) ne sont pas affichées.',
  // M106 P4 : transport public et lignes HT (arbitrage Vic).
  transport:
    'Les lignes ET les arrêts du transport public — les 7 réseaux de l’île (Car Jaune, Citalis, Kar’Ouest, Alternéo, Carsud, Estival — source : GTFS officiels, Licence Ouverte) et le téléphérique Papang (tracé OpenStreetMap). Les 9 956 arrêts apparaissent à partir du zoom quartier et sont CLIQUABLES : nom de l’arrêt, lignes qui le desservent, réseau. La ligne 2 « Zèl La Montagne » (2029) n’a pas de tracé publié : non affichée. Les pôles d’échange (gares routières, nœuds du réseau) restent portés par la couche « Axes structurants ».',
  axes:
    'Les axes routiers structurants de l’île — route des Tamarins, routes nationales et grandes liaisons — d’après la hiérarchie officielle de la BD TOPO IGN (niveaux d’importance 1 et 2). À double face pour un projet : accessibilité d’un côté, nuisances potentielles de l’autre (bruit, pollution, recul le long des axes classés). Sur la fiche d’une parcelle, LABUSE indique la distance à l’axe le plus proche, avec son nom. Cette couche porte aussi les pôles d’échange (les nœuds du réseau) : gares routières relevées dans OpenStreetMap et arrêts desservis par de nombreuses lignes (le critère est affiché dans la légende).',
  lignes_ht:
    'Les lignes électriques de l’île, DEUX réseaux sous une couche : la MOYENNE TENSION (HTA ~15-20 kV, la distribution — trait fin ; source : EDF Réunion open data, Licence Ouverte 2.0, géométrie ~02/2020 republiée le 16/10/2025, tracé indicatif réduit pour sécurité publique) et la HAUTE TENSION (HTB 63/90 kV, le transport — trait épais tireté ; source : BD TOPO IGN, aérien seul, tension indiquée). C’est une CONTRAINTE potentielle (servitudes, reculs) et un repère de raccordement — jamais un substitut à une DT-DICT ni à l’avis du gestionnaire (EDF SEI). Les positions des postes sources ne sont plus publiées (jeu vidé par EDF le 24/12/2025).',
  tcsp:
    'Sur une parcelle située à moins de 800 m d’une station de transport en commun en site propre, le PLU ne peut pas exiger plus d’une place de stationnement par logement (0,5 pour le logement social), si la desserte est de qualité. Moins de parking à construire = plus de surface vendable et un bilan plus léger. La carte montre la ZONE (rayon de 800 m à vol d’oiseau autour de chaque station en service — une pastille de 1,6 km de large), les parcelles couvertes en teinte, les stations et les voies en site propre (relevées dans OpenStreetMap). Un simple couloir bus ne compte pas (pas un site propre au sens du texte). Source : code de l’urbanisme, art. L151-34 à 36 (loi 2025-1129).',
  renouv:
    'Des parcelles déjà occupées (bâties) mais en zone constructible avec une vraie capacité résiduelle : le bâti qui peut porter davantage (extensions, surélévations, division). Segment « Densifier l’existant » calculé par LABUSE — pas une opportunité qualifiée, et rien ne dit qu’elles se vendront.',
  // M55-G point 8 / suite point 1 : l'avis LABUSE (palette des tiers) en COUCHE explicite —
  // elle peint TOUT le classement de l'île, sans tenir compte des filtres actifs (le libellé
  // le dit). En mode analyse (couche décochée), la palette suit le résultat courant.
  couleurs_verdict:
    'Les couleurs du classement LABUSE (Priorité → Écartée) sur TOUTES les parcelles de l’île, indépendamment des filtres actifs. En mode analyse, la carte ne colore que le résultat courant — cochez cette couche pour voir le classement entier.',
}

export const layerInfo = (key: string): string | undefined => LAYER_INFO[key]
