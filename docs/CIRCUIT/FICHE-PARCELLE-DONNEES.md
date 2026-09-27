# FICHE PARCELLE — donnée par donnée

*Généré du registre le 2026-09-27 par `labuse registre fiche parcelle` (le code est la vérité — ne pas éditer à la main ; relu avant commit).*

Chaque section est un tiroir de la fiche. Pour chaque donnée : d'où elle vient (source et millésime servis), par quel chemin (moteur nommé ou passe-plat), sa portée (`run` = change à la bascule · `live` = à l'injection · `projet` = saisie du client), ses états possibles, et où ailleurs elle s'affiche.

## Sols (SIS / CASIAS)

*Robinet `fiche_parcelle_sols` — route `/parcels/{idu} (clé sols)`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `sols_parcelle` | liste | Sols (SIS/CASIAS, parcelle) | georisques_sis (4 SIS 974 (MultiPolygon) — canal SSP, vu 07/09/2026), georisques_casias (453 sites 974 (435 points, 18 emprises) — canal SSP, 07/09/2026) | passe-plat · src/labuse/api/app.py:_sols_block — table lue : spatial_layers (kind=sol_pollue) | live | servie (possiblement vide, dit) · non calculée | nulle part ailleurs |
| | | *l'état des sols de la parcelle : périmètre SIS intersecté, site CASIAS/instruction le plus proche (≤ 100 m) — intersections live des couches servies, mêmes règles que la cascade sol_pollue* | | | | | |
| `sis_classe` | classe — domaine : dans, hors | Secteur d'information sur les sols (SIS) | georisques_sis (4 SIS 974 (MultiPolygon) — canal SSP, vu 07/09/2026) | passe-plat · src/labuse/api/app.py:_sols_block (sis) — table lue : spatial_layers (kind=sol_pollue, subtype=sis) | live | servie · non déterminée (la source ne dit pas) · non calculée | nulle part ailleurs |
| | | *la parcelle est-elle dans un périmètre SIS (étude de sols obligatoire au changement d'usage L556-2 CE ; information écrite de l'acheteur/locataire obligatoire L125-7 CE)* | | | | | |
| `casias_statut` | classe — domaine : sur_place, proche_100m, hors | Ancien site industriel (CASIAS) | georisques_casias (453 sites 974 (435 points, 18 emprises) — canal SSP, 07/09/2026) | passe-plat · src/labuse/api/app.py:_sols_block (casias) — table lue : spatial_layers (kind=sol_pollue, subtypes casias/instruction) | live | servie · non déterminée (la source ne dit pas) · non calculée | nulle part ailleurs |
| | | *site CASIAS/instruction sur la parcelle ou à moins de 100 m — inventaire historique, pas une pollution avérée (le libellé le dit)* | | | | | |

## Dispositifs et périmètres (droit des sols)

*Robinet `fiche_parcelle_droit_sols` — route `/parcels/{idu} (clé dispositifs)`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `dispositifs_parcelle` | liste | Dispositifs et périmètres (parcelle) | gpu_prescriptions_er (GPU — prescriptions typepsc 05 (idurba par commune)), gpu_prescriptions_ebc (GPU — prescriptions typepsc 01 (idurba par commune)), dpu_perimetres (GPU), peb_dgac (Roland-Garros B/C/D (GPU) ; Pierrefonds non publié), sup_gpu | passe-plat · src/labuse/api/app.py:_dispositifs_block — table lue : spatial_layers (kinds plu_gpu_prescription/dpu/peb/sup) | live | servie (possiblement vide, dit) · non calculée | nulle part ailleurs |
| | | *liste des dispositifs du droit des sols touchant la parcelle (ER avec part, EBC avec part, DPU, zone PEB, SUP par catégorie) — intersections live des couches servies, mêmes seuils que la cascade (source unique cascade_rules.yaml)* | | | | | |
| `er_emplacement_reserve` | classe — domaine : grevee, non_grevee | Emplacement réservé (ER) | gpu_prescriptions_er (GPU — prescriptions typepsc 05 (idurba par commune)) | passe-plat · src/labuse/api/app.py:_dispositifs_block (er) — table lue : spatial_layers (kind=plu_gpu_prescription, famille ER) | live | servie · non déterminée (la source ne dit pas) · non calculée | nulle part ailleurs |
| | | *la parcelle est-elle grevée d'un emplacement réservé du PLU (destination, part de la parcelle) — famille ER = typepsc 05 + rescue/veto libellé (source unique cascade_rules)* | | | | | |
| `ebc_classe` | classe — domaine : intersecte, hors | Espace boisé classé (EBC) | gpu_prescriptions_ebc (GPU — prescriptions typepsc 01 (idurba par commune)) | passe-plat · src/labuse/api/app.py:_dispositifs_block (ebc) — table lue : spatial_layers (kind=plu_gpu_prescription, typepsc 01) | live | servie · non déterminée (la source ne dit pas) · non calculée | nulle part ailleurs |
| | | *la parcelle intersecte-t-elle un espace boisé classé du PLU (part de la parcelle ; part soustraite de l'assiette du bloc potentiel — L113-1 CU)* | | | | | |
| `dpu_perimetre` | classe — domaine : simple, renforce, hors, non_publie | Droit de préemption urbain (DPU) | dpu_perimetres (GPU) | passe-plat · src/labuse/api/app.py:_dispositifs_block (dpu) — table lue : spatial_layers (kind=dpu) | live | servie · non déterminée (la source ne dit pas) · non calculée | nulle part ailleurs |
| | | *la parcelle est-elle dans un périmètre de préemption publié (DPU simple/renforcé) — les communes sans DPU publié au GPU sont « non déterminée — non publié par la commune »* | | | | | |
| `peb_zone` | classe — domaine : A, B, C, D, hors | Plan d'exposition au bruit (PEB) | peb_dgac (Roland-Garros B/C/D (GPU) ; Pierrefonds non publié) | passe-plat · src/labuse/api/app.py:_dispositifs_block (peb) — table lue : spatial_layers (kind=peb) | live | servie · non déterminée (la source ne dit pas) · non calculée | nulle part ailleurs |
| | | *zone PEB de l'aérodrome (A/B/C/D) si la parcelle y est — Roland-Garros servi (annexes GPU) ; Pierrefonds non publié au GPU (couverture partielle dite)* | | | | | |
| `scot_parcelle` | texte | SCOT (schéma de cohérence territoriale) | scot_gpu (GPU — périmètres SCOT (idurba CNIG par document)) | passe-plat · src/labuse/api/fiche_blocs3.py:scot — table lue : spatial_layers (kind=scot) | live | servie · non déterminée · non calculée | nulle part ailleurs |
| | | *le SCOT qui couvre la parcelle (nom, statut, date d'approbation) — document supra-communal opposable au PLU* | | | | | |

## Contraintes environnementales (APER / mesures compensatoires)

*Robinet `fiche_parcelle_contraintes_env` — route `/parcels/{idu} (clés enr_exclue_toiture, mesures_compensatoires)`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `enr_exclue_parcelle` | texte | EnR au sol interdites (APER, sauf toiture) | enr_aper_ofb (OFB — zonages exclus des aires d'accélération EnR (loi APER)) | passe-plat · src/labuse/api/fiche_blocs3.py:enr_exclue_toiture — table lue : spatial_layers (kind=enr_exclue_hors_toiture) | live | servie · non déterminée · non calculée | nulle part ailleurs |
| | | *la parcelle est-elle dans une zone où les EnR au SOL sont EXCLUES (loi APER) — le photovoltaïque/ombrière au sol y est exclu, la toiture n'est pas concernée* | | | | | |
| `mesures_compensatoires_parcelle` | texte | Mesure compensatoire (GéoMCE) | geomce (GéoMCE — géoportail des mesures compensatoires (national)) | passe-plat · src/labuse/api/fiche_blocs3.py:mesures_compensatoires — table lue : spatial_layers (kind=mesures_compensatoires) | live | servie · non déterminée · non calculée | nulle part ailleurs |
| | | *la parcelle recoupe-t-elle une mesure compensatoire environnementale (GéoMCE, MTE/OFB) — obligation de compensation liée à un projet, à instruire* | | | | | |

## Historique cadastral (filiation DFI)

*Robinet `fiche_parcelle_filiation` — route `/parcels/{idu} (clé filiation)`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `filiation_parcelle` | liste | Historique cadastral (filiation DFI) | dgfip_dfi (situation 19/06/2026 — 409 623 liens 974 (1989→2025)) | passe-plat · src/labuse/ingestion/dfi.py:filiation_parcelle — table lue : dfi_filiation | live | servie (possiblement vide, dit) · non calculée | nulle part ailleurs |
| | | *la généalogie OFFICIELLE de la parcelle : d'où elle vient (mères), ce qu'elle est devenue (filles), nature et date de chaque événement (DFI DGFiP) — passe-plat trié ; absence NORMALE (informatisation 1980-90+, aménagements fonciers exclus) ; contrôle croisé avec le cadastre d'époque (géométrie), jamais un conflit* | | | | | |

## Quartier INSEE (Autour)

*Robinet `fiche_parcelle_quartier` — route `/parcels/{idu} (clé iris_quartier)`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `iris_quartier` | liste | Quartier INSEE (IRIS) | insee_rp_iris (RP2022 — parution 16/10/2025 (géographie 01/01/2024)), contours_iris (Contours IRIS — géographie 2024 (IGN/INSEE)) | passe-plat · src/labuse/ingestion/iris_rp.py:stats_iris (iris_de_parcelle) — table lue : iris_rp | live | servie (possiblement vide, dit) · non calculée | outil « Étude de zone » |
| | | *le quartier INSEE de la parcelle (IRIS, contours géographie 2024) : logements, vacance, âge du bâti (part ≤ 1990), taille des ménages (NPER_RP/RP), part 60 ans et +, part locataires/HLM — RP2022, maille IRIS DITE (affine la commune, ne la remplace pas)* | | | | | |

## Fibre (Réseaux et accès)

*Robinet `fiche_parcelle_fibre` — route `/parcels/{idu} (clé fibre)`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `fibre_parcelle` | classe — domaine : raccordable, non_raccordable, aucun_immeuble | Fibre (raccordable FttH) | arcep_fibre (2026_T1 — 330 051 immeubles 974 (découpage départemental)) | passe-plat · src/labuse/ingestion/arcep_fibre.py:fibre_parcelle — table lue : arcep_immeubles | live | servie · non déterminée (la source ne dit pas) · non calculée | nulle part ailleurs |
| | | *raccordabilité FttH de l'immeuble Arcep le plus proche de la parcelle (≤ 100 m, DISTANCE DITE — jamais un booléen nu) + opérateurs présents ; « aucun immeuble » est un état, pas un zéro* | | | | | |

## En-tête (adresse, géométrie)

*Robinet `fiche_parcelle_entete` — route `/parcels/{idu}`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `adresse_ban` | texte | Adresse | ban (2026) | passe-plat · src/labuse/api/app.py:_ban_adresse — table lue : adresses (id_ban) ⋈ adresse_parcelles | live | servie · non déterminée · non calculée | nulle part ailleurs |
| | | *meilleure adresse BAN rattachée à la parcelle — None si aucune (le front dit « Adresse non disponible », jamais un champ vide)* | | | | | |
| `parcelle_geometrie` | geometrie | Géométrie de la parcelle | cadastre_api_carto (PCI Parcellaire Express (DGFiP), édition courante) | passe-plat · src/labuse/api/app.py (parcels.geom / geom_2975) — table lue : parcels.geom (geom_simple pour les tuiles) | live | servie · non calculée | nulle part ailleurs |
| | | *le polygone cadastral de la parcelle (contour carte, fiche, PDF) — même table cadastre, même millésime partout (sonde lot 4.5)* | | | | | |
| `exposition_versant` | classe — domaine : Nord, Nord-Est, Est, Sud-Est, Sud, Sud-Ouest, Ouest, Nord-Ouest, plat | Exposition (versant) | rge_alti (RGE ALTI® (IGN) — édition courante) | passe-plat · src/labuse/faisabilite/exposition.py:exposition_parcelle — table lue : parcels (centroïde) → MNT RGE ALTI (gdaldem aspect, WMS GetMap) — calcul live, aucune valeur stockée | live | servie · non déterminée (la source ne dit pas) · non calculée | nulle part ailleurs |
| | | *orientation du versant (octant dominant) et pente moyenne autour de la parcelle, calculées à la volée sur le MNT RGE ALTI (gdaldem aspect, fenêtre 200 m, pondérée par la pente) ; terrain quasi plat → « plat », jamais une orientation inventée sur du bruit* | | | | | |
| `secteur_lieu_dit` | texte | Secteur (lieu-dit) | bd_nyme | passe-plat · src/labuse/api/app.py:_secteur_lieudit — table lue : lieux_dits (toponyme le plus proche par idu) | live | servie · non déterminée · non calculée | nulle part ailleurs |
| | | *toponyme du lieu-dit BD NYME le plus proche du centre de la parcelle (rayon borné 600 m ; None au-delà) — servi sous l'adresse de la fiche comme « Secteur : … »* | | | | | |

## Règlement d'urbanisme (zones + extraits)

*Robinet `fiche_parcelle_urbanisme` — route `/parcels/{idu}`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `reglement_plu_bloc` | liste | Règlement de la zone (extraits) | gpu_plu_api_carto (GPU/PLU par commune (révisions — détail en fiche)), sudocuh (Sudocuh — état au 31/12/2024 (Licence Ouverte 2.0)) | moteur `plu_destinations` · src/labuse/api/app.py:_reglement_plu_block — table lue : parcel_zone_plu + corpus règlements | live | servie (possiblement vide, dit) · non calculée | nulle part ailleurs |
| | | *zones PLU de la parcelle + extraits de règlement calibrés (corpus) — chaque extrait cite son document* | | | | | |
| `zone_plu_famille` | classe — domaine : U, AU, A, N | Zonage PLU (par type) | gpu_plu_api_carto (GPU/PLU par commune (révisions — détail en fiche)) | moteur `zone_servie` · src/labuse/faisabilite/zone_servie.py:zone_dominante | live | servie · non déterminée (la source ne dit pas) · non calculée | couche « Zonage PLU (par type) » · PDF « Pré-dossier PC (ZIP CERFA 13406*17) » · PDF « Lettre de zonage » |
| | | *famille (U/AU/A/N) de la zone DOMINANTE par surface de la parcelle (drapeau a_cheval, zone_parts servies) — moteur zone_servie (ZONE-1) ; ≠ zonage_commune (parts d'une commune)* | | | | | |
| `au_ouverture_statut` | classe — domaine : conditionnelle_operation, au_sous_plancher, declasse_au_fermee, declasse_au_statut_inconnu, générique | Statut d'ouverture de la zone AU | gpu_plu_api_carto (GPU/PLU par commune (révisions — détail en fiche)) | passe-plat · src/labuse/api/app.py:_au_ouverture_block — table lue : parcel_au_statut | live | servie · non déterminée (la source ne dit pas) · non calculée | nulle part ailleurs |
| | | *statut d'ouverture de la zone À Urbaniser (ouverte / sous condition d'opération d'ensemble / fermée) — moteur d'ouverture AU (règlement PLU calibré), motif cité* | | | | | |

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
| `tier_opportunite` | classe — domaine : brulante, chaude, a_creuser, reserve_fonciere, ecartee | Verdict · Classement servi | bd_topo (BD TOPO® V3 (IGN) — édition courante), cosia (CoSIA 2025 (PVA juil.-août 2025, 20 cm)), dvf (géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020), filosofi_carreaux (millésime 2021), sitadel (2026-07) | moteur `scoring_p_v2` · src/labuse/cli.py (build-mvt) ; parcel_flags | run | servie · non déterminée (la source ne dit pas) · non calculée | couche « Verdict · Classement servi » · outil « Étudier un bien » · PDF « Rapport Flash » · PDF « Dossier parcelle » |
| | | *tier du run servi (brûlante→froide), reconstruit à la bascule* | | | | | |
| `rang_tier` | nombre | Rang (dans le tier) | interne (aucun réservoir) | moteur `scoring_p_v2` · src/labuse/api/app.py:3283 | run | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *rang au sein du tier* | | | | | |

## Constructibilité

*Robinet `fiche_parcelle_constructibilite` — route `/parcels/{idu}`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `capacite_logements` | nombre | Capacité (logements) | bd_topo (BD TOPO® V3 (IGN) — édition courante), cosia (CoSIA 2025 (PVA juil.-août 2025, 20 cm)), gpu_plu_api_carto (GPU/PLU par commune (révisions — détail en fiche)) | moteur `potentiel` · src/labuse/faisabilite/potentiel.py:bloc_potentiel (table_rase.logements) | run | servie · non couverte (n sous seuil, dit) · non calculée | outil « Faisabilité » |
| | | *logements estimés du scénario table rase (après plafond de densité et stationnement) — bloc potentiel (EXPORTS-1 lot 3)* | | | | | |
| `sdp_residuelle_m2` | nombre | SDP résiduelle | cosia (CoSIA 2025 (PVA juil.-août 2025, 20 cm)), gpu_plu_api_carto (GPU/PLU par commune (révisions — détail en fiche)) | moteur `potentiel` · src/labuse/faisabilite/potentiel.py:bloc_potentiel (au_sol.sdp_residuelle_m2) | run | servie · non couverte (n sous seuil, dit) · non calculée | outil « Faisabilité » · outil « Densifier l'existant » · outil « Successions à venir » · outil « Blocs fonciers » · PDF « Dossier parcelle » |
| | | *max(0, SDP_max − SDP_existante) du run servi, sous garde de lecture zone dominante (A/N → 0 avec cause dite — ZONE-1)* | | | | | |
| `charge_fonciere_eur` | nombre | Charge foncière | cadastre_api_carto (PCI Parcellaire Express (DGFiP), édition courante), dvf (géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020) | moteur `bilan_promoteur` · src/labuse/faisabilite/bilan.py | live | servie · non couverte (n sous seuil, dit) · non calculée | outil « Faisabilité » · PDF « Dossier banquier » |
| | | *prix de sortie × SDP − coûts − marge (bilan à rebours)* | | | | | |
| `potentiel_verdict` | texte | Potentiel (verdict) | bd_topo (BD TOPO® V3 (IGN) — édition courante), cosia (CoSIA 2025 (PVA juil.-août 2025, 20 cm)), gpu_plu_api_carto (GPU/PLU par commune (révisions — détail en fiche)) | moteur `potentiel` · src/labuse/faisabilite/potentiel.py:bloc_potentiel (verdict) | run | servie · non déterminée · non calculée | PDF « Dossier parcelle » |
| | | *phrase composée du bloc « au sol / en hauteur / table rase » (moteur potentiel) — jamais un bloc creux (section omise si rien d'évaluable)* | | | | | |
| `prix_neuf_observe_eur_m2` | nombre | Prix du neuf — observé (€/m²) | dvf (géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020) | moteur `marche_service` · src/labuse/ingestion/dvf_prix_neuf.py:resolve_prix_neuf_marche (servi par faisabilite/bilan.py:resolve_prix_sortie_servi) | live | servie · non couverte (n sous seuil, dit) · non calculée | fiche « Prix & tendance » · PDF « Dossier banquier » |
| | | *neuf observé ≤ 3 ans après achèvement (resolve_prix_neuf_marche : bassin sourcé > secteur > commune > repli île) — USAGE RÉSERVÉ : bilan et exports (fiche, PDF) lisent CET id (arbitrage Q3 ; scission 0-bis)* | | | | | |
| `mixite_clause` | texte | Mixité sociale (clause) | gpu_plu_api_carto (GPU/PLU par commune (révisions — détail en fiche)) | moteur `bilan_promoteur` · src/labuse/faisabilite/bilan.py:_clause_mixite | live | servie · non déterminée · non calculée | PDF « Dossier banquier » |
| | | *déclenchement de la clause de mixité Art. 2 : SDP ≥ seuil OU logements ≥ seuil OU terrain > seuil (seuils des hypothèses de bilan, source déclarée sinon « Estimé ») — bloc unique servitude + déclenchement (EXPORTS-1 5.1)* | | | | | |
| `surface_vendable_m2` | nombre | Surface vendable (Estimé) | bd_topo (BD TOPO® V3 (IGN) — édition courante), cosia (CoSIA 2025 (PVA juil.-août 2025, 20 cm)), gpu_plu_api_carto (GPU/PLU par commune (révisions — détail en fiche)) | moteur `potentiel` · src/labuse/faisabilite/potentiel.py:bloc_potentiel (table_rase.vendable_m2) | run | servie · non couverte (n sous seuil, dit) · non calculée | PDF « Dossier parcelle » |
| | | *SHAB vendable du scénario table rase (fourchette du moteur commun) — distincte de capacite_logements* | | | | | |
| `surface_plancher_m2` | nombre | Surface de plancher créée (table rase) | bd_topo (BD TOPO® V3 (IGN) — édition courante), cosia (CoSIA 2025 (PVA juil.-août 2025, 20 cm)), gpu_plu_api_carto (GPU/PLU par commune (révisions — détail en fiche)) | moteur `potentiel` · src/labuse/faisabilite/potentiel.py:bloc_potentiel (table_rase.plancher_m2) | run | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *surface de plancher CRÉÉE par le scénario table rase (moteur commun, emprise constructible × occupation × niveaux) — c'est l'ASSIETTE de taxe_amenagement_estimee_eur ; distincte de capacite_logements ET de sdp_residuelle_m2 (potentiel au sol après bâti existant) : deux concepts, deux données, jamais deux chiffres pour un même nom (RECETTE-7 lot 0)* | | | | | |
| `marge_surelevation_m` | nombre | Marge de surélévation (au faîtage) | lidar_hd_mnh (Survol 11/08–11/10/2023 · MNx édités 13/03/2025), bd_topo (BD TOPO® V3 (IGN) — édition courante), gpu_plu_api_carto (GPU/PLU par commune (révisions — détail en fiche)) | moteur `potentiel` · src/labuse/faisabilite/potentiel.py:surelevation | run | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *hauteur restante sous la règle de FAÎTAGE de la zone, comparée au faîtage bâti mesuré (BD TOPO) — RECETTE-7 E1 : faîtage contre faîtage ; repli égout+toiture type avec incertitude* | | | | | |
| `taxe_amenagement_estimee_eur` | nombre | Taxe d'aménagement — taux communal (référence) | taxe_amenagement | moteur `taxe_amenagement` · src/labuse/api/app.py:_taxe_amenagement_block (taxe_amenagement.calculer, surface=0) | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *référence de taxe d'aménagement servie sur la fiche/le Dossier : le TAUX communal public (daté) et la part départementale de droit (plafond 2,5 %) — SANS montant en euros, car la taxe porte sur la surface de plancher CRÉÉE par un projet (art. L331 c. urb.) et aucun projet n'est saisi à ce stade (RECETTE-8 W1/W2 : avant, elle imprimait « 22 469 € pour 458 m² de table rase », un scénario que personne n'avait choisi). Le montant chiffré est au Financier, sur la SDP du projet. Taux communal PUBLIC si connu, sinon « non renseigné » (jamais inventé)* | | | | | |
| `rtaa_exigences` | liste | Rappel RTAA DOM (exigences de conception) | rtaa_dom | passe-plat · src/labuse/api/modules.py:faisabilite_sens1 (load_yaml_config rtaa_dom) — table lue : config/rtaa_dom.yaml | live | servie (possiblement vide, dit) · non calculée | outil « Faisabilité » |
| | | *exigences réglementaires de conception DOM (aération, protection solaire, eau chaude solaire) servies en rappel dans la Faisabilité — règles portées par config/rtaa_dom.yaml, vérifiées sur Légifrance, hors scoring* | | | | | |

## Le bien

*Robinet `fiche_parcelle_le_bien` — route `/parcels/{idu}`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `emprise_batie_m2` | nombre | Emprise bâtie | bd_topo (BD TOPO® V3 (IGN) — édition courante), cosia (CoSIA 2025 (PVA juil.-août 2025, 20 cm)) | moteur `bati_revele` · src/labuse/bati.py:le_bien_block (BD TOPO au sol ; CoSIA parcel_bati_revele en note) | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *emprise au sol du bâti — empreinte vecteur BD TOPO (somme des intersections), cohérente avec le nombre de bâtiments ; CoSIA servi À PART quand il détecte du bâti hors BD TOPO* | | | | | |
| `hauteur_bati_m` | nombre | Hauteur du bâti | bd_topo (BD TOPO® V3 (IGN) — édition courante), lidar_hd_mnh (Survol 11/08–11/10/2023 · MNx édités 13/03/2025) | moteur `potentiel` · src/labuse/faisabilite/potentiel.py:_hauteur_bati_m | live | servie · non couverte (n sous seuil, dit) · non calculée | couche « Bâti 3D (extrusion, hauteur) » |
| | | *hauteur du bâti principal — max des bâtiments intersectants (BD TOPO) en fiche/potentiel ; l'extrusion 3D de la carte PRÉFÈRE le faîtage LiDAR HD mesuré (batiment_hauteur_lidar.faitage_m, flag `lidar` par bâtiment), repli BD TOPO* | | | | | |
| `n_batiments` | nombre | Nombre de bâtiments | bd_topo (BD TOPO® V3 (IGN) — édition courante) | moteur `bati_revele` · src/labuse/bati.py:le_bien_block (bati.fiche_block — BD TOPO) | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *compte des bâtiments de la parcelle (BD TOPO, intersection ≥ 10 m²)* | | | | | |
| `surface_libre_sol_m2` | nombre | Surface au sol libre | bd_topo (BD TOPO® V3 (IGN) — édition courante), cosia (CoSIA 2025 (PVA juil.-août 2025, 20 cm)), cadastre_api_carto (PCI Parcellaire Express (DGFiP), édition courante) | moteur `bati_revele` · src/labuse/bati.py:le_bien_block (surface parcelle − emprise bâtie) | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *surface au sol non bâtie restante (surface parcelle − emprise bâtie), plancher à 0* | | | | | |
| `nature_toit` | classe — domaine : plat, monopente, double_pente, croupe_complexe | Nature du toit | lidar_hd_mnh (Survol 11/08–11/10/2023 · MNx édités 13/03/2025), bd_topo (BD TOPO® V3 (IGN) — édition courante) | moteur `solaire` · src/labuse/solaire_toiture.py:analyse_toiture (cache toiture_lidar, lecture fiche) | live | servie · non déterminée (la source ne dit pas) · non calculée | nulle part ailleurs |
| | | *forme du toit du plus grand bâtiment lue sur le LiDAR HD (MNH), servie ≥ 0,70 de confiance sinon « non déterminée — pans non nets » (RETOURS-15 U5)* | | | | | |
| `pente_toit_deg` | nombre | Pente du toit | lidar_hd_mnh (Survol 11/08–11/10/2023 · MNx édités 13/03/2025) | moteur `solaire` · src/labuse/solaire_toiture.py:analyse_toiture (cache toiture_lidar, lecture fiche) | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *pente médiane du toit du plus grand bâtiment (degrés), mesure directe LiDAR HD (MNH) — servie même sous le seuil de forme* | | | | | |
| `dpe_connu` | texte | DPE connu (étiquette, année) | dpe_ademe (2026) | passe-plat · src/labuse/api/app.py:_dpe_connu_block — table lue : dpe_records | live | servie · non déterminée · non calculée | nulle part ailleurs |
| | | *dernier DPE connu du bâtiment rattaché (étiquette énergie/GES, date, type de bâtiment) + nombre de DPE — info fiche SEULE, jamais un signal scoring ni un ciblage (M71 B1 : DPE neuf en DROM) ; DONNEES-1 lot 2 : la ligne ne s'affiche QUE si un DPE existe (non obligatoire en DROM, ~0,3 % de couverture — aucune ligne « non déterminé »)* | | | | | |
| `rnb_batiments_liste` | nombre | Identifiants RNB des bâtiments | rnb | moteur `bati_revele` · src/labuse/bati.py:le_bien_block (RNB actifs ∩ parcelle — rnb_batiments) | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *identifiant national (RNB) de chaque bâtiment ACTIF dont l'emprise recoupe la parcelle, du plus grand recouvrement au plus petit, avec le lien officiel rnb.beta.gouv.fr* | | | | | |
| `ban_plus_adresses_bati` | nombre | Adresses liées au bâti (BAN PLUS) | ban_plus | moteur `bati_revele` · src/labuse/bati.py:le_bien_block (liens adresse↔bâtiment — ban_plus_liens) | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *nombre de liens officiels adresse ↔ bâtiment de la parcelle (BAN PLUS, IGN) — la clé qui relie l'adresse BAN au bâtiment BD TOPO et, par le RNB local, à l'ID-RNB* | | | | | |
| `part_artificialisee_pct` | nombre | Part artificialisée (OCS GE) | ocsge (OCS GE 2.0 D974 — 2017 + 2022 ; diff artif 2025-09-16) | moteur `bati_revele` · src/labuse/bati.py:le_bien_block (parcel_ocsge — précalcul ingestion/ocsge.py) | live | servie · non couverte (n sous seuil, dit) · non calculée | couche « Artificialisation (OCS GE) » |
| | | *part de la parcelle artificialisée d'après l'OCS GE 2022 (matrice du décret 2023-1096, étape 1 — avant lissage des seuils réglementaires) — donnée d'îlot, jamais la précision cadastrale ; n'entre pas dans le score* | | | | | |
| `usage_sol_dominant` | classe | Usage du sol dominant (OCS GE) | ocsge (OCS GE 2.0 D974 — 2017 + 2022 ; diff artif 2025-09-16) | moteur `bati_revele` · src/labuse/bati.py:le_bien_block (parcel_ocsge — précalcul ingestion/ocsge.py) | live | servie · non déterminée (la source ne dit pas) · non calculée | nulle part ailleurs |
| | | *code d'usage OCS GE dominant par aire intersectée (millésime 2022) — donnée d'îlot* | | | | | |
| `cosia_detecte_m2` | nombre | Bâti détecté CoSIA (hors BD TOPO) | cosia (CoSIA 2025 (PVA juil.-août 2025, 20 cm)) | passe-plat · src/labuse/bati.py:le_bien_block (cosia_detecte_m2) — table lue : parcel_bati_revele.emprise_cosia_m2 | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *surface de bâti détectée par CoSIA au-delà de l'empreinte BD TOPO (parcel_bati_revele), servie À PART car CoSIA sur-détecte à la maille parcelle ; None tant qu'il n'y a pas de sur-détection nette (> emprise BD TOPO + 50 m²)* | | | | | |
| `part_impermeabilisee_cosia_pct` | nombre | Part imperméabilisée (CoSIA) | cosia (CoSIA 2025 (PVA juil.-août 2025, 20 cm)) | passe-plat · src/labuse/bati.py:le_bien_block (_cosia_couverture — part_impermeabilisee_pct) — table lue : parcel_cosia_couverture | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *part de la parcelle scellée (bâti + revêtement imperméable + piscine + serre) mesurée par CoSIA à 20 cm, Σ surface de ces classes / contenance — complète l'artificialisation OCS GE d'îlot (≠ imperméabilisé), ne recoupe aucune ligne OCS GE affichée ; hors score* | | | | | |
| `part_vegetalisee_cosia_pct` | nombre | Part végétalisée/boisée (CoSIA) | cosia (CoSIA 2025 (PVA juil.-août 2025, 20 cm)) | passe-plat · src/labuse/bati.py:le_bien_block (_cosia_couverture — part_vegetalisee_boisee_pct) — table lue : parcel_cosia_couverture | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *part de la parcelle en végétation vivante (feuillu, conifère, broussaille, pelouse, culture, vigne) mesurée par CoSIA à 20 cm, Σ surface de ces classes / contenance — donnée de parcelle, aucune ligne OCS GE affichée ne la donne ; hors score* | | | | | |
| `part_sol_nu_cosia_pct` | nombre | Part sol nu (CoSIA) | cosia (CoSIA 2025 (PVA juil.-août 2025, 20 cm)) | passe-plat · src/labuse/bati.py:le_bien_block (_cosia_couverture — part_sol_nu_pct) — table lue : parcel_cosia_couverture | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *part de la parcelle en terre nue (sol nu, terre labourée) mesurée par CoSIA à 20 cm, Σ surface de ces classes / contenance — donnée de parcelle, aucune ligne OCS GE affichée ne la donne ; hors score* | | | | | |
| `etablissements_parcelle_liste` | liste | Établissements sur la parcelle | sirene_etablissements (SIRENE géolocalisé — publication mensuelle INSEE), ban (2026), bodacc (2026) | passe-plat · src/labuse/api/app.py:_etablissements_block — table lue : etablissement_parcelle + sirene_etablissements | live | servie (possiblement vide, dit) · non calculée | nulle part ailleurs |
| | | *établissements SIRENE rattachés à la parcelle par l'adresse BAN (précision « adresse » seulement) — nom, NAF fin, tranche d'effectif, état + régime collectif BODACC ; nom masqué si non diffusible* | | | | | |

## Risques et protections

*Robinet `fiche_parcelle_risques` — route `/parcels/{idu}`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `n_vigilances` | nombre | Vigilances | abf_merimee, deal_ppr (PPR/PPRL approuvés 2011–2026 (arrêtés, DEAL Lizmap)), georisques_mvt, georisques_icpe, georisques_cavites, georisques_ssp, znieff_inpn (INPN, mise à jour 29/08/2025) | moteur `cascade` · src/labuse/api/anti_fiche.py (motifs RÉDHIBITOIRE/VIGILANCE de la cascade) | run | servie · non couverte (n sous seuil, dit) · non calculée | outil « Pièges et risques » |
| | | *compte des couches cascade en SOFT_FLAG/HARD_EXCLUDE* | | | | | |
| `aleas_parcelle_liste` | liste | Aléas de la parcelle | deal_ppr (PPR/PPRL approuvés 2011–2026 (arrêtés, DEAL Lizmap)), georisques_mvt, georisques_azi_tri (GASPAR azi+tri par commune (07/09/2026)) | moteur `cascade` · src/labuse/api/app.py:_aleas_block (lignes servies layer='risques') | run | servie (possiblement vide, dit) · non calculée | nulle part ailleurs |
| | | *liste des aléas touchant la parcelle (nature, niveau, part concernée, référence de l'arrêté PPR pour un aléa réglementaire) — dérivée de la cascade servie, accord garanti avec Pièges et risques* | | | | | |
| `sar_divergence` | texte | Divergence SAR (indication) | sar_region (couche SIG officielle NON diffusée (recherche 07/09/2026)) | moteur `cascade` · src/labuse/cascade/layers/phase1.py:SarLayer | run | servie · non déterminée · non calculée | nulle part ailleurs |
| | | *warning « zone PLU U/AU ∩ vocation naturelle/agricole du proxy de vocations Région » — indication non opposable (le SAR officiel n'est pas diffusé en vecteur), jamais un malus* | | | | | |
| `endiguement_zone_protegee` | classe — domaine : dans, hors | Système d'endiguement | endiguement (EDD Hydrétudes déc. 2024 (attrs Source par zone)) | passe-plat · src/labuse/cascade/layers/fiche_couches2.py (endiguement) — table lue : spatial_layers (kind=endiguement) | live | servie · non déterminée (la source ne dit pas) · non calculée | nulle part ailleurs |
| | | *la parcelle est-elle dans une ZONE PROTÉGÉE derrière une digue — information : la protection n'est pas une garantie d'inconstructibilité mais un fait à instruire (aléa résiduel)* | | | | | |

## Marché et secteur

*Robinet `fiche_parcelle_marche` — route `/parcels/{idu}`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `prix_terrain_secteur_eur_m2` | nombre | Terrain nu secteur | cadastre_api_carto (PCI Parcellaire Express (DGFiP), édition courante), dvf (géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020) | moteur `sector_price` · src/labuse/faisabilite/bilan.py (sector_price) | live | servie · non couverte (n sous seuil, dit) · non calculée | PDF « Rapport Flash » · PDF « Dossier banquier » · PDF « Argumentaire » |
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
| `parc_social_rpls_logements` | nombre | Parc social (logements RPLS) | rpls_sdes | passe-plat · src/labuse/api/app.py (marche_secteur — rpls_commune) — table lue : rpls_commune (nb_logements, construct_median) | live | servie · non couverte (n sous seuil, dit) · non calculée | fiche « Population & logement » |
| | | *nombre de logements locatifs sociaux de la commune (RPLS SDES, millésime 01/01/2025) — contexte marché de la fiche commune, du Flash et du PDF, jamais un signal scoring* | | | | | |
| `radar_annonces_liste` | liste | Annonces Radar de la parcelle | radar_pige (Collecte manuelle — biens en vente (faits + lien)), dvf (géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020) | moteur `marche_pige` · src/labuse/api/app.py:_radar_annonces_block (pige_biens ⋈ pige_faits + v_parcel_dvf_last) | live | servie (possiblement vide, dit) · non calculée | nulle part ailleurs |
| | | *annonces Radar VALIDÉES rattachées à la parcelle (date, prix demandé, statut en cours/retirée/vendue, lien fiche annonce) ; pour une annonce en cours avec mutation DVF, l'écart prix demandé vs acté (concept ecart_demande_acte_pct, maille parcelle)* | | | | | |

## Réseaux et accès

*Robinet `fiche_parcelle_reseaux` — route `/parcels/{idu}`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `pente_deg` | nombre | Pente | rge_alti (RGE ALTI® (IGN) — édition courante) | passe-plat · src/labuse/api/app.py:3283 (viabilisation) — table lue : parcel_terrain.pente_moy_deg | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *pente moyenne parcelle (RGE ALTI), flag terrassement* | | | | | |
| `piscine_m2` | nombre | Piscine ~m² | bd_ortho (BD ORTHO IGN 974 — millésime 2025 (piscine, 90,7 %)) | passe-plat · src/labuse/api/app.py:3283 — table lue : parcel_equipements.piscine_surface_m2 | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *surface détectée parcel_equipements (BD ORTHO 2025)* | | | | | |
| `distance_arret_m` | nombre | Transport public — au plus proche | gtfs_pan (7 jeux PAN, màj 2025-12-29 → 2026-08-17), osm_transport (extraction Overpass (base OSM vivante, ODbL)) | moteur `parcelle_proximites` · src/labuse/registre/moteurs/parcelle.py:plus_proche | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *plus proche arrêt/pôle (distance en m)* | | | | | |
| `tcsp_stationnement_allege` | classe — domaine : sous_800m, au_dela, aucune_station | Stationnement allégé (TCSP, L151-36) | gtfs_pan (7 jeux PAN, màj 2025-12-29 → 2026-08-17), osm_transport (extraction Overpass (base OSM vivante, ODbL)) | moteur `parcelle_proximites` · src/labuse/api/app.py:_proximites_block (drapeau sous_800m, L151-36 strict) | live | servie · non déterminée (la source ne dit pas) · non calculée | nulle part ailleurs |
| | | *la parcelle est-elle à MOINS de 800 m (à vol d'oiseau) d'une station de transport en site propre — plafond d'une aire de stationnement par logement (0,5 pour le logement social), opposable au PLU (art. L151-34 à 36) ; distance et station nommées* | | | | | |
| `part_logements_egout_pct` | nombre | Logements raccordés à l'égout | insee_rp2022_egoul (RP2022 — fichier détail Logements, publié le 16/10/2025 (INSEE)), gpu_zonage_assainissement (GPU — idurba par commune ; SIG 4/24 au 11/07/2026) | moteur `anc` · src/labuse/anc_service.py:statut_anc (producteur nommé, délégation) | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *part des logements raccordés au tout-à-l'égout (INSEE RP2022 EGOUL, maille IRIS, repli commune) — le TAUX, jamais un verdict* | | | | | |
| `viabilisation_verdict` | texte | Viabilisation (faisceau) | bd_topo (BD TOPO® V3 (IGN) — édition courante), rge_alti (RGE ALTI® (IGN) — édition courante), parkings_osm_aper | passe-plat · src/labuse/api/app.py:_viabilisation_block — table lue : parcel_viabilisation (faisceau) | live | servie · non déterminée · non calculée | nulle part ailleurs |
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
| `type_proprietaire` | classe — domaine : personne morale, personne physique non recensée | Propriétaire (type) | dgfip_parcelles_pm (Panel millésimes 2019→2025 (situation 1ᵉʳ janvier)) | passe-plat · src/labuse/api/app.py:3586 (proprietaire_moral, parcelle_personne_morale) ; garde de lecture cascade/context.py (EXPORTS-1 5.4) — table lue : parcelle_personne_morale.denomination (millésime 2025) | live | servie · non déterminée (la source ne dit pas) · non calculée | outil « Successions à venir » · outil « Blocs fonciers » |
| | | *personne morale (dénomination) / personne physique non recensée — fichier PM parcelle_personne_morale, millésime 2025 (même assiette que la carte — EXPORTS-1 5.4 : la ligne « non renseigné » stockée au run est rebranchée sur le fichier PM à la lecture)* | | | | | |
| `proprietaire_timeline_liste` | liste | Historique propriétaire (millésimes PM) | dgfip_parcelles_pm (Panel millésimes 2019→2025 (situation 1ᵉʳ janvier)) | moteur `proprietaire_historique` · src/labuse/proprietaire_historique.py:historique — table lue : pm_proprietaires_millesimes ∪ parcelle_personne_morale | live | servie (possiblement vide, dit) · non calculée | nulle part ailleurs |
| | | *timeline unifiée versionné∪servi du fichier PM (2019→2025), diff CONSTAT — servi jamais écrasé* | | | | | |
| `evenements_proprietaire_liste` | liste | Événements propriétaire (BODACC) | bodacc (2026), sirene_etablissements (SIRENE géolocalisé — publication mensuelle INSEE), recherche_entreprises_dinum | moteur `v_score` · src/labuse/api/app.py:_q_v2_fiche (score_v, evenement) — table lue : parcel_v_score + bodacc_* | live | servie (possiblement vide, dit) · non calculée | nulle part ailleurs |
| | | *événements datés du score V (procédures, radiations) — faits publics, chacun sourcé* | | | | | |

## Division (copropriétés/lots)

*Robinet `fiche_parcelle_division` — route `/parcels/{idu}`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `divisible_classe` | classe — domaine : candidate, non_candidate, non_recalculee | Division (candidate) | cadastre_api_carto (PCI Parcellaire Express (DGFiP), édition courante), cosia (CoSIA 2025 (PVA juil.-août 2025, 20 cm)), gpu_plu_api_carto (GPU/PLU par commune (révisions — détail en fiche)) | moteur `division_or` · src/labuse/api/app.py:2692-2696 | run | servie · non déterminée (la source ne dit pas) · non calculée | nulle part ailleurs |
| | | *présence dans division_or_candidates — run figé q_v10, workflow de revue* | | | | | |
| `coproprietes_liste` | liste | Copropriétés (RNIC) | rnic_anah | passe-plat · src/labuse/api/app.py:_q_v2_fiche (coproprietes) — table lue : rnic_coproprietes | live | servie (possiblement vide, dit) · non calculée | nulle part ailleurs |
| | | *copropriétés immatriculées rattachées à la parcelle (lots, syndic) — RNIC/ANAH* | | | | | |

## Solaire (rosace, productible)

*Robinet `fiche_parcelle_solaire` — route `/parcels/{idu}`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `prod_spec_kwh_kwc` | nombre | Productible | bd_topo (BD TOPO® V3 (IGN) — édition courante), pvgis (PVGIS v5.3 · modèle SARAH3 (relevé au run du builder solaire)), lidar_hd_mnh (Survol 11/08–11/10/2023 · MNx édités 13/03/2025), bd_ortho_irc | moteur `solaire` · src/labuse/api/modules.py:prospection_solaire | run | servie · non couverte (n sous seuil, dit) · non calculée | outil « Prospection solaire » · outil « Toits bien exposés » · fiche « Fiche soleil (photo toit + rosace) » |
| | | *productible PVGIS SARAH3 gelé au run du builder (parcel_solar)* | | | | | |

## Confiance données

*Robinet `fiche_parcelle_confiance` — route `/parcels/{idu}`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `verdict_icd` | texte | Confiance données | interne (aucun réservoir) | moteur `cascade` · src/labuse/api/app.py:3283 (bloc icd) | run | servie · non déterminée · non calculée | nulle part ailleurs |
| | | *verdict de complétude des couches + liste des manquants* | | | | | |
