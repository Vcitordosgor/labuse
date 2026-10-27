# DONNEES-ETAT-FIX-1 — réparation des écarts 1, 2, 3, 4, 6, 7, 9

Branche `fix/donnees-etat-fix-1` (worktree `~/Desktop/labuse-etatfix`), depuis `origin/main` (`a582f8f4e`). Le 27/10/2026 (VPS déjà le 28/10). **Pas de merge, pas de déploiement.** Gestes prod autorisés et réellement faits : **poser le crontab** et **l'env** (lots A/B). Dump récent vérifié avant tout geste : `labuse-labuse-20261027-222603.dump` (22:55, 7,1 Go).

> ⚠️ **Rappel de régime.** Les correctifs qui sont du CODE ne prennent effet en prod qu'au **prochain déploiement** (comme toute branche non mergée). Certains correctifs étaient déjà dans `main` et **ont été mis en prod aujourd'hui** par POSTDEPLOY-1027 (ORF-01/02/03, mail-queue cède) ; ce qui est **nouveau sur cette branche** attend le déploiement. Chaque lot précise son état.

---

## Tableau de synthèse

| Écart | Correctif | Nature | En prod ? | Preuve |
|------|-----------|--------|-----------|--------|
| 2, 3 | `deploy_vps.sh` repose+vérifie le crontab à chaque deploy ; crontab reposé maintenant | code + geste prod | crontab **posé ce soir** ; auto-repose au prochain deploy | `--verifier` vert, `/healthz/crons` ok:true, sentinelle silencieuse |
| 9 | état orphelin `recap-matin` purgé | geste prod | **fait** | plus d'état `recap-matin` actif |
| 4 | PermissionError résolu (déjà) + **bug de verrous ia_log corrigé** + plafond/ clé en place | code + geste prod | PermissionError **résolu en prod** ; fix verrous **sur branche** | passage réel 0,21 € + test de régression |
| 6 | `sante-endpoints` cède à la sauvegarde (comme `mail-queue`) | code | mail-queue cède **déjà en prod** ; sante-endpoints **sur branche** | test + rejeu fenêtre 13:30 local |
| 7 | VACUUM range vraiment (ORF-03) | code | **en prod** (déployé 27/10) | passage local : 6 tables vacuumées |
| 1 | rotation dumps 2 quotidiens + 1 hebdo | code | **sur branche** | test ; + liste des poubelles (ci-dessous) |

---

## Lot A — Le crontab (écarts 2, 3, 9)

**La cause.** Il existe DEUX scripts de déploiement : `deploy.sh` (racine, CRON-1) qui sait poser le crontab, et `deploy/scripts/deploy_vps.sh` (installé `/opt/labuse/deploy.sh`) qui est **le vrai déployeur** lancé à chaque mise en prod. Or `deploy_vps.sh` **ne touchait jamais le crontab** : il changeait le binaire (donc le registre des jobs) sans reposer `/etc/cron.d/labuse`. Résultat ETAT-2 : crontab périmé en silence (`agents-sources` absent, `restore-test` fantôme).

**Correctif code.** `deploy_vps.sh` gagne une étape 4b : il régénère le crontab depuis le registre (`labuse jobs crontab --tz reunion`), **sauvegarde l'ancien** (`/etc/cron.d/labuse.bak-deploy-*`), le pose, puis **VÉRIFIE** l'égalité au registre (`--verifier`). Tout écart ou toute erreur **arrête le déploiement** (`exit 5`). Plus jamais « déployé mais crontab périmé ».

**Geste prod (fait ce soir).** Crontab régénéré depuis le binaire prod et reposé. L'ancien est sauvé en `/etc/cron.d/labuse.bak-etatfix-20261028-013357`. Diff appliqué :
- `+ agents-sources` (dim 23:00, 1 semaine ISO sur 2) — était attendu par le registre, manquait au cron ;
- `− restore-test` (gelé fantôme) — retiré du registre, traînait au cron.

**Orphelin recap-matin.** `recap-matin.json` déplacé en `recap-matin.json.orphelin-purge-20261028` (aucun état actif ne subsiste ; l'historique `job_runs` reste, c'est un journal).

**Preuves.**
- `labuse jobs crontab --tz reunion --verifier /etc/cron.d/labuse` → **« == registre (aucun écart) »** (vert).
- `GET /healthz/crons` → **`ok: true`** (zéro job non-ok).
- Sentinelle Mac (`watch-prod`) : fichier d'état repassé à **`ok`** ; **plus aucune alerte après 22:27 CEST** (fin de la tempête qui tombait toutes les 10 min depuis ~20:13). *(Observation partielle : ~25 min de silence constaté ; le mandat demandait 1 h, mais la cause — `/healthz/crons` rouge — est levée.)*

---

## Lot B — Les enquêteurs IA (écart 4)

**PermissionError `.local/state/jobs` : déjà résolu.** Le crash du 13/10 venait du défaut RELATIF `jobs_state_dir=.local/state/jobs` résolu contre un CWD non inscriptible. Le validateur **CRON-PROD-1** (`config.py:_dossiers_jobs_absolus`, posé le 19/10 — après le crash) ancre tout chemin relatif sur `$HOME`, et la prod pose en plus les chemins ABSOLUS (`LABUSE_JOBS_STATE_DIR=/var/lib/labuse/state/jobs`, inscriptible par `labuse`, `HOME=/home/labuse`). Le PermissionError **ne peut plus se reproduire** — confirmé : le passage réel ci-dessous a bien écrit son état.

**Env.** `LABUSE_AGENT_PLAFOND_EUR=5` est **déjà posé** (`/etc/labuse/labuse.env:64`) ; `ANTHROPIC_API_KEY` présent. Rien à poser.

**Crontab.** `agents-sources` remis au crontab par le Lot A (dim 23:00, semaines ISO paires).

**Passage réel (prod, autorisé).** Lancé sur la portée par défaut (`circuit_garanties.sources_sans_amont` = **9 sources**, pas 5 — la portée réelle est de 9). **Coût réel : 0,2053 €** (9 appels `web_search`, ledger `ia_log`) — très en-dessous du plafond 5 €.

**MAIS : bug découvert — le passage a ÉCHOUÉ** (`statut: echec`, `PendingRollbackError`, 9/9 rejetées, 0 neuf, 11 min). C'est la **première fois** qu'`agents-sources` dépassait le PermissionError et atteignait sa boucle — il a alors buté sur un cycle de verrous jamais vu :

> La session du job (`ctx.db`) lit le coût cumulé (`SELECT … FROM ia_log`) et reste « idle in transaction » en tenant un **AccessShareLock** sur `ia_log` pendant tout l'appel API. Or chaque passage de `ai/core._log_cost` fait `ALTER TABLE ia_log ADD COLUMN IF NOT EXISTS compte_id` — qui prend un **ACCESS EXCLUSIVE** (même en no-op) depuis la session par-source. Les deux se bloquent mutuellement (cycle applicatif que Postgres ne tranche pas) → le passage patauge jusqu'à casser en `PendingRollbackError`.

**Correctif code (chirurgical, dans l'agent).** `_cout_agent_source_eur` **relâche la transaction** (rollback d'une lecture seule) juste après avoir lu le coût : plus aucun verrou `ia_log` n'est tenu pendant l'appel API → l'`ALTER` par-source passe sans blocage.

**Preuve.** `tests/test_donnees_etat_fix1.py` : (1) après la lecture du coût, la session **n'est plus en transaction** et une session parallèle peut faire l'`ALTER` sans attendre ; (2) test miroir prouvant le MÉCANISME (une lecture laissée ouverte **bloque** bien l'`ALTER` jusqu'au `lock_timeout`). Le coût réel du passage est affiché (0,21 €).

> ⚠️ **À retenir.** Le fix des verrous est **sur la branche, PAS en prod**. Sur le code prod actuel, `agents-sources` **échoue encore** — l'incident `job-echec:agents-sources` (ouvert 28/10 01:46) se **refermera au premier passage réussi après déploiement**. **Déployer cette branche avant de se fier au cron du dimanche** (sinon le passage du dimanche échouera pareil).

---

## Lot C — La collision de 13:30 (écart 6)

**Déjà en prod (déployé 27/10).** `mail-queue-consommer` **cède** à la sauvegarde (COCKPIT-1 corr. A — lit le verrou `backup-postgres`), ORF-01 purge le pool après timeout (connexion sale), ORF-02 écrit l'alerte disque **sans DDL** (`to_regclass` au lieu de `CREATE/ALTER` → plus de timeout pendant le dump). Le prochain créneau 13:30 (28/10) est le premier vrai test en prod.

**Manquait : `sante-endpoints`.** Il ne cédait pas → sous la charge du dump, ses requêtes dépassaient le timeout (SIGALRM → « another command is already in progress ») et ouvraient le faux incident de 13:37 (journaux 14→27/10).

**Correctif code.** `sante_endpoints` **cède** à la sauvegarde, exactement comme `mail-queue` (même garde `_sauvegarde_en_cours()`). La sonde `/health` (`healthcheck`), elle, continue — seule la sonde MÉTIER lourde (requêtes DB) cède.

**Preuve.** `tests/test_cockpit_corrections_c.py::test_sante_endpoints_cede_a_la_sauvegarde` + rejeu local de la fenêtre 13:30 (verrou de dump tenu → `mail-queue` ET `sante-endpoints` sautent proprement, statut ok, **0 incident ouvert**). Suite cockpit-C : 11 verts.

*(L'alerte disque qui s'écrit pendant le dump : déjà garantie par ORF-02, en prod.)*

---

## Lot D — Le VACUUM à vide (écart 7)

**La cause.** Le 25/10, `pg-maintenance` tournait sous l'**ancien binaire** : (1) `autocommit` posé sur le proxy de pool (no-op) → « VACUUM cannot run inside a transaction » ; (2) l'`except` par table avalait tout → `tables: []` **vert mensonger**. Les deux sont corrigés par **ORF-03** (déjà dans `main`, **déployé le 27/10**) : autocommit posé sur la **vraie** connexion psycopg, et **0 table vacuumée = ROUGE** (jamais de vert par vacuité).

**Vérifié.** Les 6 tables chaudes (`parcels`, `event_log`, `pige_biens`, `pige_faits`, `veilles`, `dvf_mutations`) **existent bien** en base — la liste n'est pas périmée.

**Preuve (passage local réel).** `pg_maintenance` local →
`tables = ['parcels', 'event_log', 'pige_biens', 'pige_faits', 'veilles', 'dvf_mutations']`, `absentes = 0`.
Le prochain dimanche 04:00 en prod rangera donc vraiment.

---

## Lot E — Le disque (écart 1)

**Rotation ramenée à 2 quotidiens + 1 hebdo** (l'historique long vit sur le Mac + le disque externe, pas sur le VPS) :
- `jobs_impl.BACKUP_ROTATION_N` 4 → **2** (le job force `LABUSE_BACKUP_KEEP=2`) ;
- `backup_postgres.sh` : défaut `KEEP` 4 → **2** ; rétention hebdo 3 → **1** (`tail -n +2`).
- Effectif au **prochain déploiement**. Le garde-disque structurel reste le dernier filet.

> Note : le disque est **redescendu de 94 % à 74 %** entre ETAT-2 et maintenant (de la place a été libérée côté dumps) ; l'incident `disque` s'est **auto-résolu** (repassé sous 85 %). La rotation 2+1 évite qu'il remonte.

### Poubelles et vieux runs en base PROD — **LISTE SEULE, aucune suppression (Vic tranche)**

**A. Tables RECONSTRUCTIBLES** (déjà exclues du dump ; rebâties par ingestion/scoring — occupent la base vivante, pas les sauvegardes) :

| Table | Poids | Remarque |
|------|------:|----------|
| `dryrun_cascade_results` | **16 Go** | résultats de dry-run cascade (reconstructible) |
| `p_model_ext_dataset` | 1 557 Mo | dataset d'entraînement |
| `cascade_results` | 1 419 Mo | résultats cascade |
| `p_model_candidates` | 862 Mo | candidats modèle |
| `dryrun_parcel_evaluations` | 325 Mo | évaluations dry-run |
| `score_snapshot_parcelles` | 321 Mo | snapshots de score |
| `p_model_dataset{,_v2,_v2bis}` | 24 ko ×3 | quasi vides |

→ ~**20 Go** vivants ; un `TRUNCATE` les viderait (rebâtis au prochain run). **Décision Vic.**

**B. Vieux runs servis** (servi actuel = **q_v20**) dans `score_labuse` / `score_labuse_runs` :

| Run | Lignes | Poids approx. | Remarque |
|-----|-------:|-------------:|----------|
| `q_v16` | 431 663 | ~1 771 Mo | ancien millésime (parc 431 663, 2 runs derrière) — candidat le plus sûr |
| `q_v18` | 433 229 | ~1 777 Mo | précédent du précédent |
| `q_v20` | 433 229 | ~1 777 Mo | **servi — NE PAS toucher** |

→ purger `q_v16` (et éventuellement `q_v18`) libérerait ~1,7 à 3,5 Go. **Décision Vic.**

**C. Snapshots de mandats anciens** (préfixe `m6_*`) :

| Table | Poids |
|------|------:|
| `m6_a02_backup_plu_dup` | 252 Mo |
| `m6_snapshot_mvt_post2a` | 221 Mo |
| `m6_snapshot_mvt_post2b` | 221 Mo |

→ reliquats du mandat M6. **Décision Vic.**

**D. Schémas `sauvegarde_*`** : **aucun** (0 — déjà nettoyés).

---

## Tests

Sur base locale (venv du repo principal, DSN rôle `openclaw`) : **42 passés** —
`test_cron1_registre.py`, `test_cockpit_corrections_c.py` (dont le nouveau `sante-endpoints cède`), `test_fix_orfevre1_point2.py`, `test_solidite1_lot1.py`, `test_donnees_etat_fix1.py` (4 nouveaux : deploy repose crontab · coût agent libère le verrou · le verrou tenu bloque bien l'ALTER · rotation 2+1).

## Fichiers touchés (branche)

- `deploy/scripts/deploy_vps.sh` — étape 4b : repose+vérifie le crontab (Lot A).
- `deploy/scripts/backup_postgres.sh` — rotation 2 quotidiens + 1 hebdo (Lot E).
- `src/labuse/jobs_impl.py` — `sante_endpoints` cède (Lot C) · `_cout_agent_source_eur` relâche le verrou `ia_log` (Lot B) · `BACKUP_ROTATION_N` 4→2 (Lot E).
- `tests/test_cockpit_corrections_c.py` — test `sante-endpoints cède`.
- `tests/test_donnees_etat_fix1.py` — nouveau.

## Gestes prod réellement effectués (lecture/écriture autorisée lots A/B)

1. Crontab reposé depuis le registre + vérifié (ancien sauvé `/etc/cron.d/labuse.bak-etatfix-20261028-013357`), `cron` redémarré.
2. État orphelin `recap-matin` déplacé (`.orphelin-purge-20261028`).
3. Un passage réel `agents-sources` (coût 0,21 €) — a révélé le bug de verrous, laissé un incident `job-echec:agents-sources` qui se refermera au 1er passage réussi post-déploiement.
Aucune suppression de table/run. Aucun merge. Aucun déploiement de code.

## Ce qui reste à faire (Vic)

1. **Déployer cette branche** (le nouveau `deploy_vps.sh` reposera le crontab tout seul et portera les fixes B/C/E) — **avant le prochain dimanche** pour qu'`agents-sources` ne ré-échoue pas.
2. Trancher la **liste Lot E** (poubelles / vieux runs) — rien n'a été supprimé.

## Pièges / à savoir

- `/healthz/crons` considère un job **récemment lancé mais en échec** comme « frais » (vert) : la tempête de la sentinelle est donc bien éteinte, mais l'échec réel d'`agents-sources` se lit dans les **incidents** (`job-echec:*`), pas dans `/healthz/crons`.
- `ALTER TABLE … ADD COLUMN IF NOT EXISTS` prend un **ACCESS EXCLUSIVE même en no-op** : ne jamais le jouer depuis une session qui tient déjà un verrou de lecture sur la même table (c'est la racine du bug Lot B).
- Génération du crontab : `--tz reunion` (le registre est en UTC).
