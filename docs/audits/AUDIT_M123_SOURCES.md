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

## PHASE 2 — LES RETARDS (vérification amont, sans réingestion)

Arbitrage Vic : vérifier l'amont MAINTENANT, rendre le tableau des retards avérés + l'impact estimé ;
la réingestion des couches cascade attend un geste dédié couche par couche. Impact = parcelles
actuellement HARD_EXCLUDE par la couche (mesuré `dryrun_cascade_results`) — ce qu'une réingestion
POURRAIT faire bouger.

| Couche / source | Millésime base | Amont vérifié | Retard ? | Impact (parcelles exclues auj.) |
|---|---|---|---|---:|
| **trait de côte** | 2018 | Cerema « Indicateur national de l'érosion côtière » = **maj 2018-06-28** (inchangé) | **NON** | 3 |
| **Filosofi INSEE** | 2021 *(comment `features.py` dit 2019 — stale)* | INSEE Filosofi **2021 = dernier millésime** | **NON** (donnée) ; comment à corriger (hors ce mandat, dans le modèle) | contexte (non exclusion) |
| **QPV** | génération 2024 | ANCT QPV 2024 (maj 2024-12/2025-07) = géographie courante | **NON** | fiscal (non exclusion) |
| **classement sonore** | arrêtés déc. 2023 | cadence ~5 ans, 2023 récent | **NON** (présumé) | `bruit_route` (flag, non HARD) |
| **zonage PLU/GPU** | GPU par commune | **NON DATABLE auto** — révisions PLU par commune (GPU) | **INCONNU** → vérif manuelle par commune requise | **103 722** |
| **risques / PPR** | — | **NON DATABLE auto** — arrêtés DEAL Lizmap | **INCONNU** → vérif manuelle DEAL requise | **44 764** |
| **foncier public** | suit le cadastre | à jour (suit le socle) | **NON** | 36 379 |
| **forêts ONF / parc national** | 2021 | INPN/ONF, périmètres stables | **NON** (présumé) | 6 890 / 6 137 |

**Verdict retards** : **AUCUN retard avéré** parmi les couches datables/vérifiables (trait de côte,
Filosofi, QPV, sonore = à jour amont). Les DEUX couches à fort impact — **zonage PLU/GPU (103 722)** et
**PPR/risques (44 764)** — sont NON DATABLES automatiquement (révisions par commune / arrêtés DEAL) :
leur fraîcheur exige une **vérification manuelle producteur**, et un retard y serait à fort impact
d'exclusion. Aucune réingestion lancée — geste dédié couche par couche, sur ton arbitrage.

---

## PHASE 2 — LES ~14 CASSÉES (résolution, preuve avant/après)

| Cassée | Traitement | Avant → Après (preuve) |
|---|---|---|
| **Forêts ONF — doublons d'ingestion** | dedup EXACT (geom+name+subtype), cascade booléenne inchangée | `foret_publique` **227 → 65** (−162) · golden 0 FAIL avant ET après |
| **OCS GE — doublons d'ingestion** | dedup EXACT | `ocs_ge` **3250 → 1643** (−1607) · golden 0 FAIL avant ET après |
| **Géorisques PPR — sonde v1 404** | endpoint corrigé v1 → **v2 DEAL Lizmap** (la couche `ppr` en venait déjà ; seule l'URL de sonde était morte) | endpoint_url mis à jour ; donnée servie inchangée |
| **Radar — 54 sondes mortes** | **corrigé Phase 2** : `verification_manuelle` honnête + sonde ODS | 54 non_sondable → 59 vérif manuelle + 8 sondées |
| **DPE — geopoint faux** | **déjà géré** (`is_reunion_authentic`) ; réingestion : 235 métropole écartées | source quasi vide amont (17, 2 F/G) — mesuré, non un bug nôtre |
| **BODACC — mojibake** | **déjà corrigé** (M103) à l'ingestion + filet cascade | historique |
| **Fichiers fonciers — convention** | **RETIRÉ** (raison écrite) | hors vitrine |
| **ABF — endpoint mort** | data.culture.gouv décommissionné : **non re-fetchable** ; 200 tampons en base, covisibilité non instruite | LIMITATION assumée (dite) |
| **GPU assainissement — 4/24 SIG** | 20 communes en repli taux RP2022 : **couverture producteur partielle** | LIMITATION assumée (dite) |
| **Classement sonore — PEB aéro.** | PDF préfecture, pas de SIG open data | LIMITATION assumée (dite) |
| **PEIGEO — host down** | fallback Région ODS opérationnel | assumée (fallback) |
| **SAFER — DAAF absent** | proxy RPG.LATEST (meilleure donnée disponible) | assumée (proxy dit) |
| **ENS — 3 communes N/A** | Le Port/Saint-André/Sainte-Suzanne : **0 ENS réel** (donnée correcte, pas un bug) | non-défaut confirmé |
| **pv_candidat — signal mort** | feature du MODÈLE (interdit ce mandat) → dit dormant | hors périmètre (algo) |

**Bilan cassées** : 3 corrigées avec preuve avant/après (ONF, OCS, PPR endpoint) + 3 déjà réglées
(radar, DPE geopoint, BODACC) + 1 retirée (Fichiers fonciers) ; 6 sont des **limitations amont
assumées et dites** (endpoint mort, couverture producteur, PDF, proxy) — pas des bugs réparables chez
nous ; 1 non-défaut (ENS) ; 1 hors périmètre (pv, modèle).

---

## PHASE 2 — VÉRIF MANUELLE PLU × SUDOCUH (communes révisées depuis nos ingestions)

**Méthode.** Le squelette Sudocuh (planification PLU/PLUi, 31/12/2024) vit dans le registre curaté
`config/veille_plu.yaml` (24 communes, champ `procedure`/`stade`/`date_acte`/`confiance`). On le croise
avec la date d'ingestion réelle de notre zonage (`spatial_layers kind='plu_gpu_zone'`, `max(created_at)`
par commune, **~28/06 → 03/07/2026**). **Critère de staleness** : une procédure devenue **opposable**
(date d'approbation) **postérieure** à notre ingestion → notre zonage GPU est en retard sur cette commune.

**Résultat mesuré.** 11 communes portent une procédure au registre (13 = `aucune`) :

| Commune | Procédure | Stade | date_acte | notre ingestion | Postérieur ? | Confiance |
|---|---|---|---|---|---|---|
| Saint-André | revision_plu | prescrite | 2022-06-22 | 2026-06-29 | **non** (antérieur) | SOURCE |
| Saint-Leu | revision_plu | prescrite | 2022-05-17 | 2026-06-28 | **non** | SOURCE |
| Trois-Bassins | revision_plu | prescrite | 2022-06-02 | 2026-06-29 | **non** | SOURCE |
| Saint-Philippe | elaboration | prescrite_dormante | 2002-08-30 | — (RNU, 0 zone) | **non** | SOURCE |
| Étang-Salé · Plaine-des-Palmistes · Saint-Denis · Saint-Louis · Saint-Paul · Sainte-Marie · Sainte-Suzanne | clôturée | approuvée_**probable** | **ABSENT** | 2026-06/07 | **indéterminable** | **DEDUIT** |

**Verdict : 0 commune à réingérer sur preuve Sudocuh.** Raisons, source par source :
- Les 3 `revision_plu` **SOURCE** sont des **prescriptions de 2022** — une révision prescrite n'est pas
  encore opposable ; le GPU nous a servi le PLU en vigueur en 06/2026, postérieur aux prescriptions.
- Les 7 `approuvée_probable` sont **DEDUIT** (`date_acte` ABSENT) : la doctrine veille interdit de servir
  une inférence comme un fait, et **le GPU sert toujours l'opposable courant** — si l'approbation est
  antérieure à 06/2026, elle est **déjà dans notre ingestion** ; aucune n'est datée après.
- Saint-Philippe = RNU (0 zone ingérée) — concordant, pas de PLU à rafraîchir.

**PPR hors périmètre Sudocuh.** Sudocuh ne couvre **que le PLU/PLUi**. La fraîcheur PPR/aléas (couche
`ppr`, 44 764 exclues) relève du producteur **DEAL** — non datable auto (cf. section RETARDS), à vérifier
sur ton geste dédié producteur. Aucune réingestion lancée ici.

**Ce que ça déclenche.** Rien à réingérer aujourd'hui. Le registre reste la sentinelle : si une des 7
`approuvée_probable` se voit **dater** (passe DEDUIT → SOURCE avec une approbation > 06/2026), elle devient
candidate à réingestion — à ce moment-là, et sur ton arbitrage couche par couche.

---

## PHASE 2 — BPE / ZNIEFF : PÉRIMÈTRE (mandat propre recommandé)

Tu m'as dit : *« si c'est plus qu'une session, dis-le et on le met dans un mandat propre »*. **Mesuré :
c'est un mandat propre.** Voici pourquoi, source par source.

**ZNIEFF** — connecteur présent (`connectors/__init__.py`, ODS `…/records`, endpoint vivant) mais
**0 donnée ingérée** : ni ingester qui écrit une table, ni CLI, ni couverture. Le construire au standard
du dépôt = un module ~ `amenites.py` (139 l.) : pagination ODS → géométries → `spatial_layers kind='znieff'`
(index spatial) → mesure 24 communes → bascule catalogue `a_faire→connecte` + sonde radar + tests.

**BPE** — **chevauche une feature DÉJÀ servie.** Le signal d'accès aux équipements existe et tourne :
`acces_equipements` (`features.py:89`, `Σ exp(-dist/800 m)` école/santé/commerce) est alimenté par
`parcel_amenites` (OSM) — **431 663 lignes, couverture pleine**. BPE INSEE n'est donc **pas un signal neuf** :
c'est un **re-sourcing officiel** de cette même feature (CSV national à filtrer au 974, table, recalcul de
distances par parcelle). Et le choix « BPE remplace-t-il ou complète-t-il OSM dans `acces_equipements` ? »
est une **décision de feature = modèle = interdit ce mandat**.

**Verdict.** Deux ingesters pleins (~130–240 l. chacun, cf. `amenites.py` 139 / `georisques_layers.py` 238),
chacun avec download+parse, table+migration, CLI résumable, mesure de couverture, bascule catalogue+radar,
tests — plus, pour BPE, une question de feature hors périmètre. **C'est au-delà du reste de cette session
faite au standard.** Un ingester à moitié bâti laisserait un état pire que le marqueur `a_faire` propre
actuel. **Recommandation : mandat dédié « BPE/ZNIEFF — ingesters + couverture », câblage algo en phase
modèle.** Rien n'a été bâti à moitié ici.

---

## CE QUI N'A PAS ÉTÉ TOUCHÉ

Inspection strictement en lecture. Aucune réingestion, aucune correction, aucune suppression — tout
attend ton arbitrage (Phase 2). Scoring/modèle/cascade non touchés. Branche `feat/m123-sources-etat`
non mergée.
