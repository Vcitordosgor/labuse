# VERITE-TERRAIN-3 — Volet A : « Sommes-nous à jour ? »

**Date de l'audit :** 16 octobre 2026
**Périmètre :** fraîcheur des 118 sources servies (vitrine) de LABUSE, La Réunion (974), avec **priorité absolue aux documents d'urbanisme (PLU/GPU) et PPR des 24 communes**.
**Nature :** LECTURE SEULE. Aucune écriture en base, aucune correction de code, aucun accès VPS.

## Méthode

- **Ce que LABUSE sert** : lu dans la base Postgres locale (`openclaw@localhost/labuse`, lecture de fait) — notamment `plu_reglement_extrait` (idurba / millésime / document PDF servis par commune) et `parcel_zone_plu` (zonage servi) — et dans le CSV préparé `cache/sources_servies.csv` (colonne `source_millesime`).
- **Ce que publie l'amont aujourd'hui** : interrogé EN DIRECT (16/10/2026), GET uniquement, appels séquentiels espacés ~2 s, cache dans `cache/` (un fichier par appel) :
  - PLU : API Carto GPU du Géoportail de l'urbanisme — `document?partition=DU_<INSEE>` (document en vigueur, champ `name` = référence idurba) **et** `zone-urba?geom=<centroïde>` (`partition`/`datvalid`).
  - PPR : Géorisques GASPAR `pprn?codeInsee=<INSEE>` (champ `content[]` : `idGaspar`, `modeleProcedure`, `etatRevision`, `dateModification`).
  - Autres sources : data.gouv.fr API dataset (`last_modified` + resource la plus récente), ADEME, Dido/SDES, Géoplateforme WFS, Opendatasoft, etc.

### ⚠️ Caveat de fiabilité
La base est **locale** (worktree de dev). La table `source_veille` a pour dernier passage le **24/09/2026** et affiche 83 sources « injoignable » : c'est un **artefact réseau du poste de dev, PAS la réalité prod**. Les colonnes `dernier_vu`/`dernier_statut`/« injoignable » du CSV **n'ont donc PAS été utilisées pour conclure** ; chaque verdict ci-dessous repose sur un **appel amont refait en direct le 16/10/2026** (ou, à défaut, est marqué NON VÉRIFIABLE).

---

## Tableau 1 — Documents d'urbanisme, 24 communes

**Résultat d'ensemble : les 21 communes dotées d'un règlement PLU ingéré servent EXACTEMENT le document en vigueur au GPU** (la référence `idurba` servie = le champ `name` du document GPU `document?partition=DU_<INSEE>`, octet pour octet). Les 3 communes restantes (97409, 97413, 97417) n'ont **aucun document publié au GPU** aujourd'hui (`document?partition=` renvoie 0 feature) : LABUSE y sert le zonage sans règlement calibré, ce qui est l'état attendu.

Légende « doc servi » = `idurba` dans `plu_reglement_extrait` ; « doc GPU en vigueur » = `name` renvoyé par `document?partition=DU_<INSEE>` (et `datvalid` de `zone-urba` au centroïde, entre parenthèses).

| Commune | INSEE | Doc servi (LABUSE) | Doc GPU en vigueur (16/10/2026) | Procédure en cours ? | Verdict |
|---|---|---|---|---|---|
| Les Avirons | 97401 | 97401_PLU_20241206 | 97401_PLU_20241206 (datvalid 2024-12-06) | — | **À JOUR** |
| Bras-Panon | 97402 | 97402_PLU_20260428 | 97402_PLU_20260428 | — | **À JOUR** |
| Entre-Deux | 97403 | 97403_PLU_20240924 | 97403_PLU_20240924 | — | **À JOUR** |
| L'Étang-Salé | 97404 | 97404_PLU_20250917 | 97404_PLU_20250917 | — | **À JOUR** |
| Petite-Île | 97405 | 97405_PLU_20230609 | 97405_PLU_20230609 | — | **À JOUR** |
| La Plaine-des-Palmistes | 97406 | 97406_PLU_20230527 | 97406_PLU_20230527 | — | **À JOUR** |
| Le Port | 97407 | 97407_PLU_20241209 | 97407_PLU_20241209 | — | **À JOUR** |
| La Possession | 97408 | 97408_PLU_20251217 | 97408_PLU_20251217 | — | **À JOUR** |
| Saint-André | 97409 | zonage GPU servi, **pas de règlement calibré ingéré** | **0 document au GPU** | PLU en élaboration (pas publié au GPU) | **NON VÉRIFIABLE** (GPU vide) |
| Saint-Benoît | 97410 | 97410_PLU_20200206 | 97410_PLU_20200206 | — | **À JOUR** (doc ancien mais en vigueur) |
| Saint-Denis | 97411 | 97411_PLU_20260805 | 97411_PLU_20260805 | — | **À JOUR** |
| Saint-Joseph | 97412 | 97412_PLU_20251210 | 97412_PLU_20251210 | — | **À JOUR** |
| Saint-Leu | 97413 | zonage GPU servi, **pas de règlement calibré ingéré** | **0 document au GPU** | **OUI — révision générale, enquête publique 01/09→09/10/2026 close ; approbation annoncée « début 2e semestre 2026 »** | **PROCÉDURE EN COURS** |
| Saint-Louis | 97414 | 97414_PLU_20251218 | 97414_PLU_20251218 (datvalid 2025-09-26 au centroïde) | — | **À JOUR** |
| Saint-Paul | 97415 | 97415_PLU_20251217 | 97415_PLU_20251217 | — | **À JOUR** |
| Saint-Pierre | 97416 | 97416_PLU_20240625 | 97416_PLU_20240625 | — | **À JOUR** |
| Saint-Philippe | 97417 | zonage GPU servi, **pas de règlement calibré ingéré** | **0 document au GPU** | PLU : état à vérifier (GPU vide) | **NON VÉRIFIABLE** (GPU vide) |
| Sainte-Marie | 97418 | 97418_PLU_20251126 | 97418_PLU_20251126 | — | **À JOUR** |
| Sainte-Rose | 97419 | 97419_PLU_20190504 | 97419_PLU_20190504 | — | **À JOUR** (doc ancien mais en vigueur) |
| Sainte-Suzanne | 97420 | 97420_PLU_20250929 | 97420_PLU_20250929 | — | **À JOUR** |
| Salazie | 97421 | 97421_PLU_20220524 | 97421_PLU_20220524 | — | **À JOUR** |
| Le Tampon | 97422 | 97422_PLU_20230811 | 97422_PLU_20230811 | — | **À JOUR** |
| Les Trois-Bassins | 97423 | 97423_PLU_20220602 | 97423_PLU_20220602 | — | **À JOUR** |
| Cilaos | 97424 | 97424_PLU_20240213 | 97424_PLU_20240213 | — | **À JOUR** |

**Notes :**
- 97423 Les Trois-Bassins : la colonne `millesime` de `plu_reglement_extrait` vaut `2017-02-21`, mais la référence `idurba` servie est bien `97423_PLU_20220602`, **identique** au document GPU en vigueur. Le `millesime` interne 2017 est une incohérence de saisie interne sans effet sur la correspondance au GPU.
- Les 3 « NON VÉRIFIABLE » (97409, 97413, 97417) le sont parce que **le GPU ne publie aucun document** pour ces communes : impossible de comparer une date d'approbation GPU postérieure. LABUSE y sert le zonage (parcel_zone_plu : 97409 = 22 759 parcelles, 97413 = 23 023, 97417 = 9) mais aucun `plu_reglement_extrait`. État cohérent ; à re-sonder dès qu'un document apparaît au GPU (Saint-Leu notamment).

### PPR / PPRN (Géorisques GASPAR, 24 communes)

Toutes les 24 communes ont été interrogées (`pprn?codeInsee=<INSEE>`). LABUSE sert « PPR/PPRL approuvés 2011–2026 (DEAL Lizmap) » (veille 07/09/2026). La plupart des communes portent un PPRN-Multi avec `etatRevision=true` et `dateModification` du **14-15/01/2025** (lot national homogène, antérieur à l'ingestion LABUSE → couvert). **Deux communes ressortent avec une modification 2026 à signaler :**

| Commune | INSEE | PPR GASPAR | etatRevision | dateModification | Statut vérifié |
|---|---|---|---|---|---|
| **Saint-André** | 97409 | 974DEAL20180003 (PPRN-Multi) | true | **18/05/2026** | **PPRN inondations/mouvements de terrain APPROUVÉ par arrêté préfectoral n° 477 du 16/04/2026** (confirmé web). LABUSE sert « 2011–2026 » (veille 07/09/2026) → vraisemblablement capté, **à vérifier à la main** que la version 2026 est bien la couche servie. |
| **Saint-Philippe** | 97417 | PPRN-Multi_2023_0044 (PPRN-Multi) | true | **06/10/2026** | **Procédure PRESCRITE 12/06/2023, toujours en élaboration/concertation** (pas encore approuvée au 16/10/2026). → **PROCÉDURE EN COURS**, rien à ingérer tant que non approuvé. |

Les 22 autres communes : PPR stables (dateModification 14-15/01/2025) → cohérent avec ce que LABUSE sert, **À JOUR**.


---

## Tableau 2 — Autres sources servies (vérifiées en direct 16/10/2026)

Vérifications réparties entre l'auditeur principal (cadastre/DVF/DPE/SITADEL/BAN/RPG/CoSIA/GTFS/DGFiP-PM/OLL) et deux sous-agents (INSEE/fiscal/logement ; risques/IGN/environnement). Toutes les dates amont sont des relevés data.gouv/API du 16/10/2026, mis en cache.

| Source | Catégorie | Millésime servi | Dernière version amont (date) | Verdict | Preuve |
|---|---|---|---|---|---|
| Cadastre (API Carto PCI) | cadastre | millésime 2026-09 (maj 10/10/2026) | dataset PCI last_modified 2026-09-09 | **À JOUR** | data.gouv parcellaire-express-pci |
| DFI filiation (DGFiP) | cadastre | situation 19/06/2026 | resource « situation janvier 2026 » publiée 2026-06-19 (dernière) | **À JOUR** | data.gouv …dfi… |
| BAN PLUS | cadastre | maj 27/08/2026, moisson 13/09/2026 | dataset last_modified 2026-08-27 | **À JOUR** | data.gouv ban-plus |
| Base Adresse Nationale | acces | sync 19/08/2026 (mensuel) | republiée en continu (resource 16/10/2026) | **EN RETARD ~2 mois** (mineur, mensuel) | data.gouv base-adresse-nationale |
| Transport GTFS (PAN, 7 réseaux) | acces | 7 jeux PAN, màj 10/10/2026 | agrégat PAN re-sync 11/10/2026 | **À JOUR** | data.gouv horaire-du-reseau-citalis |
| DVF / valeurs foncières | marche | géo-DVF 2021–2025 + archives 2014–2020 | geo-dvf/latest = années 2021→2025 | **À JOUR** | files.data.gouv.fr/geo-dvf/latest/csv/ |
| SITADEL | dynamique | 2026-08 (mensuelle) | dernière période publiée = 2026-08 (fin 31/08, modif 29/09/2026) | **À JOUR** | Dido SDES 6513f0189d7d312c80ec5b5b |
| DPE ADEME existant | energie | sync 19/09/2026 (hebdo) | dataUpdatedAt 2026-10-14 (flux continu) | **EN RETARD ~4 sem.** (mineur, hebdo) | data.ademe dpe03existant |
| RPG déclarations agricoles | agricole | proxy RPG.LATEST — campagne 2024 | dataset RPG last_modified 2026-09-29 (RPG.LATEST = campagne 2024) | **À JOUR** | data.gouv rpg |
| CoSIA | occupation_sol | CoSIA 2025 (PVA juil-août 2025) | édition nationale IGNF_COSIA_2024-2026 (dataset 14/10/2026) | **À JOUR** (D974 millésime 2025 = courant) | data.gouv cosia |
| DGFiP parcelles personnes morales | proprietaire | panel 2019→2025 (situation 1er janvier) | dernière = situation_2025 | **À JOUR** | data.economie fichiers-…-personnes-morales |
| Loyers OLL (ADIL/AGORAH) | marche | OLL 2024 — Île de La Réunion | dataset touché 15/10/2026 (millésime publié = 2024) | **À JOUR** (2024 = dernier millésime OLL publié) | data.gouv 56fd90e8c751df174ac485cb |
| EDF HTA (open data 974) | acces | géométrie ~02/2020, publié 16/10/2025 | endpoint joignable (HTTP 200) | **À JOUR** | opendata-reunion.edf.fr |
| BPE INSEE | attractivite | millésime 2025 | BPE24.parquet publié 30/03/2026 | **À JOUR** | data.gouv base-permanente-des-equipements-3 |
| Population légale INSEE | demographie | 2023 | geo.api.gouv dernière pop. légale en vigueur | **À JOUR** | geo.api.gouv.fr/communes |
| Zonage ABC DHUP | logement | arrêté 23/06/2026, vigueur 26/06 | zonage ABC vigueur 26/06/2026 (màj 03/07/2026) | **À JOUR** | data.gouv liste-…-zonage-abc |
| Taxe foncière REI DGFiP | fiscalite | REI 2025 | REI-2025 publié 21/08/2026 | **À JOUR** | data.gouv …rei-4 |
| QPV 2024 ANCT | fiscal | génération 2024 | QPV 2024 (périmètres 16/01/2024) | **À JOUR** | data.gouv quartiers-prioritaires-…-qpv |
| RPLS logements sociaux | logement | millésime 01/01/2025 | RPLS au 01/01/2025 publié 22/08/2025 | **À JOUR** | data.gouv …logements-locatifs-…-sociaux |
| RNIC copropriétés Anah | logement | re-sync 10/10/2026 | actualisation quotidienne (màj 16/10/2026) | **À JOUR** | data.gouv …immatriculation-des-coproprietes |
| Inventaire SRU DHUP | logement | (sans millésime en base) | donnees-sru-2026 publié 11/08/2026 | **À JOUR** | data.gouv communes-et-inventaire-sru |
| Loyers DHUP carte | marche | carte 2025 | carte des loyers 2025 (màj 11/12/2025 ; pas de 2026) | **À JOUR** | data.gouv carte-des-loyers-…-2025 |
| Fibre Arcep Ma connexion | reseaux | 2026_T2 | dernière publi màj 14/09/2026 (= T2 2026, T3 non publié) | **À JOUR** | data.gouv ma-connexion-internet |
| Conso NAF Cerema | urbanisme | 2021-2024 | obs au 01/01/2024, publié 12/05/2025 | **À JOUR** | data.gouv consommation-…-2009-au-1er-janvier-2024 |
| Sudocuh | urbanisme | état 31/12/2024 | dernier état annuel = 31/12/2024 (aucun 2025) | **À JOUR** | data.gouv …sudocuh-…-au-31-decembre-2024 |
| ICPE Géorisques | risques | (flux, sans millésime) | resource republiée 2026-07-20 (dataset 26/08/2026) | **À JOUR** | data.gouv …icpe…-3 |
| GASPAR base | risques | (flux, sans millésime) | resource GASPAR 2026-10-05 | **À JOUR** | data.gouv …gaspar |
| CatNat GASPAR | risques | arrêtés CatNat 974, extrait 06/09/2026 | arrêté le plus récent 974 = 17/06/2024 | **À JOUR** | api georisques gaspar/catnat |
| BD ORTHO 20 cm | imagerie | millésime 2025 | édition 2025 D974 confirmée (MAJ IGN 08/2026) | **À JOUR** | data.gouv bd-ortho-r + cartes.gouv |
| LiDAR HD MNH | terrain | survol 2023, MNx édités 13/03/2025 | WFS metadata 974 date_edition max = 2025-03-13 | **À JOUR** | data.geopf WFS LIDAR-HD metadata |
| OCS GE IGN | topographie | D974 2017+2022, diff artif 16/09/2025 | 3e millésime 2024-2026 en diffusion nationale mais D974 PAS encore publié | **À JOUR** (2022 = dernier D974 ; 3e **procédure en cours**) | cartes.gouv OCS GE 07-08/2026 |
| RNB bâtiments | topographie | flux continu, 13/09/2026 | API répond (flux continu) | **À JOUR** | rnb-api.beta.gouv.fr |
| Parc National Réunion | environnement | millésime 2021 | dataset pnrun_2021 seul périmètre (aucun 2022+) | **À JOUR** | data.regionreunion pnrun_2021 |
| CBS bruit DEAL | risques | CBS 2022, 4e échéance arrêté 2023 | 5e échéance attendue 2027 (non lancée) | **À JOUR** | reunion.developpement-durable CBS |
| Trafic RN Région | economie | comptages par tronçon | dataset traité 21/10/2025 (pas de millésime postérieur) | **À JOUR** | data.regionreunion trafic-mja-rn |
| BODACC | economie | (flux) | dernière parution 16/10/2026 | **À JOUR** | bodacc-datadila.opendatasoft |
| **ZNIEFF INPN** | environnement | **màj 29/08/2025** | **base ZNIEFF rafraîchie 08/10/2026** (2×/an) | **EN RETARD** (≥1 cycle) | data.gouv inventaire-…-znieff |
| **Classement sonore ITT Cerema** | reglement | **arrêtés déc. 2023** | **arrêtés préfectoraux 974 du 26/12/2024** | **EN RETARD ~12 mois** | data.gouv …arretes-prefectoraux-du-26-12-2024 |
| **GéoLittoral érosion côtière** | risques | **millésime 2018** | **nouvel INEC Cerema présenté 26/08/2026** | **EN RETARD ~8 ans / 1 version majeure** | cerema.fr actu INEC 08/2026 |
| BD TOPO IGN | topographie | V3, édition non enregistrée | services WMS/WFS republiés en continu (pas de n° d'édition) | **NON VÉRIFIABLE** | data.gouv bd-topo-r |
| RGE ALTI | topographie | édition non enregistrée | pyramides WMS republiées en continu | **NON VÉRIFIABLE** | data.gouv rge-alti-r |
| Contours IRIS IGN/INSEE | attractivite | géographie 2024 | WFS STATISTICALUNITS.IRIS refreshed 11/09/2026 (année d'édition non exposée) | **NON VÉRIFIABLE** (probablement 1 édition de retard : IRIS 2025) | data.gouv contours-iris-r-2 |
| Filosofi carreaux 200 m | attractivite | millésime 2021 | slug déprécié ; dernier millésime carroyé amont = 2019 | **NON VÉRIFIABLE / incohérent** (label « 2021 » sans contrepartie amont) | data.gouv (slug déprécié) |
| INSEE RP détail Logements (EGOUL) | assainissement | RP2022 publié 16/10/2025 | slug = fichiers détail 2020/2021 (màj 12/02/2025) | **NON VÉRIFIABLE** (slug ne porte pas RP2022) | data.gouv …logements-ordinaires |
| INSEE RP bases IRIS | attractivite | RP2022 parution 16/10/2025 | même slug (fichiers détail, pas bases IRIS) | **NON VÉRIFIABLE** (mauvais point de contrôle) | idem |
| INSEE RP Logement 2023 (id 41) | logement | RP2023 géo 01/01/2026 (veille) | même slug (max 2021) | **NON VÉRIFIABLE** (slug ne porte pas RP2023) | idem |
| SIRENE géolocalisé | economie | publication mensuelle | septembre 2026 publié 21/09/2026 | **NON VÉRIFIABLE** (mois servi non connu) | data.gouv geolocalisation-…-sirene |
| Cartofriches Cerema | foncier | (sans millésime) | slug fourni = extraction Loiret (non national) | **NON VÉRIFIABLE** (mauvais slug) | data.gouv cartofriches |

---

## NON TRAITÉ / NON VÉRIFIABLE

**Sources `partenariat_requis` (en attente de convention/remise ; hors flux amont surveillable, DONC non traitées par construction) :** Inventaires ZAE EPCI (135), ENS Département (139), LOVAC (141), Micro-données OLL ADIL (140), OPAH/PIG Anah (137), Périmètres ORT infra-communaux (138), Zonages assainissement SIG EPCI (134), DV3F Cerema (142), Fichiers fonciers Cerema (27), ZPPA Atlas patrimoines (110), Carte hypsométrique littoral DEAL (146), Périmètres ZAC (136), SAR couche SIG (118), Réunion Express tracé (95). → État « en attente de demande » ; rien à comparer à un amont public.

**Sources `hub`/`interne`/`manuel` (pas de millésime servi à comparer) :** DEAL Réunion WMS/WFS (13), Géoplateforme IGN (14), PEIGEO AGORAH (12), Région Réunion ODS (11), Radar pige LABUSE (84), VRD/SPANC (26), Cadastre d'époque interne (96), OSM/Overpass (19).

**Sources NON VÉRIFIABLES avec raison précise (déjà en Tableau 2) :** BD TOPO & RGE ALTI (republish continu, pas d'édition enregistrée) ; Contours IRIS (année non exposée) ; Filosofi, 3× INSEE RP, SIRENE, Cartofriches (slug déprécié / inadéquat dans `cache/sources_servies.csv`).

**Communes PLU non vérifiables (GPU vide) :** Saint-André (97409) et Saint-Philippe (97417) — 0 document publié au GPU (réglement non calibré ingéré) ; Saint-Leu (97413) → PROCÉDURE EN COURS.

**Sources NON ATTEINTES faute de temps/réseau (non marquées « à jour » par défaut) :** DEAL Lizmap WFS (50 pas géométriques 47, zones humides 112, DPF ravines 111, systèmes d'endiguement 145, espaces protégés complémentaires 113, PPR/aléas 30 au-delà de GASPAR), SUP assiettes GPU (44), PEB annexes GPU (108), GPU prescriptions/info-surf (105/106/107/63/151), INPN espaces protégés (25), ABF monuments (24), BD CARTO occ. sol (22), BD ORTHO IRC (69), SCAN50/EduGéo (155/156), BD NYME lieux-dits (154), PVGIS (48), parkings/OSM APER (51/75/94), zones exclues EnR OFB (152), contraintes EnR (153), GéoMCE (150), SIS/CASIAS/cavités/mvt/ssp Géorisques détail (115/116/33/36/32), INPI RNE (31), recherche-entreprises (45), ACV/ORT DGALN (128), coût construction EPTB (131), FRR/ZFANG/RTAA (73/72/43 — textes réglementaires, veille agent « ok/nouvelle_version » au 24/09), Annuaire DILA (99), NPNRU/PLH/SRU détail (40/42). → Pour ces sources, le point de contrôle amont existe dans `sentinelle.py` mais n'a pas été re-sondé dans cette passe.

---

## CANDIDATS ÉCARTS (à revérifier à la main par l'orchestrateur)

Sources où LABUSE paraît EN RETARD, preuve amont datée. **Aucune correction appliquée.**

| Source | Servi | Amont (16/10/2026) | Écart | Correction suggérée (NON appliquée) |
|---|---|---|---|---|
| **GéoLittoral — érosion côtière** (28) | millésime 2018 | nouvel Indicateur National de l'Érosion Côtière (INEC) Cerema présenté 26/08/2026 | ~8 ans / 1 version majeure | Re-ingérer l'INEC 2026 (nouvelles périodes ~1950→2020, maille plus fine) en remplacement du trait de côte 062018. |
| **Classement sonore ITT Cerema** (46) | arrêtés déc. 2023 | arrêtés préfectoraux 974 du 26/12/2024 (couche Cerema V2) | ~12 mois / 1 révision | Resync la couche `Routes_classement_sonore_La_Reunion_V2` sur les arrêtés 26/12/2024. |
| **ZNIEFF INPN** (76) | màj 29/08/2025 | base ZNIEFF rafraîchie 08/10/2026 (cycle 2×/an) | ≥1 cycle (~13 mois) | Resync INPN ZNIEFF (dernier passage amont 02→08/10/2026). |
| **DPE ADEME existant** (37) | sync 19/09/2026 | dataUpdatedAt 2026-10-14 (flux hebdo) | ~4 semaines | Relancer la sync hebdo DPE (mineur — cadence hebdomadaire). |
| **Base Adresse Nationale** (18) | sync 19/08/2026 | republiée en continu (16/10/2026) | ~2 mois | Relancer la sync mensuelle BAN (mineur). |
| **PPR Saint-André** (97409 / couche 30) | « PPR 2011–2026 » veille 07/09/2026 | PPRN inondations/mvt APPROUVÉ par AP n°477 du 16/04/2026 (GASPAR dateModification 18/05/2026) | à confirmer | Vérifier que la couche DEAL servie intègre bien le PPRN Saint-André approuvé 16/04/2026 (postérieur ? déjà capté par veille 07/09 ?). |
| **Contours IRIS** (64) | géographie 2024 | WFS refreshed 11/09/2026 ; IGN a publié l'édition 2025 | ~1 édition (non prouvé) | Vérifier manuellement l'année d'édition IRIS ingérée vs édition 2025 ; resync si confirmé. |
| **Filosofi carreaux 200 m** (52) | millésime 2021 | slug déprécié ; amont = millésime carroyé 2019 | incohérence | Vérifier quel millésime Filosofi est réellement servi — le label « 2021 » n'a pas de contrepartie amont (dernier carroyé = 2019) ; corriger le slug de veille. |

### Procédures en cours à surveiller (pas des retards)
- **Saint-Leu (97413) — révision générale PLU** : enquête publique close le 09/10/2026, approbation annoncée « début 2e semestre 2026 ». Dès publication au GPU → ingérer + calibrer le règlement.
- **Saint-Philippe (97417) — PPRN multirisques** : prescrit 12/06/2023, en concertation (GASPAR dateModification 06/10/2026). Non approuvé → rien à ingérer tant que non approuvé.
- **OCS GE 3e millésime (2024-2026)** : en diffusion nationale depuis juil. 2026, D974 pas encore publié.

### Candidat-écart INTERNE (hors Volet A, signalé comme demandé)
- `src/labuse/sentinelle.py` (~ligne 587, bloc S4.2) commente « second chef-lieu témoin : Saint-Pierre (97410) » : **97410 = Saint-Benoît** ; Saint-Pierre = **97416**. Le témoin GASPAR échantillonne donc en réalité Saint-Benoît. Erreur de libellé interne (le témoin fonctionne), à corriger hors de ce mandat.
