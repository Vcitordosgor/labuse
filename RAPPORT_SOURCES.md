# RAPPORT SOURCES — état post-M71 (13/08/2026)

Une ligne par source : les 42 retenues (bandeau), les 7 utilisées hors bandeau (statut catalogue
antérieur, non requalifiées en M71), et les 13 écartées. Trié par gravité. Base : 431 682
parcelles, 24 communes ; run servi q_v8_calibre.

## SQUELETTE — aucune

Post-M71, plus aucune source servie n'est un squelette : DPE est ré-ingéré à 17/17 de son amont
réel et sorti du scoring ; ZNIEFF/EDF/ODRE (0 donnée) sont écartées ; la chaîne PV est en attente
de la session de jugement (B2), son signal reste hors scoring sous exemption datée.

## INCOMPLÈTE

[INCOMPLÈTE] Géorisques — sites et sols pollués — 486 emprises / ~548 à l'API (CASIAS 480 + instructions 59 + conclusions SIS/SUP 9) — sert à : scoring (risques) — il manque ~62 objets, écart de périmètre CASIAS/SIS à trancher à la prochaine ingestion.
[INCOMPLÈTE] Géorisques — ICPE — 1 252 installations / 1 261 à l'API — sert à : scoring (vigilance) — il en manque 9, un refresh API suffit.
[INCOMPLÈTE] Cartofriches (Cerema) — 372 friches / 373 à l'API — sert à : scoring (bonus friche) — il en manque 1, un refresh API suffit.
[INCOMPLÈTE] LiDAR HD — MNH 50 cm (IGN) — canopée/NDVI sur 426 107 parcelles ; 5 556 neutralisées documentées (1,3 %, motif en base M71-E) — sert à : scoring (canopée, NDVI) — l'amont couvre l'île mais notre tuilage ortho n'a jamais été étendu à ces zones (Sainte-Rose 9,5 %) ; levée = étendre le tuilage puis relancer.
[INCOMPLÈTE] Géorisques (ligne parente) — agrège les 4 couches ci-dessus + cavités/MVT — sert à : scoring — les écarts vivent sur les lignes filles (sols pollués −62, ICPE −9).

## NON MESURÉ

[NON MESURÉ] DVF / valeurs foncières — 29 566 mutations 2021→08/2026 + 110 463 en historique 2014-2020, 24 communes — sert à : scoring (rotations, médianes) + fiche (marché) — le compte amont exact exige de télécharger les 5 csv.gz géo-DVF (~2,4 Mo cumulés) et compter les id_mutation ; jamais fait, mais tailles de fichiers et volumes concordent et le refresh détecte les livraisons.
[NON MESURÉ] Forêts publiques (ONF) — 227 emprises (BDTOPO foret_publique) — sert à : scoring (exclusion domaniale) — trancher = compter le WFS Géoplateforme BDTOPO_V3:foret_publique sur l'emprise 974 et comparer.
[NON MESURÉ] Potentiel foncier (Région) — 2 453 emprises ×2 couches (potentiel_foncier, sar) — sert à : scoring — trancher = lire total_count de l'API ODS Région sur le jeu potentiel-foncier.
[NON MESURÉ] ABF / Monuments historiques — 200 périmètres — sert à : scoring (vigilance ABF) — trancher = compter les périmètres 974 à l'atlas des patrimoines (WFS) et comparer.
[NON MESURÉ] Recherche d'entreprises (DINUM) — service de recoupement par requête (état des sociétés), pas un dataset — sert à : fiche (propriétaire, état société) — non dénombrable par nature (l'API plafonne tout comptage à 10 000) ; sans objet tant que c'est un service unitaire.
[NON MESURÉ] OCS GE (IGN) — 3 250 emprises d'occupation du sol — sert à : scoring — hors bandeau (partiel au catalogue, retard M66 non traité en M71) — trancher = compter les objets OCS GE 974 servis par la Géoplateforme et comparer.
[NON MESURÉ] Fichiers fonciers (Cerema) — les liens parcelle↔personne morale (82 701, 12 605 identifiants) qui portent la couche propriétaire en dérivent — sert à : scoring (étage propriétaire) + fiche — hors bandeau (manuel au catalogue, convention) — trancher = demander l'extraction conventionnée Cerema et comparer les comptes PM.

## PLAFOND AMONT

[PLAFOND AMONT] Urbanisme PLU/GPU — 427 419 parcelles zonées, 23/24 communes — sert à : scoring (constructibilité) + fiche (zone) — on a tout ce que le GPU publie : Saint-Philippe (4 153 parcelles) n'y a AUCUNE couche (commune RNU), dit depuis M71 (« Non publié au GPU », verdict non évaluable), pas un défaut de notre côté.
[PLAFOND AMONT] DPE ADEME — 17 DPE, tous 974, 15 rattachés parcelle = 100 % de l'amont réel (le « 913 » de l'API est contaminé à 98 % par des logements de métropole mal géocodés) — sert à : fiche (« DPE connu », hors scoring depuis M71) — l'amont est dérisoire parce que le DPE réglementaire est neuf en DROM (obligation 07/2024).
[PLAFOND AMONT] SUP — assiettes GPU — 417 assiettes — sert à : scoring (servitudes) — on ingère ce que le GPU sert ; des SUP non versées au GPU par les gestionnaires existent, c'est le plafond de l'amont.
[PLAFOND AMONT] GPU — zonages d'assainissement — 258 emprises, 4 communes/24 (Étang-Salé, Le Port, Saint-Denis, Saint-Paul) — sert à : fiche (contexte ANC) — l'amont GPU ne publie que ces 4 communes en SIG (constat 11/07/2026), les 20 autres n'ont que des PDF d'enquête.
[PLAFOND AMONT] Zonage SAFER (DAAF) — proxy RPG.LATEST 38 460 parcelles agricoles — sert à : scoring (flag agricole) — hors bandeau (partiel au catalogue) — le zonage SAFER officiel n'existe pas en open data, le proxy est le maximum publiable.
[PLAFOND AMONT] ENS (Département) — 73 espaces protégés réglementaires (proxy INPN/patrinat, 21/24 communes + 3 « vérifié N/A ») — sert à : scoring — hors bandeau (partiel au catalogue) — la couche ENS départementale officielle n'est pas publiée (demande AGORAH/DEAL en attente).
[PLAFOND AMONT] DEAL Réunion (WMS/WFS) — 8 emprises ANRU servies via proxys — sert à : fiche (contexte commune) — hors bandeau (a_faire au catalogue) — l'hôte carto DEAL est injoignable (HTTP 000), les proxys sont le maximum accessible.

## ÉCARTÉE (requalifiées M71 — hors bandeau)

[ÉCARTÉE] Cadastre Etalab (bulk) — doublon de « Cadastre (API Carto PCI) » : même donnée, canal d'ingestion en masse — sert à : ingestion du socle — listée avec badge doublon, exclue des comptages.
[ÉCARTÉE] RGE ALTI 5 m — doublon de « RGE ALTI (altimétrie) » : même référentiel IGN, résolution 5 m — sert à : source du raster de pente — listée avec badge doublon, exclue des comptages.
[ÉCARTÉE] GPU assainissement (info-surf typeinf 19) — doublon de « GPU — zonages d'assainissement » : même couche, canal info-surf — sert à : fiche (ANC) — listée avec badge doublon, exclue des comptages.
[ÉCARTÉE] Région Réunion Open Data — hub/portail (275 datasets) requalifié `hub` : un portail n'est pas une source — sert à : rien en propre (canal d'accès) — sorti du bandeau.
[ÉCARTÉE] Géoplateforme IGN — hub/portail requalifié `hub` — sert à : rien en propre (canal d'accès WFS/WMS) — sorti du bandeau.
[ÉCARTÉE] ZNIEFF (INPN/Région) — 0 donnée ingérée, 0 usage : requalifiée a_faire — sert à : rien — endpoint vivant, ingestion à faire si le signal environnemental est voulu.
[ÉCARTÉE] EDF SEI Réunion — 0 donnée : requalifiée a_faire, last_sync purgé (une date de fraîcheur sur du vide était un faux positif) — sert à : rien.
[ÉCARTÉE] Registre national des installations (ODRÉ) — 0 donnée : requalifiée a_faire, last_sync purgé — sert à : rien.
[ÉCARTÉE] PVGIS — parcel_solar calculé sur 431 663 parcelles mais AUCUNE lecture applicative : requalifiée partiel « ingéré, non exploité » — sert à : rien (gisement dormant) — à brancher (fiche énergie) ou laisser hors bandeau.
[ÉCARTÉE] Parkings OSM (loi APER) — 901 parkings filtrés ingérés, aucune lecture : requalifiée partiel « ingéré, non exploité » — sert à : rien — même arbitrage que PVGIS.
[ÉCARTÉE] PEIGEO (hub régional) — a_faire HISTORIQUE (pas une requalification M71) : hôte injoignable, 0 donnée — sert à : rien.
[ÉCARTÉE] BPE INSEE — a_faire HISTORIQUE : 0 donnée (les aménités du scoring viennent d'OSM) — sert à : rien — à ingérer si on veut croiser OSM avec l'officiel.
[ÉCARTÉE] VRD / assainissement (SPANC) — manuel HISTORIQUE : 0 donnée (l'ANC est servi par EGOUL/GPU/Office de l'eau) — sert à : rien.

## MAXIMUM

[MAXIMUM] Cadastre (API Carto PCI) — 431 682 parcelles, 24 communes — sert à : socle de tout (carte, fiche, scoring) — la totalité du PCI 974.
[MAXIMUM] RGE ALTI (altimétrie) — pente sur 431 663 parcelles (100 % depuis M71-E, slivers récupérés) + raster 5 m conservé — sert à : scoring (pente) + fiche — couverture complète.
[MAXIMUM] Parc National de La Réunion — 3 emprises (cœur/adhésion, millésime 2021) — sert à : scoring (exclusion) — le parc entier.
[MAXIMUM] SITADEL — 50 292 autorisations 2004→06/2026, 24 communes (amont ~42,8 k depuis 2013 + locaux + antérieur) — sert à : scoring (permis) + fiche (permis à proximité, dépôts) — plus que l'amont courant ne republie.
[MAXIMUM] BD TOPO IGN — 817 506 bâtiments, 235 643 tronçons voirie, 12 716 ravines, 6 120 surfaces d'eau — sert à : scoring (bâti, accès, contraintes) — couverture IGN complète.
[MAXIMUM] Base Adresse Nationale — 341 426 adresses / 340 851 publiées (100,2 %), 24 communes — sert à : fiche (adresse), géocodage local — tout l'amont.
[MAXIMUM] OpenStreetMap / Overpass — 15 214 aménités ; les 4 distances calculées sur 431 663 parcelles (100 %) — sert à : scoring (accès équipements τ=800 m) — au-delà des ~8,8 k POI des 4 catégories comptées amont.
[MAXIMUM] SIRENE — 82 701 liens parcelle↔PM, 12 605 identifiants — sert à : fiche (propriétaire) — l'usage est le recoupement propriétaires (pas l'annuaire) : tous les propriétaires PM sont recoupés.
[MAXIMUM] DEAL — trait de côte — 24 168 segments (millésime 2018) — sert à : scoring (littoral) — le linéaire complet publié.
[MAXIMUM] BODACC — 678 annonces de procédures collectives, journal M71 : 12 605/12 605 identifiants propriétaires sondés ou documentés (177 avec procédure, 9 556 « rien » datés, 2 872 non-SIREN) — sert à : scoring (étage 2) + fiche (signal propriétaire) — le sondage est prouvé, entretenu par le cron J+1.
[MAXIMUM] DEAL — PPR / aléas — 164 périmètres PPR + 993 aléas — sert à : scoring (risques, graduation M-I) — les PPR approuvés des 24 communes.
[MAXIMUM] INPI RNE — 27 146 dirigeants des sirens propriétaires — sert à : scoring (âge dirigeant, étage 2) + fiche — tous les sirens propriétaires couverts.
[MAXIMUM] Géorisques — cavités — 151/151 à l'API — sert à : scoring — tout l'amont.
[MAXIMUM] Géorisques — mouvements de terrain — 3 085/3 085 à l'API — sert à : scoring — tout l'amont.
[MAXIMUM] QPV 2024 (ANCT) — 57 emprises / 56 quartiers officiels (un découpage double) — sert à : fiche (contexte commune) — génération 2024 complète.
[MAXIMUM] Inventaire SRU (DHUP) — 24/24 communes — sert à : fiche (contexte logement) — exhaustif.
[MAXIMUM] NPNRU — 8 quartiers — sert à : fiche (contexte commune) — le programme publié.
[MAXIMUM] INSEE RP Logement 2023 — 24/24 communes à la maille publiée — sert à : fiche (contexte marché) — tout ce que l'INSEE diffuse à cette maille.
[MAXIMUM] PLH des 5 EPCI — 5/5 (extraction documentaire, orientations) — sert à : fiche (commune + parcelle) — exhaustif.
[MAXIMUM] RTAA DOM — corpus réglementaire en config (textes Légifrance) — sert à : fiche + exports (pente RGE ALTI, règles DOM) — documentaire, complet pour l'usage.
[MAXIMUM] Classement sonore ITT (Cerema) — 1 004 segments (arrêtés déc. 2023) — sert à : scoring (bruit) — le classement publié entier.
[MAXIMUM] 50 pas géométriques (DEAL) — 163 emprises (limite haute) — sert à : scoring (littoral) — la limite publiée unique.
[MAXIMUM] BD ORTHO 20 cm (IGN) — tuilage ciblé bâti∪parkings, millésime 2025 ; piscines matérialisées 8 307 parcelles (juge 90,7 %) ; 23 529 candidats PV en attente de la session de jugement (B2, GO donné, montage en pause) — sert à : scoring (piscine) + fiche (badges) — tout ce que l'usage cible.
[MAXIMUM] Sudocuh — 24/24 communes, état 31/12/2024 — sert à : outil Vérif procédure PLU (radar) — l'enquête entière.
[MAXIMUM] Contours IRIS (IGN/INSEE) — 344 emprises (330 IRIS + replis commune) — sert à : agrégation statistique (ANC) — maille complète.
[MAXIMUM] INSEE RP2022 — EGOUL — taux de non-raccordement agrégés aux 330 IRIS ; parcel_anc 278 685 — sert à : fiche (ANC) — tout le fichier détail à sa maille.
[MAXIMUM] Office de l'eau — Chroniques — seed versionné des chiffres publiés (chronique n°149, ~189 000 installations ANC) — sert à : calage/contrôle croisé ANC — la publication entière, par conception sans table.
[MAXIMUM] BD ORTHO IRC (IGN) — canal infrarouge du tuilage ciblé — sert à : NDVI végétation (scoring) + chaîne PV (en attente de session) — tout ce que l'usage cible.
[MAXIMUM] SAR Réunion (PEIGEO) — 2 453 emprises SAR intégrées (via le jeu Région) — sert à : scoring — hors bandeau (a_faire au catalogue : retard M66 non traité en M71, à requalifier) — le document régional unique est intégré.
[MAXIMUM] Filosofi INSEE (carreaux 200 m) — 14 773 carreaux = l'amont exact (millésime 2021) — sert à : scoring (3 features de niveau de vie) — hors bandeau (partiel au catalogue : retard M66 non traité en M71, à requalifier).

---
Comptes : 42 retenues (28 MAXIMUM · 4 PLAFOND AMONT · 5 NON MESURÉ · 5 INCOMPLÈTE) + 7 utilisées
hors bandeau (2 MAXIMUM · 3 PLAFOND AMONT · 2 NON MESURÉ) + 13 écartées (10 requalifiées M71 +
3 historiques) = 62 lignes de catalogue. SQUELETTE : 0.
