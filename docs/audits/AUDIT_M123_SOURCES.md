# AUDIT M123 — LES 67 SOURCES : FRAÎCHEUR · COUVERTURE · BRANCHEMENT (Phase 1, STOP)

**Branche** : `feat/m123-sources-etat` — Phase 1 = inspection MESURÉE, aucune réparation avant le STOP.
**Méthode** : `data_sources` + `source_radar` (sonde) + comptages SQL directs (run servi) + cartographie
du code (ingestion → table/`spatial_layers` kind → consommateur servi). Ce mandat NE touche PAS à l'algo.

**Les trois critères** : **Fraîcheur** (millésime en base vs sonde radar) · **Couverture** (communes /24,
parcelles/features) · **Branchement** (`branchée` = ingérée + servie · `fantôme` = ingérée mais servie
nulle part · `vide` = déclarée mais 0 ligne / non ingérée).

---

## SYNTHÈSE POUR LE STOP

- **Fraîcheur — le radar est majoritairement AVEUGLE** : **13/67 `a_jour`** (sonde exploitable),
  **54/67 `non_sondable`** (HEAD 400/403/404/500/501, pas de `Last-Modified`, ou accès manuel). Pour
  ces 54, la fraîcheur amont n'est PAS vérifiable automatiquement — plusieurs URL de sonde semblent
  mortes (EDF SEI 410 Gone, Géorisques ×4 = 500, PPR/DEAL 501). *Défaut du radar à traiter en Phase 2.*
- **Branchement** : **~57 branchées · 2 fantômes (DPE, PV) · ~8 vides**.
- **Couverture** : le socle parcellaire est plein (cadastre/DVF/SITADEL/PM/BAN/pente/canopée = **24/24
  communes**) ; trous mesurés : `parcel_residuel` **23/24**, GPU assainissement **4/24**, QPV 13/24,
  ENS 21/24, Office de l'eau **6 communes**, DPE **17 lignes**.
- **5 doublons** (3 tagués + 2 proxys), **~14 sources cassées** (défauts qualité notés), **8 vides**
  avec cause mesurée.

---

## 1. LE TABLEAU DES 67

Fraîcheur : `à jour` = radar `a_jour` · `?` = `non_sondable` (fraîcheur amont non vérifiable). Millésime
= base. Couverture : communes /24 + volume. Branchement : branchée / fantôme / vide.

| # | Source | Fraîcheur (radar · millésime base) | Couverture | Branchement |
|---:|---|---|---|---|
| 1 | 50 pas géométriques (DEAL) | ? · cadastre 1877 (géoréf. 2012) | `cinquante_pas` 163 (île) | branchée (cascade) |
| 2 | ABF / Monuments historiques | à jour · — | `abf` 200 tampons (île) | branchée (cascade) — *covisibilité non instruite* |
| 3 | BD ORTHO 20 cm | ? · IGN 974 2025 | tuiles raster (île) | branchée (fiche/détection) |
| 4 | BD ORTHO IRC | ? · — | tuiles IRC (île) | branchée (NDVI végétation) |
| 5 | BD TOPO IGN | ? · — | `batiment` 817 506 · `voirie` 235 643 (île) | branchée (**score** + cascade) |
| 6 | BODACC (procédures collectives) | à jour · — | `bodacc_annonces_owner` 1 418 propriétaires | branchée (cascade étage 2 + filtre) |
| 7 | BPE INSEE | ? · — | 0 (a_faire) | **vide** |
| 8 | Base Adresse Nationale | à jour · Last-Mod 17/08/2026 | `adresse_parcelles` 416 357 · **24/24** (96 %) | branchée (fiche, géocodage) |
| 9 | Cadastre (API Carto PCI) | ? · — | lookup unitaire | branchée (lookup) |
| 10 | Cadastre Etalab (bulk) | à jour · — | `parcels` 431 663 · **24/24** | branchée (**socle**) — DOUBLON de #9 |
| 11 | Cartofriches (Cerema) | ? · — | `friche` 372 (île) | branchée (**score** + cascade) |
| 12 | Classement sonore ITT | ? · arrêtés déc. 2023 | `bruit_route` 1 004 tronçons | branchée (cascade) — *PEB aéro. bloqué* |
| 13 | Contours IRIS | ? · géo 2024 | `iris_insee` 344 | branchée (taux ANC secteur) |
| 14 | DEAL Réunion (WMS/WFS) | ? · — | `anru` 8 emprises | branchée (fiche) |
| 15 | DEAL — PPR / aléas | ? · — | `ppr` 164 · `georisque_alea` 993 | branchée (**cascade exclusion**) |
| 16 | DEAL — trait de côte | à jour · 2018 | `trait_de_cote` 24 168 | branchée (cascade) |
| 17 | DGFiP — personnes morales | à jour · 2025 | `parcelle_personne_morale` 82 701 · **24/24** | branchée (fiche, filtre) |
| 18 | DPE ADEME | à jour · — | `dpe_records` **17 lignes** | **fantôme** (`# TODO étage 2`, servi nulle part) |
| 19 | DVF / valeurs foncières | à jour · 2021–2025 | `dvf_mutations` 29 566 · **24/24** | branchée (**score, le cœur** + cascade) |
| 20 | EDF SEI Réunion | ? · — (410 Gone) | 0 (a_faire) | **vide** |
| 21 | ENS (Département) | ? · — | `ens` 73 · **21/24** communes | branchée (cascade) |
| 22 | FRR ex-ZRR | ? · FRR 01/07/2024 | attribut commune (24) | branchée (fiche fiscal) |
| 23 | Fichiers fonciers (Cerema) | ? · — | `parcel_source_results` **0** | **vide** (câblée cascade `proprietaire` → UNKNOWN) |
| 24 | Filosofi INSEE 200 m | ? · 2021 | `filosofi_carreaux_200m` 14 773 (île) | branchée (**score**) |
| 25 | Forêts publiques (ONF) | ? · — | `foret_publique` 227 (65 distinctes) | branchée (cascade) — *doublons d'ingestion* |
| 26 | GPU — zonages assainissement | ? · — | `zonage_assainissement` 258 · **4/24** SIG | branchée (fiche, partielle) |
| 27 | GPU assainissement (info-surf) | ? · — | même couche | branchée — **DOUBLON de #26** |
| 28 | Géoplateforme IGN | ? · — | hub (amont BD TOPO/ORTHO/OCS) | branchée (hub) |
| 29 | Géorisques (BRGM) | ? · — (404/500) | cavite/mvt/icpe/sol_pollue | branchée (cascade) |
| 30 | Géorisques — ICPE | ? · — (500) | `icpe` 1 261 | branchée (cascade) |
| 31 | Géorisques — cavités | ? · — (500) | `cavite` 151 | branchée (cascade) |
| 32 | Géorisques — mouvements de terrain | ? · — (500) | `mvt` 3 085 | branchée (cascade, info ×0) |
| 33 | Géorisques — sites et sols pollués | ? · — (500) | `sol_pollue` 513 | branchée (cascade) |
| 34 | INPI RNE (dirigeants) | ? · — (404) | `pm_dirigeants` / `owner_enrichment` 9 730 | branchée (cascade étage 2 + fiche) |
| 35 | INSEE RP Logement 2023 | ? · — | `anc_maille_taux` | branchée (fiche ANC) |
| 36 | INSEE RP2022 — détail Logements | ? · RP2022 | `anc_maille_taux` 330 IRIS | branchée (fiche ANC) |
| 37 | Inventaire SRU (DHUP) | à jour · — | `commune_contexte_sru` **24/24** | branchée (carence SRU) |
| 38 | LiDAR HD — MNH 50 cm | ? · — | `parcel_vegetation` 431 663 · **24/24** | branchée (**score** canopée) |
| 39 | NPNRU (DEAL/ANCT) | ? · — | `anru_quartiers` 8 | branchée (filtre/fiche) |
| 40 | OCS GE (IGN) | ? · — | `ocs_ge` 3 250 (1 643 distinctes) | branchée (cascade) — *proxy BDCARTO, non natif* |
| 41 | OSM — transport (pôles) | ? · Overpass | `pole_echange` 61 · `transport_arret` 9 956 | branchée (fiche accès) |
| 42 | Office de l'eau Réunion | ? · n°149 (2023) | `anc_office_eau_commune` **6 communes** | branchée (fiche ANC échelle commune) |
| 43 | OpenStreetMap / Overpass | ? · — | `amenite` 15 214 · `parcel_amenites` 431 663 | branchée (**score** accès) |
| 44 | PEIGEO (hub régional) | ? · — (host down) | fallback Région ODS | branchée (fallback) |
| 45 | PLH des 5 EPCI | ? · — | config `plh_tco.yaml` (extraction doc.) | branchée (fiche contexte, config) |
| 46 | PVGIS | ? · — | `ortho_detections` PV (feature MORTE) | **fantôme** (PV ingéré, signal mort M71 B2) |
| 47 | Parc National | ? · 2021 | `parc_national` 3 (cœur/adhésion) | branchée (cascade exclusion) |
| 48 | Parkings OSM (loi APER) | ? · — | `parkings_aper` 901 (450 conformes) | branchée (fiche stationnement) |
| 49 | QPV 2024 (ANCT) | à jour · 2024 | `qpv` 57 · **13/24** communes | branchée (fiche fiscal ; feature `qpv` RETIRÉE) |
| 50 | RGE ALTI (altimétrie) | ? · — (405) | (voir #51) | branchée — DOUBLON avec #51 |
| 51 | RGE ALTI 5 m | ? · — | `pente` 147 398 · raster `rgealti_pente_5m` | branchée (**score** pente + cascade) — **le canal qui juge** |
| 52 | RTAA DOM (textes) | ? · — | texte de référence (config) | branchée (norme faisabilité, référence) |
| 53 | Recherche d'entreprises (DINUM) | ? · — | `owner_enrichment` 9 730 | branchée (fiche PM) |
| 54 | Registre national installations (ODRÉ) | ? · — | 0 (a_faire) | **vide** |
| 55 | Région Réunion Open Data | ? · — | hub (amont Parc/Potentiel/PLU) | branchée (hub) |
| 56 | SAR Réunion | ? · — | `sar` 2 453 (proxy) | branchée (cascade info) — DOUBLON proxy #66 |
| 57 | SIRENE | ? · — | via Recherche entreprises (indirect) | branchée (fiche PM) |
| 58 | SITADEL | à jour · 2026-06 | `sitadel_permits` 50 292 · **24/24** | branchée (**score** permis + cascade) |
| 59 | SUP — assiettes GPU | ? · — | `sup` 417 | branchée (cascade) |
| 60 | Sudocuh | à jour · 31/12/2024 | veille PLU (config) | branchée (veille, config) |
| 61 | Urbanisme PLU/GPU (API Carto) | ? · GPU/PLU par commune | `plu_gpu_zone` 5 845 · `prescription` 10 490 | branchée (**score** zone + cascade) |
| 62 | VRD / assainissement (SPANC) | ? · — | champ EPCI manuel (pas de table) | branchée (fiche collectif/NC, manuel) |
| 63 | ZFANG | ? · décret 2026-421 | attribut commune (6 Est) | branchée (fiche fiscal) |
| 64 | ZNIEFF | ? · — | 0 (a_faire) | **vide** |
| 65 | Zonage SAFER (DAAF) | ? · — | `safer` 38 460 (proxy RPG) | branchée (cascade) — *proxy RPG, DAAF absent* |
| 66 | data.regionreunion — Potentiel foncier | ? · — | `potentiel_foncier` 2 453 | branchée (cascade bonus) |
| 67 | OSM — transport (téléphérique) | ? · Overpass | `pole_echange`/`telepherique` 7 (Papang seul) | branchée (fiche accès) |

*(Couverture « île » = couche régionale WFS/raster, non ventilée par commune ; « N/24 » = communes
réellement renseignées, mesuré.)*

---

## 2. LES DOUBLONS (5)

| Ligne masquée / secondaire | Canonique / jumeau | Nature | Le canal qui JUGE |
|---|---|---|---|
| Cadastre Etalab (bulk) | Cadastre (API Carto PCI) | même parcellaire DGFiP | **c'est le BULK Etalab qui alimente `parcels`** (le socle scoré) |
| RGE ALTI 5 m | RGE ALTI (altimétrie) | même référentiel IGN | **c'est le 5 m (`rgealti_pente_5m`) qui alimente la pente** scorée |
| GPU assainissement (info-surf typeinf 19) | GPU — zonages d'assainissement | même couche GPU | — (affichage) |
| SAR Réunion | data.regionreunion Potentiel foncier | proxy SAR via le même jeu Région | — (cascade info) |
| Parc National (INPN) | Région ODS `pnrun_2021` | même objet INPN, 2 canaux | — (cascade) |

Les 3 premiers sont les DOUBLON tagués (`technical_notes LIKE 'DOUBLON%'`), masqués de la vitrine. Les
2 derniers sont des proxys de facto (même donnée amont, deux lignes de catalogue).

---

## 3. LES SOURCES CASSÉES (défauts qualité mesurés, non corrigés)

| Source | Défaut | Preuve (file:line) |
|---|---|---|
| DPE ADEME | `_geopoint` ADEME FAUX (100 % hors Réunion) → re-géocodage BAN ; base à **17 lignes** (quasi vide) | `seed_sources.py:268` |
| ABF / Monuments historiques | endpoint `data.culture.gouv.fr` décommissionné ; tampons ~500 m sur-couvrent, covisibilité non instruite | `seed_sources.py:304-306` |
| Forêts publiques (ONF) | doublons d'ingestion : 65 géométries distinctes vs 227 lignes | `seed_sources.py:127` |
| OCS GE | proxy BDCARTO (pas OCS-GE natif 974) ; 1 643 distinctes vs 3 250 lignes | `seed_sources.py:285` |
| GPU assainissement | couverture **4/24** communes SIG, 20 en repli taux RP2022 | `seed_sources.py:52` |
| Géorisques PPR | pas d'endpoint v1 (404) → v2 DEAL Lizmap | `seed_sources.py:68` |
| Classement sonore | PEB aérodromes bloqué (PDF préfecture, pas de SIG) | `seed_sources.py:243` |
| PEIGEO | hôte injoignable (HTTP 000) → fallback Région ODS | `seed_sources.py:159` |
| Fichiers fonciers | convention « démarchage commercial interdit » → `parcel_source_results` VIDE | `seed_sources.py:338` |
| BODACC | mojibake UTF-8 (4 formes, M103) — corrigé à l'ingestion + filet cascade | `seed_sources.py:480` |
| Zonage SAFER | DAAF introuvable open data → proxy RPG.LATEST | `seed_sources.py:145` |
| Radar (transverse) | **54/67 `non_sondable`** — sondes HEAD 400/403/404/500/501, plusieurs URL mortes | `source_radar` (mesuré) |
| pv_candidat | signal MORT (0 validé / 23 529) → feature retirée | `p_model/features.py:164` |

---

## 4. LES VIDES / FANTÔMES (cause mesurée)

| Source | État | Cause mesurée |
|---|---|---|
| Fichiers fonciers (Cerema) | **vide** (`parcel_source_results` = 0) | convention interdit le démarchage → jamais ingéré (`seed_sources.py:338`) |
| DPE ADEME | **fantôme** (17 lignes, servi nulle part) | ingestion partielle + `# TODO étage 2` : le signal `passoire` n'est câblé à rien |
| PVGIS / pv_candidat | **fantôme** (PV dans `ortho_detections`, signal mort) | 0 validé sur 23 529 → feature retirée (M71 B2) |
| BPE INSEE | **vide** (0) | `a_faire` — jamais ingéré (pas d'URL sondable) |
| EDF SEI | **vide** (0) | `a_faire` — endpoint **410 Gone** |
| RNI installations (ODRÉ) | **vide** (0) | `a_faire` — jamais ingéré |
| ZNIEFF | **vide** (0) | `a_faire` — sonde 200 mais aucune ingestion |
| RTAA DOM | référence (pas de table) | texte réglementaire, servi comme norme de faisabilité (pas une donnée parcellaire) |

---

## 5. STOP — ARBITRAGE DE VIC (ligne par ligne si besoin)

Rien n'est réparé avant ta décision. Quatre paniers :

**A · Fantômes → lesquels passer en public ?**
- **DPE ADEME** (17 lignes, passoire F/G non câblé) : promouvoir en fiche + filtre, ou laisser dormant
  au catalogue ? *(couverture faible, à re-télécharger d'abord — cf. panier D).*
- **PVGIS / PV** (signal mort) : abandonner la feature au catalogue (dormante dite) ou re-valider ?

**B · Doublons → lesquels fusionner/nommer ?**
- 3 tagués (Cadastre, RGE ALTI, GPU assainissement) : fusion sur la canonique + **la vitrine doit dire
  le canal qui juge** (Etalab bulk pour `parcels`, RGE ALTI **5 m** pour la pente).
- 2 proxys (SAR↔Potentiel foncier, Parc National↔Région ODS) : garder deux lignes ou fusionner ?

**C · Vides → retélécharger ou abandonner ?**
- `a_faire` jamais branchées : BPE, EDF SEI (410 Gone), RNI, ZNIEFF — abandonner proprement du catalogue,
  ou brancher ? Fichiers fonciers (convention interdite) : abandonner la ligne ou la garder dite dormante ?

**D · Retards → lesquels réingérer ?**
- Le radar ne peut confirmer que **13** ; pour les 54 `non_sondable`, dois-je faire une **vérification
  amont manuelle** des millésimes datés à risque (trait de côte **2018**, Filosofi **2021**, DVF
  clampé 2021+, QPV 2024, classement sonore 2023) et réingérer les retards, ou seulement les prioritaires ?
- **Le radar lui-même** (54 sondes mortes) : à réparer en Phase 2 (URL/mode de sonde) — confirmes-tu ?

---

## CE QUI N'A PAS ÉTÉ TOUCHÉ

Inspection strictement en lecture. Aucune réingestion, aucune correction, aucune suppression — tout
attend ton arbitrage (Phase 2). Scoring/modèle/cascade non touchés. Branche `feat/m123-sources-etat`
non mergée.
