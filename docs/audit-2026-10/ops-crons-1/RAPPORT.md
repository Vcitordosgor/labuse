# OPS-CRONS-1 — Sauvegarde & tâches planifiées en prod

Branche `fix/ops-crons-1`. Diagnostic **lecture seule** du VPS (`labuse-vps`, 51.255.163.56,
fuseau `Indian/Reunion +04`). Source du mandat : `docs/audit-2026-10/CHASSE-APP/CHASSE-APP-20-10.md`
(parties A et B). Relevé le 20/10/2026 ~12:00 Réunion.

## TL;DR — un seul défaut, pas six

**Les six crons signalés en défaut par `/healthz/crons` tournent tous, chaque nuit, `code 0`.**
Ce n'est pas la sauvegarde ni les tâches qui sont cassées : c'est **la trace** que lit
`/healthz/crons`. L'API lit les fichiers d'état des jobs dans un dossier **gelé**
(`/opt/labuse/app/.local/state/jobs/`, figé au 30/08 et 22/09), alors que les crons écrivent
leur état **frais** ailleurs (`/home/labuse/.local/state/jobs/`). **Un seul geste** répare les six.

Le correctif de code existe déjà et est **mergé dans main** (`54b3e58e`, fix/crons-prod) mais
**n'est pas déployé** : le code prod ne contient pas le validateur `_dossiers_jobs_absolus`
(`grep -c` = 0) et l'API n'a pas redémarré depuis le **14/10 17:02** (avant le merge).

---

## Cause racine (prouvée)

`config.jobs_state_dir` a pour défaut la valeur **relative** `.local/state/jobs`. Elle se résout
contre le **CWD de chaque process** :

| Process | Qui | CWD | Dossier d'état effectif | Fraîcheur |
|---|---|---|---|---|
| **cron** | `labuse` | `/home/labuse` | `/home/labuse/.local/state/jobs/` | **FRAIS** (écrit chaque nuit) |
| **API** | `labuse` (systemd `WorkingDirectory=/opt/labuse/app`) | `/opt/labuse/app` | `/opt/labuse/app/.local/state/jobs/` | **GELÉ** (snapshot d'un ancien déploiement) |

`/opt/labuse/app/.local/state/jobs/` est un snapshot livré avec le dépôt : il ne reçoit plus
que les runs lancés *depuis* `/opt/labuse/app` (runs manuels, bouton « Lancer maintenant » de
l'API). C'est pourquoi `ingest-dvf.json` (run manuel no-op DVF-DEGEL-1 du 20/10 01:16) et
`fiche-commune-cache.json` (11/10) y sont frais, mais pas les crons nocturnes.

**Pourquoi les LOGS semblent frais mais pas l'ÉTAT ?** Les logs atterrissent dans
`/var/log/labuse/jobs/` (absolu, cohérent pour tout le monde), tandis que l'état reste sur un
chemin relatif divergent. Seul l'état d'un job (le JSON) alimente `/healthz/crons`.

### Preuves

```
# État que l'API LIT (gelé) — /opt/labuse/app/.local/state/jobs/backup-postgres.json
"debut": "2026-08-30T22:00:50Z", "dump": "labuse-labuse-20260830T220050Z.sql.gz", 31480 Mo

# État que le cron ÉCRIT (frais) — /home/labuse/.local/state/jobs/backup-postgres.json
"debut": "2026-10-19T09:30:04Z", "dump": "labuse-labuse-20261019-133004.dump", 6921 Mo, ok

# Journal — /var/log/labuse/jobs/backup-postgres.log : un run/jour jusqu'au 2026-10-19 09:30Z (code 0)
# Dumps réels — /var/backups/labuse/labuse-labuse-20261019-133004.dump (6,9 Go), 16→19/10 présents
```

`/healthz/crons` → `"ok": false`, avec `backup-postgres en_retard dernier_ok 2026-08-30 … 50,4 j`.

---

## Partie 1 — La sauvegarde

### 1.a La trace ment, pas la sauvegarde

**La sauvegarde fonctionne.** Preuves : `backup-postgres.log` = un run/jour `code 0` jusqu'au
19/10 09:30Z ; dumps présents (16/10→19/10, 6,9 Go chacun) ; état frais en `/home` (19/10, ok).
Le « 30/08 · 50 jours » de `/healthz/crons` vient du fichier d'état **gelé** décrit ci-dessus.

> Note : le run quotidien du **20/10** se déclenche à **13:30 Réunion** ; au moment du relevé
> (~12:00) il n'avait pas encore tourné — c'est normal, pas un retard.

**Geste (corrige la trace, ne touche pas à la sauvegarde) :** voir « Geste unique » ci-dessous.

### 1.b `restore-test` — aucune restauration d'essai n'a jamais été jouée

`restore-test` est **gelé** dans le crontab : `# GELÉ (Phase 8 Stéphanie) 0 1 1 * * … jobs run restore-test`
(mensuel, 1er du mois, 05:00). **Aucun fichier d'état `restore-test.json` n'existe** — ni en
`/home`, ni en `/opt`. Donc : **le job de restauration n'a jamais tourné en prod.** Seule une
vérification *structurelle* (`pg_restore --list`) a été exercée, côté Mac, sur les copies hors-VPS
(ex. 1737 objets sur la copie 20261019). Une restauration réelle dans une base, elle, n'a jamais
été faite.

**Comment en jouer une sans charger la prod (proposition, à NE PAS lancer sans go) :**
le job restaure *déjà* le dernier dump dans une **base jetable** puis `DROP` (`besoin_db=False`).
Mais exécuté sur le VPS, il mobilise l'I/O et le Postgres de production pendant ~20 min.
Pour un essai **à charge nulle côté prod**, le rejouer **sur le Mac**, contre le dump
hors-VPS déjà posé sur le disque externe (`/Volumes/MUSIQUE-VIDEO/LABUSE-SAUVEGARDES`) :
`createdb labuse_restore_test && pg_restore -d labuse_restore_test <dump> && <quelques requêtes de contrôle> && dropdb labuse_restore_test`.
Zéro contact avec la base ni le serveur de prod. (À scripter proprement si go ; ici on décrit seulement.)

### 1.c Les dumps quittent-ils le VPS ? (réponse seule)

**Oui.** Un agent sur le Mac (`backup_offsite_disque.sh`, `StartOnMount` + dimanche 14:30) tire le
dernier dump par `ssh labuse-vps` vers le **disque externe** `/Volumes/MUSIQUE-VIDEO/LABUSE-SAUVEGARDES`,
vérifie le `sha256` (calculé sur le VPS) et `pg_restore --list` avant de ranger. Le marqueur VPS
`/var/backups/labuse/.copie-externe.json` atteste la **dernière copie : 19/10/2026 12:33Z**
(`labuse-labuse-20261019-133004.dump`, 6921 Mo, sha256 vérifié, disque `MUSIQUE-VIDEO`).

Réserves (constat, pas une action) : la copie dépend du **disque branché** (StartOnMount) et du
droit **Accès complet au disque** de launchd (caveat TCC connu). Le job VPS `backup-offsite` a été
retiré du registre au profit de ce modèle « tirage Mac ». Code vigie « branche le disque »
(seuil 10 j) mergé mais **pas déployé** (API 14/10) → prod ne l'affiche pas encore.

---

## Partie 2 — Les quatre tâches « à l'arrêt » : toutes des traces fausses

| Tâche | `/healthz/crons` dit | **Réalité (journal `code 0`)** | État frais en `/home` | Pourquoi la trace ment |
|---|---|---|---|---|
| `filtres-sources` | **jamais lancée** | quotidien, dernier **20/10 03:05Z** | ✓ 20/10 07:05 | `filtres-sources.json` **absent** du dossier gelé `/opt` → `jamais_vu` |
| `sync-gpu` | **jamais lancée** | **mensuel (15)**, dernier **15/10 00:00Z** | ✓ 15/10 04:00 | `sync-gpu.json` **absent** du dossier gelé `/opt` → `jamais_vu` |
| `sonde-sources` | retard **27 j** | quotidien, dernier **20/10 03:00Z** | ✓ 20/10 07:03 | `/opt` figé au **22/09** → âge 27,6 j |
| `coherence-robinets` | retard **27 j** | quotidien, dernier **20/10 03:25Z** | ✓ 20/10 07:43 | `/opt` figé au **22/09** → âge 27,6 j |

- **Aucune ligne absente du crontab** : les quatre sont bien présentes et non commentées.
- **Aucune n'est gelée.**
- **Aucune erreur silencieuse** : tous les journaux finissent `code 0`.
- `sync-gpu` est **mensuelle (le 15)**, pas quotidienne : « jamais lancée » est faux, elle a
  tourné le 15/10 ; prochaine le 15/11. (Sa course de 2 s = no-op, aucun nouveau PLU détecté.)

**Hors périmètre trace (à ne pas confondre) :** le constat du mandat « `gpu_plu` ingestion vide, les
PLU ne sont jamais rafraîchis » est une question de **donnée**, pas de cron : `sync-gpu` *détecte*
un changement de PLU et pose un événement de veille ; il n'*ingère* pas le PLU. Le job tourne ;
l'absence de rafraîchissement PLU relève du dossier fraîcheur/déploiement q_v19, pas d'ici.

---

## Geste unique (répare les six d'un coup) — à faire AVEC go

La divergence est sur le **chemin d'état** lu par l'API. Deux voies, même résultat :

1. **Recommandé / durable** — déployer `main` (qui contient déjà `_dossiers_jobs_absolus`,
   ancrage `$HOME`) puis `systemctl restart labuse`. *Mais* `deploy_app.sh` est interdit par ce
   mandat → geste de Vic hors de cette branche.

2. **Pont sans déploiement (dans le périmètre)** — poser dans `/etc/labuse/labuse.env` le chemin
   **absolu** où les crons écrivent déjà, puis redémarrer l'API :
   ```
   LABUSE_JOBS_STATE_DIR=/home/labuse/.local/state/jobs
   LABUSE_JOBS_LOG_DIR=/var/log/labuse/jobs
   LABUSE_LOCK_DIR=/run/lock
   ```
   `sudo systemctl restart labuse`. `env_prefix=LABUSE_` → le code *actuel* lit ces chemins ; les
   crons sourcent le même `labuse.env` → convergence immédiate. Chemin absolu = **inchangé** par le
   futur validateur, donc compatible avec le déploiement (1). Répare aussi le visualiseur de logs admin.

**Vérification attendue après geste :** `/healthz/crons` → `"ok": true`, `backup-postgres` daté du
jour (ou 19/10 jusqu'au run de 13:30), et `sonde-sources` / `filtres-sources` / `coherence-robinets` /
`sync-gpu` en `ok`. **On ne touche ni à la sauvegarde ni aux jobs** — uniquement au chemin de lecture.

## Détail annexe (hors scope, inerte)

Deux fichiers de sauvegarde traînent dans `/etc/cron.d/` : `labuse.bak-dvfdegel-20261020` et
`labuse.bak-offsite-20261014-162648`. Leurs noms contenant un point, **cron les ignore** (règle
`/etc/cron.d`) → inoffensifs. Nettoyables un jour, mais pas un défaut.
