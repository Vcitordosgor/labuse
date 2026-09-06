# FICHE PARCELLE — donnée par donnée

*Généré du registre le 2026-09-06 par `labuse registre fiche parcelle` (le code est la vérité — ne pas éditer à la main ; relu avant commit).*

Chaque section est un tiroir de la fiche. Pour chaque donnée : d'où elle vient (source et millésime servis), par quel chemin (moteur nommé ou passe-plat), sa portée (`run` = change à la bascule · `live` = à l'injection · `projet` = saisie du client), ses états possibles, et où ailleurs elle s'affiche.

## En-tête (adresse, géométrie)

*Robinet `fiche_parcelle_entete` — route `/parcels/{idu}`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `adresse_ban` | texte | Adresse | ban | passe-plat · src/labuse/api/app.py:_ban_adresse — table lue : adresses (id_ban) ⋈ adresse_parcelles | live | servie · non déterminée · non calculée | nulle part ailleurs |
| | | *meilleure adresse BAN rattachée à la parcelle — None si aucune (le front dit « Adresse non disponible », jamais un champ vide)* | | | | | |
| `parcelle_geometrie` | geometrie | Géométrie de la parcelle | cadastre_api_carto (PCI Parcellaire Express (DGFiP) — « latest » ingérée) | passe-plat · src/labuse/api/app.py (parcels.geom / geom_2975) — table lue : parcels.geom (geom_simple pour les tuiles) | live | servie · non calculée | nulle part ailleurs |
| | | *le polygone cadastral de la parcelle (contour carte, fiche, PDF) — même table cadastre, même millésime partout (sonde lot 4.5)* | | | | | |

## Règlement d'urbanisme (zones + extraits)

*Robinet `fiche_parcelle_urbanisme` — route `/parcels/{idu}`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `reglement_plu_bloc` | liste | Règlement de la zone (extraits) | gpu_plu_api_carto (GPU/PLU par commune (révisions — détail en fiche)), sudocuh (Sudocuh — état au 31/12/2024 (Licence Ouverte 2.0)) | moteur `plu_destinations` · src/labuse/api/app.py:_reglement_plu_block — table lue : parcel_zone_plu + corpus règlements | live | servie (possiblement vide, dit) · non calculée | nulle part ailleurs |
| | | *zones PLU de la parcelle + extraits de règlement calibrés (corpus) — chaque extrait cite son document* | | | | | |
| `zone_plu_famille` | classe — domaine : U, AU, A, N | Zonage PLU (par type) | gpu_plu_api_carto (GPU/PLU par commune (révisions — détail en fiche)) | moteur `zone_servie` · src/labuse/faisabilite/zone_servie.py:zone_dominante | live | servie · non déterminée (la source ne dit pas) · non calculée | couche « Zonage PLU (par type) » · PDF « Pré-dossier PC (ZIP CERFA 13406*17) » · PDF « Lettre de zonage » |
| | | *famille (U/AU/A/N) de la zone DOMINANTE par surface de la parcelle (drapeau a_cheval, zone_parts servies) — moteur zone_servie (ZONE-1) ; ≠ zonage_commune (parts d'une commune)* | | | | | |

## Dispositifs et périmètres (QPV, ANRU, ZFANG, FRR)

*Robinet `fiche_parcelle_dispositifs` — route `/parcels/{idu}`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `perimetres_dispositifs_liste` | liste | Périmètres et dispositifs (parcelle) | qpv_2024 (génération 2024), npnru, zfang (Décret n° 2026-421 du 29 mai 2026 (LF 2026, art. 18)), frr_ex_zrr (ZSAR 1978 · FRR 01/07/2024 · réf. ZRR 2017 (Région)) | passe-plat · src/labuse/api/app.py:_territoire_fiscal_block — table lue : spatial_layers (qpv/anru/zfang/frr ; tva_primo dérivé) | live | servie (possiblement vide, dit) · non calculée | nulle part ailleurs |
| | | *périmètres touchant LA parcelle : QPV, NPNRU/ANRU, bande TVA primo (dérivée), ZFANG/FRR (commune) — en français, sourcés, jamais un sigle nu* | | | | | |

## Score d'opportunité (tier)

*Robinet `fiche_parcelle_score` — route `/parcels/{idu}`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `tier_opportunite` | classe — domaine : brulante, chaude, a_creuser, reserve_fonciere, ecartee | Verdict · Classement servi | bd_topo (BD TOPO® V3 (IGN) — édition non enregistrée), cosia (CoSIA 2025 (PVA juil.-août 2025, 20 cm)), dvf (géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020), filosofi_carreaux (millésime 2021), sitadel (2026-07) | moteur `scoring_p_v2` · src/labuse/cli.py (build-mvt) ; parcel_flags | run | servie · non déterminée (la source ne dit pas) · non calculée | couche « Verdict · Classement servi » · outil « Étudier un bien » · PDF « Rapport Flash » · PDF « Dossier parcelle » |
| | | *tier du run servi (brûlante→froide), reconstruit à la bascule* | | | | | |
| `rang_tier` | nombre | Rang (dans le tier) | interne (aucun réservoir) | moteur `scoring_p_v2` · src/labuse/api/app.py:3283 | run | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *rang au sein du tier* | | | | | |

## Constructibilité

*Robinet `fiche_parcelle_constructibilite` — route `/parcels/{idu}`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `capacite_logements` | nombre | Capacité (logements) | bd_topo (BD TOPO® V3 (IGN) — édition non enregistrée), cosia (CoSIA 2025 (PVA juil.-août 2025, 20 cm)), gpu_plu_api_carto (GPU/PLU par commune (révisions — détail en fiche)) | moteur `potentiel` · src/labuse/faisabilite/potentiel.py:bloc_potentiel (table_rase.logements) | run | servie · non couverte (n sous seuil, dit) · non calculée | outil « Faisabilité » |
| | | *logements estimés du scénario table rase (après plafond de densité et stationnement) — bloc potentiel (EXPORTS-1 lot 3)* | | | | | |
| `sdp_residuelle_m2` | nombre | SDP résiduelle | cosia (CoSIA 2025 (PVA juil.-août 2025, 20 cm)), gpu_plu_api_carto (GPU/PLU par commune (révisions — détail en fiche)) | moteur `potentiel` · src/labuse/faisabilite/potentiel.py:bloc_potentiel (au_sol.sdp_residuelle_m2) | run | servie · non couverte (n sous seuil, dit) · non calculée | outil « Faisabilité » · outil « Densifier l'existant » · PDF « Dossier parcelle » |
| | | *max(0, SDP_max − SDP_existante) du run servi, sous garde de lecture zone dominante (A/N → 0 avec cause dite — ZONE-1)* | | | | | |
| `charge_fonciere_eur` | nombre | Charge foncière | cadastre_api_carto (PCI Parcellaire Express (DGFiP) — « latest » ingérée), dvf (géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020) | moteur `bilan_promoteur` · src/labuse/faisabilite/bilan.py | live | servie · non couverte (n sous seuil, dit) · non calculée | outil « Faisabilité » · PDF « Dossier banquier » |
| | | *prix de sortie × SDP − coûts − marge (bilan à rebours)* | | | | | |
| `potentiel_verdict` | texte | Potentiel (verdict) | bd_topo (BD TOPO® V3 (IGN) — édition non enregistrée), cosia (CoSIA 2025 (PVA juil.-août 2025, 20 cm)), gpu_plu_api_carto (GPU/PLU par commune (révisions — détail en fiche)) | moteur `potentiel` · src/labuse/faisabilite/potentiel.py:bloc_potentiel (verdict) | run | servie · non déterminée · non calculée | PDF « Dossier parcelle » |
| | | *phrase composée du bloc « au sol / en hauteur / table rase » (moteur potentiel) — jamais un bloc creux (section omise si rien d'évaluable)* | | | | | |
| `prix_neuf_observe_eur_m2` | nombre | Prix du neuf — observé (€/m²) | dvf (géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020) | moteur `marche_service` · src/labuse/ingestion/dvf_prix_neuf.py:resolve_prix_neuf_marche (servi par faisabilite/bilan.py:resolve_prix_sortie_servi) | live | servie · non couverte (n sous seuil, dit) · non calculée | PDF « Dossier banquier » |
| | | *neuf observé ≤ 3 ans après achèvement (resolve_prix_neuf_marche : bassin sourcé > secteur > commune > repli île) — USAGE RÉSERVÉ : bilan et exports (fiche, PDF) lisent CET id (arbitrage Q3 ; scission 0-bis)* | | | | | |
| `mixite_clause` | texte | Mixité sociale (clause) | gpu_plu_api_carto (GPU/PLU par commune (révisions — détail en fiche)) | moteur `bilan_promoteur` · src/labuse/faisabilite/bilan.py:_clause_mixite | live | servie · non déterminée · non calculée | PDF « Dossier banquier » |
| | | *déclenchement de la clause de mixité Art. 2 : SDP ≥ seuil OU logements ≥ seuil OU terrain > seuil (seuils des hypothèses de bilan, source déclarée sinon « Estimé ») — bloc unique servitude + déclenchement (EXPORTS-1 5.1)* | | | | | |
| `surface_vendable_m2` | nombre | Surface vendable (Estimé) | bd_topo (BD TOPO® V3 (IGN) — édition non enregistrée), cosia (CoSIA 2025 (PVA juil.-août 2025, 20 cm)), gpu_plu_api_carto (GPU/PLU par commune (révisions — détail en fiche)) | moteur `potentiel` · src/labuse/faisabilite/potentiel.py:bloc_potentiel (table_rase.vendable_m2) | run | servie · non couverte (n sous seuil, dit) · non calculée | PDF « Dossier parcelle » |
| | | *SHAB vendable du scénario table rase (fourchette du moteur commun) — distincte de capacite_logements* | | | | | |
| `surface_plancher_m2` | nombre | Surface de plancher (Estimé) | bd_topo (BD TOPO® V3 (IGN) — édition non enregistrée), cosia (CoSIA 2025 (PVA juil.-août 2025, 20 cm)), gpu_plu_api_carto (GPU/PLU par commune (révisions — détail en fiche)) | moteur `potentiel` · src/labuse/faisabilite/potentiel.py:bloc_potentiel (table_rase.plancher_m2) | run | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *surface de plancher du scénario table rase (moteur commun) — distincte de capacite_logements* | | | | | |
| `marge_surelevation_m` | nombre | Marge de surélévation (à l'égout) | bd_topo (BD TOPO® V3 (IGN) — édition non enregistrée), gpu_plu_api_carto (GPU/PLU par commune (révisions — détail en fiche)) | moteur `potentiel` · src/labuse/faisabilite/potentiel.py:surelevation | run | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *hauteur restante sous la règle de hauteur à l'égout de la zone (moteur commun, EXPORTS-1 3.2)* | | | | | |
| `taxe_amenagement_estimee_eur` | nombre | Taxe d'aménagement estimée (table rase) | interne (aucun réservoir) | moteur `taxe_amenagement` · src/labuse/api/app.py:_taxe_amenagement_block (taxe_amenagement.calculer) | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *estimation de la taxe pour le scénario table rase du potentiel (assiette = surface de plancher créée) ; taux communal PUBLIC si connu, sinon « non renseigné » (jamais inventé) ; taux départemental plafond 2,5 % à confirmer* | | | | | |

## Le bien

*Robinet `fiche_parcelle_le_bien` — route `/parcels/{idu}`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `emprise_batie_m2` | nombre | Emprise bâtie | bd_topo (BD TOPO® V3 (IGN) — édition non enregistrée), cosia (CoSIA 2025 (PVA juil.-août 2025, 20 cm)) | moteur `bati_revele` · src/labuse/bati.py:le_bien_block (BD TOPO au sol ; CoSIA parcel_bati_revele en note) | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *emprise au sol du bâti — empreinte vecteur BD TOPO (somme des intersections), cohérente avec le nombre de bâtiments ; CoSIA servi À PART quand il détecte du bâti hors BD TOPO* | | | | | |
| `hauteur_bati_m` | nombre | Hauteur du bâti | bd_topo (BD TOPO® V3 (IGN) — édition non enregistrée) | moteur `potentiel` · src/labuse/faisabilite/potentiel.py:_hauteur_bati_m | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *hauteur du bâti principal (BD TOPO, max des bâtiments intersectants)* | | | | | |
| `n_batiments` | nombre | Nombre de bâtiments | bd_topo (BD TOPO® V3 (IGN) — édition non enregistrée) | moteur `bati_revele` · src/labuse/bati.py:le_bien_block (bati.fiche_block — BD TOPO) | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *compte des bâtiments de la parcelle (BD TOPO, intersection ≥ 10 m²)* | | | | | |
| `surface_libre_sol_m2` | nombre | Surface au sol libre | bd_topo (BD TOPO® V3 (IGN) — édition non enregistrée), cosia (CoSIA 2025 (PVA juil.-août 2025, 20 cm)), cadastre_api_carto (PCI Parcellaire Express (DGFiP) — « latest » ingérée) | moteur `bati_revele` · src/labuse/bati.py:le_bien_block (surface parcelle − emprise bâtie) | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *surface au sol non bâtie restante (surface parcelle − emprise bâtie), plancher à 0* | | | | | |
| `nature_toit` | classe — domaine : plat, monopente, double_pente, croupe_complexe | Nature du toit | lidar_hd_mnh (LiDAR HD MNH — dalles publiées 25/06/2025 (IGN)), bd_topo (BD TOPO® V3 (IGN) — édition non enregistrée) | moteur `solaire` · src/labuse/solaire_toiture.py:analyse_toiture (cache toiture_lidar, lecture fiche) | live | servie · non déterminée (la source ne dit pas) · non calculée | nulle part ailleurs |
| | | *forme du toit du plus grand bâtiment lue sur le LiDAR HD (MNH), servie ≥ 0,70 de confiance sinon « non déterminée — pans non nets » (RETOURS-15 U5)* | | | | | |
| `pente_toit_deg` | nombre | Pente du toit | lidar_hd_mnh (LiDAR HD MNH — dalles publiées 25/06/2025 (IGN)) | moteur `solaire` · src/labuse/solaire_toiture.py:analyse_toiture (cache toiture_lidar, lecture fiche) | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *pente médiane du toit du plus grand bâtiment (degrés), mesure directe LiDAR HD (MNH) — servie même sous le seuil de forme* | | | | | |
| `dpe_connu` | texte | DPE connu (étiquette, année) | dpe_ademe | passe-plat · src/labuse/api/app.py:_dpe_connu_block — table lue : dpe_records | live | servie · non déterminée · non calculée | nulle part ailleurs |
| | | *dernier DPE connu du bâtiment rattaché (étiquette énergie/GES, date, type de bâtiment) + nombre de DPE — info fiche SEULE, jamais un signal scoring (M71 B1 : DPE neuf en DROM)* | | | | | |

## Risques et protections

*Robinet `fiche_parcelle_risques` — route `/parcels/{idu}`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `n_vigilances` | nombre | Vigilances | abf_merimee, deal_ppr (PPR/PPRL approuvés 2011–2026 (arrêtés, DEAL Lizmap)), georisques_api, znieff_inpn (INPN, mise à jour 29/08/2025) | moteur `cascade` · src/labuse/api/anti_fiche.py (motifs RÉDHIBITOIRE/VIGILANCE de la cascade) | run | servie · non couverte (n sous seuil, dit) · non calculée | outil « Pièges et risques » |
| | | *compte des couches cascade en SOFT_FLAG/HARD_EXCLUDE* | | | | | |
| `aleas_parcelle_liste` | liste | Aléas de la parcelle | deal_ppr (PPR/PPRL approuvés 2011–2026 (arrêtés, DEAL Lizmap)), georisques_api | moteur `cascade` · src/labuse/api/app.py:_aleas_block (lignes servies layer='risques') | run | servie (possiblement vide, dit) · non calculée | nulle part ailleurs |
| | | *liste des aléas touchant la parcelle (nature, niveau, part concernée, référence de l'arrêté PPR pour un aléa réglementaire) — dérivée de la cascade servie, accord garanti avec Pièges et risques* | | | | | |

## Marché et secteur

*Robinet `fiche_parcelle_marche` — route `/parcels/{idu}`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `prix_terrain_secteur_eur_m2` | nombre | Terrain nu secteur | cadastre_api_carto (PCI Parcellaire Express (DGFiP) — « latest » ingérée), dvf (géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020) | moteur `sector_price` · src/labuse/faisabilite/bilan.py (sector_price) | live | servie · non couverte (n sous seuil, dit) · non calculée | PDF « Rapport Flash » · PDF « Dossier banquier » · PDF « Argumentaire » |
| | | *médiane DVF rayon adaptatif 500→1500 m, trim 5 %, min 8 ventes, indice fiabilité* | | | | | |
| `prix_sortie_bati_eur_m2` | nombre | Prix de sortie — bâti secteur | dvf (géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020) | moteur `sector_price` · src/labuse/api/app.py:_q_v2_fiche (sector_price via marche_service, phrase_prix_ancien) | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *sector_price PARCELLE (n, rayon effectif, période) servi AU SERVEUR par _q_v2_fiche — même phrase écran et PDF (EXPORTS-1 1.3, plus de calcul front)* | | | | | |
| `ventes_100m_n` | nombre | Ventes à moins de 100 m (36 mois) | dvf (géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020) | moteur `marche_service` · src/labuse/api/site_voisinage.py:voisinage_proche (profil voisinage_100m) | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *count mutations DVF à <100 m sur 36 mois (profil voisinage_100m, config/dvf_profils.yaml) + médiane* | | | | | |
| `ventes_retenues_n` | nombre | Ventes retenues (nuage) | dvf (géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020) | moteur `marche_service` · src/labuse/marche_service.py:filtre_ventes | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *ventes DVF retenues par le filtre de comparables (couverture VISIBLE — EXPORTS-1 lot 2)* | | | | | |
| `ventes_ecartees_n` | nombre | Ventes écartées (nuage) | dvf (géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020) | moteur `marche_service` · src/labuse/marche_service.py:filtre_ventes | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *ventes DVF écartées par le filtre de comparables, avec motif (couverture visible)* | | | | | |
| `dvf_parcelle_liste` | liste | Mutations de la parcelle (DVF) | dvf (géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020) | moteur `marche_service` · src/labuse/api/app.py:_q_v2_fiche (dvf_parcelle) — table lue : v_parcel_dvf_last + dvf_secteur_medianes | live | servie (possiblement vide, dit) · non calculée | nulle part ailleurs |
| | | *dernière mutation de la parcelle + médianes du secteur cadastral (indicateur secondaire, étiqueté — EXPORTS-1 1.3)* | | | | | |
| `parc_social_rpls_logements` | nombre | Parc social (logements RPLS) | rpls_sdes | passe-plat · src/labuse/api/app.py (marche_secteur — rpls_commune) — table lue : rpls_commune (nb_logements, construct_median) | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *nombre de logements locatifs sociaux de la commune (RPLS SDES, millésime 01/01/2025) — contexte marché de la fiche commune, du Flash et du PDF, jamais un signal scoring* | | | | | |

## Réseaux et accès

*Robinet `fiche_parcelle_reseaux` — route `/parcels/{idu}`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `pente_deg` | nombre | Pente | rge_alti (RGE ALTI® (IGN) — édition non enregistrée) | passe-plat · src/labuse/api/app.py:3283 (viabilisation) — table lue : parcel_terrain.pente_moy_deg | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *pente moyenne parcelle (RGE ALTI), flag terrassement* | | | | | |
| `piscine_m2` | nombre | Piscine ~m² | bd_ortho (BD ORTHO IGN 974 — millésime 2025 (piscine, 90,7 %)) | passe-plat · src/labuse/api/app.py:3283 — table lue : parcel_equipements.piscine_surface_m2 | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *surface détectée parcel_equipements (BD ORTHO 2025)* | | | | | |
| `distance_arret_m` | nombre | Transport public — au plus proche | gtfs_pan (7 jeux PAN, màj 2025-12-29 → 2026-08-17), osm_transport (extraction Overpass (base OSM vivante, ODbL)) | moteur `parcelle_proximites` · src/labuse/registre/moteurs/parcelle.py:plus_proche | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *plus proche arrêt/pôle (distance en m)* | | | | | |
| `tcsp_stationnement_allege` | classe — domaine : sous_800m, au_dela, aucune_station | Stationnement allégé (TCSP, L151-36) | gtfs_pan (7 jeux PAN, màj 2025-12-29 → 2026-08-17), osm_transport (extraction Overpass (base OSM vivante, ODbL)) | moteur `parcelle_proximites` · src/labuse/api/app.py:_proximites_block (drapeau sous_800m, L151-36 strict) | live | servie · non déterminée (la source ne dit pas) · non calculée | nulle part ailleurs |
| | | *la parcelle est-elle à MOINS de 800 m (à vol d'oiseau) d'une station de transport en site propre — plafond d'une aire de stationnement par logement (0,5 pour le logement social), opposable au PLU (art. L151-34 à 36) ; distance et station nommées* | | | | | |
| `part_logements_egout_pct` | nombre | Logements raccordés à l'égout | insee_rp2022_egoul (RP2022 — fichier détail Logements, publié le 16/10/2025 (INSEE)), office_eau_chroniques (Chronique n°149 — données 2023) | moteur `anc` · src/labuse/anc_service.py:statut_anc (producteur nommé, délégation) | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *part des logements raccordés au tout-à-l'égout (INSEE RP2022 EGOUL, maille IRIS, repli commune) — le TAUX, jamais un verdict* | | | | | |
| `viabilisation_verdict` | texte | Viabilisation (faisceau) | bd_topo (BD TOPO® V3 (IGN) — édition non enregistrée), rge_alti (RGE ALTI® (IGN) — édition non enregistrée), parkings_osm_aper | passe-plat · src/labuse/api/app.py:_viabilisation_block — table lue : parcel_viabilisation (faisceau) | live | servie · non déterminée · non calculée | nulle part ailleurs |
| | | *indicateur de viabilisation par faisceau de preuves (accès, réseaux) + gestionnaires — jamais un booléen inventé* | | | | | |

## Autour de cette parcelle

*Robinet `fiche_parcelle_autour` — route `/parcels/{idu} + /parcels/{idu}/zone`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `population_zone` | nombre | Habitants (zone) | filosofi_carreaux (millésime 2021) | moteur `zone` · src/labuse/zone.py (population_zone — point Filosofi UNIQUE) | live | servie · non couverte (n sous seuil, dit) · non calculée | outil « Étude de zone » · PDF « Rapport Flash » |
| | | *somme carreaux Filosofi 200 m intersectant l'isochrone* | | | | | |
| `n_permis_proximite` | nombre | Permis à 500 m sur 24 mois | sitadel (2026-07) | moteur `marche_service` · src/labuse/marche_service.py:permits (profil flash_500m → nearby_permits) | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *permis Sitadel dans le rayon 500 m, fenêtre 24 mois — LE profil client (arbitrage Q7), paramètres TRANSMIS au moteur (EXPORTS-1 4.1, plus jamais les défauts 300 m · 5 ans)* | | | | | |
| `depots_secteur_n` | nombre | Déposés sur le secteur (36 mois) | sitadel (2026-07) | moteur `marche_service` · src/labuse/ingestion/permits.py:depots_recents (via marche_service, profil fiche_36m) | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *dépôts Sitadel de la section cadastrale (préfixe IDU 10), fenêtre 36 mois (DEPOTS_FENETRE_MOIS, profil fiche_36m)* | | | | | |
| `historique_permis_liste` | liste | Sur cette parcelle (permis) | sitadel (2026-07), cadastre_epoque | moteur `marche_service` · src/labuse/api/app.py:_historique_site — table lue : sitadel_permits | live | servie (possiblement vide, dit) · non calculée | nulle part ailleurs |
| | | *permis déposés/autorisés sur la parcelle (Sitadel) + caducité — chaque ligne datée* | | | | | |
| `voisinage_100m_liste` | liste | Autour, à moins de 100 m | dvf (géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020), sitadel (2026-07) | moteur `marche_service` · src/labuse/api/site_voisinage.py:voisinage_proche — table lue : dvf_mutations_parcelle + sitadel_permits (buffer 100 m) | live | servie (possiblement vide, dit) · non calculée | nulle part ailleurs |
| | | *ventes DVF + permis récents (36 mois) dans le buffer 100 m, site exclu (doctrine M38)* | | | | | |
| `equipements_proximite_liste` | liste | À proximité (équipements) | bpe_insee (millésime 2025 (géographie au 01/01/2025)), osm_overpass | passe-plat · src/labuse/api/app.py:_proximites_equipements_block — table lue : parcel_amenites + spatial_layers (amenite/amenite_bpe) | live | servie (possiblement vide, dit) · non calculée | nulle part ailleurs |
| | | *équipements du quotidien nommés + distance (moteur BPE, couverture partielle DITE)* | | | | | |

## Propriétaire

*Robinet `fiche_parcelle_proprietaire` — route `/parcels/{idu}`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `type_proprietaire` | classe — domaine : personne morale, personne physique non recensée | Propriétaire (type) | dgfip_parcelles_pm (Panel millésimes 2019→2025 (situation 1ᵉʳ janvier)) | passe-plat · src/labuse/api/app.py:3586 (proprietaire_moral, parcelle_personne_morale) ; garde de lecture cascade/context.py (EXPORTS-1 5.4) — table lue : parcelle_personne_morale.denomination (millésime 2025) | live | servie · non déterminée (la source ne dit pas) · non calculée | nulle part ailleurs |
| | | *personne morale (dénomination) / personne physique non recensée — fichier PM parcelle_personne_morale, millésime 2025 (même assiette que la carte — EXPORTS-1 5.4 : la ligne « non renseigné » stockée au run est rebranchée sur le fichier PM à la lecture)* | | | | | |
| `proprietaire_timeline_liste` | liste | Historique propriétaire (millésimes PM) | dgfip_parcelles_pm (Panel millésimes 2019→2025 (situation 1ᵉʳ janvier)) | moteur `proprietaire_historique` · src/labuse/proprietaire_historique.py:historique — table lue : pm_proprietaires_millesimes ∪ parcelle_personne_morale | live | servie (possiblement vide, dit) · non calculée | nulle part ailleurs |
| | | *timeline unifiée versionné∪servi du fichier PM (2019→2025), diff CONSTAT — servi jamais écrasé* | | | | | |
| `evenements_proprietaire_liste` | liste | Événements propriétaire (BODACC) | bodacc, sirene_etablissements (SIRENE géolocalisé — publication mensuelle INSEE), recherche_entreprises_dinum | moteur `v_score` · src/labuse/api/app.py:_q_v2_fiche (score_v, evenement) — table lue : parcel_v_score + bodacc_* | live | servie (possiblement vide, dit) · non calculée | nulle part ailleurs |
| | | *événements datés du score V (procédures, radiations) — faits publics, chacun sourcé* | | | | | |

## Confiance données

*Robinet `fiche_parcelle_confiance` — route `/parcels/{idu}`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `verdict_icd` | texte | Confiance données | interne (aucun réservoir) | moteur `cascade` · src/labuse/api/app.py:3283 (bloc icd) | run | servie · non déterminée · non calculée | nulle part ailleurs |
| | | *verdict de complétude des couches + liste des manquants* | | | | | |

## Solaire (rosace, productible)

*Robinet `fiche_parcelle_solaire` — route `/parcels/{idu}`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `prod_spec_kwh_kwc` | nombre | Productible | bd_topo (BD TOPO® V3 (IGN) — édition non enregistrée), pvgis (PVGIS v5.3 · modèle SARAH3 (relevé au run du builder solaire)), lidar_hd_mnh (LiDAR HD MNH — dalles publiées 25/06/2025 (IGN)), bd_ortho_irc | moteur `solaire` · src/labuse/api/modules.py:prospection_solaire | run | servie · non couverte (n sous seuil, dit) · non calculée | outil « Prospection solaire » · outil « Toits bien exposés » · fiche « Fiche soleil (photo toit + rosace) » |
| | | *productible PVGIS SARAH3 gelé au run du builder (parcel_solar)* | | | | | |

## Division (copropriétés/lots)

*Robinet `fiche_parcelle_division` — route `/parcels/{idu}`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `divisible_classe` | classe — domaine : candidate, non_candidate, non_recalculee | Division (candidate) | cadastre_api_carto (PCI Parcellaire Express (DGFiP) — « latest » ingérée), cosia (CoSIA 2025 (PVA juil.-août 2025, 20 cm)), gpu_plu_api_carto (GPU/PLU par commune (révisions — détail en fiche)) | moteur `division_or` · src/labuse/api/app.py:2692-2696 | run | servie · non déterminée (la source ne dit pas) · non calculée | nulle part ailleurs |
| | | *présence dans division_or_candidates — run figé q_v10, workflow de revue* | | | | | |
| `coproprietes_liste` | liste | Copropriétés (RNIC) | rnic_anah | passe-plat · src/labuse/api/app.py:_q_v2_fiche (coproprietes) — table lue : rnic_coproprietes | live | servie (possiblement vide, dit) · non calculée | nulle part ailleurs |
| | | *copropriétés immatriculées rattachées à la parcelle (lots, syndic) — RNIC/ANAH* | | | | | |
