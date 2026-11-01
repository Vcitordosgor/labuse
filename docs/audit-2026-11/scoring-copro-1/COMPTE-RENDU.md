# SCORING-COPRO-1 — copropriété hors palier, étage 0 aligné, PPR unifié ; run q_v21

**Branche** `fix/scoring-copro-1` · worktree `~/Desktop/labuse-scoring` · ports 9240/6440 · base Mac
`labuse` (434 582 parcelles, run servi de départ **q_v20**). Aucun merge, aucun accès prod. Registre lu
d'abord : `docs/audit-2026-11/nu-1/E/RAPPORT.md` (E-010, E-011, E-015) et le compte-rendu
`docs/audit-2026-11/ppr-unique-1/`. Sessions sœurs en cours (ESTIMER-PRECISION-1, ROUGES-7) : seuls le
scoring et son run ont été touchés.

---

## Les trois corrections (code)

### 1. Copropriété HORS palier actionnable — NU-E-010
`scoring/p_v2/statuts.py · assign_paliers`. La fonction était PURE de `p` et ne masquait jamais la
copropriété : **393 copros portaient « Priorité » (70) ou « À suivre » (323)** alors que la doctrine et
le docstring disent « hors copropriété ». Désormais une parcelle `copro` est masquée vers **`sans_signal`**
(masque APRÈS l'anti-churn, AVANT l'étage 0 — une copro écartée reste « Écartée »). Son **libellé propre**
— déjà gravé dans le vocabulaire client, `verdict_servi.COPRO_MOTIF` = « Copropriété — hors univers de
classement (pas d'assiette foncière mobilisable) » — est servi sur la fiche à la place du rang. Même
doctrine que rang/percentile (déjà NULL pour une copro). Colonne `copro` absente → aucun masque
(rétro-compatible, golden intact).

### 2. La fraction de copropriété ne gonfle plus le signal — NU-E-011
`api/score_v2.py · _row_payload` et `api/app.py · _q_v2_fiche`. Une copropriété étant **hors du taux de
base** (`taux_base = moyenne de p HORS copro`), lui servir un multiple `p/taux_base` ou une fraction de
vente la comparait à une population dont elle est exclue (« Écartée » **et** « 1 chance sur 20 » ne peuvent
coexister — témoin audit `97404000AV0167`). Le service force désormais `fraction = None` **et**
`mult_base = None` dès que `copro` est vrai → `enrichir_verbal(None, …)` ne porte alors **ni mot ni
réglette**. Front `ScoreV2Block.tsx` : quand `hors_classement` est présent, le bloc fraction/« de vente
sous 1 an » est masqué — on ne montre plus « 1/20 … » à côté de « hors univers de classement ». Vaut pour
TOUT run (neuf comme ancien). `mult_base` reste STOCKÉ (colonne NOT NULL, audit interne) mais n'est jamais
servi pour une copro.

### 3. Étage 0 aligné sur le run scoré — NU-E-015
`bascule_gardes.py · check_etage0_aligne` (neuf) + câblage dans `coherence_flux.verifier`. Le scoring grave
dans `p_score_v2_runs.params.etage0_run` la cascade sur laquelle il a lu les parcelles écartées ; la
fiche/carte/filtres servent la cascade du manifeste (`runs.cascade()`). La garde **CRIE** (NON bloquant,
régime `check_fraicheur`) si les deux divergent — c'est-à-dire si les parcelles écartées affichées ne sont
pas celles qui ont fondé le classement servi. Statuts : OK / DÉSALIGNÉ / INDÉTERMINÉ.

### 4. Lecture PPR unique dans la cascade (code `i` + toutes les zones rouges)
`cascade/layers/phase1.py · RisquesLayer` + `cascade/context.py · union_coverage_interdit` (neuf). La
cascade jugeait le rouge par une **liste figée** `ppr_red_subtypes = ['INTERDICTION']` qui ne reconnaissait
pas le code hérité `i` de Saint-Philippe (NU-D-001). Elle lit désormais la couleur par le **module UNIQUE**
`labuse.ppr` (`labuse_ppr_couleur`), comme la fiche, l'Étude et le Gabarit : « rouge » = rouge réglementaire
∪ code non classé (prudence — « on ne construit jamais dans une zone PPR dont la couleur n'est pas certaine »,
doctrine PPR-UNIQUE-1 du 31/10). L'union des zones interdites passe par le prédicat partagé
`ppr.interdit_sql()`. Preuve : la cascade écarte enfin `97417000AH0053` (100 % code `i`) — « Exclue : PPR
zone rouge (inconstructible) — 100 % de la surface ».

> **Vérifié en base** : le code `i` (subtype `i`, suptype PM1, code_risque `i`) est le SEUL code PPR
> non-INTERDICTION/PRESCRIPTION présent (les 74 zones rouges DEAL ont toutes subtype=`INTERDICTION`, les 88
> bleues `PRESCRIPTION`). La nouvelle lecture ne change donc la classification QUE pour les **1 243**
> parcelles touchant une zone `i` (1 237 à Saint-Philippe 97417, 6 à Saint-Joseph 97412). Tout le reste est
> identique octet pour octet.

---

## Le run q_v21 (local seulement — PAS servi en prod)

**Recette `q_v15`** (identique à q_v20), **`rebuild=False`** : q_v21 réutilise le dataset de features de
q_v20 → `p_raw` reproduit à l'identique (vérifié parcelle par parcelle) celui de q_v20. L'écart de palier
est donc IMPUTABLE aux seules trois corrections, jamais à une dérive de données ou de modèle.

### Cascade `q_v21_sources` (étage 0 de q_v21)
Produite par ISOLATION de l'effet PPR (le `flux-run` complet = ~6 h sur 434 k parcelles, et introduirait une
dérive incidente vs la cascade servie `q_v19_sources`) :
- clone de `q_v19_sources` (la cascade sur laquelle q_v20 a été scoré) pour les 431 989 parcelles NON
  touchées par une zone `i` ;
- **ré-évaluation fraîche** des 1 243 parcelles `i`-affectées sous le nouveau code PPR.

Comme la classification PPR est identique pour toute zone non-`i`, ce clone est **exactement** ce qu'un
re-run complet produirait (effet isolé, 0 dérive). Résultat : `exclue` **153 283 → 153 638 (+355)**,
`a_creuser` 258 371 → 258 019, `opportunite` 21 575 inchangé.
*(Le total cascade 433 232 = 433 229 + 3 parcelles `i` absentes de `q_v19_sources` ; hors univers de
scoring — sans effet.)*

### Scoring + manifeste + contrôles
`LABUSE_ETAGE0_RUN=q_v21_sources labuse flux-run`-équivalent → `run_score_v2(run_id='q_v21',
rebuild=False, recette='q_v15')`. **n = 433 229 parcelles**, étage 0 gravé = `q_v21_sources`, snapshot
`m5-2026-11-01`. Manifeste local écrit par la MÊME procédure que q_v20 (seuls `scoring_run` → q_v21 et
`cascade_run` → q_v21_sources bougent ; mvt/division/résiduel inchangés — hors mandat « ne touche que le
scoring ») :

| Contrôle (bascule) | Résultat |
|---|---|
| `_run_complet(q_v21)` | **OK** — score v2 + cascade (empruntée `q_v21_sources`) |
| Compte des parcelles | **q_v21 = q_v20 = 433 229 (écart 0)** |
| Étage 0 aligné (`check_etage0_aligne`) | **OK** — scoré sur `q_v21_sources`, qui est la cascade servie |
| Run fiche cohérent | **OK** — « q_v21 » présent en v2 ET cascade |
| Cascade servie présente | **OK** — `q_v21_sources`, 433 232 lignes |
| « Aucune lecture de table obsolète » | **KO ATTENDU, hors scope** — `parcel_renouvellement` / `score_e` / `parcel_flags` restent sur q_v20 (tables run-scopées ANNEXES, pas le scoring — un déploiement prod les rejoue avec le reste). |

**Déploiement final (prod, hors de ce mandat)** : `labuse flux-run --label q_v21 --recette q_v15`
(cascade complète 24 communes + scoring avec `LABUSE_ETAGE0_RUN=q_v21`), rebuild des tables annexes
(renouvellement/score_e/flags/mvt), puis `labuse golden promote q_v21` / bouton Circuit.

---

## Écart chiffré q_v20 → q_v21

Palier CLIENT (via `tiers_client.code_palier`), 433 229 parcelles communes. **746 parcelles changent de
palier**, dans deux sens, pour deux causes exactes — **aucun changement inexpliqué** :

| Cause | n | Sens |
|---|---:|---|
| **Copropriété (E-010)** | **393** | actionnable → **Sans signal** (70 ex-« Priorité » + 323 ex-« À suivre ») |
| **PPR code `i` (zone rouge)** | **353** | Sans signal/À suivre → **Écartée** (352 + 1) |

Totaux palier client :

| Palier | q_v20 | q_v21 | Δ |
|---|---:|---:|---:|
| À suivre (actionnable) | 802 | **408** | −394 |
| Sans signal | 279 144 | 279 185 | +41 |
| Écartée | 153 283 | **153 636** | +353 |

(L'actionnable perd 393 copros vers Sans signal + 1 vers Écartée ; Sans signal reçoit 393 copros et cède
352 vers Écartée.)

### Les 380 parcelles ENTIÈREMENT en zone rouge
Set reproduit par la mesure PPR-UNIQUE-1 (`terrain.charger` → zone d'implantation nulle après retrait du
rouge = 0 logement) : **380 parcelles** (identique au compte ppr-unique-1). Vérification du palier q_v21 :

| | q_v20 | q_v21 |
|---|---|---|
| Écartée | 100 | **374** |
| Sans signal | 279 | **6** |
| **Actionnable (« À suivre »)** | **1** | **0** ✅ |

**Aucune des 380 parcelles entièrement en zone rouge n'est dans un palier actionnable en q_v21** (374
Écartée + 6 Sans signal). *(Les 6 restées « Sans signal » sont rouges là où l'on bâtirait mais couvrent
< 50 % de la parcelle en surface — non exclues par la cascade, mais non actionnables : conforme au mandat.)*

---

## Recette

- **Tableau d'écart** : `ecart_q_v20_q_v21.txt` (cross-tab complet + attribution des causes).
- **10 parcelles changeant de palier, vérifiées une à une** : `verif_10_parcelles.txt`
  - 5 copropriétés (ex. `97401000AN0684`, `97401000AS0397`) : `copro=true` (source `p_model_ext_copro`),
    `p_raw` **identique** q_v20↔q_v21 (classement inchangé, seul le palier bouge), « À suivre » → « Sans
    signal », `mult_base` stocké mais NON servi.
  - 5 PPR `i` Saint-Philippe (ex. `97417000AE0091` 100 %, `97417000AE0016` 74,6 %) : couverture rouge
    74,6–100 %, cascade `a_creuser` → `exclue`, « Sans signal » → « Écartée », `p_raw` identique.
- **Suite de cohérence VERTE avec q_v21 servi en local** : `pytest tests/coherence_ecrans/ -m coherence`
  = **6 passed** (zone / surface / SDP / médiane / aléas / estimation — un fait, une valeur, à l'euro / au
  m² près — avec q_v21 servi).
- **Tests unitaires** : `test_paliers1` (copro→sans_signal + rétro-compat), `test_p_v2_api`
  (copro sans fraction ni ×N), `test_scoring_copro1` (garde étage 0 OK/DÉSALIGNÉ + cascade `i` exclue,
  `reel`), `test_ppr_marginal_coverage` réaligné sur la doctrine PPR-UNIQUE-1 (code non classé = rouge ;
  graduation marginale réservée aux zones bleues). Suite non-reel complète : voir ci-dessous.

## Fichiers touchés
Backend : `scoring/p_v2/statuts.py`, `scoring/p_v2/pipeline.py` (commentaire seul — mult_base inchangé),
`api/score_v2.py`, `api/app.py`, `cascade/layers/phase1.py`, `cascade/context.py`, `bascule_gardes.py`,
`coherence_flux.py`. Front : `frontend/src/components/fiche/ScoreV2Block.tsx`. Tests :
`test_paliers1.py`, `test_p_v2_api.py`, `test_ppr_marginal_coverage.py`, `test_scoring_copro1.py` (neuf).
Recette/scripts : `docs/audit-2026-11/scoring-copro-1/`.

## Ce qui n'a PAS été touché (et pourquoi)
- **mvt / division / résiduel** : hors mandat (« ne touche que le scoring et son run »). Le manifeste local
  les laisse sur q_v20/q_v19/seq 17 ; un déploiement prod les rejoue avec le run.
- **Le run n'est PAS servi en prod** — servi LOCALEMENT le temps de la recette ; le manifeste de dépôt
  reste **q_v20** (sauvegarde `served_manifest.q_v20.bak.json`). La bascule prod est un geste manuel de Vic.
