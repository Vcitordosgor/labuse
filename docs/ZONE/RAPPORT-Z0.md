# ÉTUDE DE ZONE — Z0 : enquête registre des sources + schéma (AVANT ingestion)

Branche `feat/etude-zone`. Enquête **read-only** demandée avant toute ingestion — parce que Vic s'est
déjà fait surprendre deux fois par des couches qu'on croyait absentes (BPE et équipements OSM existent
déjà). Objectif : dire ce qui EXISTE (à ne pas ré-ingérer) et ce qui est réellement ABSENT, et repérer
les doublons à éviter (décision 02 de la maquette : « le mandat commence par l'inventaire des tiroirs
actuels »). Référence : `docs/ZONE/maquette-zone-v1.html`.

## 🚧 Finding Z0-000 (BLOQUANT pour Z1→Z5) — le mandat est absent
`docs/ZONE/MANDAT-ZONE.md` **n'existe nulle part** : ni dans l'arbre, ni dans l'historique git, ni dans
le worktree `labuse-merge`, ni en fichier non suivi. Le commit `b8191034` (« docs: maquette etude de
zone v1 ») ne porte **que la maquette** (354 lignes), pas le mandat. Les exigences détaillées de chaque
lot (Z1→Z5), leur ordre, leurs doctrines (Sourcé/Estimé, run-scoped, périmètre) et leurs critères
d'acceptation vivent dans ce document. **Sans lui, Z1→Z5 ne peuvent pas être exécutés fidèlement** —
improviser une ingestion de nouvelles sources (isochrones, SIRENE établissements, MOBPRO) violerait la
règle « tu n'improvises pas ». Ce rapport Z0 (l'enquête, explicitement demandée et auto-suffisante) est
livré ; l'exécution s'arrête ensuite, en attente du mandat.

## Le registre des sources
Déclaratif et centralisé : `src/labuse/ingestion/seed_sources.py` (≈ 70 sources) → table `data_sources`
(clé `name`) → endpoint `GET /sources` → page front `components/sources/`. Chaque source porte : nom,
catégorie, producteur, millésime, type d'accès, statut, niveau de fiabilité, notes légales/techniques.
Modèle de statuts : `src/labuse/sources_catalog.py`.

## Ce qui est DÉJÀ présent (NE PAS ré-ingérer)
| Besoin « Étude de zone » | Déjà en base | Détail |
|---|---|---|
| **Qui vit dans la zone** (habitants, ménages, revenu, âge) | ✅ `filosofi_carreaux_200m` (14 773 carreaux, SRID 2975) | `ind` habitants · `men` ménages · `ind_snv` niveau de vie (→ revenu médian ESTIMÉ) · `men_pauv`/`men_prop` · tranches d'âge `ind_0_3`…`ind_80p` (→ « % < 25 ans »). Millésime Filosofi 2021. **Déjà servi** à la fiche (`marche_secteur.filosofi_200m`, au centroïde). |
| **Équipements & commerces** (BPE) | ✅ `spatial_layers` kind `amenite_bpe` (~35,5 k, gammes A–G) | BPE INSEE 2025, géolocalisé, DEP 974. `src/labuse/ingestion/bpe.py`. |
| **Équipements OSM** (compléments) | ✅ kind `amenite` (~15,2 k) | OSM/Overpass. `ingestion/amenites.py`. Distinct de BPE (jamais fusionnés). |
| **Générateurs de flux / transports** | ✅ `transport_arret` (9 956) · `transport_ligne` (300) · `pole_echange` (61) · `telepherique` | GTFS 7 réseaux (PAN) + pôles OSM + Papang. `ingestion/transport_reseaux.py`. |
| **Distances aux équipements** (fiche actuelle) | ✅ `parcel_amenites` (dist_ecole/sante/commerce/tcsp, mètres) | Vol d'oiseau, précalculé PAR parcelle ; **alimente le scoring** (p_model) + la fiche. |
| **Marché de la zone** (PDF, écran 3) | ✅ DVF + `voisinage_proche` (< 100 m) + SITADEL | Tiroir « Marché et secteur » + bloc « voisinage proche ». |
| **Maille intermédiaire** | ✅ `iris_insee` (344, kind spatial) | Contours IRIS ; ANC/assainissement s'appuie sur IRIS. |
| **Entrée par adresse** | ✅ Base Adresse Nationale (autocomplétion) | Pour l'entrée adresse → parcelle (parcours Flash). |

## Ce qui est ABSENT (à ingérer/construire — cœur du futur Z1+)
| Besoin | État | Enjeu |
|---|---|---|
| **Isochrones (temps de trajet)** | ❌ AUCUN code ni table | Le cœur de la maquette (« le temps remplace le vol d'oiseau », décision 03). Aujourd'hui : seulement des distances en mètres (vol d'oiseau). Source candidate : Géoplateforme IGN (déclarée) → service isochrone. À construire. |
| **SIRENE établissements géolocalisés par NAF** (concurrents, écran 2) | ❌ Pas de table établissements | SIRENE existe SEULEMENT en **enrichissement du propriétaire par SIREN** (Score V, `owner_enrichment`) — pas un annuaire d'établissements adressés/géocodés interrogeable par code NAF. À ingérer (avec géocodage BAN). |
| **MOBPRO (actifs travaillant sur zone)** (« 6 240 actifs y travaillent », écran 2) | ❌ Absent | Aucune table/ingestion. Source INSEE MOBPRO à ingérer si retenu. |
| **Moteur de zone** (agrégation Filosofi/BPE/SIRENE DANS un polygone isochrone) | ❌ Absent | Le « un seul moteur, deux visages ». Aujourd'hui l'agrégat Filosofi est servi au **centroïde**, pas dans une zone paramétrable. |

## Doublons à éviter (décision 02 — « rien n'est dupliqué »)
Le bloc fiche « Autour de cette parcelle » et l'outil ne doivent PAS répéter l'existant :
- **Marché/DVF** : déjà tiroir « Marché et secteur » + `voisinage_proche` (< 100 m). → renvoi, jamais un doublon.
- **Réseaux/transports** : déjà tiroir « Réseaux et accès » + bloc « proximités » (distances arrêt GTFS/pôle/téléphérique). → renvoi.
- **Revenu/pauvreté Filosofi** : DÉJÀ servi dans `marche_secteur.filosofi_200m` **au centroïde**. L'Étude de zone le recalculerait **dans l'isochrone** (maille zone ≠ point) — il faudra **un seul point de calcul** partagé, pas deux chiffres divergents pour « le revenu du secteur ».
- **Équipements** : `parcel_amenites` donne déjà des distances (mètres) ; le bloc les présenterait en **temps** (isochrone). Décider si l'on remplace la distance par le temps ou si l'on garde les deux mailles.

## Synthèse pour Vic
- **Les deux surprises sont confirmées** : BPE (`amenite_bpe`) et équipements OSM (`amenite`) sont déjà
  ingérés. **Et il y a plus** : GTFS transports, Filosofi carreaux 200 m (avec population + revenu +
  âge, déjà servi à la fiche), IRIS, `parcel_amenites` (distances précalculées) existent aussi.
- **Le vrai travail neuf de l'« Étude de zone »** se réduit à : (1) les **isochrones** (temps de
  trajet, IGN) ; (2) **SIRENE établissements géolocalisés** (concurrents par NAF) ; (3) éventuellement
  **MOBPRO** (actifs) ; (4) le **moteur d'agrégation dans la zone** (réutilisant Filosofi/BPE/GTFS déjà
  là). Tout le reste est de la **restitution** de données existantes.
- **Attention doublon** : un seul point de calcul pour le revenu/pauvreté (Filosofi) — la fiche le sert
  déjà au centroïde.
- **Prérequis à Z1** : le mandat `MANDAT-ZONE.md` (absent) pour cadrer périmètre, ordre des lots et
  doctrines. Sans lui, je ne lance aucune ingestion.
