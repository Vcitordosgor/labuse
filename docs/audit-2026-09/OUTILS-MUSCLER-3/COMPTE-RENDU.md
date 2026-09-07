# OUTILS-MUSCLER-3 — Compte-rendu

**Étape 0** verte (branche `feat/blocs-fonciers`, arbre propre, `main` contient le tip de
`feat/remonter-le-temps-2` `aa6e53ae`).

**Verdict A (3 lignes).** Le chantier est **tenable tel que décrit** : **11 225 blocs** contigus (2+
parcelles, même SIREN) sur l'île — le chiffre d'audit ~12 000 est confirmé. Coût du batch ~30-60 s ;
**aucun index à créer** (`idx_parcels_geom_2975` GIST existe et est utilisé). Regroupement **PM
seulement** (les particuliers n'ont pas d'identité stable ; l'écran le dit).

**La commande (NON exécutée — c'est Vic qui la lance) :**
```
LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse PYTHONPATH=$PWD/src labuse blocs-build
```
Idempotent (DELETE + rebuild, `bloc_key=siren:min(idu)`), journalisé (`run_progress`). Run réel :
11 225 blocs / 59 835 parcelles / ~25 s ; rejoué = même checksum.

**Commits** (poussés, PAS de merge) : `acbf1bb6` Lot A (cadrage + `scripts/blocs_cadrage.sql`) ·
`c1568fcf` Lot B (`models.py` 2 tables, `blocs.py`, CLI `blocs-build`, `tests/test_blocs.py`) ·
`097efe85` Lot C (endpoints `/modules/blocs[/{id}]`, `Blocs.tsx`, registre M29, `api.ts`).

**Preuves** : `C-captures.md` + `captures/*.png` (rendu réel via API 8000 + vite 5180, Playwright) et
preuve DOM (bandeau « 11 225 blocs », carte CBO TERRITORIA 323 345 m² Estimé, détail 118 IDU, état vide
honnête à Cilaos). **Perf** liste ~21-22 ms (île/dense/rurale), détail 1-2 ms.

**Tests** : back `test_blocs.py` 7 verts (bloc vérifié à la main + isolée/proprios différents/particulier/
non-contiguës/idempotence + endpoints liste/détail/filtres/404) ; collection 2778 sans erreur d'import.
Front tsc/vite OK, vitest **191**.

**Décisions signalées (faute d'instruction) :** (1) le résiduel agrégé se lit sur la **vue servie
`parcel_residuel`** (run résiduel `run_seq=2`), pas via `q_v11_m137` — le pin scoring ne porte pas le
résiduel, cohérent avec « aucun badge de score ». (2) **Domaine public** : la règle « cadastral seulement »
est satisfaite par construction (la table `parcels` EST la couche cadastrale) ; en conséquence des PM
**publiques** (COMMUNE DE…, État) apparaissent comme blocs — je ne les ai **pas** exclues (ce serait une
règle ajoutée non demandée). À arbitrer si Vic veut les masquer. (3) Aucun filtre de slivers (toutes les
parcelles cadastrales du SIREN comptent, conforme au mandat).

**A résisté :** le worktree n'a pas de `node_modules` (lié à `Desktop/labuse/frontend`, gitignoré) ; l'API
worktree met ~70 s à démarrer (ensures/migrations) avant de répondre — capture faite après.
