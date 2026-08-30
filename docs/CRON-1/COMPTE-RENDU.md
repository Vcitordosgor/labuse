# CRON-1 — Exploitation planifiée de LABUSE

Branche `feat/outils-1`. Tout développé et testé EN LOCAL (dry-run) ; rien posé sur le VPS (la pose passe
par `deploy.sh` au déploiement groupé). Golden non touché (`config/served_run.txt` inchangé = `q_v11_m137` ;
K5 n'écrit qu'un candidat, jamais le servi). Fuseau : crontab en heure SERVEUR UTC, heure Réunion (UTC+4)
en commentaire par ligne ; `deploy.sh` refuse la pose si `timedatectl` ≠ UTC.

## Fondation — bâtie et TESTÉE en local

**K1 — le wrapper commun** `scripts/jobs/run-job.sh` : verrou par job (flock sur Linux, repli `mkdir`
atomique sur macOS de dev), log daté, délègue à `labuse jobs exec`. **Double lancement REFUSÉ prouvé**
(exit 200, « déjà en cours — lancement refusé »). Timeout par job (SIGALRM), fichier d'état JSON (début,
fin, statut, durée, compteurs métier, erreur), alerte mail admin à l'échec, **règle dry-run globale**
(sans SMTP, un job qui enverrait un mail calcule/logue, marque « dry-run », n'envoie rien).

**K2 — la CLI** `labuse jobs list / run / status / exec` + le **registre** `src/labuse/jobs.py` (13 jobs :
nom, description, cron UTC, heure Réunion, cadence, timeout, callable). Le cron ne fait QUE `labuse jobs
run <nom>` → `run-job.sh` → un seul verrou, partagé par le cron ET le bouton admin. *(Note : `python -m
labuse.cli` ne voit pas les commandes tardives — garde `__main__` en milieu de fichier, pré-existante ;
le binaire installé `labuse` charge tout. Le wrapper utilise le binaire.)*

**K3 — quotidiens** (tous exécutés en local, état+log écrits) : `backup-postgres` (pg_dump|gzip, rotation
14 j, taille min ; **dump 31 Go produit, statut ok**), `sources-fraicheur` (**67 sources → à_jour/en_retard/
en_panne persistés** en base, badges), `radar-cycle` (cycle de vie, ne fetch rien), `radar-digests`
(idempotent event_log, **dry-run capable**), `healthcheck` (sonde /health + **disque 70,1 %**, 2 échecs →
alerte).

**K9 — robustesse** : `restore-test` (**échec propre prouvé sur dump corrompu** : « 0 tables », base jetable
`labuse_restore_test` bien DROPée ; le succès sur dump valide = 31 Go trop lent en local, tourne sur le VPS),
**alerte disque** (SEUIL_DISQUE_PCT=85, une par jour via l'état), **témoin externe (dead man's switch)
prouvé** (`LABUSE_PING_<NOM>` → ping tenté/logué ; absent → silencieux).

**K8 — crontab versionné** `deploy/cron.d-labuse` : 13 lignes en UTC, **heure Réunion en commentaire par
ligne, relu ligne à ligne (chaque UTC+4 = l'heure annoncée)**, MAILTO, zéro logique (juste `labuse jobs
run`). `deploy.sh` : garde `timedatectl` (refus si ≠ UTC, message d'adaptation) + pose cron + logrotate.
`deploy/logrotate.d/labuse-jobs` : 30 j.

**K6 — Brevo/SMTP** : `labuse mail-test` (existant, fonctionne) ; règle dry-run dans `mail.send_email`
(`no-config` sans SMTP) ; doc pas-à-pas EXPLOITATION §14.

**K5 — golden** : `labuse golden candidat` **testé** (lecture seule : « le run récent EST le servi — pas de
candidat »), `labuse golden promote <run>` = le geste (valide le run, réécrit `served_run.txt`) — **non
exécuté** (préserve le golden). Aucune bascule automatique.

**K7 — backend** `/admin/cron` (+ `/{nom}/log`, `/{nom}/run`) : **testé** (TestClient 200, 13 jobs ; run
détaché via la CLI = même verrou).

## Vérif finale

| Contrôle | Résultat |
|---|---|
| `pytest tests/` | **1999 passed, 43 skipped, 0 failed** |
| tsc / build / vitest | inchangés (aucun code frontend modifié dans ce mandat) |
| Golden | **intact** (`served_run.txt` = q_v11_m137, aucun fichier scoring) |
| Verrou double lancement | **refusé (exit 200)** — prouvé |
| radar-digests | idempotent (dedup event_log) + dry-run — prouvé |
| sources-fraicheur | 67 statuts écrits en base |
| restore-test | échec propre sur dump corrompu + base jetable nettoyée — prouvé |
| dead-man ping | tenté quand la var est posée, silencieux sinon — prouvé |
| crontab | relu : chaque heure UTC = heure Réunion annoncée |

## Ce qui RESTE (transparence — non livré/non testé dans ce mandat)

- **K7 — la PAGE admin `/admin/cron` (frontend)** n'est PAS construite : seul le backend l'est. Le
  branchement des badges `sources-fraicheur` sur la page des 59 sources (front) reste à faire.
- **K4 — ingest-sirene/sitadel/dpe/sync-gpu** : jobs déclarés + câblés aux commandes existantes, mais NON
  testés en direct (données externes lourdes). La génération d'événements de veille foncière est câblée à
  `evaluer_toutes` (existant).
- **K5** : le run candidat calculé automatiquement en fin d'ingestion scoring + le rapport mail de
  comparaison ne sont qu'esquissés (`golden candidat` compare ; le déclenchement post-ingestion reste à
  brancher). La bascule (`promote`) est prête mais non exécutée.
- **restore-test** succès (dump valide) : non joué en local (31 Go) ; échec prouvé.
- **backup-pull-mac** : `deploy/scripts/pull_backups.sh` existe déjà (réutilisé, doc EXPLOITATION §14).

**Provenance** — lectures Postgres ; écritures = 2 colonnes idempotentes `data_sources.fraicheur_statut`
(migration in-place) + les fichiers d'état sous `.local/` (gitignoré). Golden non touché. Suite pytest verte.
