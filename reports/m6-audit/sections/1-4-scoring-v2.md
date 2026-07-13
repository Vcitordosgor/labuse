# §1.4 — Validité du scoring v2 & protocole forward

**Audit LECTURE SEULE — M6 Phase 1** · 2026-07-13 · branche `audit/grand-check`
Run audité : `m36-l2f-2026-2026-07-12` (431 663 parcelles, snapshot `m5-2026-07-12`).
Modèle P M3.6 GELÉ : sha256 de `reports/m36-foncier/artifacts-m36-scoring2026.joblib`
**re-vérifié ce jour** = `00a58008143d5260…` = manifeste `FREEZE-scoring2026.json` ✔.
Aucune écriture base, aucune modification de code ; `labuse monitor-forward` **non exécuté**
(il écrit hors de `reports/m6-audit/`, cf. B.2) — analysé statiquement.

**Verdicts en une ligne** : branchements **29/29 OK** (0 feature vide ; 1 constante au
scoring, 2 à poids ≈ 0) · politique NULL **SAINE** (bin « manquant » explicite, net
négatif ; 0 brûlante sous 7/9 de complétude, 17 chaudes/1 032 sous 2/3 — listées) ·
dispositif forward **ARMÉ** (3 snapshots gelés complets, monitor-forward opérationnel,
protocole N+2 documenté) · **7 anomalies consignées**, aucune bloquante.

---

## BLOC A — Validité du scoring v2

### A.1 — La chaîne complète (formules retracées)

Code lu : `src/labuse/scoring/p_v2/{pipeline,statuts,monitoring}.py`,
`src/labuse/scoring/p_model/{features,model,woe,ext_sql,sql}.py`, `src/labuse/api/*`.

```
(1) DONNÉES     rebuild_features() : p_model_ext_dvf (UNION DVF histo 2014-2020 +
                prod 2021-2025) → p_model_ext_mut_l2 (mutations L2 dédupliquées,
                flag exclue_l2f) → p_model_ext_dataset (1 ligne / parcelle × année,
                fenêtres strictes as-of 01/01/Y) + p_model_ext_copro.
                p_model_static & p_model_permits : RÉUTILISÉS de M3 (lecture seule,
                PAS re-matérialisés par score-v2 — cf. anomalie ANO-7).
(2) DÉRIVÉES    derive() : rot_nu/rot_bati (shrinkage gamma-Poisson vers le taux
                commune, prior m ∈ [50, 5000]) ; acces_equipements = Σ exp(-dist/800 m)
                (distance absente = contribution 0) ; dormance_droits = pct_potentiel.
(3) MODÈLE P    artifact gelé (REFUS si sha256 ≠ manifeste). 29 features → encodage
                WoE (≤ 10 bins, bin « manquant » TOUJOURS explicite) → logistique L2
                (C=5, seed 974) + 5 interactions (tenure×permis, tenure×surface,
                ndvi×zone_plu, tenure×rot_nu, surface×permis) + dummies années
                2017-2023 (toutes = 0 en 2026). z = intercept (−4,2391) + shift + Σ coef·WoE.
(4) RECALAGE    à chaque run : intercept SEUL, bissection pour que mean(sigmoïde(z))
                = taux observé de la dernière année labellisée (ici 2025, taux_base
                1,563 %). Coefficients et binning INTACTS (politique mandat 1.3).
(5) CALIBRATION p_raw = isotonique(z) (ajustée sur 2025 au gel), clip [1e-7, 1-1e-7].
(6) RANGS       univers HORS COPRO (copro = RNIC ∪ mutations DVF exclusivement-
                appartements ; 3 424 parcelles) ; ties départagés par aléa seedé 974.
                percentile = 100·(1 − (rang−1)/N) ; mult_base = p/taux_base.
(7) TIERS v2    plancher C : sdp_residuelle > 0 OU (surface ≥ 600 m² ∧ zone U/AU).
                n_entree calibré pour ~1 150 chaudes → run : n_entree=2445, n_sortie=3423.
                chaude = (rang ≤ n_entree | maintien | bypass événement < 6 mois)
                         ∧ plancher C ∧ ¬copro ∧ ¬étage 0.
                brûlante = chaude ∧ contrib_D ≥ 1,4208 ∧ (événement BODACC < 12 mois
                         ∨ contrib_D ≥ 1,7468 [top décile]) — seuil calibré mécaniquement
                         pour un effectif ∈ [30, 120] → 119.
                réserve foncière = top décile SDP ∧ p < médiane ∧ ¬chaude ∧ ¬étage 0.
                Hystérésis : sans objet ici (premier run v2, prev_run = null).
(8) ÉTAGE 0     pipeline : dryrun_parcel_evaluations run_label='q_v2', status ∈
                {exclue, faux_positif_probable} → tier 'ecartee' (prime sur tout).
(9) VERDICT     produit (API/tuiles/listes) : tier v2 du run + étage 0 du RUN SERVI
    EFFECTIF    = Q_A_RUN_LABEL = 'q_v3_datagap' (score_v_constants.py:32) qui prime.
                → 119 brûlantes en base, 2 en étage 0 q_v3_datagap = 117 effectives ;
                  1 032 chaudes, 72 en étage 0 = 960 effectives (chips M5.1 ✔ vérifié SQL).
```

⚠ **ANO-1 (structurelle)** : l'étage 0 utilisé PAR LE PIPELINE au moment du tiering est
`q_v2` (codé en dur, `pipeline.py:218`), celui du PRODUIT est `q_v3_datagap`. Les deux
référentiels divergent (2 brûlantes + 72 chaudes « fantômes » : tier chaud en base,
écartées à l'affichage). Consigné en SYNTHESE-M51 (« 117 et non 119 ») mais la racine —
deux référentiels d'étage 0 — reste ouverte. Constat, pas de correctif (mandat).

### A.2 — Branchements réels des 29 features (dataset `annee=2026` du run)

Le dataset n'a pas été re-matérialisé depuis le run (un seul run v2 ; monitor-forward ne
rebuild pas) : les % ci-dessous sont ceux du moment du run.

| Feature | Bloc | Coef | Table source (chaîne) | % non-NULL 2026 | Variance 2026 | Verdict |
|---|---|---|---|---|---|---|
| rot_nu | Z | +0,678 | p_model_ext_mut_l2 ← DVF union + frame (shrinkage) | 100 | OK | **OK** |
| rot_bati | Z | +0,478 | idem | 100 | OK | **OK** |
| med_pm2_terrain_36m | Z | −0,062 | p_model_ext_mut_l2 (médiane secteur 36 m) | 94,3 | OK | **OK** |
| med_pm2_bati_36m | Z | −0,089 | idem | 96,1 | OK | **OK** |
| tendance_pm2_bati | Z | +0,100 | idem (12 m vs début fenêtre) | 88,2 | OK | **OK** |
| permis_24m_norm | Z | +0,073 | p_model_permits ← sitadel_permits | 100 | OK | **OK** |
| dens_bati_secteur | Z | −0,271 | p_model_static/bati ← spatial_layers (BD TOPO) | 100 | OK | **OK** |
| pct_bati_secteur | Z | −0,329 | idem | 100 | OK | **OK** |
| filo_snv_pp | Z | +0,216 | p_model_filo ← filosofi_carreaux_200m | 89,3 | OK | **OK** |
| filo_pct_pauv | Z | +0,260 | idem | 89,3 | OK | **OK** |
| filo_pct_prop | Z | +0,050 | idem | 89,3 | OK | **OK** |
| filo_dens_pop | Z | −0,161 | idem | 89,3 | OK | **OK** |
| qpv | Z | **−0,004** | p_model_geo ← spatial_layers kind=qpv | 100 | 9,6 % true | **MORTE (poids ≈ 0, IV 0,0000)** |
| pente_moy_deg | Z | −0,141 | parcel_terrain (RGE ALTI 5 m) | 98,1 | OK | **OK** |
| acces_equipements | Z | +0,065 | parcel_amenites (4 dist OSM) | 100 (les 4 dist) | OK | **OK** |
| zone_plu | Z | +0,514 | p_model_geo ← GPU (dont 'inconnu' 1,0 %) | 100 | 5 cat. | **OK** |
| window_coverage | Z | +0,492 | déterministe (fenêtre DVF) | 100 | **CONSTANTE = 1,0** | **MORTE AU SCORING 2026** |
| nu_constructible | D | +0,666 | emprise bâti ≤ 20 m² × zone U/AU | 100 | 18,1 % true | **OK** |
| surface_m2 | D | +0,284 | p_model_frame (mvt_parcels/parcels) | 100 | OK | **OK** |
| dormance_droits | D | −0,093 | parcel_residuel.pct_potentiel | **61,1** | OK | **OK (39 % hors périmètre, bin manquant)** |
| sous_densite | D | −0,187 | parcel_residuel | **61,1** | OK | **OK (idem)** |
| sdp_residuelle_m2 | D | +0,498 | parcel_residuel | **61,1** | OK | **OK (idem)** |
| tenure_bin | D | +0,819 | p_model_ext_mut_all (DVF union 2014+) | 100 (82,9 % 'inconnu') | 5 cat. | **OK** |
| permis_bin | D | +1,001 | p_model_permits | 100 (91,2 % 'jamais') | 5 cat. | **OK** |
| canopee_pct | D | +0,605 | parcel_vegetation (LiDAR HD) | 98,7 | OK | **OK** |
| ndvi_moyen | D | +0,114 | parcel_vegetation | 98,7 | OK | **OK** |
| friche | D | **+0,000** | spatial_layers kind=friche (Cartofriches) | 100 | 641 true (0,15 %) | **MORTE (poids ≈ 0, IV 0,0000)** |
| piscine | D | +0,787 | ortho_detections type=piscine hors faux_positif | 100 | 4,1 % true | **OK** |
| pv_candidat | D | +0,337 | ortho_detections type=pv | 100 | 4,6 % true | **OK** |

Contrôle de fraîcheur amont : `p_model_permits` en phase avec `sitadel_permits`
(max identiques 2026-08-17 — date **future**, cf. ANO-4). Interactions : les 5 sont
présentes dans l'artifact, coefficients non nuls (−1,88 à +0,46).

**Liste « champs morts »** :
1. `window_coverage` — alimentée mais **variance nulle en 2026** (fenêtres 36 mois
   pleines partout depuis l'union 2014+) : contribution uniforme +0,0124, ne
   discrimine rien au scoring courant. Utile au train (fenêtres 2017 clampées) — pas
   un bug, mais une feature morte à l'inférence.
2. `qpv` — coef −0,0038, IV 0,0000 : régularisée à néant, calculée pour rien.
3. `friche` — coef +0,0004, IV 0,0000 : idem (641 true seulement île entière).
4. Colonne `nu` du dataset : calculée (`ext_sql.py:255`), consommée nulle part
   (`nu_constructible` est recalculée indépendamment). Colonne morte inoffensive.
   (Les autres colonnes non-features — dist_*, n_mut_*, rot_*_brute, stock_secteur,
   label_l2, owner_type — sont des intrants de dérivation ou des métas assumées.)

**Verdict A.2 : branchements OK.** 29/29 features réellement alimentées depuis leur
table source ; aucune vide ; 1 constante (structurelle 2026) + 2 poids nuls = consignées.

### A.3 — Politique des NULL

**Mécanisme (woe.py)** : jamais d'imputation, jamais de zéro implicite dans l'encodage.
Valeur manquante → index de bin −1 → `missing_woe` : WoE PROPRE appris au train si
≥ 200 manquants, sinon 0 (neutre). En amont : `zone_plu` NULL → catégorie 'inconnu'
(WoE −0,199), pas de mutation → `tenure_bin='inconnu'` (WoE −0,091), pas de permis →
'jamais' (WoE −0,041), distance équipement absente → contribution 0, rotations →
coalesce 0 puis shrinkage vers la commune. **Aucun « inconnu » ne booste.**

Log-hazard du bin « manquant » (artifact gelé, coef × missing_woe) :

| Groupe manquant | Détail | Net |
|---|---|---|
| Prix DVF secteur | terrain +0,025 · bâti +0,071 · tendance −0,056 | **+0,040** (≈ neutre) |
| Filosofi (4 features liées) | −0,130 −0,157 −0,030 +0,098 | **−0,220** |
| Résiduel (3 features liées) | +0,029 +0,059 −0,156 | **−0,069** |
| Végétation | −0,536 −0,101 | **−0,637** |
| Pente | | −0,039 |
| PLU 'inconnu' / tenure 'inconnu' / permis 'jamais' | | −0,102 / −0,074 / −0,041 |

Une parcelle « tout manquant » encaisse ≈ **−1,0 de log-hazard** : elle score BAS.
Garde-fou supplémentaire : le **plancher C** (`statuts.py:46`) met sdp NULL → 0 et
exige zone ∈ {U, AU} — une parcelle sans données résiduel NI PLU **ne peut
mécaniquement pas** être chaude/brûlante.

**Vérification empirique** (9 groupes nullables comptés : med_terrain, med_bâti,
tendance, Filosofi, pente, résiduel, végétation, PLU connu, tenure connue ;
requête jointe run × dataset 2026) :

| Complétude n_ok/9 | Parcelles | Chaudes+brûlantes | Taux |
|---|---|---|---|
| ≤ 4 | 14 025 | **0** | 0 % |
| 5 | 14 233 | 4 | 0,03 % |
| 6 | 42 564 | 13 | 0,03 % |
| 7 | 106 310 | 64 (dont 6 brûlantes) | 0,06 % |
| 8 | 207 487 | 740 (dont 84 brûlantes) | 0,36 % |
| 9 | 47 044 | 330 (dont 29 brûlantes) | 0,70 % |

Le taux de tier chaud **croît strictement avec la complétude**. Aucune brûlante sous
7/9. Aucune chaude sous 5/9 (56 %).

**Contre-exemples chiffrés** (tier chaud avec < 2/3 des groupes renseignés, soit ≤ 6/9) :
**17 chaudes, 0 brûlante** (sur 1 151), toutes à percentile ≥ 99,59 porté par des
signaux RÉELS (zone U/AU + surface + permis/piscine/rotation), les manques étant
tenure 'inconnu' + prix bâti/Filosofi de secteur :

| idu | commune | rang | n_ok | manquants |
|---|---|---|---|---|
| 97418000BK0104 | 97418 | 245 | 5/9 | bâti, tendance, filo, tenure |
| 97407000AX0142 | 97407 | 1370 | 5/9 | bâti, tendance, filo, tenure |
| 97407000AX0143 | 97407 | 1636 | 5/9 | bâti, tendance, filo, tenure |
| 97418000AZ0560 | 97418 | 1678 | 5/9 | bâti, tendance, filo, tenure |
| 97413000CA0256 | 97413 | 327 | 6/9 | tendance, filo, tenure |
| 97418000AT2288 | 97418 | 549 | 6/9 | filo, résiduel, tenure |
| 97409000BO0631 | 97409 | 626 | 6/9 | bâti, tendance, tenure |
| 97413000CA0259 | 97413 | 809 | 6/9 | tendance, filo, tenure |
| 97413000CA0257 | 97413 | 940 | 6/9 | tendance, filo, tenure |
| 97418000AT2287 | 97418 | 1159 | 6/9 | filo, résiduel, tenure |
| 97416000DO0264 | 97416 | 1201 | 6/9 | terrain, filo, tenure |
| 97407000AX0020 | 97407 | 1264 | 6/9 | bâti, tendance, résiduel |
| 97413000CA0198 | 97413 | 1391 | 6/9 | tendance, filo, tenure |
| 97420000AE0496 | 97420 | 1397 | 6/9 | terrain, tendance, tenure |
| 97415000EZ0166 | 97415 | 1613 | 6/9 | terrain, résiduel, tenure |
| 97407000AX0206 | 97407 | 1658 | 6/9 | bâti, tendance, filo |
| 97416000DI0233 | 97416 | 1742 | 6/9 | terrain, résiduel, tenure |

**Verdict A.3 : politique NULL SAINE.** La règle « une parcelle sans données ne score
jamais haut par défaut » est respectée : le manquant est explicite, net négatif, et
verrouillé par le plancher C. Les 17 contre-exemples partiels sont des parcelles à
signaux positifs réels, pas des « scores par défaut » — mais ils justifient l'indice
de confiance (A.4) pour l'afficher au client.

### A.4 — SPEC : indice de confiance données (ICD) par parcelle — **IMPLÉMENTATION AU BACKLOG**

**Définition.** ICD ∈ [0, 100] : complétude PONDÉRÉE des groupes de données qui
alimentent le scoring v2 pour la parcelle, calculée sur la ligne `annee = année du run`
de `p_model_ext_dataset`, au moment du run, versionnée par run. L'ICD **ne modifie
jamais** le score ni le tier (modèle gelé) : c'est une méta d'affichage.

**Champs comptés et pondération** (9 groupes = les groupes nullables de A.3 ; poids
proportionnels à l'enjeu — IV de l'artifact + rôle dans le plancher C et contrib_D) :

| Groupe | Test « renseigné » | Poids |
|---|---|---|
| Résiduel / capacité C | `pct_potentiel IS NOT NULL` (⇔ sous_densite, sdp) | 20 |
| Zonage PLU | `zone_plu <> 'inconnu'` | 15 |
| Végétation | `canopee_pct IS NOT NULL` (⇔ ndvi) | 15 |
| Prix terrain secteur | `med_pm2_terrain_36m IS NOT NULL` | 10 |
| Prix bâti secteur | `med_pm2_bati_36m IS NOT NULL` | 10 |
| Filosofi | `filo_snv_pp IS NOT NULL` (⇔ les 4) | 10 |
| Tenure | `tenure_bin <> 'inconnu'` | 10 |
| Tendance prix | `tendance_pm2_bati IS NOT NULL` | 5 |
| Pente | `pente_moy_deg IS NOT NULL` | 5 |
| **Total** | | **100** |

Les features jamais NULL par construction (rotations, permis, surface, piscine, PV,
QPV, friche, accès équipements, window_coverage) ne comptent pas : elles n'apportent
aucune information de complétude. NE PAS confondre avec `scoring/completeness.py`
(score §7A des FAMILLES de la cascade, autre grain, autre usage) — le pattern
poids/bandes est réutilisable, pas les familles.

**Seuils d'affichage** (calés sur la distribution observée : médiane 8/9, P10 ≈ 7/9) :
- **ICD ≥ 85** : confiance haute — aucun badge (cas nominal, ~60 % du parc).
- **60 ≤ ICD < 85** : « données partielles » — badge gris, tooltip listant les groupes
  manquants en libellés client (« prix du secteur inconnus », « capacité PLU non
  calculée »…).
- **ICD < 60** : « confiance faible » — badge orange ; sur une chaude/brûlante, la
  fiche affiche en plus une ligne d'avertissement sous le verdict d'en-tête. (Au run
  audité : 0 brûlante et 17 chaudes seraient concernées selon le poids exact.)

**Où l'afficher** : (1) fiche parcelle, à côté du verdict d'en-tête (chip) ; (2) liste :
badge sur carte uniquement si < 85 ; (3) export CSV et API fiche (`icd`, `icd_detail`) ;
(4) PDF fiche (mention obligatoire si < 60). Jamais dans le tri par défaut.

**Stockage** : au prochain run v2, colonnes `icd smallint` + `icd_detail jsonb`
({groupe: bool}) dans `parcel_p_score_v2` (versionné par run, même transaction que le
scoring) ; pour les runs existants, backfill LECTURE de `p_model_ext_dataset`. Aucun
recalcul du modèle. Tests attendus : bornes 0/100, parcelle témoin par bande, absence
d'effet sur rang/tier (invariance).

---

## BLOC B — Protocole forward (remplace tout backtesting)

**Rappel du cadre** : produire un « taux de mutation des brûlantes d'il y a 6-12 mois »
est IMPOSSIBLE et INTERDIT — les snapshots datent des 10-12/07/2026 (aucun recul), le
statut courant est contaminé Phase 0, DVF 2025-2026 est censuré 40-60 % (vérifié :
`max(date_mutation)` prod = 2025-12-31, zéro mutation 2026 en base). Le seul chiffre
commercial autorisé est le walk-forward M3.6 (B.4).

### B.1 — Snapshots gelés : présents et intègres ✔

Mécanisme : tables `score_snapshots` (en-tête) + `score_snapshot_parcelles` (détail),
protocole M1 « un label ne s'écrase JAMAIS » (REFUS runtime, `pipeline.py:297` et
`score_v.snapshot_scores`). Vérification SQL ce jour :

| Label | Gelé le | Run source | Parcelles | Brûlantes |
|---|---|---|---|---|
| `v1.2-2026-07-10` | 2026-07-12 15:23 | q_v3_datagap | 431 663 | 79 |
| `v1.3-2026-07-12` | 2026-07-12 15:25 | q_v3_datagap | 431 663 | 120 |
| `m5-2026-07-12` | 2026-07-12 22:11 | m36-l2f-2026-2026-07-12 | 431 663 | 119 |

Volumétrie pleine (3 × 431 663), datés, cohérents avec les synthèses (79/120/119 ✔).
Manifeste sha256 : **seul l'artifact modèle en a un** (vérifié conforme) ; les snapshots
DB n'ont pas d'empreinte cryptographique (ANO-5) — l'intégrité repose sur le refus
d'écrasement + les sauvegardes base. Trou d'id (3) dans la séquence : snapshot avorté,
sans impact.

### B.2 — `labuse monitor-forward` : opérationnel ✔ (non exécuté ici, analysé statiquement)

- La commande **existe** (`cli.py:1442` → `scoring/p_v2/monitoring.run_monitor`).
- **DB : lecture seule** (uniquement des SELECT). MAIS elle **écrit des fichiers** :
  `reports/monitoring/AAAA-MM.md` + `AAAA-MM-faux-negatifs.csv`. Conformément au mandat
  (fichiers uniquement sous `reports/m6-audit/`) et parce qu'une exécution en juillet
  **écraserait** le rapport 2026-07 existant, elle n'a PAS été exécutée — analyse statique.
- Preuve d'opérationnalité : rapport `reports/monitoring/2026-07.md` généré le 12/07
  (M5 lot 5) — top gelé 1 151, 0 hit (attendu, gel du jour), churn « au prochain run »,
  1 faux négatif sondé. Contenu conforme au code, protocole B0 rappelé dans le rapport.
- ⚠ Le faux négatif sondé (97412000CY0369, « permis 2026-08-17 ») est un **permis daté
  dans le FUTUR** dans Sitadel (ANO-4) : artefact de donnée source, pas un vrai miss.

### B.3 — Protocole « niveaux à l'édition N+2 » : documenté ✔

Retrouvé et jugé complet, en quatre endroits concordants :
1. **`reports/m36-foncier/SYNTHESE-M36.md` (Lot 2 — B0 censure)** : la démonstration
   chiffrée — un millésime DVF 974 vu à ~16 mois ne contient que 27-45 % des parcelles
   L2-F finales, mais le classement concorde (RR@1158 early vs late : 3,2→3,9 ; 3,3→3,4)
   → « la censure enlève du niveau, pas de l'ordre » ; amendement : **verdicts de NIVEAU
   sur édition N+2 minimum**, suivi de CLASSEMENT en continu. Annotation de complétude
   attendue par âge (2023 ≈ complète à 42 mois ; 2024 ~80 % à 30 mois ; 2025 ~40 % à 18 mois).
2. Docstring de `monitoring.py` (protocole B0 gravé dans le code).
3. Chaque rapport mensuel généré rappelle « niveaux provisoires… jugement à N+2 ».
4. `SYNTHESE-M5.md` lot 5. Appuis chiffrés : `completude-censure.csv`,
   `concordance-censure.csv`.
Seule réserve mineure : pas de page unique « protocole forward » consolidée hors
synthèses — confort documentaire, rien de manquant sur le fond.

### B.4 — LE chiffre commercial et son paragraphe

**Source exacte retrouvée et re-vérifiée** : `reports/m36-foncier/walk-forward.csv`
(lignes `label` = L2-F, colonne `rr@1158_hors_copro`), reproduit dans
`SYNTHESE-M36.md` (Lot 2 — walk-forward 6 folds, train ≤ N-2, calibration N-1, test N)
et dans `FREEZE-scoring2026.json.verdict_reference`. Par fold 2020→2025 :
**9,41 · 8,61 · 8,63 · 7,30 · 7,08 · 6,73** → plage **6,7 à 9,4** ✔ (le chiffre de la
mémoire projet est exact). Fold 2025 : 6,73, IC95 bootstrap [5,53 ; 7,84] (seed 974),
vs modèle M3 précédent 2,85-2,91 (`decision-promotion.csv`). Calibration : ECE ≤ 0,0033
sur les 6 folds. RR@1158 = taux de mutation du top-1158 hors copro ÷ taux de base du
même univers (~1,5 %/an) ; 1158 = taille de la liste produit historique.

**LE PARAGRAPHE COMMERCIAL EXACT (utilisable en RDV client)** :

> « Nous avons rejoué notre modèle sur six années de test successives, 2020 à 2025,
> chaque année étant prédite sans jamais avoir été vue à l'entraînement. Résultat
> constant : les parcelles que le modèle classe en tête — notre liste prioritaire
> d'environ 1 150 parcelles à l'échelle de l'île, hors copropriété — ont réellement
> muté dans l'année **entre 6,7 et 9,4 fois plus souvent** que la moyenne des parcelles
> de La Réunion. Sur l'année de test la plus récente (2025), le facteur est de
> **6,7** (intervalle de confiance à 95 % : 5,5 à 7,8), pour un taux de base d'environ
> 1,5 % : concrètement, environ **une parcelle sur dix** de la liste prioritaire a muté
> dans l'année, contre une sur soixante-cinq ailleurs. Ces chiffres sont mesurés sur
> les ventes foncières réelles publiées par l'État (DVF), hors ventes d'appartements
> en copropriété, et nous continuons de mesurer la performance de chaque liste gelée,
> mois après mois, sur les ventes qui se publient. »

**Conditions de validité** (à respecter tel quel) :
- univers HORS COPRO ; top 1 158 par probabilité (≈ le périmètre « chaudes ») ;
- événement = mutation L2-F (vente / VTB, hors unités de copro) dans l'année de test ;
- features as-of 01/01 de l'année de test, même recette que l'artifact gelé ;
- « moyenne de l'île » = taux de base du même univers hors copro (~1,5 %/an).

**Ce qu'on n'a PAS le droit de dire** :
- tout « taux de mutation des brûlantes depuis le gel » ou « d'il y a 6-12 mois »
  (snapshots des 10-12/07/2026 : aucun recul ; statut courant contaminé Phase 0) ;
- tout NIVEAU mesuré sur 2025-2026 courant avant l'édition N+2 (censure DVF 40-60 %) ;
- appliquer 6,7-9,4× aux **117 brûlantes** ou à une parcelle nommée : le walk-forward
  juge le top-1158, pas le sous-ensemble brûlantes (jamais évalué séparément), et
  jamais une promesse individuelle (« cette parcelle va muter ») ;
- toute garantie de rendement ou d'exhaustivité ; le mot « prédiction certaine ».

---

## Anomalies consignées (constats — aucune action, mandat lecture seule)

| # | Anomalie | Impact | Où |
|---|---|---|---|
| ANO-1 | Étage 0 : référentiel `q_v2` codé en dur dans le pipeline vs `q_v3_datagap` servi au produit → 119 vs 117 brûlantes (et 1 032 vs 960 chaudes) | Cohérence compteurs (géré à l'affichage M5.1, racine ouverte) | pipeline.py:218 / score_v_constants.py:32 |
| ANO-2 | `window_coverage` constante (1,0) sur 2026 : feature morte à l'inférence | Aucun (décalage uniforme) | dataset 2026 |
| ANO-3 | `qpv` et `friche` : coef ≈ 0, IV 0,0000 — calculées pour rien | Aucun sur le score | artifact gelé |
| ANO-4 | Permis Sitadel daté 2026-08-17 (futur) → pollue la sonde faux négatifs (1/1 du rapport 2026-07 est cet artefact) | Bruit monitoring | sitadel_permits / p_model_permits |
| ANO-5 | Snapshots DB sans empreinte sha256 (seul l'artifact modèle est manifesté) | Intégrité logique (refus d'écrasement) mais pas cryptographique | score_snapshots |
| ANO-6 | Colonne `nu` du dataset calculée, jamais consommée | Aucun | ext_sql.py:255 |
| ANO-7 | Help CLI `score-v2 --rebuild` promet « DVF/**Sitadel** frais » mais `rebuild_features()` ne re-matérialise PAS `p_model_permits` (ni `p_model_static`) — hérités de M3 (`build_all`). Sans impact sur CE run (p_model_permits vérifié en phase avec sitadel_permits) ; risque de staleness aux runs futurs si `build_all` n'est pas relancé | Fraîcheur permis des runs futurs | cli.py:1421 / pipeline.py:92 |

**Fin §1.4** — modèle P M3.6 : intact (sha vérifié), non touché.
