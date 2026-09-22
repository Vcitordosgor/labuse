# SCORING-6 — Construction du moteur : Score LABUSE + Signal de mutation

**Date : 21/09/2026 · Branche : `feat/scoring-6` (base main `b4b82a74`) · worktree `~/Desktop/labuse-scoring6`.**
**Type : construction sur run candidat. `q_v11_m137` reste servi. Aucun merge, aucune promotion, aucun run île entière.**

Base de vérité : `SCORING-5-RAPPORT.md` (corrigé) + `SCORING-5-RETOUR.md` + `PLU-CALIBRAGE-6/7`. Le mandat n'invente rien : il code ce que ces rapports ont spécifié et mesuré. Le barème provisoire est celui, calé sur les 30 témoins, de `reports/scoring-5/temoins_score_v1.py`.

**Étape 0** : `pwd` = worktree scoring6, branche `feat/scoring-6`, arbre propre, base `b4b82a74` = `main`. OK.

---

## 1. Ce qui est codé, lot par lot

### A — Résiduel sur assiette clippée (`9d6b1a0e`)
`faisabilite/db.py` : `parcel_faisabilite(..., assiette_clippee=False)` — chemin **opt-in** (défaut byte-identique, servi inchangé). Quand la zone **dominante** n'est pas constructible mais qu'une portion U/AU subsiste, `_sous_zone_constructible` résout la plus grande sous-zone U/AU ; `_greve_certaine_m2` soustrait de l'assiette les contraintes géométriques **certaines** (PPR rouge, PEB A/B, marchepied DPF, abord de ravine, 50 pas ; ER/EBC déjà soustraits par `_EMPRISE`) — seuils lus de `cascade_rules.yaml` (source unique) ; la surface CES/pleine-terre est ramenée à la portion (`_pct_constructible`). Le flag est propagé à `compute_residuel` / `compute_residuel_batch` et exposé en CLI (`compute-residuel --assiette-clippee`, requis pour le run q_v15).

**Preuve (base `labuse`, `captures/scoring6/lot_a_assiette.py`)** : témoin **N-96 % `97402000AB1117`** → tout-ou-rien = `zone_non_constructible`, assiette clippée = sous-zone **Uc, SDP résiduelle 81 m² > 0**. Témoin U `97402000AH1389` identique dans les deux modes (servi intact). C'est la preuve exigée par SCORING-5-RETOUR §3 : le reclassement B des A/N 90-99 % ne produit rien SANS ce calcul.

### B — Score LABUSE V1 (`5d4e2aad`)
Module `scoring/score_labuse.py` + barème `config/score_labuse.yaml` (hash dans `score_version = labuse_v1+<hash8>`). Chaîne (SCORING-5-RETOUR §1) : `score = clip(barème_capacité × coef_faisabilité, 0, 100)`.
- **capacité** : SDP résiduelle (lue de la **vue `parcel_residuel`** servie — elle mangera l'assiette clippée du lot A au run q_v15) → points saturants ; ×0,5 en zone AU différée.
- **coef faisabilité** : pente × forme × accès × bâti gradué (nu 1,0 · ≤20 % 0,9 · 20-50 % 0,8 · >50 % ou ≥R+2 0,65), plancher 0,4. Le bâti pèse sur le coefficient, **jamais** sur l'assiette (acquis PALIERS-1).
- **contexte** : hors calcul (correction Vic SCORING-5-RETOUR §1).

Sortie par parcelle : `score`, `bande`, `non_calculable`+`cause` (zone non résolue / règle PLU non validée / donnée critique absente / géométrie), `couverture` (% + manquantes FR), `confiance` (niveau + notes), `contributions` (FR : ce qui monte / baisse), `score_version`, `run_label`. **Absence de donnée = facteur neutre 1,0 + couverture qui baisse, jamais un malus. NC ≠ 0.**

### C — Cascade v2 A/B/C/D (`67aee146`)
`config/cascade_v2.yaml` + `scoring/cascade_v2.py` : classe de chaque couche (SCORING-5-RAPPORT §5). **A** = seule exclusion dure ; **B** = pénalité (jamais exclusion) ; **C** = info filtrable ; **D** = supprimée/déplacée. **PPR/ER/EBC/PEB + A/N ventilées** : A si recouvrement ≥ 99 %, B en partiel (portion exploitable, valorisée par le lot A) — le % est parsé du `detail` du dry-run (SCORING-5-RETOUR §5.3). Proxy `ocs_ge` BDCARTO (classe D) **remplacé par la vraie OCS GE** (`parcel_ocsge`, 100 %, `lire_ocsge`) en information de contrôle. `safer`/`dvf`/`sitadel`/`proprietaire`/événements → D. Motifs conservés (`ReclassementParcelle.motifs`) pour les filtres. **Invariant testé : une classe B ne produit jamais d'exclusion.**

### D — Signal de mutation V2 (`b4b90d7a`)
`p_v2/qv15.py` : `features_qv15` = **recette q_v14 MOINS `piscine` et `pv_candidat`** (sous-ensemble strict, aucune variable nouvelle — SCORING-5-RETOUR §4). Mécanique reprise de qv14/qv12 (fit global + isotonique par segment 2024). Cible inchangée P(vente L2-F < 12 mois de la date du score). `signal_mutation.py` : `signal_niveau(p)` fort/moyen/faible aux **seuils absolus PALIERS-1** (0,20 / 0,10, `scoring_client.yaml`) ; `signal_version()`. Recette `q_v15` branchée dans `pipeline.py` (même famille que q_v14). Le **fit/gel du modèle est un geste de l'arène (Vic)** : `verify_artifacts` refuse proprement tant que l'artefact n'existe pas — SCORING-6 ne fit ni ne bascule l'île.

### E — Combinaison V3 + sortie unique (`c5b68714`)
`scoring/score_labuse_combine.py` : assemble Score × Signal × cascade v2 par parcelle → table versionnée **`score_labuse`** (clé run_label, parcel_id) + métadonnée `score_labuse_runs` (DDL idempotent). Colonnes = tout le lot B + lot D + lot C + `sdp_residuelle_m2`. Classement **V3 lexicographique** (`ordonner`) : bande (A>B>C>D>NC) PUIS Signal DANS la bande PUIS SDP PUIS IDU. Le Signal ne franchit jamais une frontière de bande. **Aucun quota, aucun rang stocké, aucun percentile.**

### F — Exploitation (`cd6f5760`)
- CLI `labuse score-labuse --run <label> [--communes ...] [--parcelles ...] [--cascade-label] [--signal-run] [--no-persist]` — Score (+ Signal + cascade v2) sur un sous-ensemble, **sans cascade ni run complet**, écrit dans `score_labuse`. Résumé par bande.
- CLI `labuse ingestion-delta --source X | --list` + `scoring/ingestion_journal.py` (table `ingestion_delta` : source, date, parcelles touchées ; `parcelles_a_recalculer`) — la pièce manquante du recalcul en delta (SCORING-5-RAPPORT §8.3).
- `deploy/scripts/sync-run.sh --run-label LABEL` : dump **filtré par run_label** des tables versionnées (DELETE+COPY côté VPS) au lieu des ~80 M lignes tous labels ; `score_labuse` ajoutée aux tables de run (SCORING-5-RETOUR §5.5).

---

## 2. Tests — liste et résultat

Tous **verts**. `PYTHONPATH=src` sur le worktree (piège connu : sinon les modules jouent le checkout principal).

| Fichier | n | Ce qu'il verrouille |
|---|---:|---|
| `test_scoring6_assiette.py` (A) | 6 | sous-zone U/AU choisie, aucune portion → None, capacité > 0 sur petite assiette, monotonicité en surface |
| `test_scoring6_score_labuse.py` (B) | 12 | déterminisme, golden lame-bâtie 64, NC ≠ 0, pénalité jamais exclusion, vrai 0 ≠ NC, monotonicité SDP/emprise, couverture, AU différée, **versionnement lié au hash**, bandes, contributions |
| `test_scoring6_cascade_v2.py` (C) | 10 | classes A/B/C/D par règle, ventilation PPR/ER/EBC/PEB/A-N, **B n'exclut jamais**, parse %, reclassement |
| `test_scoring6_signal_v2.py` (D) | 6 | q_v15 ⊂ q_v14 (exactement −2), flag ventes_pm, seuils fort/moyen/faible, p indéfini, version, refus d'artefact absent |
| `test_scoring6_combine.py` (E) | 7 | bande domine le Signal, Signal départage dans la bande, NC en dernier, ties SDP/IDU, ordre total déterministe |
| `test_scoring6_exploitation.py` (F) | 4 | commandes CLI enregistrées, flag `--assiette-clippee`, modules |
| `test_scoring6_garanties.py` (G) | 5 | **indépendance aux filtres**, **aucun rang/percentile stocké**, ordonner ≠ recalcul, **fuite temporelle = aucune feature nouvelle**, NC ≠ 0 |
| **Total SCORING-6** | **50** | |

**Non-régression servi** : `test_faisabilite` 19 · `test_prospect`/`test_mn_faisabilite`/`test_plu_calibrage2/lot2/4` 43 · `test_scoring`/`test_scoring_pure` — **tous verts, 0 nouvelle rupture**. Le chemin par défaut (`assiette_clippee=False`) est byte-identique ; les tables `score_labuse`/`score_labuse_runs`/`ingestion_delta` sont **neuves**, jamais lues par le servi.

Correspondance aux tests exigés (mandat §2.G) : déterminisme (B), indépendance aux filtres (G), zéro quota/percentile (G+E), NC ≠ 0 (B+G), monotonicité 30 témoins (dry-run §3 + B), fuite temporelle (G, par sous-ensemble strict du banc K0 audité), versionnement (B), non-régression servi (ci-dessus), garde-fou 974 (dry-run), cascade A/B/C/D par règle (C).

---

## 3. Dry-run (`captures/scoring6/dry_run.py`, base `labuse`, pas de run île entière)

**score_version = `labuse_v1+1518ba79`.**

### 3.1 — 30 témoins : **30/30 reproduits exactement** (score, bande, signal)
Extrait :

| idu | cat | score | bande | signal |
|---|---|---:|:--:|:--:|
| 97407000BC0579 | bonne | 100 | A | faible |
| 97411000AB0798 | bonne | 64 | **B** | faible |
| 97401000AI0166 | limite | 72 | B | faible |
| 97406000AM0664 | limite | 36 | C | faible |
| 97402000AL0088 | limite (A-96 %) | 0 | D | faible |
| 97415000AC0070 | limite | — | **NC** | faible |
| 97420000AD0103 | mauvaise | 0 | D | faible |

Toutes les catégories atterrissent où le rapport SCORING-5 les attendait ; le cas d'école `97411000AB0798` (bonne a priori → 64, bande B) est bien la lame bâtie ≥ R+2. (Signal = q_v14 stand-in : tous « faible » sur ces témoins, cohérent — ce sont des parcelles foncières, pas des mutations imminentes.)

### 3.2 — Saint-Paul entière (51 129 parcelles, **43,9 s = 0,86 ms/parcelle**)

| Bande | Effectif |
|---|---:|
| A (≥ 80) | 622 |
| B (50-79) | 4 541 |
| C (30-49) | 6 613 |
| D (< 30) | 26 786 |
| **NC** (zone non résolue) | 12 567 |
| garde : sans bande | **0** |

NC = 12 567, toutes « zone non résolue » (Saint-Paul est la commune `strict` « gold » : les zones hors calibrage ne se résolvent pas — attendu, pré-calibrage).

### 3.3 — Cascade v2 sur Saint-Paul (effectifs de verdicts vs q_v13_sources1)

| classe | verdicts |
|---|---:|
| A (exclusion dure) | 873 944 |
| B (pénalité) | 105 450 |
| C (information) | 866 981 |
| D (supprimée/déplacée) | 269 665 |

**Parcelles exclues : v1 (HARD_EXCLUDE q_v13_sources1) = 17 652 · v2 (classe A seule) = 16 544** → **~1 108 parcelles** sortent de l'exclusion dure et passent en **pénalité d'assiette** (portion exploitable, valorisée par le lot A). C'est exactement l'effet net attendu du reclassement B (SCORING-5-RAPPORT §5).

---

## 4. Ce qui reste avant q_v15 (gestes de Vic)

1. **Merge `feat/plu-calibrage-6` (+ PLU-7)** : la garde validées-only + les deux formes de schéma (recul à l'alignement, pleine-terre composée) — la cause `regle_plu_non_validee` est déjà gérée par le Score (lot B) et la NC est prévue.
2. **`residuel-serve` post-calibrage** : `labuse compute-residuel --ile --new-run "<label>" --assiette-clippee` en **process frais** (lru_cache) → comparer au run 2 → `residuel-serve <seq>`. Le Score lit la vue → il mange la bonne capacité sans changement de code.
3. **Bandes finales** : les bornes A ≥ 80 / B 50-79 / C 30-49 / D < 30 sont **provisoires** (`config/score_labuse.yaml`, calées sur les témoins pré-calibrage) — à re-caler sur témoins re-scorés après residuel-serve.
4. **Fit/gel du modèle Signal q_v15** (arène) : produit `reports/q-v15/` ; ensuite `labuse score-v2 --run-id … --recette q_v15` puis le Signal réel entre dans la combinaison (à la place du stand-in q_v14 du dry-run).
5. **Vocabulaire client** du couple Score × Signal (Priorité / À suivre / …) — décision Vic (§6).

---

## 5. Écarts par rapport aux rapports SCORING-5 / RETOUR

1. **Barème de capacité en 0-100, pas « 0-70 ».** Le mandat (Lot B) et le §2.1 du RAPPORT décrivent une capacité « 0-70 pts » (structure pré-calibrage). Le barème **effectivement calé sur les 30 témoins** (`reports/scoring-5/temoins_score_v1.py`, qui a produit `TEMOINS.csv` que Vic a validé) utilise des paliers de capacité 0-100 × coef 0-1,0 → score 0-100. J'ai implémenté **la version calibrée sur témoins** (elle reproduit `TEMOINS.csv` au point près, 30/30), conformément à la décision Vic « les valeurs sortent des parcelles témoins ». Le « 0-70 » était la fourchette structurelle avant calibration ; aucune valeur n'est inventée hors des rapports.
2. **Signal du dry-run = q_v14 (stand-in).** Le modèle q_v15 n'est pas fit (geste de Vic). Le dry-run couple donc le Score avec le Signal servi actuel (q_v14) pour démontrer la combinaison V3 ; `signal_version` trace la recette cible q_v15. Aucune conséquence sur le Score (déterministe).
3. **Table `score_labuse` (colonne run_label), pas un nom `score_labuse_<run_label>` littéral.** Suivi de l'idiome établi du projet (`dryrun_cascade_results`, `parcel_residuel_runs`) : une table unique versionnée par la colonne `run_label`. Intention du mandat respectée (une sortie unique, versionnée par run).

Aucun autre écart. Rien de servi n'a changé ; aucun run île entière, aucun merge, aucune promotion, aucun `residuel-serve`.
