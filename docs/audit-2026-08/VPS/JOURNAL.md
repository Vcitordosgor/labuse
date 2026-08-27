# JOURNAL — MANDAT VPS (mise à niveau et go-live)

Session du 27/08/2026 (heure Réunion). Toute commande VPS = une entrée : commande → résultat.
VPS : `ssh labuse-vps` (OVH VPS-3, vps-5563949c, Gravelines). Aucun secret dans ce journal.

---

## V1 — ÉTAT DES LIEUX ET FILET

### V1.1 Inventaire (27/08 ~17h55 Réunion / 13h55 UTC)

Commandes : `hostname/uptime/lsb_release/df/free/python3 --version/psql --version/systemctl is-active/caddy version`, puis inspection `/opt/labuse`, base, `/etc/labuse`, unit systemd, `/var/backups/labuse`, `/etc/cron.d`, Caddyfile, ufw, fuseaux.

| Élément | État constaté |
|---|---|
| OS | Ubuntu 24.04.4 LTS, uptime 49 j, load ~0 |
| Disque | 96 Go, 51 Go utilisés, **45 Go libres** |
| RAM | 12 Go, ~1 Go utilisé, 10 Go dispo, **pas de swap** |
| Python | 3.12.3 |
| PostgreSQL | 18.4 (pgdg), localhost only |
| Caddy | v2.11.4, HTTPS, rideau basic_auth (exemption /stripe/webhook), en-têtes X-Robots/nosniff/Referrer, cache assets, page 401 habillée |
| Services | labuse, caddy, postgresql, fail2ban : tous `active` |
| App | `/opt/labuse/app` = **copie non-git du 23/07** (103 entrées à la racine, mtime 23/07 19:44) ; venv `/opt/labuse/venv` du 21/07 |
| Base `labuse` | **19 Go**, 431 663 parcelles, PAS de table `parcel_cascade` (schéma juillet), run q_v7_defisc |
| Fuseau | Système **Etc/UTC** ; PG (base labuse) : `Indian/Reunion` ✓ |
| systemd unit | uvicorn 2 workers, port 8000 local, `Restart=on-failure`, EnvironmentFile=/etc/labuse/labuse.env, durcissement (ProtectSystem=full etc.) — commentaires disent « Nginx » (réalité : Caddy) |
| Env vars (noms) | LABUSE_DATABASE_URL, LABUSE_ENV, LABUSE_AUTH_PASSWORD, LABUSE_SECRET_KEY, LABUSE_PUBLIC_URL, LABUSE_SERVED_RUN, LABUSE_PILOT_COMMUNE_INSEE/NAME, LABUSE_HTTP_TIMEOUT_S, ANTHROPIC_API_KEY, LABUSE_QA_ALLOWLIST, LABUSE_BACKUP_DIR, LABUSE_BACKUP_KEEP, LABUSE_TRUSTED_PROXIES |
| ufw | 22 LIMIT, 80/443 ALLOW |
| Crons | `/etc/cron.d/labuse-*` ×9 (juillet) : backup 03h00 (via `deploy/scripts/backup_postgres.sh`, dumps 4 Go quotidiens présents 21→27/08), radar lun 02h40, catnat 5-du-mois, sitadel 04h15 + hebdo, dpe mar, ban 5-du-mois, dvf mer, bodacc 04h30, abuse-scan 06h00 — **fuseau système UTC** (les heures cron sont en UTC, pas Réunion) |

Constats V1 (à traiter dans les lots suivants) :
- Le backup quotidien EXISTE déjà (contrairement au « prévus » du contexte). Correction : `deploy/scripts/backup_postgres.sh` VÉRIFIE déjà par `pg_restore --list` dans le job (garde J+2 du 22/07). Il manque : la rétention hebdo (rotation 7 seulement) et les jobs avis-echeance/purge-sessions. Les 7 dumps × 4 Go occupent ~28 Go.
- Crons en UTC (système Etc/UTC) → V6 devra fixer le fuseau des jobs (CRON_TZ ou TZ) en Indian/Reunion.
- Pas de swap : à surveiller pour la restauration 19 Go + uvicorn 5 workers (V4).

### V1.2 Datation de la copie /opt/labuse/app

md5 de fichiers marqueurs VPS vs `git show <commit>:<fichier>` sur l'historique origin/main :
la copie est HÉTÉROGÈNE — la plupart des fichiers matchent `e41b57c8` (22/07 22:50, [LEX-D]),
88 fichiers matchent des commits de la vague M12 du 24/07 (`fd31eb3e`→`840ae6a1`). Copie rsync
en deux temps, aucun état git unique. Non versionnés trouvés (diff arbre VPS vs git) :
`data/ban/adresses-974.csv(.gz)` (retéléchargeable, `labuse ingest-ban --download`),
`src/labuse.egg-info/` et `frontend/dist/` (artefacts). AUCUN .env dans l'app (config en
/etc/labuse, archivée). Décision : l'app entière archivée dans le filet → rollback total possible.

### V1.3 Filet posé et VÉRIFIÉ — `/var/backups/labuse/pre-maj-20260827/`

| Fichier | Taille | Vérif |
|---|---|---|
| `labuse-pre-maj.dump` | 3,8 Go | `pg_dump -Fc` frais (14h00-14h11 UTC), `pg_restore --list` OK (FK, MV listées) |
| `config.tgz` | 6 Ko | /etc/labuse + Caddyfile + labuse.service + cron.d/labuse-* |
| `app-copie-juillet.tgz` | 266 Mo | /opt/labuse/app complet (sans node_modules/__pycache__) |

**V1 CLOS.** Rollback complet possible : base (dump vérifié) + config + app.

---

## V2 — LE CODE PASSE SOUS GIT

- Repo GitHub `Vcitordosgor/labuse` : PUBLIC (aucun credential nécessaire au VPS). ⚠ Branche par
  défaut GitHub = `claude/eager-pascal-cmObd` (bizarre — à corriger par Vic dans les réglages GitHub,
  noté pour le rapport) → clone en EXPLICITANT la branche.
- `feat/vps-golive` poussée (`5c482a8d` : VP-001 garde version pg_dump + deploy_vps.sh + journal).
- Clone : `sudo -u labuse git clone --branch feat/vps-golive https://github.com/Vcitordosgor/labuse.git /opt/labuse/app-new` → OK, HEAD `5c482a8d`.
  RÈGLE DE RÉGIME : le VPS reste sur `feat/vps-golive` jusqu'au merge par Vic ; après merge,
  `git checkout main` — deploy.sh tire la branche COURANTE, il est neutre au choix.
- venv : `python3 -m venv /opt/labuse/venv-new` (Python 3.12.3 système) + `pip install -e app-new` (en cours).
- `deploy/scripts/deploy_vps.sh` écrit (repo) : backup auto AVANT → git pull --ff-only branche
  courante → pip install -e → `labuse init-db` (schéma additif idempotent) → build front si
  frontend/ a bougé → restart + healthcheck /readyz ; rollback documenté en tête de script.
  Pose : `install -m 755 deploy/scripts/deploy_vps.sh /opt/labuse/deploy.sh` (fera partie de la bascule).

## V3 — LA BASE MIGRE (en cours)

- Dump local du jour `labuse-labuse-full-20260827-154408.dump` (6 481 723 320 octets) transféré
  par `rsync --partial --inplace` → `/var/backups/labuse/incoming/`, **md5 IDENTIQUE des deux côtés**
  (`963e26f7e2259e0263e2a1de6e1f5a89`). Transfert ~6 min, aucune coupure.
- `labuse_new` créée (OWNER labuse, PostGIS, `ALTER DATABASE … SET timezone 'Indian/Reunion'`).
- INCIDENT bénin : 1er pg_restore lancé via la session ssh (risque de mort au timeout) → tué et
  relancé PROPREMENT détaché (`setsid`, log /tmp/restore.log) après DROP/CREATE de labuse_new.
  Au passage : un script poussé par heredoc portait `$$` (PID bash) dans le quoting psql → fuseau
  refusé ; script re-poussé par scp, fuseau posé correctement.
