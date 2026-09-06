# CALCULS-INVENTAIRE — CIRCUIT-4 (lot 1, verdicts mis à jour lots 2-3)

L'inventaire EXHAUSTIF des calculs servis : les 113 données du registre avec
`calcul == "moteur"` (52 passe-plats et 3 constantes n'ont pas de formule — pas de fiche),
regroupées par CALCUL (une fiche = un calcul, `src/labuse/regles/<donnee>.py`), classées.
Généré depuis le registre + les fiches (source : le code). Garde :
`tests/test_circuit4_lot1.py` refuse toute donnée moteur sans fiche et toute fonction de
`registre/moteurs/` non couverte.

## Règles externes (loi, code, barème, arrêté) — 16 calculs, 31 données

| fiche (calcul) | données servies | opérations (formule codée, abrégée) | entrées | verdict |
|---|---|---|---|---|
| `autres_loges_pct` | `autres_loges_pct` | pct = max(0 ; 100 − locataires_pct − proprietaires_pct), arrondi 0,1 (round(x×10)/10). Calculé au serveur (CIRCUIT-1 lot 2.4), jamais au front. | locataires_pct, proprietaires_pct (INSEE RP, statuts d'occupation) | reference_introuvable |
| `destination_statut` | `destination_statut`, `reglement_plu_bloc` | Lecture du règlement CALIBRÉ de la zone (corpus PLU ingéré, extraits cités document/page/millésime) : destination autorisée / interdite / conditionnée par zone, servie avec son ext… | corpus PLU calibré (extraits par zone); parcel_zone_plu; CDAC_SEUIL_M2 = 1000 | conforme |
| `marge_surelevation_m` | `marge_surelevation_m` | marge = hauteur_règle − hauteur_bâti, avec hauteur_règle = hé (hauteur à l'ÉGOUT du règlement de zone, YAML calibré) en priorité, repli hf (faîtage) SEULEMENT si l'égout est absent… | config/plu_<commune>.yaml (he_m, hf_m, hauteur_src); hauteur_bati_m (BD TOPO) | partiel |
| `mixite_clause` | `mixite_clause` | Déclenchement si SDP projetée ≥ seuil du règlement OU logements ≥ seuil OU terrain > seuil — seuils LUS de la calibration du règlement de la zone (YAML par commune), jamais des con… | config/plu_<commune>.yaml (seuils Art. 2 calibrés, article et page cités); SDP/logements du scénario | conforme |
| `n_concurrents_zone` | `n_concurrents_zone`, `emplois_fourchette` | n_concurrents = count(sirene_etablissements ACTIFS du code NAF choisi dans l'isochrone), chacun servi avec son temps d'accès (bande d'isochrone) ; les établissements en diffusion p… | sirene_etablissements (NAF, tranche d'effectifs, geo, statut de diffusion); isochrone | conforme |
| `n_permis_proximite` | `n_permis_proximite`, `depots_secteur_n`, `historique_permis_liste` | n_permis_proximite = count(sitadel_permits) dans le rayon 500 m, fenêtre 24 mois (LE profil client, arbitrage Q7, paramètres TRANSMIS au front). depots_secteur_n = dépôts de la sec… | sitadel_permits (date, type, geom, idu_codes) | partiel |
| `part_logements_egout_pct` | `part_logements_egout_pct` | pct = 100 × logements raccordés au tout-à-l'égout ÷ logements total, à la maille IRIS de la parcelle, REPLI commune si l'IRIS manque — le TAUX est servi avec sa maille, jamais une … | insee_rp2022_egoul (fichier détail Logements EGOUL, RP 2022, maille IRIS) | reference_introuvable |
| `permis_5a_n` | `permis_5a_n`, `permis_12m_n` | permis_5a_n = count(sitadel_permits) de la commune avec date ≥ aujourd'hui − 5 ans (fenêtre calendaire). permis_12m_n = count(sitadel_permits) de la commune (et du type s'il est de… | sitadel_permits.date/commune/type/geom | partiel |
| `population_zone` | `population_zone`, `revenu_approche_eur` | population_zone = Σ ind (individus) des carreaux Filosofi 200 m INTERSECTANT l'isochrone (un carreau touché compte entier — maille source, pas de proratisation). revenu_approche_eu… | filosofi_carreaux_200m (ind, revenus, i_est_200 — INSEE Filosofi, carreaux 200 m); isochrone (fiche zone) | conforme |
| `sdp_residuelle_m2` | `sdp_residuelle_m2`, `classe_residuel` | SDP_existante = emprise_bâtie × niveaux_existants, où emprise_bâtie = max(bati_ratio(BD TOPO) × surface, emprise_cosia_m2 révélée) et niveaux_existants = étages BD TOPO, sinon ⌈hau… | spatial_layers kind=batiment (BD TOPO : etages, hauteur); parcel_bati_revele (CoSIA); parcel_faisabilite (capacité max); | partiel |
| `surface_plancher_m2` | `surface_plancher_m2`, `capacite_logements`, `surface_vendable_m2`, `potentiel_verdict` | Enveloppe gabaritaire posée DANS L'ORDRE DU RÈGLEMENT de la zone (YAML calibré par commune, sources citées article par article) : (1) emprise au sol = contour cadastral réel inseté… | parcels.geom_2975/surface_m2; parcel_zone_plu (zone dominante); config/plu_<commune>.yaml (reculs, CES, pleine terre, hé | partiel |
| `taxe_amenagement_eur` | `taxe_amenagement_eur` | Assiette = surface_taxable × valeur forfaitaire de l'année (892 €/m² hors IdF, millésime 2026 du YAML daté) + forfaits d'installations (piscine 251 €/m², PV au sol 10 €/m², station… | config/taxe_amenagement.yaml (millésime 2026, source service-public A15416, relevé 2026-08-28); taxe_amenagement_taux (d | conforme |
| `vacance_pct` | `vacance_pct` | pct = 100 × logements_vacants ÷ logements_total (INSEE RP de la commune), arrondi 0,1 ; None si le dénominateur manque ou est nul. | commune_insee_logement (logements, vacants — INSEE RP) | conforme |
| `ventes_retenues_n` | `ventes_retenues_n`, `ventes_ecartees_n`, `dvf_parcelle_liste`, `voisinage_100m_liste`, `ventes_100m_n` | filtre_ventes (marche_service) : chaque vente DVF est RETENUE ou ÉCARTÉE AVEC MOTIF (nature de mutation hors vente, prix nul, surface nulle, hors bornes de bon sens, doublon multi-… | dvf_mutations_parcelle (nature, prix, surfaces, geom); config/dvf_profils.yaml | conforme |
| `zan_reste_ha` | `zan_reste_ha` | Délégation : le calcul vit dans api/rarete.py:compute_rarete (une seule vérité). Enveloppe restante estimée depuis la consommation ENAF observée (commune_conso_enaf, Cerema 2021-20… | commune_conso_enaf.conso_2021_2024_m2 (Cerema, portail artificialisation) | reference_introuvable |
| `zone_plu_famille` | `zone_plu_famille`, `zonage_plu_couche` | Zone servie = la zone GPU couvrant la PLUS GRANDE SURFACE de la parcelle (parcel_zone_plu, PK idu — même source que l'écran, la couche et la faisabilité depuis ZONE-1) ; famille U/… | parcel_zone_plu (idu, zone, zone_fam, parts); GPU (Géoportail de l'urbanisme, zonages) | conforme |

## Méthodes standard (statistiques, géométriques, techniques) — 14 calculs, 32 données

| fiche (calcul) | données servies | opérations (formule codée, abrégée) | entrées | verdict |
|---|---|---|---|---|
| `charge_fonciere_eur` | `charge_fonciere_eur`, `bilan_ca_eur`, `bilan_cout_construction_eur`, `bilan_frais_eur`, `bilan_marge_eur`, `bilan_vrd_eur`, `bilan_demolition_eur`, `ecart_prix_demande_pct`, `sensibilite_cout_construction` | Bilan à rebours classique : CA = SHAB vendable × prix de sortie observé (fiche prix_sortie_bati_eur_m2) ; coût construction = SDP × coût/m² (SDP ≈ SHAB × 1,15 — circulations/gaines… | sector_price (prix de sortie); faisabilité (SHAB/SDP); Hypotheses/bilan_params (coûts, marge 9 %, frais 12 %, plancher×1 | reference_introuvable |
| `comparateur_composite` | `comparateur_composite` | Normalisation min-max de chaque indicateur présent sur [0;100] selon sa direction (direction −1 → 1−frac), avec frac = (v − min) ÷ (max − min) sur les 24 communes ; borne dégénérée… | indicateurs_communes (stock, velocite, permis, deficit_sru, pression_zan, prix_neuf); poids (réglables, défauts INDICATE | conforme |
| `distance_arret_m` | `distance_arret_m` | Objet `kind` le plus proche de la parcelle par KNN PostGIS (ORDER BY sl.geom_2975 <-> p.geom_2975 LIMIT 1), distance = round(ST_Distance(geom_2975, geom_2975))::int en MÈTRES (proj… | spatial_layers (kind, subtype, geom_2975); parcels.geom_2975 | ecart |
| `ecart_demande_acte_pct` | `ecart_demande_acte_pct` | ecart = 100 × (médiane_demandé − médiane_acté) ÷ médiane_acté, servi seulement si les DEUX côtés tiennent n ≥ 5 (SEUIL_N), avec les deux n et les deux millésimes. Référence du MÊME… | pige_biens/pige_faits (prix affichés, types, paires vendues); DVF acté via marche_service (référence locale/commune) | conforme |
| `emprise_batie_m2` | `emprise_batie_m2`, `n_batiments` | Par parcelle : emprise = aire de l'intersection géométrique des bâtiments (BD TOPO kind=batiment) avec la parcelle, COMPLÉTÉE par l'emprise CoSIA (couverture du sol IA) là où BD TO… | spatial_layers kind=batiment (BD TOPO); CoSIA (emprise_cosia_m2); parcels.geom_2975 | reference_introuvable |
| `hauteur_bati_m` | `hauteur_bati_m` | h = max(hauteur des bâtiments BD TOPO intersectant la parcelle) en mètres (attrs->>'hauteur' de spatial_layers kind=batiment) ; NULL si aucune hauteur ingérée — jamais une inventio… | spatial_layers kind=batiment (attrs->hauteur, geom_2975); parcels.geom_2975 | reference_introuvable |
| `loyer_median_eur_m2` | `loyer_median_eur_m2` | Estimation loyers.py — le DOUTE du catalogue des moteurs (moteurs.csv) est reconduit tel quel : les entrées exactes restent à confirmer (fiche honnête, pas une formule inventée). | à confirmer (DOUTE porté par moteurs.csv depuis CIRCUIT-2) | reference_introuvable |
| `prix_ancien_median_eur_m2` | `prix_ancien_median_eur_m2` | Médiane des €/m² DVF « ventes strictes » de la commune (filtre de retenue du baromètre : natures de mutation de vente, surfaces > 0, bornes de bon sens) — moteur prix_ancien_commun… | dvf_mutations (nature, prix, surface, commune) | conforme |
| `prix_demande_median_eur_m2` | `prix_demande_median_eur_m2`, `delai_vente_median_j`, `annonces_actives_n`, `n_biens_du_jour`, `n_biens_veille` | Sur pige_biens × pige_faits validés (valide_at NOT NULL) et NON à-qualifier : médiane percentile_cont(0.5) des prix affichés €/m² (terrain : prix ÷ surface_terrain ; bâti maison/ap… | pige_biens (statut, type_bien, dates); pige_faits (prix, surfaces, valide_at) | conforme |
| `prix_neuf_observe_eur_m2` | `prix_neuf_observe_eur_m2`, `prix_neuf_vefa_acte_eur_m2`, `tranche_prix_vefa`, `vefa_couche` | prix_neuf_vefa_acte = médiane des VEFA déclarées à l'acte (neuf_vefa_commune, fenêtre 36 mois glissants, ≥ 10 ventes avec prix sinon rien). prix_neuf_observe = ventes ≤ 3 ans après… | dvf (VEFA, dates d'achèvement Sitadel); neuf_vefa_commune (live, 36 mois) | conforme |
| `prix_sortie_bati_eur_m2` | `prix_sortie_bati_eur_m2`, `prix_terrain_secteur_eur_m2` | Médiane des €/m² DVF sur un segment HOMOGÈNE type × période, rayon ADAPTATIF : 500 m → 1 000 m → 1 500 m → commune, on prend le plus serré atteignant n ≥ 8 (MIN_N_SECTEUR) ; périod… | dvf_mutations_parcelle (prix, surface, type, date, geom); parcels.geom_2975; constantes SECTEUR-2 T1 : MIN_N_SECTEUR=8,  | conforme |
| `prix_terrain_zone_eur_m2` | `prix_terrain_zone_eur_m2` | Médiane des €/m² DVF terrain nu de la commune par famille de zone (U/AU/A/N), seuil 10 ventes par cellule sinon rien. | dvf_mutations_parcelle (terrains); parcel_zone_plu.zone_fam | conforme |
| `prod_spec_kwh_kwc` | `prod_spec_kwh_kwc`, `azimut_bati_deg` | prod_spec = productible spécifique PVGIS (kWh/kWc/an, base SARAH3) au point de la grille solaire la plus proche, gelé au run du builder (parcel_solar, millésime porté en base) ; az… | solar_grid (PVGIS SARAH3); spatial_layers kind=batiment; parcel_vegetation; filosofi_carreaux_200m | reference_introuvable |
| `velocite_delai_median_mois` | `velocite_delai_median_mois` | Médiane (percentile_cont(0.5), interpolation linéaire) de delai_mois sur m10_permit_delais WHERE valide AND famille = 'logements' AND delai_mois >= 0, par commune. La même requête … | m10_permit_delais.delai_mois (valide, famille=logements); commune_contexte_sru.objectif_pct/taux_lls (DHUP); commune_con | conforme |

## Choix LABUSE (définitions à nous, assumées) — 33 calculs, 46 données

| fiche (calcul) | données servies | opérations (formule codée, abrégée) | entrées | verdict |
|---|---|---|---|---|
| `assemblage_parcelles_n` | `assemblage_parcelles_n`, `assemblage_surface_m2` | assemblage_parcelles_n = compte des parcelles retenues dans l'assemblage courant ; assemblage_surface_m2 = Σ surface_m2 cadastrale des parcelles retenues. Délégation : la logique (… | parcels.surface_m2; sélection client (idus) | choix_assume |
| `copilote_compte_parcelles` | `copilote_compte_parcelles` | count sur la MÊME facette canonique que le filtre écran (mêmes WHERE : tiers, zones, communes, run servi) — égalité verrouillée par test : le Copilote ne peut pas dire un autre nom… | parcels; parcel_p_score_v2 (run servi); parcel_zone_plu | choix_assume |
| `courrier_demandes_n` | `courrier_demandes_n` | Délégation : courrier.py:demandes_de — count des demandes de courrier du compte. | courrier_demandes (compte_id) | choix_assume |
| `couverture_commune_pct` | `couverture_commune_pct` | Compteurs de couverture lus des données réelles : parcelles = count(parcels) ; communes = count(DISTINCT commune) ; dvf = count(dvf_mutations) ; radar = count(pige_biens) ; run ser… | parcels; dvf_mutations; pige_biens; p_score_v2_runs | choix_assume |
| `crm_cartes_n` | `crm_cartes_n`, `pipeline_entrees_n` | n(statut) = count(pipeline_entries WHERE compte_id IS NOT DISTINCT FROM :cid) GROUP BY status — périmètre du compte (NULL = pilote). | pipeline_entries (status, compte_id) | choix_assume |
| `divisible_classe` | `divisible_classe` | Présence dans division_or_candidates (candidates à la division parcellaire : géométrie, bâti CoSIA, zone PLU — heuristique du builder division-or), run figé q_v10, workflow de REVU… | parcels (géométrie); CoSIA (bâti); parcel_zone_plu | choix_assume |
| `ecart_candidat_pct` | `ecart_candidat_pct` | Comparaison des DISTRIBUTIONS de tiers entre le run candidat et le run servi (part de chaque tier, écarts en points) — lecture seule, jamais une bascule. | parcel_p_score_v2 (candidat + servi); p_score_v2_runs | choix_assume |
| `evenements_proprietaire_liste` | `evenements_proprietaire_liste` | Signaux DATÉS assemblés des sources publiques : procédures collectives BODACC, radiations/cessations SIRENE, mutations DVF — chaque événement porte sa source et sa date (faits publ… | bodacc_*; sirene_etablissements; dvf_mutations | choix_assume |
| `ia_cout_eur` | `ia_cout_eur` | cout = Σ cout_eur du ledger ia_log sur le mois courant (date_trunc('month')) + nombre d'appels ; ventilation 30 j : par jour, par licence, cumul 7 j. Le cout_eur unitaire est écrit… | ia_log (cout_eur, ts, compte_id, modele) | choix_assume |
| `mutations_12m_n` | `mutations_12m_n` | n = count(dvf_mutations de la commune) WHERE date_mutation > max(date_mutation de la commune) − 12 mois — fenêtre ancrée sur la DERNIÈRE mutation CONNUE de la commune, pas sur la d… | dvf_mutations.date_mutation/commune | choix_assume |
| `n_a_faire` | `n_a_faire` | Délégation : etats_sources.compteurs sur lister_etats — n = nouvelles versions à injecter + sources à rafraîchir (arbitre d'état unique des sources). | data_sources; source_veille | choix_assume |
| `n_bascules_7j` | `n_bascules_7j` | count(parcelles dont le tier au run SERVI ∈ {brulante, chaude} ET dont le tier au run PRÉCÉDENT était NULL ou hors de ces deux tiers) — auto-jointure parcel_p_score_v2 sur parcelle… | parcel_p_score_v2 (tier, run_id) des deux runs | choix_assume |
| `n_comptes_actifs` | `n_comptes_actifs` | n = count(comptes WHERE statut = 'actif'). | comptes.statut | choix_assume |
| `n_densifiables` | `n_densifiables`, `densifier_couche` | Parcelles BÂTIES à capacité résiduelle (agrégation des verdicts cascade + résiduel du run servi → parcel_renouvellement, reconstruit à la bascule) ; n = count au run servi, la couc… | dryrun_cascade_results; parcel_residuel; parcel_renouvellement (run servi) | choix_assume |
| `n_depots_a_verifier` | `n_depots_a_verifier` | n = count(pige_faits WHERE valide_at IS NULL) — faits déposés en attente de validation humaine. | pige_faits.valide_at | choix_assume |
| `n_extraits_plu` | `n_extraits_plu`, `n_communes_rnu`, `n_procedures_plu` | Par commune du référentiel : statut = servable (extraits ingérés, idurba réconcilié) · rnu (registre config/rnu_communes.yaml) · revision (opposabilité en attente GPU) · non_ingere… | corpus PLU ingéré (plu_ingest.corpus_status); config/rnu_communes.yaml; veille_plu (radar Sudocuh) | choix_assume |
| `n_notifications` | `n_notifications` | n = count(event_log e WHERE _visible(e) AND NOT _seen(e)) du compte — les fragments de visibilité/lecture (_visible/_seen) restent chez api/events.py (une sémantique, deux lecteurs… | event_log; event_seen (lectures par compte) | choix_assume |
| `n_parcelles_commune` | `n_parcelles_commune` | n = count(*) FROM parcels WHERE commune = :c — compte brut, aucune fenêtre. | parcels.commune | choix_assume |
| `n_parcelles_ile` | `n_parcelles_ile` | n = p_score_v2_runs.n_parcelles du run servi (registre du run, lecture par clé primaire) ; repli count(parcel_p_score_v2 du run) si le registre ne connaît pas le run ; indisponible… | p_score_v2_runs.n_parcelles; parcel_p_score_v2 (repli) | choix_assume |
| `n_parcelles_pm` | `n_parcelles_pm` | Délégation : api/modules.py:patrimoine — n_parcelles est le compte du portefeuille complet du SIREN (jointure parcelle_personne_morale × parcels, millésime servi 2025) ; même assie… | parcelle_personne_morale (DGFiP, millésime 2025); parcels | choix_assume |
| `n_piscines` | `n_piscines` | count(parcel_equipements WHERE piscine IS TRUE), filtres alignés sur le listing : bâti (emprise p_model_bati > 0 / = 0 / tous), surface piscine ≥ seuil demandé, confiance (SEUIL_PI… | parcel_equipements (piscine, piscine_surface_m2, confiance); p_model_bati.emprise_bati_m2; piscine_corrections | choix_assume |
| `n_sources` | `n_sources`, `n_sources_surveillees` | n_sources = count(data_sources) sous le prédicat canonique WHERE_AFFICHEES (statut connecte/manuel, non doublon/retirée/dormante/masquée/désactivée) — sources_catalog, LA définitio… | data_sources; source_veille | choix_assume |
| `n_veilles` | `n_veilles` | Délégation : copilote_v2/veilles.py:lister — count des veilles du compte. | veilles (compte_id) | choix_assume |
| `n_vigilances` | `n_vigilances`, `verdict_icd`, `simulplu_resultat` | n_vigilances = compte des couches de la cascade au verdict SOFT_FLAG ou HARD_EXCLUDE pour la parcelle (dryrun_cascade_results du run servi). verdict_icd = complétude des couches au… | dryrun_cascade_results (run servi); spatial_layers (17 couches) | choix_assume |
| `parcelles_par_zone_n` | `parcelles_par_zone_n` | Compte de parcelles par famille puis par zone_filtre : n(fam, zone) = count(parcel_zone_plu WHERE zone_filtre IS NOT NULL), groupé par (zone_fam, zone_filtre), optionnellement rest… | parcel_zone_plu.zone_fam; parcel_zone_plu.zone_filtre; parcels.commune | choix_assume |
| `part_zone_U_pct` | `part_zone_U_pct`, `part_zone_AU_pct`, `part_zone_A_pct`, `part_zone_N_pct` | Part de SURFACE d'une famille de zones (U, AU, A, N) dans la surface cadastrée zonée de la commune. part_fam = 100 × Σ surface_m2(parcelles de la famille) ÷ Σ surface_m2(parcelles … | parcels.surface_m2; parcel_zone_plu.zone_fam (PK idu) | choix_assume |
| `point_mort_n` | `point_mort_n` | count(DISTINCT permis PC) de la commune tels que : date < aujourd'hui − N mois, raw->>'daact' IS NULL (aucune déclaration d'achèvement), ET la parcelle du permis est toujours NON b… | sitadel_permits (type PC, date, raw->daact, idu_codes); dryrun_cascade_results (couche bati, run servi); dryrun_parcel_e | choix_assume |
| `ppr_pct` | `ppr_pct` | pct = 100 × count(DISTINCT parcelles de la commune intersectant la couche kind) ÷ total_parcelles(commune), arrondi 0,1 ; None si le dénominateur est nul. Intersection géométrique … | parcels.geom_2975/commune; spatial_layers.kind/geom_2975 | choix_assume |
| `projet_cadrage_n` | `projet_cadrage_n`, `projet_retenues_n` | Délégation : api/projets.py:_counts_by_projet — parcelles du projet / retenues, par projet. | projets, projet_parcelles | choix_assume |
| `proprietaire_timeline_liste` | `proprietaire_timeline_liste`, `acquisitions_pm_n` | Timeline = union des millésimes versionnés (pm_proprietaires_millesimes, 2019→2024) et du servi (parcelle_personne_morale 2025), anti-doublon NOT EXISTS, le servi jamais écrasé. ac… | pm_proprietaires_millesimes (2019→2024); parcelle_personne_morale (2025) | choix_assume |
| `qpv_n` | `qpv_n` | Liste (puis compte) des QPV de spatial_layers kind='qpv' rattachés à la commune (colonne commune de la couche), nom + code_qp, tri par nom. | spatial_layers (kind=qpv, name, attrs->code_qp, commune) | choix_assume |
| `statut_plu` | `statut_plu` | Préséance : RNU (registre config/rnu_communes.yaml — Saint-Philippe) l'emporte ; sinon statut du registre veille_plu (radar Sudocuh : PLU opposable, révision, élaboration). Une lec… | config/rnu_communes.yaml; veille_plu (Sudocuh) | choix_assume |
| `usage_outil_n` | `usage_outil_n` | n = count(usage_events WHERE kind='outil' AND outil IS NOT NULL AND ts > now() − fenêtre) GROUP BY outil, tri décroissant ; fenêtre ∈ {7, 30, 90} jours. | usage_events (kind, outil, ts) | choix_assume |

## Modèle (scoring : validation, pas de formule officielle) — 1 calculs, 4 données

| fiche (calcul) | données servies | opérations (formule codée, abrégée) | entrées | verdict |
|---|---|---|---|---|
| `tier_opportunite` | `tier_opportunite`, `rang_tier`, `stock_opportunites`, `verdict_couche` | Modèle m36-l2f-2026 (scoring/p_v2) : WoE binning (min_count 200, monotonie PAV) + régression logistique (C=5.0, L2, seed 974), calibration ISOTONIQUE sur 2025, recalage d'intercept… | p_model_* (cosia, sitadel, dvf, filosofi, bd_topo); parcel_v_score; parcel_residuel | modele_valide |

## Ordre de traitement (lot 1.2)

`regle_externe` d'abord (la responsabilité), puis `methode_standard`, `choix_labuse`, `modele`.

## Couverture des fonctions de `registre/moteurs/`

- `commune.autres_loges_pct` → fiche(s) : `autres_loges_pct`
- `commune.composite_communes` → fiche(s) : `comparateur_composite`
- `commune.compte_parcelles_commune` → fiche(s) : `n_parcelles_commune`
- `commune.compte_permis_commune` → fiche(s) : `permis_5a_n`
- `commune.compte_piscines` → fiche(s) : `n_piscines`
- `commune.couverture_sources` → fiche(s) : `couverture_commune_pct`
- `commune.etat_corpus_plu` → fiche(s) : `n_extraits_plu`
- `commune.indicateurs_communes` → fiche(s) : `velocite_delai_median_mois`
- `commune.mutations_12m` → fiche(s) : `mutations_12m_n`
- `commune.pct_parcelles_couche` → fiche(s) : `ppr_pct`
- `commune.permis_point_mort` → fiche(s) : `point_mort_n`
- `commune.qpv_commune` → fiche(s) : `qpv_n`
- `commune.vacance_pct` → fiche(s) : `vacance_pct`
- `parcelle.assemblage_assiette` → fiche(s) : `assemblage_parcelles_n`
- `parcelle.plus_proche` → fiche(s) : `distance_arret_m`
- `plateforme.bascules_tiers_hauts` → fiche(s) : `n_bascules_7j`
- `plateforme.cartes_par_colonne` → fiche(s) : `crm_cartes_n`
- `plateforme.compte_parcelles_ile` → fiche(s) : `n_parcelles_ile`
- `plateforme.comptes_actifs` → fiche(s) : `n_comptes_actifs`
- `plateforme.conso_ia_30j` → fiche(s) : `ia_cout_eur`
- `plateforme.conso_ia_mois` → fiche(s) : `ia_cout_eur`
- `plateforme.depots_a_verifier` → fiche(s) : `n_depots_a_verifier`
- `plateforme.notifications_non_lues` → fiche(s) : `n_notifications`
- `plateforme.usage_par_outil` → fiche(s) : `usage_outil_n`
- `proprietaire.compte_parcelles_pm` → fiche(s) : `n_parcelles_pm`
- `zonage.parcelles_par_zone` → fiche(s) : `parcelles_par_zone_n`
- `zonage.parts_zonage_surface` → fiche(s) : `part_zone_U_pct`
