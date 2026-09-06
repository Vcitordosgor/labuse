# FICHES — donnée par donnée (commune · annonce · propriétaire · soleil)

*Généré du registre le 2026-09-06 par `labuse registre fiche autres` (même format que FICHE-PARCELLE-DONNEES.md, plus court).*

# Fiche commune

## Règles d'urbanisme

*Robinet `fiche_commune_regles_urbanisme` — route `/communes/{c}/contexte`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `statut_plu` | classe — domaine : RNU, à jour, en révision, en élaboration, en modification, document local | Règles d'urbanisme (statut) | gpu_plu_api_carto (GPU/PLU par commune (révisions — détail en fiche)), sudocuh (Sudocuh — état au 31/12/2024 (Licence Ouverte 2.0)) | moteur `plu_destinations` · src/labuse/api/fiche_commune.py:137-144 | live | servie · non déterminée (la source ne dit pas) · non calculée | nulle part ailleurs |
| | | *RNU (registre) l'emporte ; sinon statut du registre veille_plu* | | | | | |

## Enveloppe ZAN

*Robinet `fiche_commune_zan` — route `/communes/{c}/contexte`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `zan_reste_ha` | nombre | Enveloppe ZAN (reste) | enaf_cerema | moteur `commune_compteurs` · src/labuse/api/rarete.py:compute_rarete (reste_zan_ha — producteur nommé, délégation) | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *enveloppe restante estimée depuis conso ENAF* | | | | | |

## Logement social — SRU

*Robinet `fiche_commune_sru` — route `/communes/{c}/contexte`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `taux_lls_pct` | nombre | Taux LLS | sru_dhup | passe-plat · src/labuse/api/fiche_commune.py (commune_contexte_sru) — table lue : commune_contexte_sru.taux_lls | live | servie · non couverte (n sous seuil, dit) · non calculée | Copilote « Contexte d'une commune (SRU, marché) » |
| | | *taux LLS de l'inventaire SRU* | | | | | |
| `deficit_sru_pts` | nombre | Déficit SRU (objectif − taux LLS, points) | sru_dhup | passe-plat · src/labuse/api/comparateur.py:56 — table lue : commune_contexte_sru (objectif_pct, taux_lls) | live | servie · non couverte (n sous seuil, dit) · non calculée | outil « Comparer des parcelles » · outil « Communes » · outil « Comparaison communes » |
| | | *greatest(objectif_pct − taux_lls, 0) depuis commune_contexte_sru* | | | | | |

## Permis & délais

*Robinet `fiche_commune_permis` — route `/communes/{c}/contexte`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `permis_12m_n` | nombre | Permis de la commune sur 12 mois | sitadel (2026-07) | moteur `commune_compteurs` · src/labuse/registre/moteurs/commune.py:compte_permis_commune | live | servie · non couverte (n sous seuil, dit) · non calculée | outil « Ce qu'ils construisent » · outil « Permis » · outil « Radar permis » · Copilote « Nombre de permis accordés » |
| | | *count sitadel_permits de la commune, fenêtre 12 mois, sans rayon (commune entière)* | | | | | |
| `velocite_delai_median_mois` | nombre | Vélocité admin (délai médian dépôt→autorisation, mois) | sitadel (2026-07) | moteur `commune_compteurs` · src/labuse/registre/moteurs/commune.py:indicateurs_communes (CTE velo) | live | servie · non couverte (n sous seuil, dit) · non calculée | outil « Comparer des parcelles » · outil « Communes » · outil « Comparaison communes » · outil « Permis » · outil « Radar permis » · Copilote « Délai médian d'instruction (commune) » |
| | | *percentile_cont(0.5) sur m10_permit_delais famille logements* | | | | | |
| `point_mort_n` | nombre | Permis au point mort | sitadel (2026-07) | moteur `commune_compteurs` · src/labuse/registre/moteurs/commune.py:permis_point_mort | live | servie · non couverte (n sous seuil, dit) · non calculée | outil « Permis au point mort » |
| | | *permis autorisés sans DOC/DAACT dans la fenêtre* | | | | | |

## Programme local — PLH

*Robinet `fiche_commune_plh` — route `/communes/{c}/contexte`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `plh_objectif_logements_an` | nombre | Objectif logements/an | plh_epci | passe-plat · src/labuse/api/fiche_commune.py (plh_epci) — table lue : plh_epci (objectif logements/an, par EPCI) | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *objectif PLH, chaque chiffre porte sa référence doc+page* | | | | | |

## Prix & tendance

*Robinet `fiche_commune_prix` — route `/communes/{c}/contexte`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `prix_ancien_median_eur_m2` | nombre | €/m² ancien | dvf (géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020) | moteur `marche_service` · src/labuse/api/moteurs.py:prix_ancien_communes (partagé PDF baromètre) | live | servie · non couverte (n sous seuil, dit) · non calculée | outil « Comparer des parcelles » · outil « Communes » · outil « Comparaison communes » · outil « Évolution du marché » · Copilote « Marché immobilier d'une commune » |
| | | *médiane DVF ventes strictes, filtre de retenue du baromètre* | | | | | |
| `prix_neuf_vefa_acte_eur_m2` | nombre | Prix du neuf — VEFA à l'acte (€/m²) | dvf (géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020) | moteur `marche_service` · src/labuse/ingestion/dvf_marche.py:neuf_vefa_commune (via marche_service, profil neuf_vefa) | live | servie · non couverte (n sous seuil, dit) · non calculée | outil « Comparer des parcelles » · outil « Communes » · outil « Comparaison communes » |
| | | *médiane VEFA déclarée à l'acte (neuf_vefa_commune, live, 36 mois) — USAGE RÉSERVÉ : le scoring (score_e) lit CET id ; affiché comparateur/communes/fiche commune sous libellé VEFA (scission 0-bis : ≠ prix_neuf_observe_eur_m2, jamais l'un sous le libellé de l'autre)* | | | | | |
| `mutations_12m_n` | nombre | Mutations 12 mois | dvf (géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020) | moteur `commune_compteurs` · src/labuse/registre/moteurs/commune.py:mutations_12m | live | servie · non couverte (n sous seuil, dit) · non calculée | outil « Évolution du marché » |
| | | *count dvf_mutations sur les 12 derniers mois DE DONNÉES (pas calendaire)* | | | | | |

## Terrain nu

*Robinet `fiche_commune_terrain_nu` — route `/communes/{c}/contexte`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `prix_terrain_zone_eur_m2` | nombre | Terrain nu (zone U / AU) | dvf (géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020), gpu_plu_api_carto (GPU/PLU par commune (révisions — détail en fiche)) | moteur `marche_service` · src/labuse/faisabilite/marche_commune.py:ligne2_terrain_zone | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *médiane DVF terrain nu par famille de zone, seuil 10 ventes* | | | | | |

## Annonces en cours — Radar

*Robinet `fiche_commune_annonces` — route `/communes/{c}/contexte`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `annonces_actives_n` | nombre | Biens en vente | radar_pige (Collecte manuelle — biens en vente (faits + lien)) | moteur `marche_pige` · src/labuse/pige/marche.py:71-91 | live | servie · non couverte (n sous seuil, dit) · non calculée | outil « Radar » · outil « Marché » |
| | | *count pige_biens actifs a_qualifier=false ; n<5 → NULL insuffisant* | | | | | |
| `prix_demande_median_eur_m2` | nombre | Prix demandé (médiane) | radar_pige (Collecte manuelle — biens en vente (faits + lien)) | moteur `marche_pige` · src/labuse/pige/marche.py:71-91 | live | servie · non couverte (n sous seuil, dit) · non calculée | outil « Radar » · outil « Marché » · fiche « Fiche bien (Radar) » |
| | | *médiane des prix affichés terrain/bâti, n<5 masqué* | | | | | |
| `ecart_demande_acte_pct` | nombre | Écart demandé/acté | dvf (géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020), radar_pige (Collecte manuelle — biens en vente (faits + lien)) | moteur `marche_pige` · src/labuse/api/fiche_commune.py:16-58 (comparable, partagé) | live | servie · non couverte (n sous seuil, dit) · non calculée | outil « Marché » |
| | | *médiane demandé vs médiane DVF actée, servi dès SEUIL_N biens* | | | | | |

## Loyers

*Robinet `fiche_commune_loyers` — route `/communes/{c}/contexte`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `loyer_median_eur_m2` | nombre | Loyer médian | interne (aucun réservoir) | moteur `loyers` · src/labuse/api/fiche_commune.py (loyer) | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *estimation locative loyers.py — entrées à confirmer (DOUTE)* | | | | | |

## Foncier repéré

*Robinet `fiche_commune_foncier` — route `/communes/{c}/contexte`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `n_parcelles_commune` | nombre | N parcelles | cadastre_api_carto (PCI Parcellaire Express (DGFiP) — « latest » ingérée) | moteur `commune_compteurs` · src/labuse/registre/moteurs/commune.py:compte_parcelles_commune | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *count parcels par commune* | | | | | |
| `stock_opportunites` | nombre | Stock d'opportunités (brûlantes + chaudes) | cosia (CoSIA 2025 (PVA juil.-août 2025, 20 cm)), dvf (géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020), sitadel (2026-07) | moteur `scoring_p_v2` · src/labuse/api/comparateur.py:47-50 | run | servie · non couverte (n sous seuil, dit) · non calculée | outil « Comparer des parcelles » · outil « Communes » · outil « Comparaison communes » |
| | | *count tiers brûlante+chaude au run servi, par insee* | | | | | |
| `n_densifiables` | nombre | Parcelles densifiables | interne (aucun réservoir) | moteur `renouvellement` · src/labuse/api/app.py:renouvellement_liste | run | servie · non couverte (n sous seuil, dit) · non calculée | outil « Densifier l'existant » |
| | | *count parcel_renouvellement au run servi* | | | | | |

## Zonage

*Robinet `fiche_commune_zonage` — route `/communes/{c}/contexte`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `part_zone_U_pct` | nombre | Zonage — U | cadastre_api_carto (PCI Parcellaire Express (DGFiP) — « latest » ingérée), gpu_plu_api_carto (GPU/PLU par commune (révisions — détail en fiche)) | moteur `zonage_commune` · src/labuse/registre/moteurs/zonage.py:parts_zonage_surface | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *surface cadastrée U / surface zonée totale (somme=100 %)* | | | | | |
| `part_zone_AU_pct` | nombre | Zonage — AU | cadastre_api_carto (PCI Parcellaire Express (DGFiP) — « latest » ingérée), gpu_plu_api_carto (GPU/PLU par commune (révisions — détail en fiche)) | moteur `zonage_commune` · src/labuse/registre/moteurs/zonage.py:parts_zonage_surface | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *surface AU / surface zonée* | | | | | |
| `part_zone_A_pct` | nombre | Zonage — A | cadastre_api_carto (PCI Parcellaire Express (DGFiP) — « latest » ingérée), gpu_plu_api_carto (GPU/PLU par commune (révisions — détail en fiche)) | moteur `zonage_commune` · src/labuse/registre/moteurs/zonage.py:parts_zonage_surface | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *surface A / surface zonée (Saint-Paul : 35,8 % — la part en PARCELLES vaut 17,8 %)* | | | | | |
| `part_zone_N_pct` | nombre | Zonage — N | cadastre_api_carto (PCI Parcellaire Express (DGFiP) — « latest » ingérée), gpu_plu_api_carto (GPU/PLU par commune (révisions — détail en fiche)) | moteur `zonage_commune` · src/labuse/registre/moteurs/zonage.py:parts_zonage_surface | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *surface N / surface zonée (Saint-Paul : 47,2 % — la part en PARCELLES vaut 6,8 %)* | | | | | |

## Risques

*Robinet `fiche_commune_risques` — route `/communes/{c}/contexte`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `ppr_pct` | nombre | PPR (part des parcelles) | deal_ppr (PPR/PPRL approuvés 2011–2026 (arrêtés, DEAL Lizmap)) | moteur `commune_compteurs` · src/labuse/registre/moteurs/commune.py:pct_parcelles_couche | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *part des parcelles de la commune intersectant la couche ppr* | | | | | |
| `catnat_n` | nombre | Arrêtés CatNat | interne (aucun réservoir) | passe-plat · src/labuse/api/fiche_commune.py — table lue : catnat_arretes (count par insee) | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *count catnat_arretes* | | | | | |

## Population & logement

*Robinet `fiche_commune_population` — route `/communes/{c}/contexte`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `habitants_n` | nombre | Habitants | filosofi_carreaux (millésime 2021), insee_rp_logement | passe-plat · src/labuse/api/fiche_commune.py:123 (population) — table lue : filosofi_carreaux_200m (Σ ind des carreaux de la commune) | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *population INSEE/Filosofi commune* | | | | | |
| `vacance_pct` | nombre | Vacance | insee_rp_logement | moteur `commune_compteurs` · src/labuse/registre/moteurs/commune.py:vacance_pct | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *100 × vacants / logements (RP)* | | | | | |
| `autres_loges_pct` | nombre | logés gratuitement | insee_rp_logement | moteur `commune_compteurs` · src/labuse/registre/moteurs/commune.py:autres_loges_pct | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *100 − locataires_pct − proprietaires_pct (INSEE RP), arrondi 0,1, plancher 0 — calculé au SERVEUR (lot 2.4, avant : ContextePanel.tsx:526)* | | | | | |

## Quartiers prioritaires

*Robinet `fiche_commune_qpv` — route `/communes/{c}/contexte`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `qpv_n` | nombre | QPV | qpv_2024 (génération 2024) | moteur `commune_compteurs` · src/labuse/registre/moteurs/commune.py:qpv_commune | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *count QPV intersectant la commune* | | | | | |

## Mairie & service urbanisme

*Robinet `fiche_commune_mairie` — route `/communes/{c}/contexte`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `mairie_coordonnees` | texte | Mairie & service urbanisme (coordonnées) | annuaire_service_public (annuaire service-public.fr — 24 mairies (OUTILS K2)) | passe-plat · src/labuse/ingestion/mairies.py (bloc MAIRIE) — table lue : mairies | live | servie · non déterminée · non calculée | nulle part ailleurs |
| | | *adresse, téléphone, courriel et horaires de la mairie — champ manquant = ABSENT, jamais inventé* | | | | | |

# Fiche annonce (Radar)

## Fiche bien (Radar)

*Robinet `fiche_annonce` — route `/radar/biens/{id}`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `prix_demande_eur` | nombre | Prix demandé | radar_pige (Collecte manuelle — biens en vente (faits + lien)) | passe-plat · src/labuse/pige/client.py — table lue : pige_faits.prix | live | servie · non couverte (n sous seuil, dit) · non calculée | nulle part ailleurs |
| | | *fait déclaré de l'annonce (pige_faits), jamais le texte* | | | | | |
| `prix_demande_median_eur_m2` | nombre | Prix demandé (médiane) | radar_pige (Collecte manuelle — biens en vente (faits + lien)) | moteur `marche_pige` · src/labuse/pige/marche.py:71-91 | live | servie · non couverte (n sous seuil, dit) · non calculée | outil « Radar » · outil « Marché » · fiche « Annonces en cours — Radar » |
| | | *médiane des prix affichés terrain/bâti, n<5 masqué* | | | | | |

# Fiche propriétaire

## Fiche propriétaire (timeline PM)

*Robinet `fiche_proprietaire` — route `/parcels/{idu} (bloc) + patrimoine`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `n_parcelles_pm` | nombre | Parcelles détenues | dgfip_parcelles_pm (Panel millésimes 2019→2025 (situation 1ᵉʳ janvier)) | moteur `proprietaire_historique` · src/labuse/registre/moteurs/proprietaire.py:compte_parcelles_pm (délégation — le calcul vit dans api/modules.py:patrimoine, une seule vérité) | live | servie · non couverte (n sous seuil, dit) · non calculée | outil « Scan patrimoine » · outil « Possède » · outil « Ce qu'ils construisent » · Copilote « Parcelles détenues par une personne morale » |
| | | *count parcelle_personne_morale par SIREN (millésime 2025)* | | | | | |

# Fiche soleil

## Fiche soleil (photo toit + rosace)

*Robinet `fiche_soleil` — route `/modules/prospection-solaire (détail)`*

| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |
|---|---|---|---|---|---|---|---|
| `prod_spec_kwh_kwc` | nombre | Productible | bd_topo (BD TOPO® V3 (IGN) — édition non enregistrée), pvgis (PVGIS v5.3 · modèle SARAH3 (relevé au run du builder solaire)), lidar_hd_mnh (LiDAR HD MNH — dalles publiées 25/06/2025 (IGN)), bd_ortho_irc | moteur `solaire` · src/labuse/api/modules.py:prospection_solaire | run | servie · non couverte (n sous seuil, dit) · non calculée | outil « Prospection solaire » · outil « Toits bien exposés » · fiche « Solaire (rosace, productible) » |
| | | *productible PVGIS SARAH3 gelé au run du builder (parcel_solar)* | | | | | |
