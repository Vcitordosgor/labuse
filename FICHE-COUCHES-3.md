# FICHE-COUCHES-3 — Audit du branchement couche → fiche, par la preuve

## 47 couches VISIBLE sur 53, dont 34 dans le PDF Dossier expert.

Répartition : **47 VISIBLE**, **1 INTERROGÉE MAIS INVISIBLE**, **5 ABSENTE** (= 53).

Branche `feat/couches-tuyau`, départ `854ad0bf`. **Lecture seule, aucune tuile touchée, aucune correction** — le rapport sert à décider si on débranche tout et on rebranche.

## Méthode

On ne lit pas le code : on prouve par l'artefact. Pour chacune des 53 couches thématiques (56 − 3 fonds/repères), une parcelle témoin RÉELLEMENT concernée est choisie par requête SQL (intersection pour une surface, KNN sous le seuil pour une proximité). Sa fiche est ouverte dans le navigateur (accordéon `.fiche-v6`, tiroirs ouverts un à un) et l'information cherchée ; le dry-run de cascade du run servi a été recalculé pour chaque témoin (les couches lues depuis `dryrun_cascade_results`). Verdict en un mot :

- **VISIBLE** — l'information apparaît dans la fiche (onglet + libellé + capture).
- **INTERROGÉE MAIS INVISIBLE** — le back la calcule, la fiche ne l'affiche pas.
- **ABSENTE** — aucun croisement.

Pour chaque VISIBLE, on vérifie aussi si la ligne est dans le **PDF Dossier expert** (`/dossier/{idu}.pdf`, `pdftotext` + recherche de termes). Le PDF est un sous-ensemble CURÉ (zonage, DPU, servitudes, dispositifs, propriétaire, pente) : la cascade « risques » et les proximités transport n'y figurent pas, d'où les 13 VISIBLE hors PDF.

Preuve : 53 captures `<kind>_<parcelle>.png` dans `captures/fiche-couches3/`. Scripts rejouables : `qa/fiche_couches3_audit.py` (témoins + dry-run + back + PDF) et `frontend/qa/fiche_couches3_dom.mjs` (visibilité DOM + captures).

## Le tableau des 53 couches

| # | couche (kind) | parcelle témoin | verdict | onglet | libellé | dans le PDF | capture |
|---|---------------|-----------------|---------|--------|---------|:-----------:|---------|
| 1 | ZFANG (zone franche) (`zfang`) | 97422000AC0004 | VISIBLE | toujours visible | ZFANG standard | oui | zfang_97422000AC0004.png |
| 2 | FRR (revitalisation rurale) (`frr`) | 97415000EK0106 | VISIBLE | Dispositifs territoriaux | ZSAR 1978 · FRR 01/07/2024 · réf. ZRR 2017 (Région) · voir le texte | oui | frr_97415000EK0106.png |
| 3 | TVA primo-accédant (`tva_primo`) | 97408000AR0196 | VISIBLE | Dispositifs territoriaux | CGI (TVA DOM, art. 296 et 278 sexies) | oui | tva_primo_97408000AR0196.png |
| 4 | Quartiers prioritaires (QPV) (`qpv`) | 97411000HM0103 | VISIBLE | Dispositifs territoriaux | Quartier prioritaire — QPV | oui | qpv_97411000HM0103.png |
| 5 | Rénovation urbaine (ANRU) (`anru`) | 97411000AR0143 | VISIBLE | Dispositifs territoriaux | La parcelle est dans le périmètre « Vauban » d'un programme national de renouvellement u | oui | anru_97411000AR0143.png |
| 6 | Parc national (`parc_national`) | 97422000AC0004 | VISIBLE | Urbanisme | Parc National de La Réunion (INPN) | oui | parc_national_97422000AC0004.png |
| 7 | Bassins versants (`bassin_versant`) | 97415000AH0906 | VISIBLE | Risques et protections | Bassin versant (code hydro 10B0000002150455292) — 77 % de la parcelle : contexte hydrogr | non | bassin_versant_97415000AH0906.png |
| 8 | ZNIEFF (I & II) (`znieff`) | 97412000AH0368 | VISIBLE | Risques et protections | Parcelle en ZNIEFF type II (Massif du Piton de la Fournaise) — 89 % de la parcelle : inv | non | znieff_97412000AH0368.png |
| 9 | Espaces naturels protégés (`enp`) | 97415000BN0970 | VISIBLE | Risques et protections | Espace protégé à protection forte : Etang de Saint-Paul (reserve naturelle, 93 % de la p | oui | enp_97415000BN0970.png |
| 10 | Zones humides (`zone_humide`) | 97411000CZ0087 | VISIBLE | Urbanisme | Zone humide inventoriée (espace fonctionnel (2009)) : Roche Ecrite Est (71 % de la parce | non | zone_humide_97411000CZ0087.png |
| 11 | Forêts publiques (`foret_publique`) | 97415000AH0019 | INTERROGÉE MAIS INVISIBLE | — | — | — | foret_publique_97415000AH0019.png |
| 12 | Équipements INSEE (BPE) (`amenite_bpe`) | 97407000AT0111 | VISIBLE | Autour de cette parcelle | À proximité : école ISEC 303 m, commerce RAVATE 10 m, santé 278 m, bus 95 m | oui | amenite_bpe_97407000AT0111.png |
| 13 | Équipements OSM (`amenite`) | 97422000BV1780 | VISIBLE | Marché et secteur | Commerces et services à proximité : école 57m, commerce 49m, santé 42m, bus 472m (score  | non | amenite_97422000BV1780.png |
| 14 | SAR — vocations (`sar`) | 97401000AI0377 | VISIBLE | Marché et secteur | Potentiel foncier Région | oui | sar_97401000AI0377.png |
| 15 | Foncier agricole (RPG/SAFER) (`safer`) | 97411000CP0226 | VISIBLE | Urbanisme | Parcelle déclarée agricole au RPG (déclarations PAC) — usage agricole, à vérifier au PLU | oui | safer_97411000CP0226.png |
| 16 | Zones d'activité (`zone_activite`) | 97416000ES1248 | VISIBLE | Marché et secteur | Parcelle dans une zone d'activité ou d'intérêt — Zone industrielle « Zone d'Activités Ma | non | zone_activite_97416000ES1248.png |
| 17 | Friches (`friche`) | 97406000AH0358 | VISIBLE | Urbanisme | Cartofriches (Cerema) | oui | friche_97406000AH0358.png |
| 18 | Piscines (CoSIA) (`piscine_cosia`) | 97423000AB0198 | ABSENTE | — | — | — | piscine_cosia_97423000AB0198.png |
| 19 | Prix logement neuf (VEFA) (`vefa_neuf`) | 97414000CL0179 | ABSENTE | — | — | — | vefa_neuf_97414000CL0179.png |
| 20 | Cimetières (`cimetiere`) | 97413000CN0018 | ABSENTE | — | — | — | cimetiere_97413000CN0018.png |
| 21 | Périmètres ABF (`abf`) | 97411000AE0619 | VISIBLE | Risques et protections | Abords MH ~500 m (tampon) — covisibilité à instruire. | oui | abf_97411000AE0619.png |
| 22 | Lignes moyenne tension (HTA) (`ligne_mt`) | 97418000AC1166 | VISIBLE | Risques et protections | Ligne moyenne tension (HTA) au contact de la parcelle — contrainte de proximité (recul,  | non | ligne_mt_97418000AC1166.png |
| 23 | Lignes haute tension (HTB) (`ligne_ht`) | 97410000AX0387 | VISIBLE | Risques et protections | Ligne haute tension (63 kV) au contact de la parcelle — contrainte potentielle (servitud | non | ligne_ht_97410000AX0387.png |
| 24 | TRI — zones inondables (`tri_zone`) | 97410000AW0056 | VISIBLE | Risques et protections | Géorisques — CASIAS (anciens sites industriels) | oui | tri_zone_97410000AW0056.png |
| 25 | Aléa inondation (`alea_inondation`) | 97403000AH0342 | VISIBLE | Risques et protections | Bassin versant (code hydro 10B0000002150455293) — 100 % de la parcelle : contexte hydrog | oui | alea_inondation_97403000AH0342.png |
| 26 | Aléa mouvement de terrain (`alea_mvt`) | 97401000AD1263 | VISIBLE | Risques et protections | Mouvement de terrain | oui | alea_mvt_97401000AD1263.png |
| 27 | Barrages, ponts, dalles (`construction_surfacique`) | 97415000AB0565 | ABSENTE | — | — | — | construction_surfacique_97415000AB0565.png |
| 28 | CASIAS (`casias`) | 97401000AS0833 | VISIBLE | Risques et protections | Site pollué recensé (CASIAS/instruction) à proximité — étude de sol à prévoir, coût de d | non | casias_97401000AS0833.png |
| 29 | Cartes de bruit (`bruit_carte`) | 97422000AP0413 | VISIBLE | Risques et protections | Dépassement de bruit (carte stratégique) : CBS RN — dépassement Lden 68 dB(A) — journée  | oui | bruit_carte_97422000AP0413.png |
| 30 | Classement sonore (`bruit_route`) | 97411000AB0366 | VISIBLE | Risques et protections | Secteur affecté par le bruit routier (classement sonore cat. 1, bande 300 m) — isolement | oui | bruit_route_97411000AB0366.png |
| 31 | Plan d'exposition au bruit (`peb`) | 97416000CR0142 | VISIBLE | Urbanisme | PEB — plans d'exposition au bruit (DGAC via annexes GPU) | oui | peb_97416000CR0142.png |
| 32 | Systèmes d'endiguement (`endiguement`) | 97408000AO1021 | VISIBLE | Risques et protections | Parcelle protégée par un système d'endiguement — SE Ravine Balthazar (classe C) : inonda | non | endiguement_97408000AO1021.png |
| 33 | Murs de soutènement (`construction_lineaire`) | 97415000CH3047 | ABSENTE | — | — | — | construction_lineaire_97415000CH3047.png |
| 34 | Érosion côtière (`trait_de_cote`) | 97418000AC0655 | VISIBLE | Risques et protections | Hors zone de recul du trait de côte. | oui | trait_de_cote_97418000AC0655.png |
| 35 | Ravines et reculs (DPF) (`dpf`) | 97412000AB0005 | VISIBLE | Urbanisme | Domaine public fluvial (parcelle traversée par le DPF) — servitude de marchepied de 3,25 | oui | dpf_97412000AB0005.png |
| 36 | PPR multirisque (`ppr`) | 97415000BO0437 | VISIBLE | Risques et protections | Zone inondable TRI — scénario frequent (17 % de la parcelle) : cartographie de la direct | oui | ppr_97415000BO0437.png |
| 37 | ICPE (`icpe`) | 97401000AL0449 | VISIBLE | Risques et protections | Installation classée (ICPE) à proximité — MAIRIE LES AVIRONS, régime Autres régimes, 0 m | oui | icpe_97401000AL0449.png |
| 38 | SIS (`sis`) | 97406000AP0252 | VISIBLE | Risques et protections | Parcelle dans un secteur d'information sur les sols (Décharge Petite Plaine - Plaine des | oui | sis_97406000AP0252.png |
| 39 | Cavités (`cavite`) | 97401000AC0449 | VISIBLE | Risques et protections | Géorisques — cavités souterraines | oui | cavite_97401000AC0449.png |
| 40 | TCSP (`tcsp`) | 97411000BL0063 | VISIBLE | Réseaux et accès | Stationnement allégé (TCSP) | non | tcsp_97411000BL0063.png |
| 41 | Axes structurants (`axe_structurant`) | 97422000BK1059 | VISIBLE | Réseaux et accès | Axe structurant N3 (route à 2 chaussées) au contact de la parcelle — deux faces : access | oui | axe_structurant_97422000BK1059.png |
| 42 | Transport — lignes (`transport_ligne`) | 97416000HP0563 | VISIBLE | Réseaux et accès | Ligne de transport « Alternéo » à ~0 m. | non | transport_ligne_97416000HP0563.png |
| 43 | Téléphérique (`telepherique`) | 97411000DR0529 | VISIBLE | Réseaux et accès | Téléphérique Papang — station « Chaudron » à ~0 m (tracé OSM (ODbL)). | oui | telepherique_97411000DR0529.png |
| 44 | Pôles d'échange (`pole_echange`) | 97416000DR0461 | VISIBLE | Réseaux et accès | Pôle d’échange « Casabona » à ~0 m Estimé (arrêts groupés à ≤ 150 m desservis par ≥ 14 l | oui | pole_echange_97416000DR0461.png |
| 45 | Transport — arrêts (`transport_arret`) | 97417000AK0087 | VISIBLE | Réseaux et accès | Arrêt « Chapelle Du Tremblet » (Carsud) à ~1 m. | non | transport_arret_97417000AK0087.png |
| 46 | Zonage PLU parcelle (`zonage_parcelle`) | 97401000AN0602 | VISIBLE | Urbanisme | Zonage PLU | oui | zonage_parcelle_97401000AN0602.png |
| 47 | Limites PLU (GPU) (`plu_gpu_zone`) | 97401000AN0602 | VISIBLE | Urbanisme | Zonage PLU | oui | plu_gpu_zone_97401000AN0602.png |
| 48 | 50 pas géométriques (`cinquante_pas`) | 97411000AC0091 | VISIBLE | Risques et protections | 50 pas géométriques — limite haute (DEAL) | oui | cinquante_pas_97411000AC0091.png |
| 49 | Artificialisation (OCS GE) (`artificialisation`) | 97413000AE0007 | VISIBLE | Urbanisme | Sol classé naturel — artificialisation à justifier (occupation du sol BD CARTO V5, grain | non | artificialisation_97413000AE0007.png |
| 50 | DPU (`dpu`) | 97411000CT1573 | VISIBLE | Urbanisme | GPU — droit de préemption urbain (info-surf) | oui | dpu_97411000CT1573.png |
| 51 | SUP (`sup`) | 97401000AD1550 | VISIBLE | Risques et protections | Servitude(s) d'utilité publique sur la parcelle : PM1. | oui | sup_97401000AD1550.png |
| 52 | Emplacements réservés (`er`) | 97402000AK0316 | VISIBLE | toujours visible | emplacement réservé | oui | er_97402000AK0316.png |
| 53 | Espaces boisés classés (`ebc`) | 97402000AL0163 | VISIBLE | Urbanisme | GPU — espaces boisés classés (prescriptions CNIG) | oui | ebc_97402000AL0163.png |

## Les cas particuliers

- **INTERROGÉE MAIS INVISIBLE (1)** : `foret_publique` — le back calcule un HARD_EXCLUDE « Exclue : forêt domaniale (domaine public — terrain inacquérable) » (parcelle 97415000AH0019), mais aucun tiroir de la fiche ne l'affiche (vérifié : ni Urbanisme, ni entête/verdict). La donnée atteint le moteur, pas l'écran.

- **ABSENTE (5)** : `piscine_cosia`, `vefa_neuf`, `cimetiere`, `construction_surfacique`, `construction_lineaire` — aucun croisement fiche (hors périmètre de FICHE-COUCHES-2). NB : la recherche naïve de « piscine » et « cimeti » tombe sur du texte SANS RAPPORT (détection de bâti CoSIA ; nom d'arrêt « Cimetière de la Chaloupe ») — faux positifs écartés à la lecture du libellé, verdict ABSENTE confirmé.

- **VISIBLE mais HORS PDF (13)** : `bassin_versant`, `znieff`, `zone_humide`, `amenite`, `zone_activite`, `ligne_mt`, `ligne_ht`, `casias`, `endiguement`, `tcsp`, `transport_ligne`, `transport_arret`, `artificialisation` — visibles à l'écran, absents du Dossier expert (curé).
