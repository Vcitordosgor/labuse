# AUDIT COURT — LES SOURCES ET LE SCORE

**Branche** : `audit/sources-score` — audit pur, aucune correction, jamais mergé.
**Méthode** : lecture de `data_sources` (67 lignes), du modèle P (`scoring/p_model/features.py:40-151`,
`scoring/p_v2/pipeline.py`, `scoring/p_model/model.py`) et de la cascade (`config/cascade_rules.yaml`) ;
comptages SQL directs sur la base servie.

**Deux « scores » à ne pas confondre :**
- **Le modèle de HASARD (P)** = `parcel_p_score_v2` (proba de mutation, `mult_base`, `rang`, `tier`).
  **Régression logistique WoE ENTRAÎNÉE** (artefact `joblib` figé + SHA, `model.py`) — coefficients +
  binning immuables ; seul l'**intercept** est recalé chaque run, le re-train est une décision humaine
  annuelle (`pipeline.py:8-16`). **C'est le juge.**
- **La CASCADE (Q)** = `dryrun.py` + `config/cascade_rules.yaml` → contrainte (étage 0 / q_score /
  `matrice_statut` / `evenement`). Elle **gate/exclut** et porte un embryon d'« étage 2 » propriétaire,
  mais elle **ne prédit pas** la mutation et n'alimente pas le tier v2 du juge.

---

## LA RÉPONSE EN UNE PHRASE

Le juge (le modèle entraîné) est un **modèle de MARCHÉ et de TERRAIN** : rotation DVF, prix, ancienneté
de détention, permis, contexte bâti/socio-éco, pente, zonage, accès, canopée. **Aucune de ses ~22
features ne regarde la SITUATION du propriétaire.** Les signaux de « vente forcée » (procédure
collective, succession, âge du dirigeant, société en cessation, passoire DPE) existent en base mais ne
touchent le juge PAS DU TOUT — au mieux un **embryon de cascade « étage 2 »** (points/événement rouge)
et des **filtres**. Ce sont les munitions inutilisées.

---

## 1. LA LISTE DE RÉFÉRENCE — LES 67 SOURCES (`data_sources`)

Une ligne par source. **Rôle** : `score` = feature du modèle de hasard entraîné · `gate` = cascade
(contrainte / étage 0 / exclusion) · `affichage` = fiche/carte/filtres · `dormante` = ingérée/déclarée,
servie nulle part · `hub` = infrastructure. **Signal** renseigné seulement si la source nourrit le score.
(millésime/cadence = `data_sources`, `—` si non renseigné.)

| # | Source | Producteur | Millésime | Cadence | Rôle | Signal (si score) |
|---:|---|---|---|---|---|---|
| 1 | 50 pas géométriques (limite haute) | DEAL Réunion | cadastre 1877 (géoréf. 2012) | — | gate | — |
| 2 | ABF / Monuments historiques | Base Mérimée (Min. Culture) | — | — | gate | — |
| 3 | BD ORTHO 20 cm | IGN | 2025 | — | **score** | piscine, NDVI (détection ortho) |
| 4 | BD ORTHO IRC | IGN | — | — | affichage | — |
| 5 | BD TOPO | IGN | — | — | **score** (+ gate) | densité/part bâti, nu constructible |
| 6 | BODACC (procédures collectives) | DILA | — | — | gate (étage 2) + filtre | — *(événement rouge, NON appris)* |
| 7 | BPE INSEE | INSEE | — | — | dormante | — *(a_faire)* |
| 8 | Base Adresse Nationale | DINUM / IGN | — | mensuel | affichage | — |
| 9 | Cadastre (API Carto PCI) | IGN | — | — | **score** | géométrie |
| 10 | Cadastre Etalab (bulk) | DGFiP / Etalab | — | — | **score** | surface_m2, secteur |
| 11 | Cartofriches | Cerema / DGALN | — | — | **score** (+ gate bonus) | friche |
| 12 | Classement sonore ITT | Cerema | arrêtés déc. 2023 | — | gate | — |
| 13 | Contours IRIS | IGN / INSEE | 2024 | — | affichage | — |
| 14 | DEAL Réunion (WMS/WFS) | DEAL Réunion | — | — | affichage | — |
| 15 | DEAL — PPR / aléas | DEAL Réunion | — | — | gate *(exclusion étage 0)* | — |
| 16 | DEAL — trait de côte | Cerema / GéoLittoral | 2018 | — | gate | — |
| 17 | DGFiP — parcelles personnes morales | DGFiP | — | — | affichage/filtre (+ cascade flag) | — |
| 18 | DPE ADEME (logements existants) | ADEME | — | hebdo | **dormante** *(exclu M71, fiche info)* | — |
| 19 | **DVF / valeurs foncières** | DGFiP / Etalab | 2021–2025 | semestriel | **score (le cœur)** | tenure, rotation nu/bâti, prix médian, tendance |
| 20 | EDF SEI Réunion | EDF SEI | — | — | dormante | — *(a_faire)* |
| 21 | ENS (Département) | INPN/MNHN | — | — | gate | — |
| 22 | FRR ex-ZRR | Légifrance / Région | FRR 01/07/2024 | — | affichage *(fiscal)* | — |
| 23 | Fichiers fonciers (Cerema) | DGFiP / Cerema | — | manuel | affichage/cascade partiel *(convention inactive)* | — |
| 24 | Filosofi INSEE (carreaux 200 m) | INSEE | 2021 *(feature : 2019)* | — | **score** | niveau de vie, % pauvreté, % propriétaires |
| 25 | Forêts publiques (ONF) | ONF / IGN | — | — | gate | — |
| 26 | GPU — zonages d'assainissement | IGN | — | — | affichage *(viabilisation)* | — |
| 27 | GPU — assainissement (info-surf) | IGN | — | — | affichage | — |
| 28 | Géoplateforme IGN | IGN | — | — | hub | — |
| 29 | Géorisques | BRGM / MTE | — | — | gate | — |
| 30 | Géorisques — ICPE | BRGM | — | — | gate | — |
| 31 | Géorisques — cavités | BRGM | — | — | gate | — |
| 32 | Géorisques — mouvements de terrain | BRGM | — | — | gate *(info)* | — |
| 33 | Géorisques — sites et sols pollués | BRGM | — | — | gate | — |
| 34 | INPI RNE (dirigeants) | INPI | — | — | gate (étage 2) + affichage | — *(âge dirigeant points, NON appris)* |
| 35 | INSEE RP Logement 2023 | INSEE | — | — | affichage *(contexte)* | — |
| 36 | INSEE RP2022 — détail Logements | INSEE | RP2022 | — | affichage *(ANC)* | — |
| 37 | Inventaire SRU (DHUP) | Min. Transition | — | — | affichage *(carence SRU)* | — |
| 38 | LiDAR HD — MNH 50 cm | IGN | — | — | **score** | canopée (parcel_vegetation) |
| 39 | NPNRU | DEAL Réunion / ANCT | — | — | affichage/filtre | — |
| 40 | OCS GE | IGN | — | — | gate *(ZAN naturel/agricole)* | — |
| 41 | OSM — transport (pôles d'échange) | OpenStreetMap | Overpass (vivant) | — | affichage *(accès, TCSP)* | — |
| 42 | Office de l'eau Réunion | Office de l'eau | n°149 — données 2023 | — | affichage *(viabilisation ANC)* | — |
| 43 | **OpenStreetMap / Overpass** | OSM | — | — | **score** | acces_equipements (école/santé/commerce/TCSP) |
| 44 | PEIGEO (hub régional) | AGORAH | — | — | dormante/hub | — *(a_faire)* |
| 45 | PLH des 5 EPCI | EPCI 974 / DEAL | — | — | affichage *(contexte habitat)* | — |
| 46 | PVGIS | CE / JRC | — | — | dormante *(PV non servi)* | — |
| 47 | Parc National de La Réunion | INPN/MNHN | 2021 | — | gate | — |
| 48 | Parkings OSM (loi APER) | OpenStreetMap | — | — | affichage *(stationnement)* | — |
| 49 | QPV 2024 | ANCT | 2024 | — | affichage *(fiscal ; feature `qpv` RETIRÉE)* | — |
| 50 | RGE ALTI (altimétrie) | IGN | — | — | affichage/doublon | — *(cf. #51)* |
| 51 | RGE ALTI 5 m | IGN | — | — | **score** (+ gate pente) | pente_moy_deg |
| 52 | RTAA DOM (textes) | Légifrance | — | — | gate/affichage *(réglementaire)* | — |
| 53 | Recherche d'entreprises (DINUM) | DINUM | — | — | affichage *(enrichissement PM)* | — |
| 54 | Registre national installations (ODRÉ) | ODRÉ | — | — | dormante | — *(a_faire)* |
| 55 | Région Réunion Open Data | Région Réunion | — | — | hub | — |
| 56 | SAR Réunion | Région / AGORAH | — | — | gate *(info vocation)* | — |
| 57 | SIRENE | INSEE | — | — | affichage/filtre *(état société)* | — |
| 58 | **SITADEL (autorisations d'urbanisme)** | SDES (Dido) | 2026-06 | mensuelle | **score** | ancienneté du dernier permis sur la parcelle |
| 59 | SUP — assiettes GPU | IGN | — | — | gate *(servitudes)* | — |
| 60 | Sudocuh (procédures d'urbanisme) | Min. Cohésion | état 31/12/2024 | — | affichage *(veille PLU)* | — |
| 61 | Transport public — GTFS (7 réseaux) | AOM Réunion | màj 2026 | — | affichage *(accès, TCSP)* | — |
| 62 | **Urbanisme PLU/GPU (API Carto)** | IGN | GPU/PLU par commune | — | **score** (+ gate zonage) | zone_plu, nu constructible |
| 63 | VRD / assainissement (SPANC) | EPCI | — | manuel | affichage *(viabilisation)* | — |
| 64 | ZFANG | Légifrance / DGOM | décret 2026-421 | — | affichage *(fiscal)* | — |
| 65 | ZNIEFF | INPN/MNHN / Région | — | — | dormante | — *(a_faire)* |
| 66 | Zonage SAFER (DAAF) | DAAF | — | — | gate *(agricole, info)* | — |
| 67 | data.regionreunion — Potentiel foncier | Région Réunion | — | — | affichage/dormante *(→ feature retirée)* | — |

**Bilan des rôles** : 12 entrées nourrissent le score (DVF, SITADEL, BD TOPO, Filosofi, RGE ALTI 5 m,
PLU/GPU, OSM, Cartofriches, LiDAR, BD ORTHO, cadastre ×2) · ~18 `gate` (cascade) · ~28 `affichage` ·
~7 `dormante` (BPE, EDF SEI, RNI, ZNIEFF, PEIGEO, DPE, PVGIS) · 2-3 `hub`. Aucune source
« propriétaire » (BODACC, INPI, DGFiP PM, Fichiers fonciers) ne nourrit le score.

### 1-bis. L'ÉCART 67 (base) vs 55 (page Sources)

La **vitrine** `/sources` n'affiche que `status = 'connecte'` **hors** lignes tagguées `DOUBLON%`
(`sources_catalog.py:17`, `app.py:583-592` ; `SOURCES_MASQUEES` = vide). Répartition en base :
**connecte 58 · a_faire 5 · manuel 2 · hub 2 = 67**. Vitrine = 58 − 3 DOUBLON = **55** (mesuré).
Les **12** de différence, et pourquoi chacune est hors catalogue :

**A · 3 DOUBLON de catalogue** (connecte, masqués M71 — même donnée qu'une ligne canonique déjà affichée) :
| Source masquée | Doublon de (affichée) | Raison |
|---|---|---|
| Cadastre Etalab (bulk) | Cadastre (API Carto PCI) | même donnée, autre canal (bulk) |
| GPU assainissement (info-surf typeinf 19) | GPU — zonages d'assainissement | même couche GPU, autre canal |
| RGE ALTI 5 m | RGE ALTI (altimétrie) | même référentiel IGN, résolution 5 m |
→ Dédup délibérée (« un critère, un endroit »), le jumeau canonique EST dans la vitrine, la donnée servie
l'est via lui. **Nuance de transparence** (pas un défaut) : pour le SCORE, c'est justement la ligne
*masquée* qui porte le canal réellement scoré — **RGE ALTI 5 m** → pente, **Cadastre Etalab bulk** →
référentiel `parcels` — pendant que la vitrine montre la ligne générique. Même producteur, le client
ne sait pas que c'est le 5 m / le bulk qui juge.

**B · 5 `a_faire`** (déclarées, PAS branchées → rien ingéré, rien servi) : BPE INSEE · EDF SEI · PEIGEO ·
RNI (ODRÉ) · ZNIEFF. → Dormantes ; la vitrine = connecteurs branchés → correctement exclues.

**C · 2 `hub`** (infrastructure, pas des jeux) : Géoplateforme IGN · Région Réunion Open Data. → Portails
par lesquels transitent des sources servies (BD ORTHO, BD TOPO, LiDAR, PLU/GPU, SAR…), mais celles-ci
ont leur PROPRE ligne au catalogue. Le hub n'est pas un dataset → correctement exclu.

**D · 2 `manuel`** (ingestion manuelle déclarée, mais tables VIDES/absentes → non servies en pratique) :
- **Fichiers fonciers (Cerema)** → `parcel_source_results` = **0 ligne** (pourtant CÂBLÉE dans des
  chemins servis : `enrichment.py:395`, `app.py:3476` — convention inactive, rien à montrer).
- **VRD / SPANC** → **aucune table** (le « VRD » du code = un poste de COÛT du bilan, pas cette source).
→ Déclarées mais non alimentées → dormantes de fait, correctement hors vitrine.

**Verdict défaut : AUCUNE source SERVIE n'est absente de la vitrine.** Les 12 sont des doublons
dédupliqués (jumeau présent), des `a_faire` non branchées, des hubs (infra catalogués par ailleurs),
ou des `manuel` vides. **Défaut LATENT à noter** (structurel, non actif) : la vitrine filtre sur
`status='connecte'` STRICT — or une source `manuel` PEUT être câblée à un chemin servi (Fichiers
fonciers l'est déjà, `enrichment.py`/`app.py`). Le jour où `parcel_source_results` est alimenté, la
donnée serait servie (fiche/cascade) tout en restant HORS vitrine → sous-report d'une source servie.
Aujourd'hui sans effet (0 ligne).

---

## 2. SCORE (JUGE) / AFFICHAGE / DORMANTE

« Score » = le **modèle de hasard entraîné**. La cascade est signalée à part (elle gate, elle ne juge
pas). ✅ = feature active du modèle · △ = feature RETIRÉE (calculée, exclue de tout nouveau train).

| Source | Modèle de hasard (P entraîné) | Cascade (contrainte/étage 2) | Affichage seul | Dormante |
|---|:---:|:---:|:---:|:---:|
| **DVF valeurs foncières** | ✅ **(le cœur : 6 features)** | ✅ (bonus prix secteur) | fiche marché, comparables | |
| **SITADEL permis** | ✅ (`permis_bin`) △`permis_24m` | ✅ (densité proximité) | fiche, délai | |
| **BD TOPO (bâti)** | ✅ (`dens_bati`, `pct_bati`, `nu_constructible`) | ✅ (voirie, ravine…) | ortho | |
| **Filosofi INSEE 200 m** | ✅ (`snv_pp`, `pct_pauv`, `pct_prop`) △`dens_pop` | | contexte fiche | |
| **RGE ALTI (pente)** | ✅ (`pente_moy_deg`) | ✅ (pente >30/60 %) | fiche | |
| **PLU / GPU (zonage)** | ✅ (`zone_plu`, `nu_constructible`) | ✅ (zonage, prescriptions) | filtre zonage, fiche | |
| **OSM / BPE (aménités)** | ✅ (`acces_equipements` = école/santé/commerce/TCSP) | ✅ (aménités) | accès fiche | BPE a_faire |
| **Cartofriches** | ✅ (`friche`) | ✅ (bonus friche) | flag friche | |
| **LiDAR HD + BD ORTHO** | ✅ (`canopee_pct`, `ndvi_moyen`, `piscine`) | ✅ (OSM faux positif) | contours, détections | |
| **Cadastre** (Etalab/API Carto) | ✅ (`surface_m2`, géométrie) + `parcel_residuel` (`sous_densite`, `sdp_residuelle`) | ✅ (surface micro) | tout | |
| **Ortho — PV** | △ (`pv_candidat` **MORT** : 0 validé /23 529, M71 B2) | | | ✅ |
| Risques (PPR, Géorisques ×5, trait de côte) | ❌ | ✅ **(exclusion étage 0)** | fiche | |
| Foncier public (ONF, Parc Nat., ENS) | ❌ | ✅ (exclusion) | | ZNIEFF a_faire |
| Règlement (50 pas, sonore, RTAA, ABF, SUP) | ❌ | ✅ (contrainte) | fiche | |
| **BODACC procédures** | ❌ | ✅ **(étage 2 : événement rouge → chaude, `v_foncier_sous_pression`)** | signaux de vie, fiche | |
| **INPI RNE — âge dirigeant** | ❌ | ✅ **(étage 2 : points, `v_foncier_propension_vendre`)** | fiche | |
| **DGFiP personnes morales** | ❌ *(`owner_type` = méta, non scoré)* | ✅ (flag propriétaire) | filtre PM, fiche | |
| **Fichiers fonciers Cerema** | ❌ | ✅ (indivision, flag) | | convention inactive, manuel |
| SRU / NPNRU / PLH / INSEE RP · ZFANG / FRR · SAR / Sudocuh | ❌ | (info/QPV △) | ✅ contexte/fiscal | |
| BAN · Transport GTFS · Office de l'eau · OCS GE | ❌ | | ✅ (adresse, accès, viabilisation) | |
| **DPE ADEME** | ❌ **(exclu M71 B1 : trop épars)** | ❌ | (fiche info au mieux) | ✅ **dormant** (`dpe_records` ~910, DROM depuis 07/2024, non exhaustif) |
| EDF SEI · RNI installations · ZNIEFF · PEIGEO · PVGIS | ❌ | ❌ | ❌ | ✅ (a_faire / non servi) |

**Le juge = ~12 familles de sources** (DVF, SITADEL, BD TOPO, Filosofi, RGE ALTI, PLU/GPU, OSM/BPE,
Cartofriches, LiDAR/ortho, cadastre, parcel_residuel). Le reste gate (cascade), affiche, ou dort.

---

## 3. SIGNAL → SOURCE → FRAÎCHEUR (les ~22 features ACTIVES du juge)

`p_model/features.py:40-151`. Le modèle n'a **que** ces entrées (bloc Z = contexte secteur ;
bloc D = parcelle). △ = retirée (calculée, hors nouveau train).

| Feature | Signal | Source | Fraîcheur |
|---|---|---|---|
| `tenure_bin` | **ancienneté de la dernière mutation** (durée de détention, toutes natures) | DVF | ~6 mois latence DGFiP |
| `rot_nu` / `rot_bati` | **rotation foncière du secteur** (36 mois, shrinkage commune) | DVF | semestriel |
| `med_pm2_terrain_36m` / `med_pm2_bati_36m` | prix médian €/m² secteur (36 mois) | DVF | semestriel |
| `tendance_pm2_bati` | tendance de prix bâti (12 mois vs fenêtre) | DVF | semestriel |
| `permis_bin` | **ancienneté du dernier permis SUR la parcelle** | SITADEL | mensuel — **garde de fraîcheur** `pipeline.py:95-118` |
| `dens_bati_secteur` / `pct_bati_secteur` / `nu_constructible` | densité/part de bâti, nu constructible | BD TOPO + PLU | statique |
| `zone_plu` | zonage U/AU/A/N (centroïde) | PLU/GPU | statique (à l'ingestion) |
| `pente_moy_deg` | pente moyenne | RGE ALTI 5 m | statique |
| `acces_equipements` | Σ accès école/santé/commerce/TCSP (exp -dist/800 m) | OSM (BPE) | statique |
| `filo_snv_pp` / `filo_pct_pauv` / `filo_pct_prop` | niveau de vie / pauvreté / part propriétaires | Filosofi INSEE (mil. 2019) | statique |
| `surface_m2` | surface parcelle | Cadastre | statique |
| `sous_densite` / `sdp_residuelle_m2` | sous-densité / SDP résiduelle | `parcel_residuel` (PLU × BD TOPO) | statique |
| `canopee_pct` / `ndvi_moyen` | canopée / végétation | LiDAR/ortho | statique |
| `friche` | friche répertoriée | Cartofriches | statique |
| `piscine` | piscine détectée (ortho) | ortho detections | statique |
| △ `permis_24m_norm` `filo_dens_pop` `qpv` `window_coverage` `dormance_droits` | (instables M35/M36) | — | calculées, **hors train** |
| ✝ `pv_candidat` | (0 validé sur 23 529 — signal MORT exempté M71 B2) | ortho PV | dormant |

**Interactions** (`libelles_client.py:86-88`) : `tenure×permis`, `tenure×rot_nu`, `tenure×surface` —
des croisements des MÊMES familles. **Zéro colonne propriétaire/détresse** dans le dataset du modèle
(vérifié : `p_model_dataset` n'a aucune colonne bodacc/dpe/succession/dirigeant).

---

## 4. LES CANDIDATES INEXPLOITÉES (signal de vente probable, HORS du juge)

Toutes **ingérées**, toutes **absentes du modèle entraîné**. Au mieux un embryon de cascade « étage 2 »
(points/événement) ou un filtre — jamais un poids appris. Triées par force du signal « vente forcée » :

| Signal | Source | Table (volume mesuré) | Statut vis-à-vis du JUGE | Munition |
|---|---|---|---|---|
| **Propriétaire en procédure collective** (LJ, redressement) | BODACC | `bodacc_annonces_owner` (1 418) · `bodacc_procedures` (672) | ❌ modèle · cascade étage 2 (événement rouge → chaude) + filtre | Liquidation → cession quasi certaine |
| **Succession / indivision** | veille succession | `parcel_veille_succession` (7 129) | ❌ modèle · **facette veille seulement** (tag) | Héritiers = vendeurs typiques |
| **Âge du dirigeant** (PM) | INPI RNE | `owner_enrichment` (9 730) | ❌ modèle · cascade étage 2 (points, `v_foncier_propension_vendre`) + fiche | Dirigeant âgé → transmission/cessation |
| **Société en cessation / radiation** | SIRENE / BODACC | filtre `etat_societe` | ❌ modèle · filtre propriétaire | Fermeture → liquidation d'actifs |
| **Personne morale « nue » qui dort** | DGFiP PM | `parcelle_personne_morale` (82 701) | ❌ modèle *(`owner_type` méta)* · filtre + cascade flag | SCI immobile sur foncier nu |
| **Passoire thermique F/G** | DPE ADEME | `dpe_records` (~910) | ❌ modèle **(exclu M71 B1 : trop épars)** · fiche info au mieux | Coût de rénovation → arbitrage de vente |
| **Vacance de logement** | INSEE RP / RPLS | **non matérialisée au parcellaire** | ❌ (donnée absente) | Bien vacant → mise en vente |

**Le constat central** : le juge prédit le **quand du marché** (le secteur bouge), jamais le **qui du
propriétaire** (celui qui DOIT vendre). Les signaux propriétaire, déjà en base, ne l'atteignent pas —
ils vivent dans un embryon de cascade « étage 2 » (BODACC/dirigeant → points/événement, non appris) et
dans des filtres. Couverture inégale et **« positifs quand présents », jamais exhaustifs** (BODACC 1 418,
succession 7 129, RNE 9 730, DPE ~910) → matière d'un **étage propriétaire en BONUS de hasard**, jamais
un filtre d'exclusion.

---

## CE QUI N'A PAS ÉTÉ TOUCHÉ

Audit strictement en lecture. Aucune correction, aucun changement. Branche `audit/sources-score`
non mergée.
