# SCORING_SPEC — Spécification complète du scoring LA BUSE

> **Mandat DOC-P.** Description exhaustive et fidèle du scoring, **reconstruite depuis le
> code réel** (le code fait foi ; les docs existantes ne sont PAS la source). Rapport seul,
> aucun code modifié. Généré le 2026-07-26.
>
> Chiffres de population = mesures live sur la base `labuse` (431 663 parcelles, run servi
> `q_v7_defisc`). Chaque affirmation renvoie au fichier/ligne ou au rapport gelé qui la fonde.
> Là où le code est ambigu ou illisible, c'est dit — rien n'est inventé pour « faire propre ».

---

## 0. Vue d'ensemble — TROIS systèmes coexistent, un seul « pilote » la fiche

Le mot « scoring » recouvre en réalité trois moteurs distincts, empilés historiquement. Les
confondre est la première source d'erreur de lecture (et de dérive documentaire, cf. §7).

| # | Nom | Rôle | Sortie | Table | Servi sur la fiche ? |
|---|-----|------|--------|-------|----------------------|
| **P×C v2** (M5) | `scoring/p_v2/` | **LE système servi.** Modèle P (hazard) × capacité C → tiers | `tier` ∈ {brulante, chaude, a_creuser, reserve_fonciere, ecartee} | `parcel_p_score_v2` | **OUI — verdict d'en-tête** |
| **Matrice Q×A** (legacy) | `scoring/dryrun.py`, `config/scoring_matrice.yaml` | Ancien « verdict d'opportunité » Q×A + **étage 0** (exclusions dures) | `matrice_statut` ∈ {chaude, a_surveiller, a_creuser, ecartee}, `status` ∈ {opportunite, a_creuser, exclue, faux_positif_probable} | `dryrun_parcel_evaluations` | Partiel : **son étage 0 alimente P×C v2** ; le reste = « historique » |
| **Score V** (vendabilité) | `scoring/score_v.py`, `score_v_constants.py` | Signal 0-100 « le propriétaire a-t-il une raison de vendre » | `v_score`, `v_band` | `parcel_v_score` | Affiché comme « signaux vendeur », **jamais** le verdict |

**Règle de résolution du verdict affiché** (`frontend/src/lib/status.ts:33` `verdictMeta`,
confirmée par `tests/test_verdict_effectif.py`) :

1. **étage 0** du run servi (exclusion dure) → « Écartée » (prime sur tout) ;
2. sinon, si un run v2 existe → **le `tier` v2 EST le verdict** (Brûlante / Chaude / …) ;
3. sinon (aucun run v2) → repli sur `matrice_statut` legacy.

Le backend confirme : `GET /parcels/{idu}` → `_q_v2_fiche()` (`api/app.py:2002`) lit
`parcel_p_score_v2` **épinglé au label `Q_A_RUN_LABEL`** (`api/app.py:1293`
`_score_v2_run_id` : `WHERE run_id = 'q_v7_defisc'`, **pas** « dernier run par timestamp »).
`/v2/modele` marque explicitement les champs matrice comme *« DEPRECATED, remplacés par
tier/rang/mult_base v2 »* (`api/score_v2.py:150`).

> ⚠ **Piège de nommage.** « Score C » (mandat §5) = la **capacité** (`plancher_c`,
> `p_v2/statuts.py`). « Score V » = la **vendabilité** (`score_v.py`). Deux choses sans rapport
> qui riment. Et `mutation.py` (« Radar Mutation V1 ») est un **quatrième** score, lecture seule,
> hors chaîne des tiers — voir §7.

**Le run servi `q_v7_defisc`** (source unique : `score_v_constants.py:46`,
`Q_A_RUN_LABEL = os.environ.get("LABUSE_SERVED_RUN", "q_v7_defisc")` ; miroir front
`VITE_RUN_LABEL`). Bascule `q_v6_m8 → q_v7_defisc` : le modèle P (artifact gelé) est
**inchangé** ; seule la composante V « fenêtre de sortie de défisc » module le rang p_raw
(+0,01 plafonné) sur 131 parcelles → 0 bascule de tier. `q_v6_m8` reste en hystérésis (rollback).

---

## 1. UNIVERS — qui est scoré, qui est exclu

### 1.1 Le socle (`p_model_frame`, `scoring/p_model/sql.py:51`)

Une ligne par **IDU dédupliqué**, source `mvt_parcels` si présente et non vide, sinon `parcels`.
Le secteur = `left(idu, 10)`, la commune = `left(idu, 5)`.

| Mesure | Valeur | Requête |
|--------|--------|---------|
| Parcelles totales (`parcels` = `mvt_parcels` = `p_model_frame`) | **431 663** | `count(*)` |
| Communes couvertes | **24** (toute La Réunion) | `count(DISTINCT commune)` |
| Nues (`nu` = emprise bâtie BD TOPO ≤ 20 m²) | **152 940** | `p_model_dataset WHERE nu` |
| Bâties (`nu = false`) | **278 723** | `p_model_dataset WHERE NOT nu` |

Le seuil « nu » est **20 m² d'emprise BD TOPO** (`NU_SEUIL_M2`, `sql.py:39` ; tolère
cabanons/artefacts). Les parcelles **bâties NE SONT PAS exclues** : elles restent scorées (le
modèle prédit aussi la mutation d'un bâti). Le caractère nu/bâti est une **feature** (bloc D),
pas un filtre d'univers.

### 1.2 Exclusions

- **Copropriété** — flag `copro = copro_rnic OR copro_dvf` (`p_model_ext_copro`,
  `ext_sql.py:32`). `copro_rnic` : la parcelle est dans le RNIC (idu_codes ∪ parcelle_idu).
  `copro_dvf` : ≥ 1 mutation L2 « exclusivement Appartement/Dépendance » avec ≥ 1 Appartement
  (sans plafond ici — même une vente en bloc signe l'immeuble collectif). La copro est
  **scorée mais retirée du classement** : `rang`/`percentile` = NULL, `tier` jamais brûlante/chaude.

  | Flag | Parcelles |
  |------|-----------|
  | `copro_rnic` | 2 465 |
  | `copro_dvf` | 2 072 |
  | **copro (l'un ou l'autre)** | **3 424** |

  Vérifié : dans le run servi, `rang IS NULL` = `percentile IS NULL` = **3 424** = exactement le
  nombre de copros. Les copros ne sont jamais rankées.

- **Étage 0 (exclusion dure)** — hérité de la matrice Q×A du run servi. Le pipeline v2 lit
  `dryrun_parcel_evaluations WHERE run_label='q_v7_defisc' AND status IN ('exclue',
  'faux_positif_probable')` (`p_v2/pipeline.py:225`) → `ecartee_etage0`. Ce sont des parcelles
  jugées non constructibles / faux positifs par la cascade (déjà bâtie, PPR rouge, zonage A/N,
  surface < 100 m², pente, foncier public non acquérable, emprise voirie… — buckets de
  l'entonnoir, `dryrun.py:268`).

  | `status` (run servi) | Parcelles |
  |----------------------|-----------|
  | faux_positif_probable | 221 360 |
  | exclue | 132 585 |
  | **Total étage 0** | **353 945** |

  Ce total (353 945) **égale exactement** le nombre de parcelles au tier `ecartee` du run v2 :
  **le tier « Écartée » est intégralement l'étage 0 de la cascade**, rien d'autre.

### 1.3 Bornes de surface, zones, communes

- **Aucune borne min/max de surface au niveau de l'univers.** La surface est une feature
  (bloc D `surface_m2`) et un critère de **capacité** (plancher C : ≥ 600 m² en U/AU, §5).
  La borne « surface < 100 m² » est une règle **de la cascade** (étage 0), pas du modèle P.
- **Toutes zones PLU** sont scorées ; `zone_plu` est une feature (U / AU / A / N / inconnu). Les
  zones A/N non constructibles sortent surtout via l'étage 0 de la cascade, pas par le modèle.
- **24 communes**, île entière. Pas de restriction « commune pilote » sur le scoring servi.

---

## 2. LABEL — définition exacte de L2-F

Le label est la cible du modèle P : **la parcelle connaît-elle une mutation foncière (L2-F)
pendant l'année civile d'observation Y ?** (`ext_sql.py:225`, colonne `label`).

### 2.1 Ce qui compte comme « mutation »

- **Source** : DVF (Demandes de Valeurs Foncières). Union matérialisée `p_model_ext_dvf` =
  `dvf_mutations_histo` (2014-2020, éditions cquest tardives réputées complètes) **∪**
  `dvf_mutations_parcelle` (2021-2025, prod) (`ext_sql.py:90`). Le M3 « base »
  (`p_model_dataset`) ne remontait qu'à 2021 ; le système **servi** utilise l'**ext** remontant à 2014.
- **Natures retenues** (`L2_NATURES`, `ext_sql.py:25`) : `'Vente'` et `'Vente terrain à bâtir'`
  **uniquement**. Exclus : VEFA, échange, adjudication, expropriation.
- **Dédup** : DVF+ livre une ligne par (mutation × parcelle × local). Dédup en deux temps →
  1 ligne par (mutation × parcelle), surface terrain = max, surfaces bâties sommées ; puis
  agrégat par mutation (`ext_sql.py:112`).
- **Fenêtre du label** : mutation dont `date_mutation ∈ [01/01/Y, 31/12/Y]` (strictement dans
  l'année). Le label vaut **NULL** pour toute année postérieure au dernier millésime DVF (année
  de scoring produit sans vérité terrain).

### 2.2 Le raffinement « -F » (foncier) : exclusion des ventes d'unités de copro

`label` (L2-F) exclut les mutations où **tous les locaux non nuls ∈ {Appartement, Dépendance},
≥ 1 Appartement, ET < 4 appartements** (`IMMEUBLE_ENTIER_MIN_APP = 4`, `ext_sql.py:65`
`l2f_mutation_flags`). Le plafond de 4 **préserve les ventes d'immeuble entier** (≥ 4 apts =
opération foncière conservée). Maison, terrain nu, local mixte, dépendance seule : conservés.

Une colonne de contrôle `label_l2` (L2 brut, sans le filtre -F) coexiste dans le dataset.

### 2.3 Fenêtre DVF et censure

Historique DVF réellement complet à partir de **2014** dans l'ext ; les millésimes se
« complètent » avec 1-3 ans de retard DGFiP (`reports/m36-foncier/annotation-taux-2023-2025.csv` :
2023 ≈ complet, 2024 ~80 %, 2025 ~40 %). D'où l'avertissement produit permanent : *« les niveaux
2025-2026 sont provisoires, le classement est fiable »* (`api/score_v2.py:23`).

### 2.4 Exemples positifs / négatifs (mesuré sur `p_model_ext_dataset`, label = L2-F)

| Année Y | Positifs (label=1) | Négatifs (label=0) | Taux de base |
|---------|--------------------|--------------------|--------------|
| 2017 | 5 174 | — | ≈ 1,2 % |
| 2021 | 6 538 | — | — |
| 2022 | 6 561 | — | — |
| 2023 | 5 650 | — | — |
| 2024 | 4 799 | — | — |
| 2025 | 4 909 | — | — |

> Nuance mesurée : la colonne `label` de `p_model_ext_dataset` (L2-F) présente des effectifs
> ~4 800-6 500/an ; la colonne large `label_l2` fait ~7 300-9 400/an. La part exclue par le
> filtre -F (unités de copro) est de **23-30 %/an** (`volumetrie-l2f.csv`). Sur ~431 663
> parcelles/an, le **taux de base du label servi est ~1,1-1,5 %** (positifs L2-F / univers). Le
> DVF compte **~4 900-6 600 mutations L2-F/an**.

---

## 3. FEATURES DU MODÈLE P — la liste exhaustive (29 features)

Registre unique : `scoring/p_model/features.py`. **29 features** (17 bloc Z « zone/secteur »,
12 bloc D « parcelle »), + 5 croisements, + dummies d'année. Confirmé par
`FREEZE-scoring2026.json` (`n_features: 29`).

Convention **as-of** commune (anti-fuite, `sql.py:1`) : pour l'année Y, une feature n'utilise
que des événements **strictement antérieurs au 01/01/Y** ; fenêtres glissantes clampées à
2014 ; couverture réelle portée par `window_coverage`.

Colonnes **méta** (jamais encodées) : `idu, annee, label, commune, secteur, owner_type`. Interdits
par construction : statut matrice, `computed_at`, Score V.

Valeur par défaut « donnée absente » : sauf mention, une valeur manquante tombe dans un **bin
« manquant » explicite** dont le WoE est propre si l'effectif ≥ 200, sinon **0 (neutre)** —
jamais de NA silencieux (`woe.py:168` `_fit_missing`).

### 3.1 Bloc Z — secteur / marché (17)

| Feature | Source | Transformation / fenêtre | Défaut si absent |
|---------|--------|--------------------------|------------------|
| `rot_nu` | DVF L2-F dédup + stock secteur | rotation nu du secteur, **shrinkage gamma-Poisson** vers le taux commune (36 mois, annualisé) | 0 mutation → taux 0 shrunk (jamais NaN) |
| `rot_bati` | idem | rotation bâti du secteur, même shrinkage | idem |
| `med_pm2_terrain_36m` | DVF L2-F nues | médiane €/m² terrain, 36 mois | NULL → bin manquant |
| `med_pm2_bati_36m` | DVF L2-F bâties | médiane €/m² bâti, 36 mois | NULL → bin manquant |
| `tendance_pm2_bati` | DVF L2-F | médiane €/m² bâti 12 derniers mois / début de fenêtre − 1 | NULL si pas de base → manquant |
| `permis_24m_norm` | Sitadel PC+PA autorisés | comptes 24 mois rattachés au secteur / stock parcelles | `coalesce 0` |
| `dens_bati_secteur` | BD TOPO × parcelles | Σ emprise bâtie / Σ surface du secteur | NULL (nullif) → manquant |
| `pct_bati_secteur` | BD TOPO | part de parcelles bâties (> 20 m²) du secteur | idem |
| `filo_snv_pp` | Filosofi INSEE carreau 200 m (2019) | niveau de vie / individu | NULL → manquant |
| `filo_pct_pauv` | Filosofi 200 m | part ménages pauvres | NULL → manquant |
| `filo_pct_prop` | Filosofi 200 m | part ménages propriétaires | NULL → manquant |
| `filo_dens_pop` | Filosofi 200 m | individus / km² | NULL → manquant |
| `qpv` | périmètres QPV (spatial_layers) | booléen, centroïde dans polygone | `false` |
| `pente_moy_deg` | RGE ALTI 5 m (`parcel_terrain`) | pente moyenne (°) | NULL → manquant |
| `acces_equipements` | OSM (`parcel_amenites`) | **Σ exp(−dist/800 m)** sur école/santé/commerce/TCSP ; τ = `EQUIP_TAU_M = 800` | distance absente = **contribution nulle** (parcelle isolée) |
| `zone_plu` | GPU zonage agrégé | U / AU (AUc+AUs fusionnés) / A / N, centroïde dans la zone | `coalesce 'inconnu'` |
| `window_coverage` | déterministe | mois DVF disponibles dans la fenêtre / 36 | déterministe [0,1] |

`rot_nu`/`rot_bati` — shrinkage (`features.py:164` `_shrink_rotation`) : exposition = stock × années
couvertes ; force du prior *m* estimée par méthode des moments sur la surdispersion inter-secteurs,
**bornée [50, 5000]** ; r̂ = (n + m·r_commune) / (expo + m). Monotonie **contrainte +1** (les seules
deux features à signe imposé).

### 3.2 Bloc D — parcelle (12)

| Feature | Source | Transformation | Défaut si absent |
|---------|--------|----------------|------------------|
| `nu_constructible` | BD TOPO (emprise ≤ 20 m²) × zone U/AU | booléen | `false` |
| `surface_m2` | référentiel parcellaire | surface (m²) | NULL → bin manquant |
| `dormance_droits` | `parcel_residuel.pct_potentiel` | part du potentiel de droits PLU non consommée ; monotonie **+1** | NULL → bin « manquant » |
| `sous_densite` | `parcel_residuel.sous_densite` | booléen | NULL → manquant/'false' |
| `sdp_residuelle_m2` | `parcel_residuel.sdp_residuelle_m2` | SDP constructible résiduelle (m²) | NULL → manquant |
| `tenure_bin` | DVF **toutes natures** (`p_model_ext_mut_all`) | ancienneté dernière mutation as-of Y → {<1, 1-2, 2-3, 3+, inconnu} | `'inconnu'` (rien détecté) |
| `permis_bin` | Sitadel (dernier permis sur la parcelle) | {<2a, 2-5a, 5-10a, 10a+, jamais} ; « < 24 mois » attendu NÉGATIF (projet en cours) | `'jamais'` |
| `canopee_pct` | LiDAR/ortho (`parcel_vegetation`) | % canopée | NULL → manquant |
| `ndvi_moyen` | `parcel_vegetation.ndvi_moyen` | NDVI | NULL → manquant |
| `friche` | Cartofriches (spatial_layers) | booléen | `false` |
| `piscine` | détection ortho validée / non-infirmée | booléen (hors `faux_positif`) | `false` |
| `pv_candidat` | détection ortho type PV | booléen | `false` |

### 3.3 Croisements et dummies (gelés dans l'artifact)

5 interactions retenues par mining GBM-shadow (`p_model/shadow.py`, sélection gloutonne sur
l'average precision de validation) — `FREEZE-scoring2026.json` :
`tenure_bin×permis_bin`, `tenure_bin×surface_m2`, `ndvi_moyen×zone_plu`, `tenure_bin×rot_nu`,
`surface_m2×permis_bin`. Plus des **dummies d'année 2017-2023** (le shift de niveau annuel est
absorbé, pas appris comme signal).

> **Angle mort features** : voir §7 pour `filo_dens_pop` (coefficient ≈ 0, mort) et les features
> à signe instable en walk-forward.

---

## 4. MODÈLE P — hazard discret sur WoE → log-hazard additif

### 4.1 Type exact (`scoring/p_model/model.py`)

**Régression logistique L2-régularisée sur features encodées en Weight-of-Evidence (WoE)**,
interprétée comme un **modèle de hazard en temps discret** (grain annuel, `PModel` docstring).

- **Grain / horizon** : parcelle × **année civile**. Le modèle prédit P(mutation L2-F pendant Y).
  Horizon = **12 mois** (l'année Y), features as-of 01/01/Y. Ce n'est PAS un modèle de survie
  continu ni multi-horizon : un hazard discret ré-estimé chaque année.
- **Encodage WoE** (`woe.py`) : ≤ 10 bins/feature (20 pré-bins quantiles → fusion). WoE(bin) =
  ln(part_positifs / part_négatifs) lissage +0,5 ; `min_count = 200` par bin ; monotonie
  **contrainte** par fusion PAV des bins adjacents violant l'ordre (uniquement `rot_nu`, `rot_bati`,
  `dormance_droits` = signe +1) ; bin « manquant » toujours explicite.
- **Logistique** : `LogisticRegression(C=5.0, L2, max_iter=2000, random_state=974)`
  (`FREEZE.C = 5.0`). Le log-hazard est **additif et traçable ligne à ligne** :
  contribution(feature) = coef × WoE(bin) ; contribution(bloc Z) = Σ features Z ; idem D. C'est ce
  qui alimente les « top 5 pourquoi » de la fiche (`p_v2/pipeline.py:116`).
- **Calibration** : **isotonique** ajustée sur l'année de validation **2025** (`model.calibrate`,
  `FREEZE.calibration = "isotonique sur 2025"`). `predict_proba` applique l'isotonique clippée
  [1e-7, 1−1e-7].
- **Recalage d'intercept** : à **chaque run servi**, seul l'intercept est recalé (décalage additif
  du log-hazard) sur la **dernière année labellisée** pour coller au taux de base observé —
  **coefficients et binning intacts** (`model.recale_intercept`, `pipeline.py:187`). Un re-train
  complet (binning + coefs + calibration) est une **décision humaine annuelle**, jamais automatique.
- **Artifact gelé** : `reports/m36-foncier/artifacts-m36-scoring2026.joblib`,
  `sha256 = 00a58008…4959b64`, gel **2026-07-12 19:54**, `model_version = m36-l2f-2026`. Le
  pipeline **REFUSE de tourner si le sha256 ne correspond pas au manifeste** (`pipeline.py:81`).

### 4.2 Entraînement

- **Train** : 2017-2024 ; **validation/calibration** : 2025 (`FREEZE.provenance`). n_features = 29,
  seed 974.
- **Walk-forward** : 6 folds, chaque fold s'entraîne sur toutes les années < année de test
  (`reports/m36-foncier/walk-forward.csv`). Le n_train croît de 863 326 (fold 2020) à 3 021 641
  (fold 2025) — dataset parcelle×année empilé.

### 4.3 Métriques réelles par fold (label L2-F, RR@1158, seed 974)

RR@k = taux de mutation dans le top-k / taux global (`evaluate.py:28`). Le protocole gelé évalue
à **k = 1158** (« la réserve jugée »), **hors copro** comme univers de référence.

| Fold (année test) | n_train | taux test | **RR@1158 (tout)** | **RR@1158 hors copro** [IC95] | ECE |
|---|---|---|---|---|---|
| 2020 | 863 326 | 1,64 % | 10,96 | **9,41** [8,09 ; 10,70] | 0,0013 |
| 2021 | 1 294 989 | 1,96 % | 9,74 | **8,61** [7,72 ; 10,02] | 0,0033 |
| 2022 | 1 726 652 | 1,96 % | 9,14 | **8,63** [7,60 ; 9,85] | 0,0024 |
| 2023 | 2 158 315 | 1,72 % | 7,37 | **7,30** [6,08 ; 8,44] | 0,0032 |
| 2024 | 2 589 978 | 1,51 % | 8,12 | **7,08** [5,99 ; 8,16] | 0,0029 |
| 2025 | 3 021 641 | 1,54 % | 6,89 | **6,73** [5,53 ; 7,84] | 0,0014 |

Synthèse gelée (`FREEZE.verdict_reference`) : *« walk-forward 6 folds RR@1158 6,9-11,0 (hors copro
6,7-9,4), fold 2025 = 6,73 [5,53-7,84] vs M3 2,91 — PROMU »*. Calibration excellente (ECE ≈ 0,001-0,003).

### 4.4 Contrôles de promotion (`decision-promotion.csv`, `verdict-strate.csv`)

Sur le held-out final **2025, hors copro, RR@1158** — comparatif des modèles/baselines :

| Modèle | RR@1158 (hors copro, 2025) |
|--------|----------------------------|
| **M3.6 (L2-F, promu)** | **6,73** |
| Ablation « Z seul » (contexte de secteur uniquement) | 5,07 |
| P complet « lot0 » (baseline pré-M3.6) | 2,85 |
| Baseline rotation DVF secteur brute | 1,08 |
| Baseline **Score V v1.3** | **0,51** (sous 1 → contre-prédictif au top-k) |

Décision : promu car ΔRR fold 2025 significatif, **tous folds RR ≥ 2**, signes stables
**24/29** (`stabilite-signes.csv` ; instables = coefs ~0). Contrôle négatif : labels permutés
intra-année → RR ≈ 1 (`evaluate.py:118`).

> Finding Phase 0 notable, à garder en tête : le « Z seul » (contexte de secteur) battait le
> « P complet lot0 » (5,07 vs 2,85). C'est ce qui a motivé la refonte M3.6 (label L2-F, DVF
> depuis 2014, croisements) portant le complet à 6,73. Le **Score V** (vendabilité) est
> **quasi-inutile pour prédire la mutation foncière** (RR@1158 = 0,51) — ce qui a été assumé :
> V n'est plus dans le tier (§7).

### 4.5 L'arène — juge champion/challenger (`scoring/arene.py`)

Outil de bascule (lecture seule, `labuse arene`) : RR@1158 + IC95 bootstrap **apparié** de ΔRR,
ECE, churn du top-1158 (budget 25 %), permutation, et **gate boussole golden éliminatoire** (une
négative factuelle golden qui passe brûlante/chaude/opportunite = REJET). Avertit explicitement
que le **RR absolu du run servi 2026 est in-sample/optimiste** (features as-of 2026 encodent déjà
les mutations 2025) et **non comparable** au walk-forward — seule la comparaison relative
champion↔challenger vaut (`arene.py:256`).

---

## 5. SCORE C (capacité) + assemblage des TIERS

« Score C » n'est pas un score 0-100 : c'est un **moteur de règles de capacité** qui filtre et
segmente le classement du modèle P (`scoring/p_v2/statuts.py`). Fonctions **pures, sans DB**.

### 5.1 Entrées (par parcelle, run v2)

`rang` (hors copro), `copro` (bool), `ecartee_etage0` (bool, hérité cascade), `p` (proba
calibrée), `contrib_d` (contribution bloc D du log-hazard), `sdp_residuelle_m2`, `surface_m2`,
`zone_plu`, `event_age_mois` (dernier événement BODACC daté).

### 5.2 Le « plancher C » (`statuts.py:46` `plancher_c`)

Une parcelle passe le plancher capacité ssi :

> **SDP résiduelle > 0** OU (**surface ≥ 600 m²** ET **zone ∈ {U, AU}**)

Motif : « un P fort sans capacité ne fait pas une opportunité produit » ; 600 m² ≈ plancher d'une
division en R+1 locale (`c_surface_min_m2 = 600.0`).

### 5.3 Événements datés (bypass)

Codes BODACC comptant comme « événement » (`pipeline.py:78`) : `BODACC_LJ`, `BODACC_RJ`,
`BODACC_SAUVEGARDE`, `BODACC_CESSION_FONDS`. Un événement < 6 mois (`event_bypass_mois`) fait
entrer une parcelle dans la zone tampon sans attendre le rang.

### 5.4 Attribution des tiers (`statuts.py:54` `assign_tiers`) + calibrage (`pipeline.py:237`)

Ordre de priorité (le dernier écrit gagne) : `a_creuser` (défaut) → `reserve_fonciere` → `chaude`
→ `brulante` → `ecartee` (étage 0 prime toujours).

- **Chaude** = (`rang ≤ n_entree` **entrée** OU `was_hot ∧ rang ≤ n_sortie` **maintien/hystérésis**
  OU `événement < 6 mois ∧ rang ≤ n_sortie` **bypass**) ∧ **plancher C** ∧ ¬copro ∧ ¬étage 0.
  - `n_entree` **calibré** pour que |{rang ≤ n_entree ∧ plancher C}| ≈ **1150** (continuité
    produit ; `calibre_n_entree`, `pipeline.py:243`). `n_sortie = round(1,4 × n_entree)`
    (anti-churn, cible < 15 %/recalcul hors événement).
- **Brûlante** = chaude ∧ `contrib_d ≥ brulante_seuil_d` ∧ (événement < 12 mois OU `contrib_d ≥
  top-décile D des chaudes`). Doctrine « un contexte seul ne franchit jamais un seuil » : il faut
  une **contribution parcellaire (bloc D)**. `brulante_seuil_d` est **calibré mécaniquement** :
  plus petit quantile de contrib_D des chaudes ramenant l'effectif brûlante dans **[30, 120]**
  (`calibre_brulante`, `statuts.py:98`).
- **Réserve foncière** = `sdp_residuelle_m2 ≥ top-décile des SDP > 0` ∧ `p < médiane` ∧ ¬étage 0
  ∧ ¬chaude. **Vitrine capacité, jamais présentée comme pipeline** (sélection négative prouvée
  Phase 0 : forte capacité mais faible probabilité).
- **À creuser** = tout le reste (survivant non chaude/réserve/écartée).
- **Écartée** = `ecartee_etage0` (exclusion dure cascade).

### 5.5 Répartition réelle des tiers (run servi `q_v7_defisc`, 431 663 parcelles)

| Tier | Parcelles | Part | Ce que c'est |
|------|-----------|------|--------------|
| 🔥 **brulante** | **120** | 0,03 % | tête chaude + contribution D forte / événement récent (garde-fou [30,120]) |
| **chaude** | **1 031** | 0,24 % | rang ≤ n_entree ∧ plancher C (chaude+brûlante ≈ 1 151 ≈ cible 1 150) |
| **reserve_fonciere** | **3 587** | 0,83 % | capacité forte, P faible |
| **a_creuser** | **72 980** | 16,9 % | survivants non prioritaires |
| **ecartee** | **353 945** | 82,0 % | = étage 0 cascade, intégralement |
| **Total** | **431 663** | 100 % | dont 3 424 copros (non rankées) |

La tête actionnable (brûlante + chaude + réserve) = **4 738 parcelles (~1,1 %)**.

### 5.6 Système legacy Matrice Q×A (encore calculé, plus « verdict »)

Pour mémoire (`config/scoring_matrice.yaml`, `dryrun.py:15` `compute_matrice`) : Q = qualité
(base 50 + Σ poids étages 0/1), A = accessibilité (étage 2). Convention officielle
(v2, 08/07/2026) : **chaude** = Q ≥ 65 ∧ A ≥ 60 ∧ A-hors-zone ≥ 60 ∧ A-complétude ≥ 50 ;
`a_surveiller` = Q ≥ 65 ; `a_creuser` = Q ≥ 50 ; sinon `ecartee` ; **exclue étage 0 = écartée** ;
**bascule événementielle** BODACC rouge = chaude sur les survivantes (doctrine, jamais balayée ;
parcelle-canari `97415000AC0253`). Répartition run servi : `matrice_statut` ecartee 409 404,
a_creuser 15 296, a_surveiller 5 821, chaude 1 142. Le score d'opportunité Q lui-même =
`opportunity.py` (base 50 − pénalités×sévérité + bonus, clamp [1,100] ; HARD_EXCLUDE → 0).

### 5.7 Score V (vendabilité) — signal parallèle, affiché à part

`score_v.py` + `score_v_constants.py` : V = max(0, min(100, A+B+C+D+E+malus)), familles A-E
(A détresse BODACC max 35, B cycle de vie **mis à 0** v1.3, C détachement géo max 15, D dormance
somme ≤ 25, E pression DPE max 15). Bandes : fort ≥ 50, présent ≥ 25, faible ≥ 1, aucun = 0.
Vue legacy `v_parcelles_brulantes` = chaude Q×A ∧ v_score ≥ **17**. Distribution live : aucun
369 684, na 47 942, faible 12 398, present 1 629, **fort 10** ; vue brûlantes = **112**. **V n'entre
plus dans le tier servi** (§7).

---

## 6. CHAÎNE DE CALCUL — de l'ingestion au tier de la fiche

```
┌─ INGESTION (par commune, reprenable) ─ ingestion/run_all.py
│   cadastre bulk → parcels ; couches (PLU/GPU, PPR, Filosofi, BD TOPO, DVF, Sitadel,
│   ortho piscines/PV, végétation, RNIC, amenites OSM, Cartofriches, QPV…)
│
├─ CASCADE + scoring d'opportunité ─ cascade/…, scoring/opportunity.py, completeness.py
│   evaluate_parcels(dryrun_label='q_v7_defisc') → dryrun_cascade_results (verdicts par couche),
│   dryrun_parcel_evaluations (opportunity_score Q, completeness, status)
│        │
│        ├─ MATRICE Q×A ─ dryrun.compute_matrice (config/scoring_matrice.yaml)
│        │     → matrice_statut ; ÉTAGE 0 = status ∈ {exclue, faux_positif_probable}
│        │
│        └─ SCORE V ─ score_v.py → parcel_v_score (v_score, v_band, signals)   [parallèle]
│
├─ MODÈLE P — pipeline v2 ─ `labuse score-v2` (scoring/p_v2/pipeline.py) :
│   1. verify_artifact()  (REFUS si sha256 ≠ gel)
│   2. rebuild_features()  → p_model_ext_dvf/mut/dataset (as-of), p_model_ext_copro
│   3. recale_intercept()  sur la dernière année labellisée
│   4. predict_proba()     → p_raw ; contributions() → contrib_Z / contrib_D / top-5
│   5. rangs & percentiles HORS COPRO (ties seedés 974)
│   6. étage 0 lu depuis le run servi (dryrun status exclue/faux_positif) → ecartee_etage0
│   7. TIERS ─ statuts.assign_tiers (plancher C, n_entree≈1150, hystérésis, brûlante [30,120])
│   8. écriture versionnée → parcel_p_score_v2 (run_id) ; snapshot gelé (M1) ; ICD (annexe)
│
└─ AFFICHAGE ─ api/app.py:2002 _q_v2_fiche (run épinglé Q_A_RUN_LABEL) + score_v2.py (/v2/*)
    verdict d'en-tête = verdictMeta (frontend/src/lib/status.ts) :
        étage 0 ? → « Écartée »   sinon tier v2 (Brûlante/Chaude/Réserve/À creuser/Écartée)
        sinon (aucun run v2) → repli matrice_statut legacy
    + rang, « ×N vs moyenne » (mult_base), 5 « pourquoi » lisibles, badges (copro, événement,
      veille_succession). p_raw stocké mais JAMAIS affiché brut.
```

Points de vérité de la chaîne :
- Le run servi est **une constante configurable** (`Q_A_RUN_LABEL` / `VITE_RUN_LABEL`), pas un
  timestamp — front et back doivent rester alignés (`test_run_serving_coherence`).
- Le tier `ecartee` v2 = l'étage 0 de la cascade **exactement** (353 945). Le modèle P ne
  « désécarte » jamais une parcelle exclue par la cascade.
- **Deux univers de dataset** : M3 base (`p_model_dataset`, années 2022-2026, DVF≥2021) vs
  **ext servi** (`p_model_ext_dataset`, 2017-2026, DVF≥2014, label L2-F). Le pipeline servi lit
  **l'ext**.

---

## 7. ANGLES MORTS — ce que je constate en lisant le code

**A. Trois systèmes qui se chevauchent, un seul servi — terrain glissant.** « Chaude » et
« écartée » existent dans DEUX taxonomies (matrice Q×A *et* tiers P×C) avec des définitions
différentes. Le même run_label `q_v7_defisc` désigne à la fois une ligne de
`dryrun_parcel_evaluations` (matrice) et une ligne de `parcel_p_score_v2` (tiers), lues dans des
tables différentes. Sans le mapping du §0, une requête sur le « mauvais » `chaude` (1 142 matrice
vs 1 031 tier) donne un chiffre faux.

**B. Feature morte : `filo_dens_pop`.** `stabilite-signes.csv` : signe majoritaire 0,0,
0/6 folds concordants → **coefficient ≈ 0**. Elle est ingérée, encodée, mais n'apporte rien.
Candidates faibles/instables (signe stable < 5/6 folds) : `permis_24m_norm` (4/6), `qpv` (4/6),
`window_coverage` (4/6), `dormance_droits` (4/6). À élaguer ou réexaminer au prochain re-train.

**C. `v_parcelles_brulantes` (112) ≠ tier `brulante` (120).** Deux définitions de « brûlante »
cohabitent (vue V legacy chaude∧V≥17 vs tier P contrib_D+événement). La vue V est encore en base
mais n'est pas le verdict. Risque de double compte / confusion dans un tableau de bord.

**D. Le Score V est prouvé quasi-inutile pour la mutation foncière (RR@1158 = 0,51 < 1) mais
reste calculé, stocké et affiché.** Toute la famille B (âge dirigeant, cessation, SCI dormante) a
été **mise à 0 point** en v1.3 après backtest (anti-signaux) ; le malus « achat récent » aussi
(contre-prédictif). Le circuit reste câblé « pour garder l'UI et le backtest » — dette assumée.
Seuls **10 parcelles** ont v_band « fort ». Sa présence entretient l'idée fausse que V participe
au tier.

**E. Millésime unique = fuite temporelle faible mais réelle sur les couches statiques.** `zone_plu`,
Filosofi, BD TOPO, ortho, végétation, `parcel_residuel` n'ont **qu'un seul millésime (ingestion
2026)** et sont appliqués rétroactivement aux années d'observation 2017-2025 (`_STATIQUE`,
`features.py:34`). Un reclassement PLU ou une piscine postérieurs à Y « fuient » dans le passé.
Consigné feature par feature au dictionnaire, mais c'est un biais optimiste structurel du
walk-forward.

**F. RR absolu du run servi = in-sample, optimiste.** Le run servi score 2026 (features as-of
01/01/2026) mais est parfois évalué contre le label 2025 → les fenêtres encodent déjà les
mutations 2025 (`arene.py:256`). Ne jamais citer le RR « tout » ≈ 23 (verdict-strate) comme perf
du modèle : c'est du in-sample avec copro (base rate copro ≈ 29 %). La vraie perf out-of-sample =
**6,73** (walk-forward fold 2025 hors copro).

**G. `mutation.py` (« Radar Mutation V1 ») : moteur orphelin.** Un quatrième score 0-100
(sous-exploitation, intensité latente, zonage, potentiel régional, marché, foncier acquérable,
malus contrainte) avec ses propres niveaux (prioritaire/forte/surveiller/faible). Ses poids sont
explicitement des **PLACEHOLDER « à caler terrain »** (`mutation.py:25`). Il lit `status`,
`opportunity_score`, `completeness_score` (matrice legacy) et le bâti — **il n'entre pas dans les
tiers servis**. Sa relation aux 3 autres systèmes n'est documentée nulle part hors ce fichier.

**H. Valeurs par défaut discutables.**
- `acces_equipements` : distance absente → **contribution nulle** = « comme si équipements
  infiniment loin ». Choix prudent, mais une parcelle sans données d'aménités et une parcelle
  vraiment isolée sont indistinctes.
- `permis_bin` défaut `'jamais'` et `tenure_bin` défaut `'inconnu'` : « inconnu » et « rien
  détecté » sont fusionnés ; leur portée varie avec Y (troncature DVF), consigné mais réel.
- WoE `missing_woe = 0` quand l'effectif manquant < 200 : neutralise, mais peut masquer un signal
  d'absence sur une feature peu couverte.

**I. Dérive documentaire (docs ≠ code).** Plusieurs docs décrivent un système qui n'est plus servi :
- `docs/BAREME_VERDICT_MUTABILITE.md` décrit le scoring comme cascade Q + complétude → verdict
  {opportunité, à creuser, écartée, faux positif} : c'est la **matrice legacy**, pas les tiers P×C.
  Seuils statiques (opp ≥ 65, compl ≥ 50) ≠ seuils dynamiques P×C (n_entree calibré, hystérésis).
- `NOTES_SCORING_DRYRUN.md` cite « source de vérité `run_label='q_v2'` » — **q_v2 a été éradiqué**
  (bascule M8) ; le servi est `q_v7_defisc` et le verdict vient de `parcel_p_score_v2`, pas du dryrun.
- La **définition du label L2-F** et le **plancher C** ne sont dans aucune doc produit — seulement
  en commentaires de code. (Ce présent document comble ces deux trous.)
- `score_v_constants.py:26` : « 120 brûlantes » est exact aujourd'hui mais est un **instantané** du
  run ; le seuil 17 est verrouillé, l'effectif suit le run.

**J. Ambiguïté honnête.** Le mapping mandat « Score P / Score C » ↔ code n'est pas 1:1 : « Score C »
n'existe pas comme colonne, c'est le moteur `plancher_c` + `assign_tiers`. Et deux endpoints ne lisent
pas le run v2 de la même façon (`app.py`/`scoreur.py` épinglent `Q_A_RUN_LABEL` ; `score_v2.py`
`_latest_run` prend le dernier par `computed_at`) — cohérent tant que le dernier run = le servi,
fragile sinon. À surveiller si un run candidat est scoré après le servi.

---

### Annexe — fichiers sources faisant foi

| Sujet | Fichier |
|-------|---------|
| Features (registre) | `src/labuse/scoring/p_model/features.py` |
| Dataset as-of + label (base) | `src/labuse/scoring/p_model/sql.py` |
| Dataset étendu + label L2-F + copro | `src/labuse/scoring/p_model/ext_sql.py` |
| WoE binning | `src/labuse/scoring/p_model/woe.py` |
| Modèle (logistique/hazard) | `src/labuse/scoring/p_model/model.py` |
| Mining interactions (shadow GBM) | `src/labuse/scoring/p_model/shadow.py` |
| Métriques (RR@k, ECE, churn…) | `src/labuse/scoring/p_model/evaluate.py` |
| Pipeline v2 servi | `src/labuse/scoring/p_v2/pipeline.py` |
| Tiers + capacité (plancher C) | `src/labuse/scoring/p_v2/statuts.py` |
| Arène (bascule) | `src/labuse/scoring/arene.py` |
| Score V (vendabilité) | `src/labuse/scoring/score_v.py`, `score_v_constants.py` |
| Matrice Q×A + étage 0 | `src/labuse/scoring/dryrun.py`, `config/scoring_matrice.yaml` |
| Opportunité / complétude (cascade) | `src/labuse/scoring/opportunity.py`, `completeness.py` |
| Radar Mutation V1 (orphelin) | `src/labuse/mutation.py` |
| API fiche / v2 | `src/labuse/api/app.py`, `api/score_v2.py`, `api/scoreur.py` |
| Manifeste de gel du modèle | `reports/m36-foncier/FREEZE-scoring2026.json` |
| Métriques walk-forward | `reports/m36-foncier/walk-forward.csv`, `verdict-strate.csv`, `stabilite-signes.csv` |
