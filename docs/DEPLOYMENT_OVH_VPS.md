# Déploiement LA BUSE — OVH VPS-3 (Ubuntu 24.04) — état réel au 27/08/2026

> **Machine** : OVH **VPS-3** — 6 vCores / 12 Go RAM / 100 Go disque, Ubuntu 24.04 LTS,
> hostname `vps-5563949c`, datacentre Gravelines. Accès : `ssh labuse-vps`.
> **Fuseau SYSTÈME : `Indian/Reunion`** (posé au mandat VPS du 27/08/2026 — les crons
> sont écrits en heure Réunion, plus en UTC).
> **Stack** : PostgreSQL **18.4** (PGDG) + PostGIS (+ `postgis_raster`, `pg_freespacemap`)
> · Python 3.12 · FastAPI/Uvicorn (systemd, 5 workers) · **Caddy v2.11** (reverse proxy,
> HTTPS automatique) · ufw + fail2ban.
> **Principe** : la base et l'app tournent sur la **même** machine ; PostgreSQL n'écoute que
> `localhost` ; l'app n'est jamais exposée en direct (toujours derrière Caddy + HTTPS).
>
> ⚠️ **Nginx et certbot ne sont PLUS utilisés** : le reverse proxy est Caddy depuis la mise à
> niveau du 27/08/2026 (les fichiers `deploy/nginx/` sont un vestige). Le code n'est plus
> synchronisé par rsync depuis le Mac : `/opt/labuse/app` est un **clone git**.

Ce document sert à **reconstruire le VPS depuis zéro** s'il brûle, en cohérence avec l'état
actuel. Pour le geste de déploiement courant, voir `docs/DEPLOY_RUNBOOK.md` ; pour les gestes
du quotidien, voir `docs/EXPLOITATION.md`.

Convention de chemins (tout le reste du document s'y réfère) :

| Rôle | Chemin |
|---|---|
| Code applicatif (**clone git** de `https://github.com/Vcitordosgor/labuse.git`) | `/opt/labuse/app` |
| Environnement Python (venv, Python 3.12) | `/opt/labuse/venv` |
| Script de déploiement (source : `deploy/scripts/deploy_vps.sh`) | `/opt/labuse/deploy.sh` |
| Variables d'environnement (secrets) | `/etc/labuse/labuse.env` (640 root:labuse) |
| Reverse proxy (source : `deploy/Caddyfile.prod`) | `/etc/caddy/Caddyfile` |
| Front React compilé (servi statiquement par Caddy) | `/opt/labuse/app/frontend/dist` |
| Sauvegardes PostgreSQL | `/var/backups/labuse` (hors dossier applicatif) |
| Logs applicatifs | journald (`journalctl -u labuse`) |
| Logs des crons | `/var/log/labuse/*.log` |
| Journal d'accès HTTP (JSON, matière de fail2ban) | `/var/log/caddy/access.log` |
| Utilisateur système dédié | `labuse` (sans shell de login) |

**Doctrine secrets — inchangée et non négociable** : aucun secret dans git, jamais. Les clés
(DB, session, Anthropic, Stripe, Brevo, SMTP) vivent **uniquement** dans
`/etc/labuse/labuse.env`, hors dépôt, en 640 root:labuse. Le dépôt ne contient que des
gabarits (`deploy/env/labuse.env.example`) avec des valeurs `CHANGE_MOI`.

---

## 0. État de transition (à purger — notes du 27/08/2026)

- **`labuse_old`** : l'ancienne base de juillet, conservée le temps de valider le nouveau
  monde. **À supprimer après le 03/09/2026** (`sudo -u postgres psql -c "DROP DATABASE labuse_old;"`).
- **`/opt/labuse/app-juillet` et `/opt/labuse/venv-juillet`** : ancienne copie rsync + venv.
  À purger une fois le nouveau monde stabilisé.
- **Filet pré-migration** : `/var/backups/labuse/pre-maj-20260827/` contient le dump de
  l'ancien monde + `config.tgz` + `app-copie-juillet.tgz`. Ne pas y toucher tant que la
  période de validation court.
- **Branche du clone** : `feat/vps-golive` tant qu'elle n'est pas mergée, puis `main`.
  `deploy.sh` déploie toujours la **branche courante** du clone.

---

## 1. Préparation du VPS Ubuntu 24.04

```bash
# En root
apt update && apt -y upgrade
hostnamectl set-hostname vps-5563949c            # (déjà le cas sur la machine OVH)
timedatectl set-timezone Indian/Reunion          # fuseau Réunion (UTC+4) — SYSTÈME, crons compris

# Pare-feu : SSH en LIMIT (anti brute-force), HTTP + HTTPS ouverts, tout le reste fermé
apt -y install ufw fail2ban
ufw limit 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
ufw status verbose        # attendu : 22 LIMIT, 80 ALLOW, 443 ALLOW

# Utilisateur système dédié (pas de mot de passe, pas de shell interactif)
adduser --system --group --home /opt/labuse --shell /usr/sbin/nologin labuse
mkdir -p /opt/labuse /etc/labuse /var/backups/labuse /var/log/labuse
chown -R labuse:labuse /opt/labuse /var/backups/labuse /var/log/labuse
chmod 750 /etc/labuse /var/backups/labuse
```

Côté poste local, l'alias `ssh labuse-vps` vit dans `~/.ssh/config` (IP du VPS + clé).

## 2. Dépendances système

```bash
apt -y install git curl ca-certificates \
    python3 python3-venv python3-pip \
    postgresql-common gnupg \
    nodejs npm                     # build du front React (npm ci + vite build)

# Caddy v2 (dépôt officiel cloudsmith)
apt -y install debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
  > /etc/apt/sources.list.d/caddy-stable.list
apt update && apt -y install caddy
caddy version                      # v2.11.x en prod au 27/08/2026
```

## 3. PostgreSQL 18 + PostGIS

On installe depuis le dépôt **PGDG** (version de prod : **PostgreSQL 18.4**).

```bash
/usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y   # ajoute le repo PGDG
apt update
apt -y install postgresql-18 postgresql-18-postgis-3 postgresql-client-18

systemctl enable --now postgresql
sudo -u postgres psql -c "SELECT version();"                 # doit afficher PostgreSQL 18.x
```

PostgreSQL n'écoute que `localhost` (défaut Debian/Ubuntu — ne pas l'ouvrir). Le fuseau de la
base est aussi `Indian/Reunion` (posé au mandat ; vérifier : `SHOW timezone;`).

Configuration mémoire : poser l'include du repo dans `conf.d` (il surcharge le
`postgresql.conf` principal sans le remplacer) :

```bash
install -o postgres -g postgres -m 644 \
  /opt/labuse/app/deploy/postgresql/postgresql.vps2.conf \
  /etc/postgresql/18/main/conf.d/zz-labuse.conf
systemctl restart postgresql
```

## 4. Création de la base LA BUSE

```bash
# Rôle applicatif + base + extensions. Choisis un MOT DE PASSE FORT (≠ 'labuse').
sudo -u postgres psql <<'SQL'
CREATE ROLE labuse LOGIN PASSWORD 'CHANGE_MOI_MOT_DE_PASSE_FORT';
CREATE DATABASE labuse OWNER labuse;
\connect labuse
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_raster;
CREATE EXTENSION IF NOT EXISTS pg_freespacemap;
SQL
```

Ordres de grandeur de la base en prod (27/08/2026) : **~19→24 Go**, 431 663 parcelles.
Le run de scoring servi est lu dans **`config/served_run.txt`** du repo (valeur actuelle
`q_v11_m137`) — **la variable d'environnement `LABUSE_SERVED_RUN` n'est plus utilisée**.

## 5. Restauration du dump PostgreSQL

Les dumps quotidiens sont **LEAN** (VP-002) : la **data** des tables reconstructibles
(dryrun/entraînement, ~16 Go, jamais saisies par l'utilisateur) est exclue — le schéma y est,
les données se rebâtissent par ingestion/scoring. La liste des tables exclues est
`_BACKUP_RECONSTRUCTIBLES` dans `src/labuse/cli.py` (GB-054) : script de backup et liste
évoluent **ensemble**.

```bash
# Récupérer le dump le plus récent (depuis le poste local qui tire les backups, ou
# depuis /var/backups/labuse s'il a survécu), puis :
sudo -u labuse bash -c 'set -a; . /etc/labuse/labuse.env; set +a; \
  /opt/labuse/venv/bin/labuse restore-db --file /var/backups/labuse/labuse-labuse-XXXXXXXX-XXXXXX.dump'

# Équivalent bas niveau : pg_restore --clean --no-owner -d labuse <dump>

# Vérification rapide
sudo -u postgres psql -d labuse -c \
  "SELECT count(*) AS parcelles FROM parcels; SELECT postgis_full_version();"
```

> **VP-001** : `labuse backup-db` **refuse** de tourner si le `pg_dump` du PATH n'est pas de
> la même majeure que le serveur (message explicite). Si besoin, `LABUSE_PG_BIN_DIR` pointe le
> dossier des bons binaires (ex. `/usr/lib/postgresql/18/bin`). Même logique pour `restore-db`.

## 6. Installation de l'application (clone git)

```bash
# Cloner le code — branche de prod : main (ou feat/vps-golive tant que non mergée)
sudo -u labuse git clone https://github.com/Vcitordosgor/labuse.git /opt/labuse/app
sudo -u labuse git -C /opt/labuse/app checkout main    # ou feat/vps-golive

# venv + installation ÉDITABLE (l'app lit config/, data/, web/ depuis l'arbre du repo)
# ⚠ M26-A : l'extra [ai] est OBLIGATOIRE — sans lui, l'interpréteur du Copilote tombe
# en run_failed « ia_indisponible » en prod (le paquet anthropic vit dans cet extra).
sudo -u labuse python3 -m venv /opt/labuse/venv
sudo -u labuse /opt/labuse/venv/bin/pip install --upgrade pip
sudo -u labuse /opt/labuse/venv/bin/pip install -e "/opt/labuse/app[ai]"

# Sanity : la commande 'labuse' répond
sudo -u labuse /opt/labuse/venv/bin/labuse --help | head

# Poser le script de déploiement courant
install -o root -g root -m 755 /opt/labuse/app/deploy/scripts/deploy_vps.sh /opt/labuse/deploy.sh
```

## 7. Variables d'environnement — `/etc/labuse/labuse.env`

Copier le gabarit du repo puis le remplir (secrets **jamais** dans git) :

```bash
install -o root -g labuse -m 640 /opt/labuse/app/deploy/env/labuse.env.example /etc/labuse/labuse.env
${EDITOR:-nano} /etc/labuse/labuse.env
```

> ⚠ **RÈGLE D'ÉCRITURE** : les crons **sourcent ce fichier en shell** (`. /etc/labuse/labuse.env`).
> Toute valeur contenant des espaces ou des chevrons DOIT être **entre guillemets** :
> `LABUSE_MAIL_FROM="LABUSE <contact@labuse.immo>"`. Sans guillemets, tous les crons cassent.

Contenu réel (les valeurs sont sur le VPS, jamais ici) :

| Bloc | Variables | Note |
|---|---|---|
| Cœur | `LABUSE_DATABASE_URL`, `LABUSE_ENV=production`, `LABUSE_SECRET_KEY` (openssl rand -hex 32), `LABUSE_AUTH_PASSWORD`, `LABUSE_PUBLIC_URL` / `LABUSE_PUBLIC_BASE_URL=https://app.labuse.immo` | fail-closed : sans mot de passe, routes métier en 503 |
| Login pilote | `LABUSE_LOGIN_PILOTE_ACTIF=0` | **AC-020 : le login pilote partagé est MORT** — l'auth passe par les comptes nominatifs |
| IA | `ANTHROPIC_API_KEY`, `LABUSE_AI_PROVIDER=anthropic` | jamais dans un log ; retrait de la clé = retour au mode règles |
| Stripe (**placeholders — Vic pose les clés LIVE**) | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_RESTRICTED_KEY`, `STRIPE_PRICE_*` | voir §12 (webhook) |
| Brevo | `BREVO_API_KEY`, `LABUSE_BREVO_TPL_*` (8 templates transactionnels) | e-mails transactionnels (digest, invitations…) |
| SMTP | `LABUSE_SMTP_HOST/PORT/USER/PASSWORD`, `LABUSE_MAIL_FROM` | relais Brevo ; `MAIL_FROM` **entre guillemets** (cf. règle) |

Appliquer le schéma (idempotent) avant le premier démarrage :

```bash
sudo -u labuse bash -c 'set -a; . /etc/labuse/labuse.env; set +a; \
  /opt/labuse/venv/bin/labuse init-db && /opt/labuse/venv/bin/labuse doctor --json | head'
```

## 8. Build du front React

Caddy sert le front **statiquement** depuis `/opt/labuse/app/frontend/dist` :

```bash
cd /opt/labuse/app/frontend
sudo -u labuse npm ci
sudo -u labuse npx vite build --base=/
```

(`deploy.sh` refait ce build automatiquement quand `frontend/` a bougé.)

## 9. Lancement via systemd

Unité fournie : `deploy/systemd/labuse.service` — Uvicorn **5 workers** sur
`127.0.0.1:8000`, `Restart=always`, `MemoryMax=6G` (garde-fou : systemd redémarre l'app
plutôt que de laisser l'OOM killer toucher PostgreSQL),
`EnvironmentFile=/etc/labuse/labuse.env`.

```bash
install -o root -g root -m 644 /opt/labuse/app/deploy/systemd/labuse.service \
  /etc/systemd/system/labuse.service
systemctl daemon-reload
systemctl enable --now labuse
systemctl status labuse --no-pager
journalctl -u labuse -n 30 --no-pager           # logs via journald (jamais de nohup)

# L'app écoute en LOCAL uniquement (127.0.0.1:8000) — vérif :
curl -s http://127.0.0.1:8000/healthz           # {"status":"ok"}
```

## 10. Reverse proxy — Caddy (HTTPS automatique)

Source dans le repo : **`deploy/Caddyfile.prod`** (aucun secret dedans). Caddy obtient et
renouvelle le certificat Let's Encrypt **tout seul** — pas de certbot, pas de cron de
renouvellement.

```bash
install -o root -g root -m 644 /opt/labuse/app/deploy/Caddyfile.prod /etc/caddy/Caddyfile
# Le domaine servi est injecté par variable d'env (fichier 600, pas un secret mais isolé) :
printf 'LABUSE_DOMAIN=app.labuse.immo\n' > /etc/caddy/labuse.env
chmod 600 /etc/caddy/labuse.env
# Selon la pose, l'unité caddy lit ce fichier (drop-in systemd EnvironmentFile=/etc/caddy/labuse.env).

caddy validate --config /etc/caddy/Caddyfile
systemctl enable --now caddy
systemctl reload caddy
```

Ce que fait ce Caddyfile (voir ses commentaires pour le détail) :

- **HTTPS auto** + redirection HTTP→HTTPS ; **HSTS** 6 mois (sous-domaine seul) ;
- **le rideau basic auth est TOMBÉ au go-live** (mandat VPS V5) : la porte est l'auth
  **applicative** (comptes argon2id + sessions en base + **2FA TOTP admin**, §11) ;
- **journal d'accès JSON** → `/var/log/caddy/access.log`, matière du jail fail2ban
  `labuse-login` (§ ci-dessous) et des autopsies ;
- front React servi statiquement à la racine (`frontend/dist`), assets `/assets/*` immuables,
  `index.html` en `no-cache` ; `/app` et `/app/*` jamais exposés (301 → `/`) ; navigation `/`
  sans cookie de session → 302 `/login` ; tout le reste (API, tuiles, PDF, webhook Stripe) →
  `127.0.0.1:8000`.

**fail2ban** (2e couche — l'app verrouille déjà le compte après 5 échecs) :

```bash
install -m 644 /opt/labuse/app/deploy/fail2ban/labuse-login.conf /etc/fail2ban/filter.d/labuse-login.conf
install -m 644 /opt/labuse/app/deploy/fail2ban/jail-labuse.conf  /etc/fail2ban/jail.d/labuse.conf
systemctl reload fail2ban
fail2ban-client status labuse-login     # jail actif, lit /var/log/caddy/access.log
```

Pré-requis DNS : `app.labuse.immo` (A/AAAA) pointe sur l'IP du VPS **avant** de démarrer
Caddy (sinon l'émission du certificat échoue et retente).

## 11. Comptes, 2FA admin (AC-025) et création d'un admin

- Le login pilote partagé est **mort** (`LABUSE_LOGIN_PILOTE_ACTIF=0`, AC-020). Chaque
  utilisateur a un compte nominatif.
- **Tout compte de rôle admin passe par `/login/2fa`** (TOTP) : au **premier login**,
  enrôlement par QR code (application d'authentification) + **8 codes de secours affichés
  une seule fois** (à ranger dans le gestionnaire de mots de passe). Tables `totp_2fa` /
  `totp_secours` ; anti-rejeu ; **5 tentatives max par défi de 5 minutes**.
- Créer un admin (**geste réservé à Vic**) — la sortie est un **lien d'invitation** pour
  poser le mot de passe :

```bash
sudo -u labuse bash -c 'set -a; . /etc/labuse/labuse.env; set +a; \
  /opt/labuse/venv/bin/labuse creer-admin EMAIL --nom "Prénom Nom"'
```

## 12. Stripe — webhook de production (geste Vic, dashboard)

Dans le dashboard Stripe (**Développeurs → Webhooks**), créer l'endpoint **LIVE**
`https://app.labuse.immo/stripe/webhook` avec les événements :
`checkout.session.completed`, `customer.subscription.updated`,
`customer.subscription.deleted`, `invoice.payment_failed`. Copier le secret `whsec_…` dans
`STRIPE_WEBHOOK_SECRET` de `/etc/labuse/labuse.env`, puis `sudo systemctl restart labuse`.
(Un webhook non signé est refusé par l'app.)

## 13. Les crons — 13 fichiers `/etc/cron.d/labuse-*`, en HEURE RÉUNION

Le VPS est en fuseau `Indian/Reunion` : **les horaires des crons sont des heures locales
Réunion** (fini les horaires UTC des anciens docs). Chaque ligne est sous
`flock -n -E 200` (code 200 = tour sauté car le précédent tourne encore — journalisé, jamais
confondu avec un échec). Chaque job écrit son log dans `/var/log/labuse/`.

```bash
install -d -o labuse -g labuse /var/log/labuse
cd /opt/labuse/app
for c in radar sitadel bodacc notifications ban sessions avis-echeance dvf dpe backup abuse fraicheur; do
  install -o root -g root -m 644 deploy/cron.d/$c /etc/cron.d/labuse-$c
done
systemctl reload cron
install -o root -g root -m 644 deploy/logrotate.d/labuse /etc/logrotate.d/labuse
```

Le crontab utilisateur (`crontab -u labuse`) reste **VIDE** — un seul mécanisme (M98).

| Cron | Quand (heure Réunion) | Ce qu'il fait | Log |
|---|---|---|---|
| `labuse-radar` | lundi 06:00 | `radar-sources` (sondes amont, zéro téléchargement) | `radar.log` |
| `labuse-sitadel` | quotidien 06:15 (+ dérivés hebdo lundi 07:45) | permis SDES delta + dérivés | `sitadel_refresh.log` |
| `labuse-bodacc` | quotidien 06:30 | procédures collectives SIREN + dérivés | `bodacc.log` |
| `labuse-notifications` | quotidien 07:00 | `evaluer-suivis` → `evaluer-veilles` → `notifier-fraicheur` → `purge-notifications` → **digest e-mail** | `notifications.log` |
| `labuse-ban` | le 5 du mois, 07:30 | BAN 974 (remplacement complet idempotent) | `ban_refresh.log` |
| `labuse-sessions` | quotidien 08:00 | `purge-sessions` (sessions expirées) | `purge_sessions.log` |
| `labuse-backup` (2e ligne) | dimanche 08:00 | maintenance `VACUUM ANALYZE` (`db_maintenance.sh`) | `maintenance.log` |
| `labuse-avis-echeance` | quotidien 08:30 | avis d'échéance loi Chatel | `avis_echeance.log` |
| `labuse-catnat` | le 5 du mois, 09:00 | arrêtés CatNat | `catnat.log` |
| `labuse-dvf` | mercredi 09:00 | DVF (Last-Modified ; reload si livraison Etalab) | `dvf.log` |
| `labuse-dpe` | mardi 09:20 | DPE ADEME 24 communes + dérivés | `dpe.log` |
| `labuse-backup` | quotidien 09:30 | `backup_postgres.sh` (dump lean + vérif + rotation) | `backup.log` |
| `labuse-abuse` | quotidien 10:00 | `abuse-scan` (patterns de scraping, aucun blocage auto) | `abuse_scan.log` |
| `labuse-fraicheur` | quotidien 10:30 | `check-fraicheur` (sentinelle : code 1 si une source dépasse 2× sa cadence) | `check_fraicheur.log` |

Ordonnancement : les ingestions passent **avant** les notifications de 07:00 (le digest parle
de la nuit), le backup de 09:30 passe **après** toutes les écritures.

**Vérifier que le Train tourne** (le jour J et à chaque revue) :

```bash
curl -sS https://app.labuse.immo/healthz/crons | python3 -m json.tool   # retards = [] attendu
sudo -u labuse bash -c 'set -a; . /etc/labuse/labuse.env; set +a; /opt/labuse/venv/bin/labuse check-fraicheur'
```

## 14. Sauvegardes et restauration

- **Quotidien 09:30 Réunion** : `deploy/scripts/backup_postgres.sh` → `pg_dump -Fc` **LEAN**
  (VP-002, cf. §5), **vérifié par `pg_restore --list` dans le job** (un dump vide ou
  illisible est supprimé et le job échoue bruyamment).
- **Rotation** : 7 dumps quotidiens + **4 hebdomadaires** (les dumps du dimanche sont
  hardlinkés avec le préfixe `hebdo-`), dans `/var/backups/labuse`.
- **Avant chaque déploiement** : `deploy.sh` refait un dump automatiquement (étape 0).
- **Restauration** : `labuse restore-db --file <dump>` (ou
  `pg_restore --clean --no-owner -d labuse <dump>`).
- **VP-001** : refus si la majeure de `pg_dump`/`pg_restore` ne colle pas au serveur ;
  corriger via `LABUSE_PG_BIN_DIR`.

## 15. Tests de santé après (re)construction

```bash
# En local sur le VPS
curl -s http://127.0.0.1:8000/healthz
curl -s http://127.0.0.1:8000/readyz            # "ready": true = schéma + données critiques OK

# Depuis l'extérieur (HTTPS public, certificat Caddy)
curl -sS https://app.labuse.immo/healthz
curl -sS https://app.labuse.immo/readyz
curl -sS https://app.labuse.immo/healthz/crons | python3 -m json.tool

# Smoke test complet fourni
sudo -u labuse bash -c 'set -a; . /etc/labuse/labuse.env; set +a; \
  /opt/labuse/app/deploy/scripts/smoke_test.sh'
```

## 16. Rollback

Voir `docs/DEPLOY_RUNBOOK.md` (le rollback est aussi documenté **en tête de
`/opt/labuse/deploy.sh`**, avec le commit d'avant affiché au début de chaque run). En bref :
`git reset --hard <commit_avant>` + `pip install -e` + restart ; la base se restaure depuis le
dump pris automatiquement à l'étape 0 du déploiement.
