# POSTDEPLOY-1027 — les trois suites du déploiement du 27/10

Branche `fix/postdeploy-1027` (depuis `origin/main`), worktree `~/Desktop/labuse-postdeploy`, ports 8840/6040.
Autonome P1-P3 ; commit + rapport + push par point. P4 n'est joué qu'**après merge dans main par Vic**.

---

## P1 — `doctor` crée les fonctions SQL

### Diagnostic

Les fonctions SQL créées par le code (`CREATE FUNCTION` du dépôt) sont au nombre de **trois** :

| Fonction | Définie dans | Usage |
|---|---|---|
| `labuse_zone_famille(text)` | `models.py` `ZONE_FAMILLE_FN` | famille U/AU/A/N depuis le subtype (faisabilité, implantation, assemblage, app, résiduel) |
| `labuse_hauteur_lidar_m(real)` | `models.py` `HAUTEUR_LIDAR_FN` | borne des hauteurs LiDAR (**Gabarit 3D** `api/gabarit.py`, résiduel, score, filtres hauteur) |
| `labuse_set_geom_2975()` | `models.py` (dans `ensure_geom_2975`) | fonction-trigger reprojection 4326→2975 |

**Racine de l'incident prod** : `ensure_schema` (le chemin pris au **boot** et par `doctor`) appelait
`_ensure_schema_steps`, qui créait bien `labuse_set_geom_2975` (via `ensure_geom_2975`) mais **jamais**
`labuse_zone_famille` ni `labuse_hauteur_lidar_m`. Ces deux-là n'étaient posées que par `create_all`
(`ensure_zone_famille_fn` / `ensure_hauteur_lidar_fn` appelées *après* `_ensure_schema_steps`) — chemin
qui n'est **pas** pris au boot prod. Sur une base où elles manquaient, le Gabarit 3D tombait en **500**
(`SELECT labuse_hauteur_lidar_m(faitage_m) …`) et `doctor` ne regardait aucune fonction → **silencieux**.

### Correctif

- `models.py` : registre **unique** `SQL_FUNCTIONS` (nom → DDL idempotent, `None` pour la fonction-trigger
  posée avec ses triggers) + `REQUIRED_SQL_FUNCTIONS`. Nouvelle `ensure_sql_functions(engine)` appelée
  **dans `_ensure_schema_steps`** → boot / `doctor --fix` / `create_all` **convergent** sur la même liste.
  `create_all` ne porte plus ses deux appels séparés (supprimés : la dérive est éliminée à la source).
- `state.py` `schema_status` : vérifie chaque `REQUIRED_SQL_FUNCTIONS` via `pg_proc` et ajoute
  `fonction <nom>` aux `missing` → une fonction absente rend `ok=False` ⇒ `doctor` sort **✗ Schéma** et
  code de sortie **1** (erreur, pas avertissement).

### Tests (`tests/test_state.py`)

- `test_doctor_signale_fonction_sql_manquante_et_ensure_schema_la_recree` : base sans
  `labuse_hauteur_lidar_m` → `schema_status` KO + nommée ; après `ensure_schema` → présente et vert.
- `test_registre_fonctions_sql_couvre_tout_create_function_du_depot` : garde — scanne le source réel
  (`CREATE FUNCTION …`) et exige que chaque nom soit dans `REQUIRED_SQL_FUNCTIONS` (empêche la récidive :
  une fonction ajoutée au code mais non déclarée serait invisible de `doctor`).

`pytest tests/test_state.py` → **13 passed** (3 ciblés + 10 existants, aucune régression).

### Comparaison avec la prod (lecture seule)

`ssh labuse-vps … psql -d labuse "SELECT proname FROM pg_proc WHERE proname IN (…)"` au 27/10 :
les **trois** fonctions sont présentes (`labuse_hauteur_lidar_m`, `labuse_set_geom_2975`,
`labuse_zone_famille`). `labuse_hauteur_lidar_m` y avait été recréée **à la main** pendant DEPLOY-1027
pour lever le 500 du Gabarit. **Aucune fonction absente en prod aujourd'hui.** Le correctif garantit
qu'au prochain `ensure_schema` prod elles seront (re)créées idempotemment sans geste manuel, et que
`doctor` les surveillerait désormais.
