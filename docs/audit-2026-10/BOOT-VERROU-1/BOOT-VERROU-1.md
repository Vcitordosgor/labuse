# BOOT-VERROU-1 — l'API démarre sans verrouiller de table

**Branche** `fix/boot-verrou-1` (base `origin/main` = `efb60a85`) · worktree `~/Desktop/labuse-bootverrou`
· ports API **8714** / Vite 5914 · un seul commit · aucun run, aucune migration de données, **aucun
schéma modifié** : on change *quand* le DDL est émis, pas ce qu'il fait.

Même incident que `assiette_source` (05/10) et `ensure_runs_schema` (réglés par **LIENS-1 lot 0**,
commit `9de46f6b`) : au boot, un DDL *no-op* prend un verrou fort, se met en file derrière une
transaction ouverte, et gèle tout le démarrage — puis toutes les lectures s'empilent derrière lui.
Recette reprise telle quelle : **lire le catalogue d'abord (`to_regclass` / `information_schema` —
des lectures sans verrou), n'émettre le DDL que si l'objet manque vraiment.**

Le symptôme du 06/10 — `ALTER TABLE parcel_zone_plu` au boot — est l'`ALTER TABLE parcel_zone_plu ADD
COLUMN IF NOT EXISTS zone_filtre` de `models.ensure_zone_filtre`, **émis au boot** (dans
`_ensure_schema_steps`, pas depuis un import ni un build). Corrigé ci-dessous.

---

## 0. Mécanique des verrous — mesurée, pas supposée

Sonde empirique sur `labuse_test` (deux connexions, `lock_timeout` 1 s ; harnais = probe jetable) :

| DDL *no-op* | verrou pris | bloqueur tenu | résultat |
|---|---|---|---|
| `ALTER TABLE … ADD COLUMN IF NOT EXISTS` (colonne déjà là) | ACCESS EXCLUSIVE | **lecteur** (ACCESS SHARE) | **BLOQUÉ** |
| `ALTER TABLE … ALTER COLUMN TYPE` (déjà large) | ACCESS EXCLUSIVE | lecteur (ACCESS SHARE) | **BLOQUÉ** |
| `CREATE INDEX IF NOT EXISTS` (index déjà là) | SHARE | lecteur (ACCESS SHARE) | passe (0,00 s) |
| `CREATE INDEX IF NOT EXISTS` (index déjà là) | SHARE | **écrivain** (ROW EXCLUSIVE) | **BLOQUÉ** |
| `CREATE TABLE IF NOT EXISTS` (table déjà là) | *aucun verrou sur l'existant* | lecteur (ACCESS SHARE) | passe (0,00 s) |

Conclusions qui **définissent le périmètre** :

1. **`ALTER TABLE` (ADD/ALTER/DROP COLUMN, DROP CONSTRAINT, DROP INDEX)** prend un ACCESS EXCLUSIVE
   *même no-op* → gèle derrière **tout lecteur** d'une table servie en continu. **Danger principal.**
2. **`CREATE INDEX`** no-op prend un SHARE → gèle seulement derrière un **écrivain** (un run de
   cascade/ingestion qui tient la table). Danger réel sur les grosses tables écrites par les runs.
3. **`CREATE TABLE IF NOT EXISTS`** no-op **ne verrouille pas** la table existante → **sans risque**,
   laissé tel quel. (L'inventaire exhaustif d'un sous-agent l'avait cru dangereux ; la sonde l'infirme.)
4. `CREATE OR REPLACE VIEW` / `FUNCTION` / `EXTENSION IF NOT EXISTS` : pas de verrou sur une table de
   données → laissés tels quels.

« Table **chaude** » = lue en continu par l'app (un ALTER y gèle le service) **ou** écrite par les
runs (un CREATE INDEX y gèle derrière le run).

---

## 1. Inventaire des DDL de boot

Chemin de boot : `api/app._lifespan` → `models.ensure_schema` → `models._ensure_schema_steps`
(≈ 40 `ensure_*`) **+** les `ensure_tables` des routeurs (`_heal_steps` : modules, ia, events,
partners, projets, protection, courrier, comptes+scoping, crm_columns, veilles, copilote_v2,
dashboard, pige, promo, zone, recherche). Inventaire croisé avec un sous-agent + lecture directe.

### 1.a — DDL sur table CHAUDE : déjà gardés AVANT ce mandat (rien à faire)

| Table | DDL | gardé par | emplacement |
|---|---|---|---|
| parcels / spatial_layers | ADD COLUMN geom_2975, triggers, GiST | `schema_pose` (colonnes+triggers) | `models.ensure_geom_2975` |
| parcels | ADD COLUMN origine | `information_schema` | `models.ensure_parcel_origine` |
| parcel_p_score_v2 | ADD COLUMN icd/icd_detail + index | `_col_presente` / `_index_present` | `models.ensure_icd_columns` |
| parcel_p_score_v2 / score_snapshot | ALTER TYPE tier/statut | `_varchar_len` | `models.ensure_constructibilite_cache` |
| parcel_residuel_runs / residuel_runs | CREATE TABLE + ADD COLUMN×3 + index | `to_regclass` / `information_schema` | `faisabilite.residuel_runs.ensure_runs_schema` (LIENS-1) |
| sitadel_permits | ADD COLUMN date_depot | `_col_presente` | `models.ensure_sitadel_depot` |
| parcel_evaluations | DROP COLUMN legacy | `_col_presente` | `models.ensure_parcel_eval_status_dropped` |
| scoped tables (FK) | ADD CONSTRAINT fk_*_compte | `pg_constraint` | `api.tenant.ensure_scoping` |

### 1.b — DDL sur table CHAUDE : **non gardés → corrigés par ce mandat**

| Table (chaleur) | DDL non gardé | fonction (boot) | → corrigé en |
|---|---|---|---|
| **parcel_zone_plu** (≈20 lecteurs — *le symptôme*) | `ADD COLUMN zone_filtre` + `CREATE INDEX idx_pzp_zone_filtre` | `models.ensure_zone_filtre` | `models.py:2203` |
| **parcels** (table la + lue) | `CREATE INDEX ix_parcels_section_numero` | `api.recherche.ensure_index` | `recherche.py:73` |
| **adresses** (autocomplete, ingérée BAN) | `CREATE INDEX … gin trgm` | `api.recherche.ensure_index` | `recherche.py:76` |
| **data_sources** (vitrine, badges, accueil) | `ADD COLUMN ×9` + `ALTER TYPE status` | `models.ensure_data_sources_millesime` | `models.py:2075` |
| **dryrun_cascade_results** (9,7 M, écrite par les runs) | `CREATE INDEX` ×2 | `models.ensure_promesses_index` / `ensure_flags_probe_index` | `models.py:1290`, `1323` |
| **comptes** (chemin d'auth, chaque requête) | `DROP CONSTRAINT` + `ADD COLUMN` (×3 au total : comptes.py + dashboard.py) | `comptes.ensure_tables`, `dashboard.ensure_tables` | `comptes.py:85`, `dashboard.py:88` |
| **sessions_auth** (résolue à chaque requête authentifiée) | `ADD COLUMN ip_hash/ua_hash` | `comptes.ensure_tables` | `comptes.py:119` |
| **ia_log** (écrite à chaque appel IA) | `ADD COLUMN compte_id` + `CREATE INDEX` | `dashboard.ensure_tables` | `dashboard.py:82` |
| **pipeline_entries** (CRM/Copilote) | `ADD COLUMN ×6` (models ×4 + projets + scoping) + `CREATE INDEX ×2` | `models.ensure_pipeline_*` / `ensure_contact_etiquette`, `projets.ensure_tables`, `tenant.ensure_scoping` | `models.py:1337…`, `projets.py:83`, `tenant.py:47` |
| **projets** (Copilote-projet) | `ADD COLUMN ×4` | `projets.ensure_tables` | `projets.py:83` |
| **watch_zones / alertes** (veille) | `ADD COLUMN compte_id` ×2 + `CREATE INDEX` ×4 + **`DROP INDEX` legacy rejoué à chaque boot** | `models.ensure_watch_zones` | `models.py:1761` |
| scoped tables (×11 : pipeline_entries, watch_zones, alertes, documents_generes, signalements, event_log, watched_parcels, projets, saved_searches, saved_filters, courrier_demandes) | `ADD COLUMN compte_id` + `CREATE INDEX ix_*_compte` | `tenant.ensure_scoping` | `tenant.py:47` |

### 1.c — DDL laissés (hors « table chaude ») — et pourquoi

- **Tous les `CREATE TABLE IF NOT EXISTS`** (events, ia, modules, partners, protection, crm_columns,
  veilles, copilote_v2, pige, promo, zone, filtres, taxe, reglages, commune_contacts, suggestions,
  enrichment, bilan_params, etc.) : **ne verrouillent pas** l'existant (sonde §0 ligne 5) → zéro gel.
- **ALTER/CREATE INDEX sur tables FROIDES** à faible concurrence, laissés (blast radius d'une seule
  fonctionnalité, probabilité de collision quasi nulle au boot) : `signalements` (file QA),
  `retours` (boîte de retours admin), `bilan_params` (config secteur), `event_log`/`notif_*`
  (créées par `events.ensure_tables`), `copilote_*`, `pige_*`, `programmes`, `crm_columns`. Candidats
  à une passe FIX ultérieure si on veut l'uniformité stricte ; pas un risque de gel du service.
- **`dashboard.admin_source_affichage` (dashboard.py:1584)** fait un `ALTER TABLE data_sources ADD
  COLUMN IF NOT EXISTS` : c'est un **endpoint admin au RUNTIME**, pas un DDL de boot → hors mandat
  (latent, mais ne concerne pas le démarrage).

---

## 2. Correctif — garde-catalogue, même forme que `9de46f6b`

Pour chaque DDL de 1.b : on teste le catalogue (lecture pure, **aucun verrou de table**) et on
n'émet le DDL **que si l'objet manque vraiment**. Chemin nominal (schéma posé) = **zéro ACCESS
EXCLUSIVE, zéro SHARE**. Objets, types et ordre inchangés ; seule la *condition d'émission* change.
Helpers réutilisés (`models._col_presente` / `_index_present` / `_varchar_len`) ou inlinés par
fichier (comme LIENS-1 avait inliné `_regclass_present` dans `residuel_runs.py`).

Fichiers (file:line = ancre du commentaire `BOOT-VERROU-1`) :

- `src/labuse/models.py`
  - `ensure_zone_filtre` **:2203** — symptôme : ALTER + CREATE INDEX gardés ; le backfill `zone_filtre`
    accompagne la *pose* de la colonne (ensuite le builder `tiles.build_parcel_zone_plu` l'écrit).
  - `ensure_data_sources_millesime` **:2075** — 9 ADD COLUMN (boucle gardée) + ALTER TYPE gardé par longueur.
  - `ensure_promesses_index` **:1290**, `ensure_flags_probe_index` **:1323** — CREATE INDEX gardés.
  - `ensure_pipeline_projet/prospection/archived/contact_etiquette` **:1337…1377** — ADD COLUMN + index gardés.
  - `ensure_watch_zones` **:1761** — ADD COLUMN + CREATE INDEX gardés ; le `DROP INDEX` legacy n'est
    plus émis que si l'index subsiste.
- `src/labuse/api/recherche.py` `ensure_index` **:67** — CREATE INDEX `parcels` + `adresses` gardés ;
  `CREATE EXTENSION` laissé (ne verrouille pas de table).
- `src/labuse/api/dashboard.py` `ensure_tables` **:78** — ADD COLUMN `comptes` ×2 + `ia_log` + son
  index gardés (helper `_col_absent`). `retours` laissé (froid).
- `src/labuse/comptes.py` `ensure_tables` **:85 / :119** — `comptes` (DROP CONSTRAINT via `pg_constraint`
  + ADD COLUMN) et `sessions_auth` (ADD COLUMN) gardés.
- `src/labuse/api/projets.py` `ensure_tables` **:83** — les 5 ADD COLUMN sortis du bloc DDL texte et
  gardés un à un (projets + pipeline_entries) ; le `CREATE TABLE` reste dans le bloc.
- `src/labuse/api/tenant.py` `ensure_scoping` **:47** — la boucle sur les 11 tables scoped : ADD
  COLUMN `compte_id` + `CREATE INDEX ix_*_compte` désormais gardés (les FK l'étaient déjà).

**Aucun DDL ne reste émis sur une table chaude au chemin nominal.** Pour le cas « schéma réellement
absent au premier démarrage » : le DDL s'exécute (colonne/index posés) ; la **preuve** (§3) arme un
`lock_timeout` court côté boot pour que, si un objet manque *et* qu'un voisin tient la table, on lève
vite avec un message clair au lieu d'attendre indéfiniment.

---

## 3. Preuve

`tests/test_boot_verrou_1.py` (étend `test_boot_sans_verrou.py` de LIENS-1).

**`test_boot_sans_verrou_sur_tables_chaudes`** — schéma posé (fixture), puis **11 bloqueurs tiennent
un ACCESS SHARE** (lecteurs) sur `parcel_zone_plu`, `data_sources`, `parcels`, `pipeline_entries`,
`comptes`, `sessions_auth`, `adresses`, `ia_log`, `dryrun_cascade_results`, `watch_zones`, `alertes`
**+ 5 bloqueurs ROW EXCLUSIVE** (écrivains) sur les tables à CREATE INDEX. On rejoue alors **tous** les
`ensure_*` corrigés via un engine `boot` au `lock_timeout` armé : ils finissent **< 10 s** sans jamais
se mettre en file (chemin nominal = zéro DDL). Les bloqueurs sont tenus par **psycopg brut** (hors pool
SQLAlchemy de l'app) pour ne pas épuiser le QueuePool.

**`test_les_gardes_mordent`** — preuve que le test **mord** : les DDL **non gardés d'origine**, rejoués
sous les mêmes verrous, lèvent bien (`OperationalError` / `lock_timeout`) :
- `ALTER TABLE parcel_zone_plu ADD COLUMN IF NOT EXISTS zone_filtre` sous un **lecteur** → lève ;
- `CREATE INDEX IF NOT EXISTS ix_dryrun_cascade_bati_exclude …` sous un **écrivain** → lève.
Donc si une garde disparaissait, le test nominal basculerait en échec.

```
$ pytest tests/test_boot_verrou_1.py tests/test_boot_sans_verrou.py -q
3 passed in 9.81s      # ~8 s = les deux attentes lock_timeout (4 s) du test « mord »
```

**Démarrage réel** (API sur **8714**, base `labuse_test` — jamais la base partagée, cf. consigne
« ne jamais tuer/bloquer un voisin ») **pendant qu'une session tient un ACCESS SHARE sur
`parcel_zone_plu`** :

```
[voisin] ACCESS SHARE tenu sur parcel_zone_plu
=== /healthz : {"status":"ok"} (prêt en 2.0s sous verrou) ===
=== /readyz HTTP : 503 ===          # répond (503 = données absentes sur la base de test, PAS un gel)
--- idle-in-transaction restants : 0 ---
--- port 8714 libre ---             # arrêt propre (SIGTERM)
```

L'API démarre et répond en 2 s **sous le verrou** qui gelait le boot avant le correctif.

### Régression (non-régression fonctionnelle)

- `tests/test_boot_verrou_1.py` + `tests/test_boot_sans_verrou.py` : **3 passés**.
- Surfaces touchées : `test_projet_m120`, `test_dashboard`, `test_retours16_recherche`,
  `test_sources1_lot1`, `test_etats_sources`, `test_copilote_projet` → **69 passés**.
- Auth / veille / comptes : `test_alertes`, `test_auth`, `test_comptes`, `test_audit_comptes`,
  `test_compte2_*`, `test_cloisonnement_1` (sauf 1), `test_documents_bibliotheque_cloison` →
  **95 passés**.
- **Pré-existant, hors scope** : `test_cloisonnement_1::test_copilote_questions_et_plafond_cloison`
  échoue sur un appel modèle réel (`BadRequestError: credit balance too low`) — environnemental,
  sans lien avec le schéma/les verrous.

Comportement **identique** : sur base fraîche, l'objet manque → la garde est fausse → le DDL est émis
comme avant ; sur base posée → la garde est vraie → on saute un DDL qui était déjà un no-op (mais qui
prenait le verrou). Zéro schéma modifié.
