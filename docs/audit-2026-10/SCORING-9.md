# SCORING-9 — Score LABUSE `q_v16` sur le résiduel run 13 servi (sans bascule)

**Branche** `fix/scoring-9` · base `962946d4` (serve résiduel run 13) · worktree `labuse-scoring9`
· venv `~/Desktop/labuse/.venv` · base `labuse` (openclaw). **Aucun promote, aucune bascule,
aucune écriture de `config/served_run.txt`, aucun merge.** Le run `q_v16` est un run CANDIDAT
(tables versionnées) ; le Signal servi reste `q_v11_m137`, le résiduel servi reste run 13.

Décision Vic : **on ne rejoue pas la cascade** — l'étage 0 reste `q_v13_sources1` (dérive mesurée
nulle par SCORING-8 lot B). Paramétrable quand même (`cascade_2026_10` en option).

---

## Étape 0 — reconstruction des caches (attendue avant tout calcul)

Le rebuild post-`residuel-serve 13` (pid 78510, `/tmp/labuse-rebuild-residuel-seq13.log`) a été
attendu jusqu'à sa sortie (`pgrep labuse.cli rebuild` vide) puis vérifié : dernière ligne
`✓ rebuild terminé {spatial_layers_sub: 1548388, mvt: {n: 431663, tuiles: 26}, fiche_commune: 24}`,
`✓ fraîcheur : tous les caches portent la clé attendue.` **Aucun `✗`, aucune erreur / Traceback.**

---

## 1. `run_qv16.py` — étage 0 paramétrable + preuve que les caches lisent le run 13

`scripts/audit/scoring/run_qv16.py` réécrit :

- **Étage 0 paramétrable** : `--etage0` (ou `LABUSE_ETAGE0_RUN`), **défaut `q_v13_sources1`**,
  `cascade_2026_10` en option. L'étage 0 est LU (override non destructif), jamais recalculé.
- **Modèle inchangé** : recette `q_v15`. La recette lit le résiduel **EN DIRECT** depuis la vue
  `parcel_residuel` (`qv12.charger_residuel`, `REMAP_K3` : `sdp_residuelle_v2_m2` etc.), donc le
  Signal reflète le résiduel servi courant quel que soit l'état d'un cache figé.

### Preuve de fraîcheur — constat important

`labuse.cli rebuild` reconstruit les couches spatiales, les tuiles MVT et les fiches communes,
mais **ne rafraîchit PAS les colonnes résiduel de `p_model_static`** (le feature store). Mesuré au
run 13 : **256 687 lignes (≈ 60 % de l'île) étaient PÉRIMÉES** (valeurs run 10 ou plus anciennes).
`run_qv16.py` appelle donc `refresh_static_residuel` (quelques secondes) puis **prouve**, sur
5 parcelles dont la SDP a changé entre run_seq 10 et 13, que la vue ET le cache portent le run 13 :

```
IDU                 run10    run13      vue    cache  verdict
97415000BH0057        344        0        0        0  ✓ run13
97415000BH0125       1799     1804     1804     1804  ✓ run13
97415000BI0078        409      572      572      572  ✓ run13
97415000BI0055        314        0        0        0  ✓ run13
97415000BI0064        364        0        0        0  ✓ run13
```

Si la preuve échoue, le script s'arrête (pas de scoring sur cache périmé). Relance idempotente :
2ᵉ passage → `refresh_static_residuel : 0 ligne` (déjà à jour).

> ⚠ **Pour Vic** : ce refresh aligne un cache sur le résiduel DÉJÀ servi (run 13) — ce n'est pas
> une bascule. Mais il révèle que le `rebuild` de service ne remet pas `p_model_static` au jour ;
> à câbler dans le pipeline de rebuild (sinon toute recomputation de Signal part d'un résiduel
> périmé). Le Signal servi `q_v11_m137` est STOCKÉ, donc non affecté par ce refresh.

---

## 2. Purge → Signal `q_v16` → Score LABUSE `q_v16` (île)

| Étape | Résultat |
|---|---|
| **Purge** (`purge_qv16.py`) | q_v16 ABSENT des 4 tables candidates (0 ligne) — état propre |
| **Signal** (`run_qv16.py`, étage 0 `q_v13_sources1`) | **431 663** parcelles · 340 s · tiers `sans_signal 280 609 / ecartee 150 260 / a_suivre 651 / priorite 143` · `params.etage0_run=q_v13_sources1` |
| **Score** (`score-labuse --run q_v16 --signal-run q_v16`) | **431 663** parcelles · 276 s · `signal_version=signal_v2+q_v15`, `cascade_label=q_v13_sources1` |

### Contrôle de complétude ✓

- `count(score_labuse where run_label='q_v16')` = **431 663**
- parcelles sans ligne q_v16 = **0**
- doublons `parcel_id` = **0**
- bande NC avec score 0 (interdit) = **0**

> Note : `score_labuse_runs.n_parcelles = 1663` pour q_v16 (comme pour q_v15) est un artefact
> connu du UPSERT par lot (dernier lot = 431663 − 215×2000 = 1663). La table `score_labuse`
> contient bien les 431 663 lignes pour chaque run.

---

## 3. Lot C (SCORING-8) — re-calage des témoins + gravure

### Les 3 périmés, sur le run 13 servi (confirmés cassés)

| IDU | cat | run 13 | invariant cassé | cause (EXPLIQUE-RUN13) |
|---|---|---|---|---|
| `97404000AX0047` L'Étang-Salé | bonne | **76** (B) | bonne < 80 | assiette déduite (touche PPR rouge) |
| `97409000AY0786` Saint-André | bonne | **0** (0) | bonne = 0 | 2243→0 m² terrain_exigu (enveloppe PPR) |
| `97411000CP0427` Saint-Denis | mauvaise | **45** (C) | mauvaise > 25 | SDP recalculée (LiDAR) → 45 (cassé depuis q_v15 déjà) |

(+ une 4ᵉ « anomalie » = l'inversion induite par ces 3.) Les **27 autres témoins tiennent.**

### Remplaçants, justifiés un par un (scorés sur le run 13)

| Périmé → Remplaçant | cat | run 13 | justification |
|---|---|---|---|
| AX0047 → **`97404000AW0304`** (L'Étang-Salé) | bonne | **80** (A) | U nue, **SDP 5 008 m²**, emprise 1 %, pente 5,5°, **cause calculée** (hors enveloppe PPR → robuste) |
| AY0786 → **`97409000AP0993`** (Saint-André) | bonne | **90** (A) | U nue, **SDP 5 791 m²**, emprise 1 %, terrain plat (1,6°), cause calculée |
| CP0427 → **`97411000CR0561`** (Saint-Denis) | mauvaise | **8** (D) | **SDP 75 m² sur pente 42,8° (~92 %)** — un logement théorique sur une rampe (profil CP0427 d'origine) |

Candidats rejetés : les très grosses SDP (19 k–55 k m²) et les parcelles `AN0150/AN0107`
(score 50 = capacité ×0,5, **zone AU différée**, non représentatives d'une « bonne » U). Jeu
complet : `reports/scoring-9/TEMOINS.csv` (27 inchangés + 3 renouvelés).

### Invariants rejoués (jeu SCORING-9, run 13) — ✓ TOUS TENUS

```
✓ bonnes ≥ 80 (sauf cas d'école AB0798 = 64, lame bâtie)
✓ mauvaises ≤ 25   (max = AD0389 25)
✓ pas d'inversion  (pire bonne 80 ≥ meilleure mauvaise 25)
✓ aucune NC à 0
```

### Gravure — FAITE (valeurs inchangées)

Les invariants tiennent **avec les valeurs courantes** du barème (paliers 80/200/400/1000/2000,
coefs de faisabilité, seuils A≥80 / B≥50 / C≥30 / D / 0). Aucune valeur n'a eu besoin de bouger :
elles classent correctement sur le run servi. `config/score_labuse.yaml` est donc **promu de
« provisoire / pré-calibrage » à CALIBRÉ sur le run 13 servi** (en-tête ré-écrit, provenance des
3 témoins renouvelés tracée). **Aucun palier / seuil / coefficient modifié.**

- `score_version` : `labuse_v1+c5f9aa60` → **`labuse_v1+d07ec637`** (le hash suit les octets du
  fichier ; **les scores/bandes sont identiques** — seule la provenance en commentaire a changé).
- Le run q_v16 stocké porte l'ancien hash `c5f9aa60` (calculé avant gravure) ; valeurs identiques,
  donc aucun re-calcul nécessaire. Une relance future portera `d07ec637`.
- Tests : `test_scoring6_score_labuse` / `test_scoring8_c26` / `test_scoring8_dedup` = **25 verts**.

---

## 4. Répartition des bandes île — avant `q_v15` / après `q_v16`

Source autoritaire : les deux runs stockés dans `score_labuse` (q_v15 servi le 25/09 sur résiduel
run 10 ; q_v16 sur run 13), joints par `parcel_id`.

| bande | avant q_v15 | après q_v16 | Δ | % après |
|---|---:|---:|---:|---:|
| A | 5 124 | **5 952** | +828 | 1,38 % |
| B | 27 293 | **35 072** | +7 779 | 8,12 % |
| C | 39 661 | **49 147** | +9 486 | 11,39 % |
| D | 75 425 | **98 386** | +22 961 | 22,79 % |
| 0 | 269 422 | **228 086** | −41 336 | 52,84 % |
| NC | 14 738 | **15 020** | +282 | 3,48 % |
| **total** | **431 663** | **431 663** | | |

**Lecture** : la bande « 0 » (sans potentiel) **perd 41 336 parcelles** ; tout le reste monte
(D +22 961, C +9 486, B +7 779, A +828). C'est le +14 M de SDP (EXPLIQUE-RUN13) qui se traduit en
bandes : des parcelles bâties à résiduel 0 passent à un résiduel exploitable. NC +282 (règles PLU
retirées + SDP NULL → NC, filet C26).

- 99 971 parcelles changent de score (hors NC des deux côtés). Transitions NC : **282 nouvelles
  NC**, 14 738 NC↔NC stables, 0 sortie de NC.
- Contrôle croisé q_v15 (DB) vs `reports/scoring-7/bandes_ile.csv` : écart ≤ ~1 % par bande
  (A +44, B +456, C +439, D +1134, 0 −2080, NC +7) — le run q_v15 a été re-persisté le 25/09 avec
  des caches statiques légèrement postérieurs à la génération du CSV SCORING-7. Sans incidence.

---

## 5. Les 20 plus grosses montées / descentes, avec cause

`reports/scoring-9/montees_descentes.csv`. Les mouvements **saturent** aux extrêmes du barème
(capacité ≥ 2000 m² → 100 pts ; terrain_exigu → 0), d'où des deltas groupés.

### 20 montées — toutes `0 → A` (+80 à +90), **cause UNIFORME**

> **bâti existant recalculé (niveaux LiDAR égout + coef 0,95 toit→plancher) → SDP résiduelle ↑**

Exemples : `97416000IA1697` Saint-Pierre 0→90 ; `97411000HM0116` Saint-Denis 0→81 ;
`97401000AP0923/AP0922` Les Avirons 0→81 ; puis une vingtaine à 0→80 (Le Tampon, Saint-Benoît,
Bras-Panon, Saint-Louis, Saint-Leu…). Ce sont des parcelles bâties jugées saturées au run 10 et
qui, avec les niveaux dérivés de l'égout LiDAR, révèlent une SDP résiduelle exploitable.

### 20 descentes — quasi toutes `A → 0` (−90 à −100), **cause dominante**

> **assiette recalculée → terrain exigu (enveloppe PPR / SUP déduite de l'implantation)**

Exemples : `97421000BO0683` Salazie 100→0 ; `97409000AW0046/AT0829/BE1977/AB0267/AK0804`
Saint-André 100→0 ; `97422000…` Le Tampon ×4 ; `97407000BI0325` Le Port 100→0. Deux cas
étiquetés « SDP résiduelle ↓ » (`97412000BW2437` Saint-Joseph, `97414000EK0652` Saint-Louis) =
recalcul d'assiette/bâti sans bascule terrain_exigu. C'est le chantier post-déploiement déjà
identifié (parcelles PARTIELLEMENT rouges mises à 0, EXPLIQUE-RUN13 §verdict).

---

## Doctrine / garanties

- **Aucun** promote, bascule, écriture `served_run.txt`, ni merge. `q_v11_m137` reste le Signal
  servi, run 13 reste le résiduel servi.
- Écritures = tables CANDIDATES uniquement (`parcel_p_score_v2`/`p_score_v2_runs`/`score_labuse`
  run `q_v16`), le cache `p_model_static` aligné sur le résiduel DÉJÀ servi, et `score_labuse.yaml`
  (gravure, valeurs inchangées).
- **API et front** : aucun lancé pendant le mandat ; vérifié arrêtés en fin de session.

## Harnais (rejouables)

```
scripts/audit/scoring/run_qv16.py          # étage0 param + preuve caches (--verify-only dispo)
scripts/audit/scoring/purge_qv16.py        # purge idempotente du run candidat
scripts/audit/scoring/scoring9_temoins.py  # diag | candidats | check <temoins.csv>
scripts/audit/scoring/scoring9_compare.py  # répartition bandes + 20 montées/descentes
reports/scoring-9/                          # TEMOINS.csv, bandes_ile.csv, montees_descentes.csv
```
