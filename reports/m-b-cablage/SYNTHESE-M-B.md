# M-B — Garde de câblage scoring au démarrage — synthèse

Branche `feat/m-b-cablage` (worktree `~/Desktop/labuse-mb`, base `origin/main` 709af2fe).
CC ne merge pas : Vic valide et merge. Méthode : mesurer d'abord — chaque incohérence existe-t-elle ?

## Mesure préalable : le câblage actuel est COHÉRENT (4/4)

| Invariant | Mesure aujourd'hui |
|---|---|
| YAML ↔ registry (P2-18) | **38 = 38**, 0 orphelin dans un sens comme dans l'autre |
| Sévérités (P1-3/P2-19) | enum {info,faible,moyen,fort} = clés `severity_multipliers` ; `info: 0` présent ; toutes les sévérités citées au YAML ∈ enum |
| bonus_keys (P1-3) | 11 clés config = 11 émises ; aucune clé utilisée absente |
| spatial_kinds (P2-30) | 25 kinds référencés, **tous présents** en base (0 absent) |

Conforme au mandat : la garde est le livrable, pas une correction. **Aucune incohérence à rapporter.**

## Ce que le code montrait (fragilités latentes que la garde verrouille)

- `engine.py:24` filtre `lc.get("name") in REGISTRY` → une couche déclarée au YAML mais non
  implémentée est **silencieusement sautée** (aucune erreur). La garde la refuse désormais.
- `opportunity.py:55` `mult.get(sev, 1)` → une sévérité inconnue/typo vaudrait **×1 par défaut**
  (pas 0, pas d'erreur). `opportunity.py:68` `bonuses.get(key, 0)` → une bonus_key absente = **0 muet**.
  La garde attrape les deux avant qu'ils ne servent.

## La garde : `cascade/cablage.py::check_cablage_scoring(session=None)`

**Bloquante** (lève `CablageError`), message ITEMISÉ nommant chaque couche/sévérité/clé/kind fautif
(jamais « configuration invalide »). Quatre invariants :
1. YAML ↔ registry, **les deux sens**.
2. Sévérités : chaque membre d'enum a un multiplicateur ; `info == 0` ; sévérités YAML ∈ enum.
3. bonus_keys utilisées (params YAML + littéraux `bonus_key=`) ⊆ config.
4. spatial_kinds référencés existent en base (si `session`), avec **tolérance base non-ingérée**
   (si aucun kind cascade n'est présent = fresh/test DB, pas un défaut de câblage → non flaggé).

## Où brancher : tranché sur mesure (les deux, à granularité différente)

Le `SELECT DISTINCT kind FROM spatial_layers` coûte **~1,2 s** (mesuré) — trop cher au boot de
chaque worker API, négligeable dans un run. D'où :

- **Boot de l'app** (`api/app.py::_lifespan`, avant `yield`, à côté de `exiger_secret_prod`) :
  garde **statique** (invariants 1-3, ~0 ms, sans base) → un déploiement miscâblé **refuse de
  démarrer**.
- **Run de cascade** (`cascade/pipeline.py::evaluate_parcels`) : garde **statique mémoïsée** une
  fois par processus → protège tout calcul (API 1-parcelle comme batch).
- **Run d'île** (`cli.py::dryrun-evaluate`) : garde **complète (statique + kinds DB)** en tête de
  commande — la part DB est ici, là où la base est déjà payée et complète.

Placer la part DB dans `evaluate_parcels` aurait cassé les tests cascade (qui sèment
`spatial_layers` PARTIELLEMENT) et tout run sur base partielle : écarté à dessein.

## Validation attendue

1. Couche retirée du registry (pas du YAML) → refus, nom dans le message. ✔ `test_couche_registry_retiree_refuse`
2. Sévérité inconnue déclarée → refus, nom dans le message. ✔ `test_severite_inconnue_refuse`
3. Couche INFO contribue exactement 0. ✔ `test_info_contribue_exactement_zero` (INFO traitée, poids 0 ; MOYEN pénalise)
4. Le câblage actuel passe la garde. ✔ `test_cablage_actuel_passe` (+ mesure statique et DB)

Bonus tests : réciproque YAML-manquante, sévérité enum sans multiplicateur, `info != 0`, bonus_key
inexistante, kind spatial absent (base peuplée) vs base vide tolérée. **10 tests, tous verts.**

## Périmètre strict

Ajouté : `cascade/cablage.py` (garde) + son test ; câblage minimal dans `api/app.py`,
`cascade/pipeline.py`, `cli.py`. **Non touché** : les couches, les coefficients, le golden, les
YAML de config (lus, pas modifiés). Tests cascade/scoring/app : 61 + 11 verts.
