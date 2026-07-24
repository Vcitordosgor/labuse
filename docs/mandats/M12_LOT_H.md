# M12 — LOT H · CRM personnalisable (colonnes par tenant, jamais de carte perdue)

Branche `feat/m12-h-crm`. **Ne pas merger** (livrable de revue). Zéro touche scoring.

## Objectif

Les colonnes du kanban de prospection (CRM) étaient EN DUR (`config/pipeline.yaml`, 8 étapes
LABUSE). Elles deviennent **personnalisables et stockées PAR TENANT en base** : chaque compte
peut renommer, ajouter, supprimer, réordonner ses colonnes, et « Réinitialiser » au modèle
LABUSE. La boussole produit — **on ne perd JAMAIS une carte** (parcelle suivie) — est tenue
côté serveur ET côté UI.

## H1 — Colonnes personnalisables, par tenant

### Schéma ajouté (`src/labuse/api/crm_columns.py`, `ensure_tables`)

```sql
CREATE TABLE IF NOT EXISTS crm_columns (
  id         serial PRIMARY KEY,
  compte_id  integer REFERENCES comptes(id) ON DELETE CASCADE,  -- NULL = bucket pilote/legacy
  key        varchar(64) NOT NULL,   -- clé STABLE ascii ; = pipeline_entries.status (join des cartes)
  label      varchar(80) NOT NULL,   -- libellé affiché (renommable sans toucher aux cartes)
  tone       varchar(16),            -- cold/warm/hot/reject (accent de colonne, cosmétique)
  position   integer NOT NULL,       -- ordre dans le kanban
  is_default boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);
-- unicité (compte_id, key) : NULLS NOT DISTINCT (PG15+) sinon repli simple
CREATE INDEX ix_crm_columns_compte ON crm_columns(compte_id);
```

Migration **additive et sûre** : `CREATE TABLE IF NOT EXISTS` + `ADD CONSTRAINT` idempotents,
appelés au boot via le schema-heal existant (`_lifespan` → boucle `ensure_tables`, sous le
verrou consultatif A5). FK `ON DELETE CASCADE` : supprimer un compte emporte ses colonnes (RGPD).

### Semis paresseux (lazy seed)
Un tenant sans colonne est semé au **kanban LABUSE par défaut** (les 8 étapes de
`config/pipeline.yaml`, tones inclus — c'est un bon défaut, on le garde), au premier accès à
`/pipeline/columns` ou `/pipeline/meta`. Reproductible, idempotent (`seed_if_empty`).

### Rattachement des cartes (aucune migration de données)
Les cartes (`pipeline_entries.status`) référencent la colonne par sa **`key` stable** — modèle
INCHANGÉ. Les cartes existantes (status = `reperee`, `contact_a_preparer`, …) mappent
directement sur les colonnes par défaut re-semées avec les MÊMES keys. **Renommer** = changer
`label` (la key ne bouge pas → aucune carte touchée). **Ajouter** = key dérivée du libellé
(slug ascii + suffixe anti-collision).

### API (toutes tenant-scopées, IDOR-safe : filtre `compte_id IS NOT DISTINCT FROM :cid`)
- `GET  /pipeline/columns` — liste (+ `cards` = nombre de cartes par colonne)
- `POST /pipeline/columns` — créer (ajout en fin)
- `PATCH /pipeline/columns/{id}` — renommer (label + tone)
- `POST /pipeline/columns/reorder` — réordonner (order = ids exacts du compte)
- `DELETE /pipeline/columns/{id}` — supprimer (cf. H2)
- `POST /pipeline/columns/reset` — réinitialiser (cf. H3)

`/pipeline/meta`, `/pipeline` (add), `/pipeline/{id}` (patch) lisent désormais les colonnes
DU TENANT (fin de `_col_keys()` basé config). L'auto-CRM projet (`_sync_crm_retenue`) place la
carte dans `contact_a_preparer` si le compte l'a, sinon sa 1re colonne (jamais une key orpheline).

## H2 — Supprimer une colonne peuplée : jamais de carte perdue

Règle appliquée **serveur (source de vérité) ET UI** :
- Colonne **peuplée** sans `move_to` → **422** (rien supprimé). L'UI ouvre un dialogue
  « où déplacer les N cartes ? » (cible obligatoire).
- Avec `move_to` : les cartes sont d'abord **déplacées** (`UPDATE pipeline_entries SET status =
  key_cible`) PUIS la colonne est supprimée. `move_to` doit appartenir au tenant (404 sinon) et
  différer de la colonne supprimée (422 sinon).
- **Dernière colonne indélébile** : supprimer l'unique colonne restante → **422** (le kanban ne
  peut jamais être vidé).
- Colonne **vide** : suppression directe, pas de cible demandée.

## H3 — Réinitialiser

`POST /pipeline/columns/reset` : **remappe TOUTES les cartes du tenant sur la 1re colonne par
défaut** (`reperee`), supprime les colonnes custom, re-sème les défauts LABUSE. Aucune carte
perdue même si elle était dans une colonne custom supprimée. L'UI confirme (`window.confirm`) et
documente le remappage dans la réponse (`note`).

## Front (`frontend/src/components/crm/Kanban.tsx`)
Bouton **« Personnaliser »** → mode édition : libellés éditables (clic → input inline), boutons
**← →** (réordonnancement par pas — DnD des colonnes noté en suivi, le DnD des CARTES reste), **✕**
(supprimer, avec dialogue de déplacement H2), **+ Colonne** (ajout), **Réinitialiser** (H3). Types
+ helpers API dans `lib/types.ts` / `lib/api.ts`.

## Tests
`tests/test_crm_columns.py` (9 tests, jeu de démo Saint-Paul, bucket pilote) :
- H1 : semis défaut LABUSE ; rename ne touche pas les cartes ; add + reorder (+ reorder à trous
  rejeté 422) ; delete colonne vide.
- **H2** : delete peuplée sans move_to → 422 (colonne + carte préservées) ; delete avec move_to
  déplace la carte (jamais perdue) ; move_to = soi / inconnu rejeté ; **dernière colonne → 422**.
- H3 : reset restaure les défauts et remappe la carte d'une colonne custom sur la 1re colonne.

## Vérification
- `npm run build` (frontend) → **0 erreur TS**, build OK.
- `pytest -k "crm or carnet or pipeline"` → **25 passed** ; suite complète worktree
  **1148 passed / 18 skipped / 0 fail** (baseline main 1139 + 9 nouveaux). `test_audit_secu`
  (cloison IDOR) 19/19, `test_api` 30/30 en isolation.
  - Note : un ordre de modules particulier (`test_audit_secu` avant `test_api`) fait tomber des
    tests d'API par **pollution pré-existante** (config auth LRU-cachée non ré-initialisée entre
    modules) — reproductible à l'identique sur `main` propre, **indépendant de ce lot**.
- **Golden 116/116 PASS** (uvicorn:8025 sur la vraie base prod ; schéma=ok, colonnes semées
  paresseusement, `/pipeline/columns` servi live ; H2 422 vérifié en smoke sur colonne peuplée).

## Suivi (hors périmètre)
- DnD des colonnes (le réordonnancement est livré via boutons ← →, comme prévu au fallback).
- Fragilité d'ordre de suite (auth LRU inter-modules) = dette existante, à traiter hors lot.
