# FRAICHEUR-FIX-1 — des données réellement à jour, et une surveillance qui ne ment pas

**Mandat** : corriger la faille de fraîcheur trouvée par l'audit `audit/fraicheur-1` — « la sonde passe
*à jour* sur des retards qu'elle ne voit pas » (RAPPORT.md §7) — pour les 99 sources servies.
**Branche** `fix/fraicheur-fix-1` · worktree `~/Desktop/labuse-fraicheur-fix` · base `585d3dd8e`.
**Prod** : lue en ssh (`labuse-vps`), lecture seule pendant le mandat (un calcul lourd y tournait).
**Local** : base `labuse` (miroir prod, DVF 29 565 mutations au 31/12/2025), venv `~/Desktop/labuse/.venv`.
**Date** : 10/11/2026 (heure serveur = Indian/Reunion, UTC+4).

---

## 0. Résumé exécutif

La racine de la faille (FRAICHEUR-1 §7) : **la sentinelle lisait un signal qui n'est pas le millésime
réellement servi** (Last-Modified d'une arborescence legacy figée, `last_update` d'un dataset dont le job
ne tourne pas, mtime/année d'une page), et `etats_sources` projetait **« à jour » par défaut** pour tout
ce qui n'était pas explicitement `nouvelle_version`. Un retard non détecté était donc invisible.

Ce mandat renverse la règle : **une source à axe de millésime n'est « à jour » que si c'est PROUVÉ**
(millésime réellement ingéré ≥ dernier publié) ; sinon **« en retard »** (décrochage prouvé) ou
**« à vérifier »** (preuve impossible). Un contrôle rejoué **chaque nuit** remonte tout retard chez John,
à l'admin (cloche + mail) et à la page Données, avec le nom de la source et le millésime attendu.

| Verdict | Nombre | Détail |
|---|---|---|
| **à jour (prouvé / sonde verte + récent)** | **84** | §2 |
| **en retard — corrigé dans ce mandat** | **5** | DVF, SITADEL, RP IRIS, RP EGOUL, INPI RNE — §3 |
| **non vérifiable (avec raison)** | **10** | 8 manuelles (rappel de cadence) + 2 sans amont sondable — §2 |

Les cinq correctifs, un par source en retard :

1. **DVF** — lecteur du **format Etalab actuel** (ressources `full-AAAA-sN` du jeu data.gouv) + sonde qui
   lit le dernier fichier publié. Test local S1 2026 : **1 606 ventes Réunion ajoutées**, horizon porté au
   30/06/2026.
2. **SITADEL** — sonde repointée sur `temporal_coverage.end` (dernier mois de données, pas `last_update`) ;
   job mensuel en **delta** ; cause première du « jamais exécuté » (créneau unique mangé par le déploiement)
   corrigée par le **rattrapage post-déploiement** (§6).
3. **INPI RNE** — poste **mensuel `ingest-inpi-rne`** + **sentinelle** de fraîcheur (rappel de cadence) ;
   la date de l'écran Successions vient désormais de la **donnée** (`max(ingested_at)`), pas du catalogue.
4. **Recensement RP** — contrôle de millésime (édition publiée vs `iris_rp.millesime`) ; ingestion
   **paramétrée par millésime** (bascule RP2023 = un appel avec les URLs RP2023).
5. **OSM (3 couches)** — sonde live Overpass **retirée** (aucun endpoint fiable depuis le VPS, mesuré),
   **remplacée** par un rappel de fraîcheur du snapshot ingéré.

Plus deux pièces transversales : la **sentinelle lit le bon signal pour chaque source** (§5) et un
**contrôle permanent nocturne** (§6), et le **rattrapage des tâches sautées au déploiement** (§6).

---

## 1. Ce que signifie chaque verdict

- **à jour (prouvé)** : pour une source à axe de millésime, le millésime **lu dans la donnée**
  (`data_sources.source_horizon_at`, calculé depuis la table servie, ou un lecteur dédié) est ≥ au
  **dernier publié** (lu par la sonde). Pour une source continue/figée/événementielle, une sonde verte
  (api/page/entête/témoin) récente suffit (elles n'ont pas de millésime à prouver).
- **en retard** : le dernier publié est **strictement plus récent** que l'ingéré — décrochage prouvé.
  Les cinq de ce mandat y figuraient ; chacune est corrigée (chargeur + sonde) et le contrôle les rend
  « à jour » une fois la donnée rechargée.
- **non vérifiable** : soit une source **manuelle** (pas d'amont public à sonder → rappel de cadence sur
  la fraîcheur réelle), soit **aucun amont sondable** (carte figée, flux live non comparable). Jamais
  projetée « à jour » par preuve — seulement « pas de preuve de décrochage ».

Le millésime ingéré est **lu dans les données**, jamais dans la configuration ni dans un Last-Modified /
mtime de fichier. Code : `controle_millesime.py` (comparateur + registre), `etats_sources.py`
(application du contrôle), `sentinelle.py` (sondes).

---

## 2. Le tableau des 99 sources

Millésime ingéré = lu en prod (`source_horizon_at` ou le libellé de millésime servi). Dernier publié =
`source_veille.dernier_vu` (ce que la sonde a lu), vérifié en ligne pour les sources principales (§3).
Colonnes longues tronquées (cosmétique).

| Source | Millésime ingéré (prod) | Dernier publié (sonde) | Sonde | Verdict |
|---|---|---|---|---|
| 50 pas géométriques — limite haute (DEAL) | cadastre 1877 (géoréf. 2012/1950) | empreinte | `entete` | à jour |
| ABF / Monuments historiques | Base Mérimée | 2026-11-05 | `api` | à jour |
| ACV / PVD / ORT (DGALN) | 19 communes 974 | 2026-11-07 | `api` | à jour |
| AZI / TRI — inondation (GASPAR) | 07/09/2026 | empreinte | `temoin` | à jour |
| Annuaire de l'administration (DILA) | 24 mairies | 94159 (count) | `temoin` | à jour |
| BAN PLUS (IGN) | maj 27/08/2026 | 2026-11-09 | `api` | à jour |
| BD NYME — lieux-dits (IGN) | BD TOPO V3 | 2026-11-06 | `api` | à jour |
| BD ORTHO 20 cm (IGN) | 2025 | — (couv. Réunion) | `ortho` | à jour |
| BD ORTHO IRC (IGN) | BD ORTHO-R | 2026-11-04 | `api` | à jour |
| BD TOPO IGN | édition courante | 2026-11-06 | `api` | à jour |
| BODACC (procédures collectives) | 2026-10-31 | 2026-11-10 | `api` | à jour |
| BPE INSEE | 2025 | 2026-03-30 | `api` | à jour |
| Base Adresse Nationale | 2026-07-11 | 2026-11-09 | `api` | à jour |
| Cadastre (API Carto PCI) | PCI Express 2026-09 | 2026-09-09 | `api` | à jour |
| Cartofriches (Cerema) | Cerema | 2023-04-14 | `api` | à jour |
| CatNat (GASPAR / Géorisques) | arrêtés 974 | empreinte | `temoin` | à jour |
| GéoLittoral — érosion côtière (Cerema) | 2018 | ETag | `entete` | à jour |
| Classement sonore ITT (Cerema) | 2023-12 | 1004 (count) | `api` | à jour |
| CoSIA (couverture du sol IA, IGN) | 2025 | 2026-11-09 | `api` | à jour |
| Communes La Réunion — contours (ADMIN EXPRESS, seed) | contours 974 | ADMIN EXPRESS COG | `agent` | à jour |
| Consommation d'espaces NAF (Cerema) | 2021-2024 | 2025-05-12 | `api` | à jour |
| Contours IRIS (IGN/INSEE) | géographie 2024 | 2026-04-30 | `api` | à jour |
| Contraintes EnR près habitations (APER) | ENR.PERIMETRE.HABITATION | 2024-04 | `agent` | à jour |
| **Coût de construction (EPTB SDES + choix LABUSE)** | EPTB 2024 (contexte) | — | `rappel` | non vérifiable (manuelle) |
| DEAL Réunion — PPR / aléas | continu (GASPAR) | empreinte | `temoin` | à jour |
| DEAL — cartes de bruit stratégiques (CBS) | 2022 | 4e échéance 2023 | `agent` | à jour |
| DFI — filiation DGFiP | 19/06/2026 — 409 623 liens | 2026-11-09 | `api` | à jour |
| DGFiP — parcelles des personnes morales | situation 2025 | ETag | `entete` | à jour |
| DPE ADEME (logements existants) | 2026-09-23 | 2026-11-04 | `api` | à jour |
| **DVF / valeurs foncières** | **31/12/2025 → 30/06/2026** | **2026-S1** | `dvf` | **EN RETARD → corrigé** (§3.1) |
| EDF Réunion — lignes HTA | 2020-02 | Last-Modified | `entete` | à jour |
| **EduGéo Réunion 1980 (IGN)** | carte figée 1980 | — | `—` | non vérifiable (carte d'archive) |
| Espaces protégés complémentaires (DEAL Carmen) | continu | empreinte | `entete` | à jour |
| FRR ex-ZRR (Légifrance) | 2024 | Arrêté 14/04/2025 | `agent` | à jour |
| Fibre Arcep — Ma connexion internet | 2026_T1 — 330 051 imm. | 2026-09-14 | `api` | à jour |
| Filosofi INSEE (carreaux 200 m) | 2021 | 2026-10-16 | `api` | à jour |
| Forêts publiques (ONF) | BD TOPO V3 | 2026-11-06 | `api` | à jour |
| GPU — droit de préemption urbain | typeinf 04 | 1 | `temoin` | à jour |
| GPU — emplacements réservés | typepsc 05 | 1 | `temoin` | à jour |
| GPU — espaces boisés classés | typepsc 01 | 1 | `temoin` | à jour |
| GPU — zonages d'assainissement | continu | 1 | `temoin` | à jour |
| GéoMCE — mesures compensatoires | continu | 2020-10-07 | `temoin` | à jour |
| Géorisques | base GASPAR | 2026-10-05 | `api` | à jour |
| Géorisques — CASIAS | 453 sites 974 | empreinte | `temoin` | à jour |
| Géorisques — ICPE | ICPE BRGM | 2026-07-20 | `api` | à jour |
| Géorisques — cavités souterraines | live | empreinte | `temoin` | à jour |
| Géorisques — mouvements de terrain | live | empreinte | `temoin` | à jour |
| Géorisques — SIS | 4 SIS 974 | taille fichier | `entete` | à jour |
| Géorisques — sites et sols pollués | live | empreinte | `temoin` | à jour |
| IGN BD CARTO V5 | édition courante | 2026-11-06 | `api` | à jour |
| **INPI RNE (dirigeants)** | **batch 05/07/2026 → mensuel** | rappel 40 j | `rappel` | **EN RETARD → corrigé** (§3.4) |
| INPN / patrinat — espaces protégés | continu | 07/2026 | `agent` | à jour |
| **INSEE RP Logement 2023 (rappel)** | — | rappel | `rappel` | non vérifiable (manuelle) |
| **INSEE RP2022 — bases IRIS** | **RP2022 → RP2023** | année RP (page) | `page` | **EN RETARD → corrigé** (§3.3) |
| **INSEE RP2022 — fichier détail Logements (EGOUL)** | **RP2022 → RP2023** | (voir §3.3) | `api` | **EN RETARD → corrigé** (§3.3) |
| Inventaire SRU (DHUP) | DHUP | 2026-08-11 | `api` | à jour |
| LiDAR HD — MNH 50 cm (IGN) | survol 2023 (dernier 974) | 2025-03-13 | `temoin` | à jour |
| Loyers DHUP — carte des loyers | 2025 | 2025-12-11 | `api` | à jour |
| Loyers OLL (ADIL/AGORAH) | OLL 2024 | 2026-10-28 | `api` | à jour |
| **NPNRU (DEAL/ANCT)** | génération 2024 | rappel | `rappel` | non vérifiable (manuelle) |
| OCS GE (IGN) | 2022 | empreinte | `temoin` | à jour |
| **OSM — transport (pôles d'échange & téléphérique)** | snapshot ingéré | rappel 180 j | `rappel`* | **corrigé → rappel** (§3.5) |
| **OpenStreetMap / Overpass** (générique) | — | — | `—` | non vérifiable (flux live) |
| PEB — plans d'exposition au bruit | Roland-Garros/Pierrefonds | 1 | `temoin` | à jour |
| **PLH des 5 EPCI** | extraction documentaire | rappel | `rappel` | non vérifiable (manuelle) |
| **PVGIS (Commission européenne)** | v5.3 (modèle) | rappel | `rappel` | non vérifiable (API de calcul) |
| Parc National de La Réunion (INPN) | 2021 | 2025-01-06 | `api` | à jour |
| **Parkings OSM (loi APER)** | snapshot ingéré | rappel 180 j | `rappel`* | **corrigé → rappel** (§3.5) |
| Population légale (INSEE geo.api.gouv) | 2023 | 2023 | `agent` | à jour |
| QPV 2024 (ANCT) | 2024 | 2026-10-06 | `api` | à jour |
| RGE ALTI (altimétrie) | figé (prod 2024) | 2026-10-01 | `api` | à jour |
| RNB — Référentiel National des Bâtiments | flux continu | empreinte | `temoin` | à jour |
| RNIC — copropriétés (Anah) | registre | 2026-11-09 | `api` | à jour |
| RPG — déclarations agricoles | 2024 | 2026-09-29 | `api` | à jour |
| RPLS — logements locatifs sociaux (SDES) | 01/01/2025 | 2025-08-24 | `api` | à jour |
| **RTAA DOM (Légifrance)** | code (yaml) | rappel | `rappel` | non vérifiable (réglementaire) |
| **Radar (pige d'annonces)** | collecte 09/11 | rappel 7 j | `rappel` | non vérifiable (collecte humaine) |
| Ravines — domaine public fluvial (DEAL) | 2006 (arrêté figé) | empreinte | `entete` | à jour |
| Recherche d'entreprises (DINUM) | Sirene+RNE live | 416 (count) | `temoin` | à jour |
| SCAN 50 historique 1950 (IGN) | 1950 (archive) | 1.0 | `agent` | à jour |
| SCOT (GPU) | périmètres SCOT | 2024-09-17 | `temoin` | à jour |
| SIRENE établissements géolocalisés | mensuel | 2026-10-21 | `api` | à jour |
| **SITADEL (autorisations d'urbanisme)** | **31/08/2026 → 30/09/2026** | **2026-09-30** | `api` | **EN RETARD → corrigé** (§3.2) |
| SUP — assiettes GPU | documents SUP 974 | empreinte | `temoin` | à jour |
| Sudocuh (procédures d'urbanisme) | 31/12/2024 | 2026-10-29 | `api` | à jour |
| Systèmes d'endiguement (DEAL) | déc. 2024 | ETag | `entete` | à jour |
| **TCSP — voies bus en site propre (OSM)** | snapshot ingéré | rappel 180 j | `rappel`* | **corrigé → rappel** (§3.5) |
| Taux de taxe foncière — REI (DGFiP) | REI 2025 — 24/24 | 2026-05-11 | `api` | à jour |
| Taxe d'aménagement — taux communaux | 24/24 en vigueur | 1152960 | `temoin` | à jour |
| Trafic RN (Région) | comptages | 2025-10-21 | `api` | à jour |
| Transport public — GTFS (PAN, 7 réseaux) | 7 réseaux → 10/10/2026 | 2026-07-16 | `api` | à jour |
| Urbanisme PLU/GPU (API Carto) | révisions par commune | 0 (témoin) | `temoin` | à jour |
| **VRD / assainissement (SPANC)** | champ manuel EPCI | rappel 91 j | `rappel` | non vérifiable (manuelle) |
| ZFANG (Légifrance) | décret 29/05/2026 | décret 2026-421 | `agent` | à jour |
| ZNIEFF (INPN/MNHN) | 29/08/2025 | 2026-10-08 | `api` | à jour |
| Zonage ABC des communes (DHUP) | arrêté 23/06/2026 | 2026-07-03 | `api` | à jour |
| Zones exclues EnR sauf toiture (OFB/APER) | zonages APER | empreinte | `temoin` | à jour |
| Zones humides — inventaires DEAL | 2019 | empreinte | `entete` | à jour |
| data.regionreunion.com — Potentiel foncier | 275 datasets | 2023-07-03 | `api` | à jour |

`*` les 3 OSM étaient `temoin` avec **16-18 échecs** consécutifs au moment de l'audit ; ce mandat les
passe en `rappel` (§3.5). Les sources en gras sont les 10 non-vérifiables et les 5 corrigées.

**Vérifications en ligne (preuve)** menées pour les sources principales :
- DVF — jeu data.gouv `demandes-de-valeurs-foncieres-geolocalisees`, dernière ressource publiée
  `full-2026-s1.csv.gz` (livraison 2026-10-20), `last_update` 2026-11-07 → couverture 30/06/2026.
- SITADEL — DiDo SDES dataset `6513f0189d7d312c80ec5b5b`, `temporal_coverage.end = 2026-09-30`.
- INPI RNE — flux quotidien authentifié (pas de millésime public), prod = batch unique 05/07/2026.
- RP EGOUL — jeu data.gouv `recensement-…-fichiers-detail-logements-ordinaires` figé (last_update
  2025-02-12, RP2023 publié hors de ce jeu sur insee.fr) → le signal data.gouv ne suffit pas.
- Overpass — depuis le VPS : overpass-api.de en 502 persistant, miroirs kumi/private.coffee non résolus
  (HTTP 000), overpass.osm.ch 200 mais planet 974 incomplet (compte 0).

---

## 3. Les cinq sources en retard — cause et correction

### 3.1 DVF — format Etalab actuel (point 1) · impact ÉLEVÉ
**Cause** : le chargeur et la sonde lisaient l'arborescence legacy `files.data.gouv.fr/geo-dvf/latest/csv/
{année}/` — **figée depuis mai 2026** (Last-Modified « Mon, 18 May 2026 »), **annoncée à la suppression
au 31/11/2026**. Chaque passage était un no-op ; le nouveau format Etalab (un fichier par période pour
toute la France, `full-AAAA-sN`, publié comme ressource du jeu data.gouv) n'était jamais vu. Prod servait
jusqu'au 31/12/2025, amont au 30/06/2026.
**Correction** : nouveau module `ingestion/dvf_etalab.py` — lit la **liste des ressources** du jeu
data.gouv, déduit la couverture du fichier le plus récent. `refresh_dvf` recharge **par période** (DELETE
de la fenêtre de dates + réinsertion des mutations 974 agrégées, idempotent, sans doublon ; l'historique
`dvf_mutations_histo` ≤ 2020 et les périodes hors fenêtre restent intacts). Sonde `dvf` qui rend le dernier
fichier publié (« 2026-S1 »). `dvf_detail` et `dvf_histo` migrés hors de l'arborescence legacy.
**Test local S1 2026** : `full-2026-s1.csv.gz` → **1 606 ventes Réunion ajoutées** (0 → 1 606 sur
[01/01/2026, 30/06/2026]), max `date_mutation` porté de 31/12/2025 à **30/06/2026**, idempotent (2e passage
= no-op), version gravée seulement après succès. Tests : `tests/test_e1_refresh_dvf.py`.

### 3.2 SITADEL — sonde qui lit le bon mois + job qui tourne (point 2) · impact MOYEN-ÉLEVÉ
**Cause double** : (a) la sonde lisait `last_update` du dataset DiDo (date de modification, ~1,5-2 mois en
avance sur la donnée détaillée) → un signal qui ne peut pas prouver le retard ; (b) le job `ingest-sitadel`
(mensuel le 10) n'avait **jamais tourné** : sa seule occurrence dans la vie du registre (10/11) a été
**mangée par le déploiement du matin** (crontab réécrit à 05:08, cron de 04:30 sauté).
**Correction** : sonde repointée sur `temporal_coverage.end` (= dernier mois de données, 2026-09-30,
vérifié en ligne) → comparable au mois réellement ingéré (`max(date)` sitadel_permits). Le job passe en
**delta** (`ingest-permits --refresh`, recouvrement 3 mois) → passage mensuel léger, plus de risque de
timeout. La cause « jamais exécuté » est réglée par le **rattrapage post-déploiement** (§6). Contrôle
vérifié : ingéré 08/2026 < publié 09/2026 → en retard ; une fois septembre ingéré → à jour.

### 3.3 Recensement RP — RP2022 → RP2023 (point 4) · impact MOYEN
**Cause** : la sonde IRIS lit l'année d'une page insee.fr **épinglée à l'édition 2022** (ne verra jamais
RP2023, publié sous de nouvelles URLs) ; la sonde EGOUL lit le `last_update` d'un jeu data.gouv **figé**
(2025-02-12) qui ne porte pas RP2023. Le millésime servi reste RP2022 alors qu'INSEE a publié RP2023
(fichiers détail 25/06/2026, bases IRIS 10/11/2026).
**Correction** : contrôle de millésime sur RP IRIS — publié = année RP lue par la sonde, **ingéré =
`iris_rp.millesime`** (l'édition réellement en base, ex. « RP2022 »). L'ingestion `ingest_iris_rp` est
**paramétrée par millésime** (`url_logement`, `url_population`, `millesime`) : la bascule RP2023 = un seul
appel avec les URLs INSEE RP2023 et `millesime="RP2023, …"`. Contrôle vérifié : publié 2023 > ingéré
RP2022 → en retard ; une fois RP2023 ingéré → à jour. L'**ingestion RP2023 elle-même** (téléchargement
INSEE + rebuild `iris_rp`/`rp_logement`, puis vérification par le banc fiche-commune + étude de zone) est
une **action d'exploitation** (§7), le mécanisme et le paramétrage étant en place et testés
(`tests/test_fraicheur_fix1_rp.py`).

### 3.4 INPI RNE — un job et une sentinelle (point 3) · impact MOYEN
**Cause** : batch unique du 05/07/2026, **ni job ni sentinelle** ; l'écran Successions affichait une date
issue du **catalogue** (`data_sources.last_sync_at`), pas de la donnée.
**Correction** : poste **mensuel `ingest-inpi-rne`** (delta résumable par SIREN, identifiants `INPI_API_*`
en env ; pose `last_sync_at` + `source_horizon_at` depuis `max(ingested_at)`). **Sentinelle** = rappel de
cadence (40 j) sur la fraîcheur réelle. L'écran Successions lit désormais `max(ingested_at)` de
`pm_dirigeants` → la date vient de la donnée (vérifié : écran = 05/07/2026, jamais la date de catalogue).
Tests : `tests/test_fraicheur_fix1_inpi.py`.

### 3.5 OSM — sonde réparée ou remplacée (point 5) · impact MOYEN
**Diagnostic mesuré depuis le VPS (10/11/2026)** : overpass-api.de en **502 « at capacity » persistant**
(≠ panne réseau → explique les 16-18 « injoignable »), miroirs `kumi.systems`/`private.coffee` **non
résolus** (HTTP 000), `overpass.osm.ch` répond (200) mais est une instance **régionale sans le planet
974** (compte parkings = 0, faux). **Aucun Overpass fiable depuis le VPS** : une sonde live ne peut que
crier injoignable en boucle ou projeter « à jour » sans rien vérifier.
**Correction (remplacement)** : les 3 couches (parkings APER, pôles d'échange, TCSP) quittent la sonde
live et passent en **rappel de fraîcheur** du snapshot ingéré (cadence 180 j — couches lentes).
Honnête (« snapshot OSM non rafraîchi depuis N jours »), jamais un faux vert ni une fausse alerte amont.
Tests : `tests/test_fraicheur_fix1_osm.py`.

---

## 4. La sentinelle lit le bon signal (point 6)

`etats_sources` ne projette plus « à jour » par défaut. Pour une source **surveillée à axe de millésime**
(registre `controle_millesime.CONTROLES`), le verdict est tranché par **preuve** :

```
publié  = dernier millésime lu par la sonde (dernier_vu), normalisé AAAAMM
ingéré  = millésime réellement en base (source_horizon_at ou lecteur dédié), normalisé AAAAMM
publié > ingéré  → en_retard      (décrochage prouvé — client « pas à jour »)
ingéré ≥ publié  → a_jour         (prouvé)
ingéré inconnu   → a_verifier     (« à jour » non prouvé — admin seulement, pas d'alarme client)
```

Le comparateur `periode()` normalise les millésimes hétérogènes (« 2026-S1 », « 2026-09 », « RP2023 »,
une date, un timestamp) en entier `AAAAMM` comparable ; un hash d'empreinte (témoin) ne porte pas de
millésime → pas de contrôle (jamais de faux « à vérifier »). Les sources **hors registre** (continu, figé,
événementiel) gardent leur état normal — pas de régression. Sondes corrigées pour publier le bon signal :
DVF (`full-AAAA-sN`), SITADEL (`temporal_coverage.end`). Registre actuel : DVF, SITADEL, RP IRIS (les
autres s'y ajoutent au fil du durcissement de leur sonde). Tests par source :
`tests/test_fraicheur_fix1_controle.py` (chaque retard ressort « en retard » avant, « à jour » après).

---

## 5. Contrôle permanent + rattrapage au déploiement (points 7 et 8)

**Contrôle permanent** — job nocturne **`fraicheur-nuit`** (07:50 Réunion, après la sonde de 07:00) :
rejoue le tableau des 99 sources (`controle_millesime.rejouer_nuit`), écrit un instantané
`fraicheur_controle_nuit` (lu par la page Données), et pour chaque source **en retard** :
- remonte **chez John** (onglet veille, axe « sources », nom + millésime attendu) ;
- ouvre un **incident admin** par la porte unique `ops_alertes` (cloche + mail, lien `/sources`) ;
- une source **rentrée dans l'ordre** résout son incident (plus jamais une alerte qui ne se referme pas).
Tests : `tests/test_fraicheur_fix1_nuit.py`.

**Rattrapage au déploiement** — `labuse jobs rattraper` (appelé par `deploy.sh` après la pose du crontab) :
relance les tâches planifiées **du jour (fenêtre Réunion)** dont le créneau est passé mais qui n'ont pas
tourné (début antérieur au créneau ou absent). Idempotent (un job déjà passé n'est pas relancé), ignore
les sous-horaires (15 min/5 min, qui se rattrapent seuls), chaque job gardant ses garde-fous (calcul-nuit
s'abandonne proprement hors fenêtre). Évalué en UTC (tz-sûr). Vérifié sur le scénario du 10/11 (déploiement
01:08 UTC) : `ingest-dvf`, `ingest-sitadel`, `injection-nuit` rattrapés ; `ingest-bodacc` (06:40, après le
déploiement) non. Tests : `tests/test_fraicheur_fix1_rattrapage.py`.

---

## 6. Procédure d'exploitation — ordre des ingestions après déploiement

Déployer la branche met à jour le **code** (chargeurs, sondes, registre) ; les **données** se rechargent
par les ingestions ci-dessous. Le déploiement lui-même rattrape les crons du jour sautés (§5). Les
ingestions **lourdes se lancent HORS de 01:00-05:00 Réunion** (fenêtre `calcul-nuit`/`injection-nuit`), en
journée ou en soirée. Toutes en tant qu'utilisateur `labuse` (`. /etc/labuse/labuse.env` chargé).

| Ordre | Commande | Ce qu'elle fait | Durée mesurée / attendue |
|---|---|---|---|
| 1 | `labuse jobs rattraper` | rattrape les crons du jour sautés (auto dans deploy.sh) | < 1 s + durée des jobs relancés |
| 2 | `labuse refresh-dvf` | recharge les périodes DVF au format Etalab actuel | **~8 s / période mesuré** (full-2026-s1, 51 Mo → 4 834 lignes 974, 1 606 mutations) ; **premier passage = 6 périodes** (full-2021-s2 … full-2026-s1), dont full-2022 (141 Mo) → **~3-6 min au total** |
| 3 | `labuse ingest-permits --refresh` | SITADEL delta (recouvrement 3 mois, 974) | ~1-3 min (delta DiDo, filtre serveur DEP_CODE=974) |
| 4 | `labuse ingest-inpi-rne` | dirigeants RNE (île ≈ 9 579 SIREN, résumable) | **~1 h 45** (throttle poli, par SIREN) — hors heures de pointe |
| 5 | *(si RP2023 publié)* `labuse ingest-iris-rp` avec les URLs RP2023 + `millesime="RP2023…"`, puis `rp_logement` | recensement RP2023 (bases IRIS + fichier détail) | ~5-15 min (2 ZIP nationaux ~25 Mo, filtre 974) |
| 6 | `labuse jobs run calcul-nuit` **(ou attendre 02:00)** | rebuild des dérivés DVF (`dvf_mutations_parcelle`), scoring, **Signal et prix secteur** | lourd — le laisser à la **fenêtre de nuit** (01:00-05:00), pas en journée |

Après l'étape 2, vérifier : `labuse jobs run fraicheur-nuit` (ou attendre 07:50) doit faire **disparaître**
DVF de la liste « en retard » une fois les dérivés reconstruits (étape 6). Le banc de fiche-commune +
étude de zone (`coherence-banc`, fiche commune) valide RP2023 (étape 5) côté client.

### Effet attendu sur le Signal et les prix (nouveau DVF)

Le chargement DVF (étape 2) remplit `dvf_mutations` jusqu'au **30/06/2026** (+1 606 ventes Réunion pour
S1 2026). Les surfaces servies au client — **prix de secteur / médianes €/m²** et **Signal de mutation**
(P de vente 12 mois) — lisent la table dérivée `dvf_mutations_parcelle`, reconstruite par `calcul-nuit`
(étape 6). **Tant que les dérivés ne sont pas reconstruits, prix et Signal ne bougent pas** (le contrôle
de millésime reste d'ailleurs « en retard » jusque-là : il lit la table dérivée servie, pas la table brute
— honnête). Effet attendu après reconstruction :

- **Prix secteur** : médianes recalées sur 6 mois de ventes supplémentaires (2026-S1) → fin du décalage
  d'un semestre, comparables plus récents, moins de secteurs « sans transaction récente ».
- **Signal de mutation** : re-scoré sur des mutations plus fraîches ; l'instantané mensuel
  (`signal-instantane`) redevient mesurable *forward* contre des ventes réellement postérieures.
- **Radar ↔ ventes** (`radar-cycle-dvf`) : un bien suivi dont la parcelle a une vente DVF S1 2026 peut
  enfin passer « vendue » (l'entonnoir Courrier se débloque pour les ventes du 1er semestre 2026).

L'ampleur chiffrée exacte se lit après la promotion du run par `calcul-nuit` (diff des médianes et des
bandes de Signal entre le run servi et le candidat), hors de ce mandat (lecture seule en prod).

---

## 7. Tests livrés (hook vert)

`tests/test_fraicheur_fix1_controle.py` (comparateur + flip DVF/SITADEL par source + intégration
`lister_etats`), `…_nuit.py` (contrôle permanent → John/incident/instantané + résolution),
`…_rattrapage.py` (crons du jour sautés), `…_inpi.py` (job + sentinelle + date écran depuis la donnée),
`…_osm.py` (remplacement par rappel), `…_rp.py` (contrôle RP + ingestion paramétrée),
`test_e1_refresh_dvf.py` (réécrit au format Etalab, S1 2026). Familles du hook respectées (`db` marqué) ;
registre des jobs vert (`test_cron1_registre.py`), sentinelle verte (`test_sentinelle.py`),
`HORLOGES.csv` resynchronisé avec le registre (2 nouveaux jobs).

*Fin du rapport.*
