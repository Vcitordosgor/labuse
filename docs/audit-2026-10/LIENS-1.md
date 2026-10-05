# LIENS-1 — démarrage sans verrou + en-tête de fiche (Errial, Google Earth)

Branche `fix/liens-1` depuis `origin/main` (`27624c22`). Worktree `~/Desktop/labuse-liens`, ports 8825 / 6025.
Un commit par lot ; aucun run ; aucune base touchée en écriture hors `labuse_test`.

---

## Lot 0 — démarrage de l'API sans verrou (prioritaire, avant déploiement)

### Le piège (vécu le 05/10)
Au démarrage, une API a exécuté `ALTER TABLE parcel_residuel_runs ADD COLUMN IF NOT EXISTS
assiette_source text`. **Même quand la colonne existe déjà**, cet `ALTER` prend un verrou
**ACCESS EXCLUSIVE** sur la table le temps de constater qu'il n'a rien à faire. Il s'est mis en
file derrière une transaction ouverte ; dès lors toutes les nouvelles lectures se sont empilées
derrière *lui* (équité de la file des verrous Postgres) → **toutes les lectures du résiduel figées
~8 min**. Même piège que `parcels.origine` (corrigé par SCORING-8) et `ensure_geom_2975`
(commit `70278401`).

### Recette appliquée (la même que `70278401`)
Chaque DDL de boot est précédé d'un **test du catalogue** (`to_regclass` / `information_schema` —
lectures pures, **aucun verrou de table**) et n'est émis **que s'il manque vraiment**. Sur le chemin
nominal (schéma déjà posé) **aucun DDL n'est exécuté** → aucun ACCESS EXCLUSIVE → le boot ne se met
jamais en file.

### 1. Inventaire des DDL exécutés au démarrage
Le boot passe par `_lifespan` (`api/app.py:106`) → **advisory lock `0x1ABE5C`** (sérialise la
réparation de schéma entre workers) → `models.ensure_schema` → `_ensure_schema_steps`
(`models.py:1112`) puis les `ensure_tables()` des routeurs.

**DDL touchant les tables CHAUDES (grosses, lues/écrites en continu — les seules où une
transaction tierce peut tenir le verrou et provoquer le gel) :**

| Fonction | Fichier:ligne | Table(s) | DDL | État |
|---|---|---|---|---|
| `ensure_geom_2975` (ALTER/TRIGGER) | `models.py:1409-1433` | parcels, spatial_layers | ADD COLUMN geom_2975, CREATE/DROP TRIGGER | **GARDÉ** `schema_pose` (info_schema + pg_trigger) |
| `ensure_parcel_origine` | `models.py:2197-2204` | parcels | ADD COLUMN origine | **GARDÉ** `_col_presente` |
| `ensure_parcel_eval_status_dropped` | `models.py:1088-1095` | parcel_evaluations | DROP COLUMN legacy | **GARDÉ** `_col_presente` |
| `ensure_residuel_cache` (ALTER parcel_residuel) | `models.py:1928-1935` | parcel_residuel | ADD COLUMN capacite_estimee/cause | **GARDÉ de fait** : court-circuit `relkind='v'` (base migrée = VUE, l'ALTER n'est jamais atteint) |
| **`ensure_runs_schema`** | **`faisabilite/residuel_runs.py:45-58`** | **parcel_residuel_runs** | **3× ADD COLUMN + CREATE INDEX** | **🔴 NON GARDÉ → corrigé par ce lot** |

**DDL sur tables FROIDES/petites** (admin, CRM, pige, dashboard, veille, signalements,
data_sources, watch_zones, documents_generes, etc. — `ensure_tables()` des routeurs,
`models.py` 1240-2107) : ce sont des `CREATE TABLE/INDEX IF NOT EXISTS` et `ADD COLUMN IF NOT
EXISTS` **non gardés**, mais sur des tables qu'**aucune transaction longue ne tient** → elles ne
peuvent pas provoquer le gel des lectures du résiduel décrit par l'incident. **Non modifiées par ce
lot** (périmètre strict, risque de régression de DDL multi-modules > bénéfice) ; listées ici comme
dette à traiter en passe dédiée si l'on veut le « zéro DDL au boot » absolu.

**Note `ensure_geom_2975`** : son bloc `CREATE INDEX IF NOT EXISTS` + `ANALYZE`
(`models.py:1468-1495`) tourne à **chaque** boot (non gardé), mais ne prend que des verrous
`SHARE`/`ShareUpdateExclusive` qui **ne conflictent pas avec un lecteur** (ACCESS SHARE) → pas de
gel des lectures ; laissé tel quel.

### 2. Correctif
`faisabilite/residuel_runs.py` — `ensure_runs_schema` réécrit avec deux aides locales
`_regclass_present` / `_colonne_presente` (catalogue, sans verrou) ; chaque `CREATE TABLE`,
`ADD COLUMN`, `CREATE INDEX`, `CREATE UNIQUE INDEX` n'est émis que si l'objet manque. Comportement
fonctionnel **strictement identique** (mêmes objets, même ordre) ; seule la **condition d'émission**
change. `migrate_to_runs` (qui réutilise `ensure_runs_schema`) et le court-circuit VUE restent
inchangés.

### 3. Test (bloque toute régression) — `tests/test_boot_sans_verrou.py`
Deux transactions tiennent un **ACCESS SHARE** sur `parcel_residuel_runs` ET `parcels` (la situation
exacte qui met un ALTER en file). Schéma déjà posé → `ensure_runs_schema` **n'émet aucun DDL** →
démarrage immédiat (`< 10 s`, mesuré ~0 s). Un `SET LOCAL lock_timeout = '4s'` transforme une
régression (DDL non gardé réintroduit) en **échec rapide** : l'ALTER buterait sur le verrou tenu et
lèverait, au lieu de geler le test (et la prod) 8 min.

**Preuve que le test mord** : un `ALTER … ADD COLUMN IF NOT EXISTS` *no-op* lancé sous le verrou tenu
lève bien `OperationalError` au bout de 2 s (vérifié hors suite). La version gardée, elle, passe sans
attendre.

**Résultat** : `tests/test_boot_sans_verrou.py` + `tests/test_residuel_runs.py` → **6 passed** (4,8 s).

> Commit autonome : mergeable **sans le lot 1**.
