# SCORING-5-RETOUR — corrections, décisions actées, mesures avant construction

**Date : 21/09/2026 · Branche : `audit/scoring-5` (base `b2b0cca1`) · rien de servi ne change, `q_v11_m137` reste servi.**
Livrables : le rapport `SCORING-5-RAPPORT.md` corrigé en place (voir §1) + le présent retour. Scripts et données de mesure : `reports/scoring-5/` (jetables, jamais destinés au merge).

---

## 1. Corrections faites au rapport

1. **Parcelle bâtie ≠ zéro pénalité** — corrigé (§2.1 temps 2 et 3 du rapport). La capacité reste nette du bâti (le résiduel croise BD TOPO + CoSIA), mais le bâti entre désormais dans le **coefficient de faisabilité** : un promoteur paie la démolition (coût ∝ volume ≈ emprise × hauteur), l'éviction/le relogement éventuel et le délai. Barème proposé, gradué par `taux_emprise_pct` et `batiment_hauteur_lidar` (70,3 %) : nu → 1,0 · emprise ≤ 20 % → 0,9 · 20-50 % → 0,8 · > 50 % ou ≥ R+2 → 0,65 ; hauteur manquante → cran par l'emprise seule + couverture. Valeurs provisoires calées sur les témoins (§3). Jamais dans l'assiette, jamais une exclusion (acquis PALIERS-1 intact).
2. **Contexte ±8 : retiré du calcul** (§2.1 temps 4, §2.2-5.5, tableau 4.1, §8, §10 du rapport). Aucune justification métier défendable pour la magnitude (pourquoi 8 ?), et double compte avec le Signal qui porte déjà le dynamisme de marché (`rot_*`, `med_pm2_*`, voisinage). En V1 le contexte est **information fiche** ; ré-examen V1.1 sur témoins seulement. La formule devient `score = clip(barème_capacité × coef_faisabilité, 0, 100)`.
3. **Acquis des trois écarts de brief** — mis en cohérence en tête de rapport, une ligne chacun : feat/paliers-1 mergée dans main (`b6aec2bd`) ; `SOURCES-AUDIT.md/.csv` = le vrai tableau des sources (pas de colonne littérale « déclenche un run ? ») ; statut réel `partenariat_requis` (pas `a_faire`).
4. **Décisions actées par Vic** gravées en tête du rapport (bloc dédié) : GO architecture · V3 lexicographique (V2 écartée) · Signal = recette q_v14, grain annuel + re-score mensuel · plafond PP = borne assumée · assemblage = information seule en V1 · ordre residuel-serve → ablations → q_v15 → bascule · bandes et barèmes issus des témoins, pas du papier.
5. **Correction d'acquis supplémentaire découverte par RESIDUEL-1** (§2 ci-dessous), reportée dans le rapport (§2.2-5.1 et §11.2) : « les 150 `propose` sont ignorées par le calcul » n'est vrai que pour l'overlay.

## 2. RESIDUEL-1 lot 1 — constat et prérequis (lecture seule, rien lancé)

**Le builder lit-il `zonage.py` en validées-only ?** OUI pour l'**overlay** calibrage (`_calibrage_overlay` ne retourne que `statut: valide` — `zonage.py:303-311`) ; **NON pour la base** : `_val()` (`zonage.py:105-116`) lit la valeur numérique de toute feuille, et **95 feuilles `propose` numériques branchent le calcul** (hauteur faîtage 10, égout 9, CES 11, retraits voie 21 + limites 13, pleine terre 18, stationnement 13 — comptage `config/plu_destinations/974*.yaml`). Hauteur et CES étant les moteurs de la capacité, ces valeurs entrent dans la SDP. Comportement documenté (PLU-CALIBRAGE-3 a préservé les valeurs de l'ancien système), mais **à trancher avant le run** : valider ces 95 feuilles (avec citation) ou acter le comportement.

**Le scoring lit-il `parcel_residuel` ou recalcule-t-il ?** Il **lit la vue, prouvé** : `build_static` LEFT JOIN `parcel_residuel` (`p_model/sql.py:292-296`), `refresh_static_residuel` UPDATE FROM la vue (`sql.py:340-368`), recette q_v12/q_v14 FROM la vue (`qv12.py:244-255`). La vue filtre `run_seq = (SELECT … WHERE is_served)` avec unicité par index partiel (`residuel_runs.py:54-69`). Aucun lecteur à `run_seq` en dur (grep = 0). Le scoring ne rappelle jamais `compute_residuel`. **Conséquence : après `residuel-serve`, le nouveau résiduel se propage au scoring au prochain rebuild features — aucun code à changer.**

**Prérequis avant le run parallèle** (rien à coder pour le lancer — la chaîne existe entière) :
1. `labuse compute-residuel --ile --new-run "<label>"` (`cli.py:1923-1985`) crée un run neuf non servi ; garde `assert_writable` refuse d'écrire dans le run servi (`residuel.py:183`) ; bascule = geste séparé `labuse residuel-serve <seq>` (`cli.py:2008-2015`), atomique et réversible ; coexistence garantie (clé `run_seq, parcel_id`). Budget ~1 h 47 (run servi : `duree_s` 6 399 s).
2. Trancher les **95 feuilles `propose` numériques** (ci-dessus).
3. **Process frais** obligatoire : `_calibrage_overlay` et `_zonage_doc` sont en `lru_cache` à vie du process (`zonage.py:78,288`) — toute édition YAML avant run impose un redémarrage.
4. Entrées à l'état attendu : bâti BD TOPO présent, `parcel_bati_revele` CoSIA frais (lus à `residuel.py:44-50`) ; hauteurs BD TOPO souvent absentes → SDP « estimée » assumée.
5. État de référence figé pour comparaison (run servi run_seq 2, pré-calibrage) : calculées (cause NULL) 253 764 · zone_non_constructible ≈ 105,8 k · terrain_exigu 50 192 · zone_non_resolue ≈ 13,6 k · habitat_interdit ≈ 5,6 k · hors_plu 4 397 · redhibitoire 4 145 (`SELECT cause, count(*) FROM parcel_residuel_runs WHERE run_seq=2 GROUP BY 1`). Comparer via `compare_residuel_servi` (`residuel.py:213-230`) ou diff SQL run-à-run **avant** tout `residuel-serve`.

## 3. Parcelles témoins — tableau, monotonicité, bandes

Fichiers : **`reports/scoring-5/TEMOINS.csv`** (30 lignes : idu, commune, catégorie, raison, composantes, score) + script jetable `reports/scoring-5/temoins_score_v1.py` (SELECT uniquement, barème provisoire en clair). 14 communes (≥ 6 exigées). Spec calculée = la spec corrigée (§1 : sans contexte, avec facteur bâti). Caveat structurel : **résiduel servi = pré-calibrage** — les scores bougeront au recalcul ; les bandes sont une méthode, pas des valeurs finales.

**Composition** : 10 « évidemment bonnes » (SDP 1 340-5 000 m², zone U, pente ≤ 10 %, emprise ≤ 15 %, 10 communes) · 10 « évidemment mauvaises » non écartées par la cascade (terrains exigus en pente 71-94 %, SDP ≤ 102 m², lames, bâties saturées emprise ≥ 148 % faîtage ≥ 9 m) · 10 « limites » (2 zonage A/N à 96 %, 2 PPR partiel drapeau fort, 2 bâties sous-utilisées, 2 non calculables `zone_non_resolue`, 2 AU fermées).

**Scores observés** : bonnes 85-100 (une à 64, voir ci-dessous) · limites 30-72 · mauvaises 0-25 · non calculables affichées telles quelles (jamais 0).

**Verdict monotonicité : VERT.** Par construction (barème non décroissant en SDP, facteurs ∈ ]0,1], plancher 0,4) et empiriquement : aucune inversion — la pire « bonne » (64) reste au-dessus de la meilleure « mauvaise » (25). Deux observations à retenir :
- **Cas d'école `97411000AB0798`** (Saint-Denis, « bonne » a priori → 64) : la donnée révèle une lame (f_forme 0,8) portant un bâtiment ≥ 9 m (f_bati 0,8). Pas une violation — le score voit ce que les critères de sélection a priori ne voyaient pas. À montrer à Vic.
- **Les 2 témoins A/N 90-99 % scorent 0** : le résiduel servi leur donne SDP 0 (`cause zone_non_constructible`). **Preuve chiffrée** que le reclassement B de la cascade (pénalité d'assiette) ne produit rien tant que le résiduel n'est pas recalculé **sur assiette clippée** : réintégrées à l'univers, elles resteraient à 0. Le calcul sur assiette clippée est donc un requis du moteur résiduel pour SCORING-6, pas un raffinement.

**Distribution île** (univers = 281 403 non-écartées q_v13_sources1 = 431 663 − 150 260 ✓ ; une requête CTE : résiduel servi × terrain × LiDAR × statut AU × accès) : NC 3 814 · 0-9 : 155 901 · 10-19 : 31 724 · 20-29 : 24 297 · 30-39 : 20 517 · 40-49 : 15 837 · 50-59 : 10 165 · 60-69 : 11 020 · 70-79 : 4 014 · 80-89 : 2 120 · 90-99 : 1 518 · 100 : 476. Seuils : ≥ 80 → **4 114 (1,5 %)** · ≥ 60 → 19 148 · ≥ 40 → 45 150 · > 0 → 133 359.

**Bandes proposées** (coupures aux trous observés sur témoins : mauvaises ≤ 25, limites ≥ 30 ; décision finale = Vic, à re-caler post-calibrage) :

| Bande | Libellé proposé | Effectif île (pré-calibrage) |
|---|---|---|
| **A ≥ 80** | opportunité majeure | 4 114 (1,5 %) |
| **B 50-79** | opportunité réelle | 25 199 |
| **C 30-49** | intérêt sous conditions | 36 354 |
| **D < 30** | sans intérêt foncier significatif | 211 922 |
| **NC** | non calculable (motif affiché) | 3 814 |

## 4. Ablations au banc K0 — tableau et recommandation

Protocole : banc K0 (train ≤ 2023 · isotonique par segment calibrée 2024 · test 2025), hygiène cible (ventes groupées flaguées, clients LABUSE exclus). A = chiffres cités de COMPTE-RENDU-SCORING-2 (jamais re-mesurés). **Contrôle de reproduction préalable** : la recette q_v14 re-fitée sur le cache reconstruit coïncide avec les acquis — AUC 0,6260 (≈ 0,626 SCORING-4), lift 2,272, préc@100 méd 0,080, Priorité absolue 34,96 % sur 123 (≈ PALIERS-1 : 34,4 % sur 119). Le banc est fiable.
Fichiers : `reports/scoring-5/ablations_k0.csv` + script jetable `scripts/audit/scoring/scoring5_ablations.py` (mode `--only ref|B|C` reprenable). Fits : ~50-70 s chacun. Rien de servi touché.

| Métrique | A — servi (cité) | réf q_v14 | **B — simplifié** (sans filo×3, piscine, pv) | **C — dynamiques seuls** (20 feats) |
|---|---|---|---|---|
| AUC global | 0,6127 | 0,6260 | 0,6231 | 0,5995 |
| AUC bâti / nu / PM / copro | — | 0,587 / 0,664 / 0,669 / 0,597 | 0,585 / 0,662 / 0,666 / 0,605 | 0,573 / 0,635 / 0,636 / 0,603 |
| ECE global | 0,0013 | 0,0020 | 0,0021 | 0,0024 |
| ECE segments (max = copro) | — | 0,0140 | 0,0136 | 0,0106 |
| Brier | — | 0,01482 | 0,01482 | 0,01485 |
| Lift décile sup | 2,06 | 2,272 | 2,238 | 2,093 |
| préc@100 médiane/commune | 0,060 | 0,080 | 0,090 | 0,090 |
| precision@500 / 1000 / 2000 | — | 0,186 / 0,132 / 0,103 | 0,194 / 0,140 / 0,108 | 0,168 / 0,138 / 0,095 |
| Priorité absolue (p ≥ 0,20) : préc (n) | 13,7 % (73, par rang) | 34,96 % (123) | 32,58 % (132) | 26,73 % (101) |
| À suivre absolue : préc (n) | — | 13,22 % (484) | 12,73 % (534) | 14,25 % (379) |
| Recall de tête (ventes 2025 captées) | — | 1,65 % | 1,71 % | 1,25 % |
| Churn top-1158 vs servi | 0,180 | 51,3 % | 51,6 % | 66,8 % |

Interactions : B garde les 4 croisements q_v14 ; C n'en garde que 2 (`tenure×permis`, `tenure×rot_nu`). Rappel bruit de tête ±8 pts (COMPTE-RENDU-SCORING-2) : l'écart Priorité B/réf (32,6 vs 35,0 %) est dans le bruit — les lignes stables (AUC, lift, préc@k) font foi.

**Recommandation (une)** : **garder la recette q_v14 complète pour q_v15 — au plus retirer `piscine`/`pv_candidat`** (mortes au servi, SCORING-RAPPORT §B.2 ; l'écart B−réf ne leur est pas attribuable), **et garder les 3 filo** : leur retrait coûte de façon petite mais cohérente sur les lignes stables (AUC −0,003, lift −0,034) pour un gain nul. **C réfute « les statiques sont du lest »** : sans zone/surface/pente/résiduel/nu, l'AUC tombe à 0,5995 (−0,026), le lift à 2,09, la Priorité à 26,7 % et le churn explose à 66,8 % — le foncier statique est indispensable au Signal ; le mouvement seul garde une tête exploitable mais perd le corps du classement. Cohérent avec l'architecture : le Score porte le foncier, mais le Signal a besoin des deux.

## 5. Ce qui bloque encore avant d'écrire SCORING-6 (mandat de construction)

1. **Geste Vic — `residuel-serve` post-calibrage** : trancher les 95 feuilles `propose` numériques, lancer `compute-residuel --ile --new-run` en process frais (~1 h 47), comparer au run 2, basculer. Tout le Score en dépend ; les bandes du §3 sont à re-caler après.
2. **Moteur résiduel sur assiette clippée** : requis prouvé par les témoins A/N 90-99 % (§3) — le reclassement B de la cascade est sans effet sans lui. À spécifier dans SCORING-6 (extension de `compute_residuel` : assiette = emprise clippée des contraintes géométriques certaines, pas la parcelle entière).
3. **Ventilations manquantes pour les frontières A/B de la cascade** : PPR rouge 100 % vs partiel (le `detail` ne porte pas le %), ER/EBC à 100 % — ajouter le % de recouvrement au `detail` du dry-run, puis compter.
4. **Journal des deltas d'ingestion** (`spatial_layers` : quel objet a changé quand) — la pièce manquante de la cascade en delta (§8.3 du rapport).
5. **`sync-run.sh` filtré par `run_label`** — correctif simple avant la première bascule nouvelle génération (§8.6 du rapport).
6. **Décisions Vic restantes** : bandes finales (post-calibrage, sur témoins re-scorés), vocabulaire client du couple Score × Signal, validation des libellés FR.
7. ~~Composition des features du Signal~~ — **tranchée par les ablations (§4)** : recette q_v14 complète pour q_v15, au plus sans `piscine`/`pv_candidat` (micro-décision Vic) ; filo gardées ; les statiques indispensables (C réfuté).
