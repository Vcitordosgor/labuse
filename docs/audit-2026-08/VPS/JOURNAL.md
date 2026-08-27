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
- Le backup quotidien EXISTE déjà (contrairement au « prévus » du contexte) mais n'est PAS vérifié par pg_restore --list dans le job, et les 7 dumps × 4 Go occupent ~28 Go.
- Crons en UTC (système Etc/UTC) → V6 devra fixer le fuseau des jobs (CRON_TZ ou TZ) en Indian/Reunion.
- Pas de swap : à surveiller pour la restauration 19 Go + uvicorn 5 workers (V4).
