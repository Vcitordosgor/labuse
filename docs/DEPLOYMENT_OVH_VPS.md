# Déploiement LA BUSE — OVH VPS-2 (Ubuntu 24.04)

> **Cible** : OVH VPS-2 — 4 vCores / 8 Go RAM / 75 Go SSD, Ubuntu 24.04 LTS.
> **Stack** : PostgreSQL 16 + PostGIS 3.4 · Python 3.12 · FastAPI/Uvicorn · Nginx · Let's Encrypt.
> **Principe** : la base et l'app tournent sur la **même** machine ; PostgreSQL n'écoute que
> `localhost` ; l'app n'est jamais exposée en direct (toujours derrière Nginx + HTTPS).
>
> ⚠️ Ce document **prépare** le déploiement. Rien n'est appliqué automatiquement — chaque commande
> est à lancer **manuellement** sur le VPS, dans l'ordre, après avoir lu la section correspondante.

Convention de chemins utilisée partout ci-dessous :

| Rôle | Chemin |
|---|---|
| Code applicatif (clone git) | `/opt/labuse/app` |
| Environnement Python (venv) | `/opt/labuse/venv` |
| Variables d'environnement (secrets) | `/etc/labuse/labuse.env` |
| Sauvegardes PostgreSQL | `/var/backups/labuse` (hors dossier applicatif) |
| Utilisateur système dédié | `labuse` (sans shell de login) |

---

## 0. Pré-requis

- Un VPS-2 OVH fraîchement installé en **Ubuntu 24.04**, accès `root` (ou un sudoer).
- Le **dump PostgreSQL** de la base actuelle, produit sur la machine source avec
  `labuse backup-db` (format `pg_dump -Fc`, ~240 Mo). À transférer par `scp` (étape 5).
- Les DNS de `labuse.immo` gérés (on y touche à l'étape 9 / go-live).

---

## 1. Préparation du VPS Ubuntu 24.04

```bash
# En root
apt update && apt -y upgrade
timedatectl set-timezone Indian/Reunion        # fuseau Réunion (UTC+4)

# Pare-feu : on n'ouvre que SSH + HTTP + HTTPS (PostgreSQL reste fermé au monde)
apt -y install ufw
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Utilisateur système dédié (pas de mot de passe, pas de shell interactif)
adduser --system --group --home /opt/labuse --shell /usr/sbin/nologin labuse
mkdir -p /opt/labuse /etc/labuse /var/backups/labuse
chown -R labuse:labuse /opt/labuse /var/backups/labuse
chmod 750 /etc/labuse /var/backups/labuse
```

## 2. Dépendances système

```bash
apt -y install git curl ca-certificates \
    python3 python3-venv python3-pip \
    postgresql-common gnupg \
    nginx \
    certbot python3-certbot-nginx

# (Optionnel — uniquement si une roue Python devait se compiler depuis les sources :
#  les wheels de shapely/pyproj/psycopg[binary] embarquent déjà GEOS/PROJ/libpq.)
# apt -y install build-essential libgeos-dev libproj-dev
```

## 3. PostgreSQL 16 + PostGIS 3.4

On installe depuis le dépôt **PGDG** pour garantir exactement PostgreSQL 16 + PostGIS 3.4
(versions de la base source : 16.13 / 3.4.2).

```bash
# Dépôt officiel PostgreSQL (PGDG)
/usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y   # ajoute le repo PGDG
apt update
apt -y install postgresql-16 postgresql-16-postgis-3 postgresql-client-16

systemctl enable --now postgresql
sudo -u postgres psql -c "SELECT version();"                 # doit afficher PostgreSQL 16.x
```

### 3bis. Configuration PostgreSQL pour 8 Go (NE PAS sauter)

Le fichier `deploy/postgresql/postgresql.vps2.conf` du repo est un **include** prêt à poser
(voir aussi la section 2 du présent pack). Copie-le dans `conf.d` (il ne remplace pas le
`postgresql.conf` principal, il le surcharge) :

```bash
install -o postgres -g postgres -m 644 \
  /opt/labuse/app/deploy/postgresql/postgresql.vps2.conf \
  /etc/postgresql/16/main/conf.d/zz-labuse-vps2.conf

systemctl restart postgresql
sudo -u postgres psql -c "SHOW shared_buffers; SHOW random_page_cost;"   # 2GB / 1.1
```

## 4. Création de la base LA BUSE

```bash
# Rôle applicatif + base + extension PostGIS. Choisis un MOT DE PASSE FORT (≠ 'labuse').
sudo -u postgres psql <<'SQL'
CREATE ROLE labuse LOGIN PASSWORD 'CHANGE_MOI_MOT_DE_PASSE_FORT';
CREATE DATABASE labuse OWNER labuse;
\connect labuse
CREATE EXTENSION IF NOT EXISTS postgis;
SQL
```

> La base de **test** (`labuse_test`) n'est utile que pour exécuter `pytest` ; inutile en prod.

## 5. Restauration du dump PostgreSQL

Transférer le dump depuis la machine source, puis le restaurer. Le dump est au format
`pg_dump -Fc --no-owner`.

```bash
# Sur la machine SOURCE (si pas déjà fait) : produire un dump frais
#   labuse backup-db --dir /tmp
#   scp /tmp/labuse-labuse-*.dump  root@VPS:/var/backups/labuse/

# Sur le VPS : restaurer dans la base 'labuse'
sudo -u postgres pg_restore --no-owner --role=labuse \
  -d labuse /var/backups/labuse/labuse-labuse-XXXXXXXX-XXXXXX.dump

# Vérification rapide
sudo -u postgres psql -d labuse -c \
  "SELECT count(*) AS parcelles FROM parcels;  SELECT postgis_full_version();"
```

> **Alternative sans dump** (repartir de zéro) : après les étapes 6–7, lancer
> `sudo -u labuse /opt/labuse/venv/bin/labuse ingest-island` pour reconstruire les 24 communes
> depuis les sources publiques (long ; à faire hors fenêtre de démo).

## 6. Installation de l'application

```bash
# Cloner le code (branche de prod — voir « Merge vers main » en fin de doc)
sudo -u labuse git clone https://github.com/vcitordosgor/labuse.git /opt/labuse/app
cd /opt/labuse/app
sudo -u labuse git checkout main        # ou le tag de release retenu

# venv + installation ÉDITABLE (l'app lit config/, data/, web/ depuis l'arbre du repo)
sudo -u labuse python3 -m venv /opt/labuse/venv
sudo -u labuse /opt/labuse/venv/bin/pip install --upgrade pip
sudo -u labuse /opt/labuse/venv/bin/pip install -e /opt/labuse/app

# Sanity : la commande 'labuse' répond
sudo -u labuse /opt/labuse/venv/bin/labuse --help | head
```

## 7. Variables d'environnement

Copier le gabarit du repo vers `/etc/labuse/labuse.env` et le remplir (secrets **jamais** dans git) :

```bash
install -o root -g labuse -m 640 /opt/labuse/app/.env.example /etc/labuse/labuse.env
# Éditer /etc/labuse/labuse.env :
#   - LABUSE_DATABASE_URL  → mot de passe choisi à l'étape 4
#   - LABUSE_ENV=production
#   - LABUSE_AUTH_PASSWORD → mot de passe pilote (obligatoire hors 'local', sinon 503 fail-closed)
#   - LABUSE_SECRET_KEY    → openssl rand -hex 32
#   - LABUSE_PUBLIC_URL=https://app.labuse.immo
openssl rand -hex 32         # à coller dans LABUSE_SECRET_KEY
```

Appliquer (idempotent) le schéma / migrations légères avant le premier démarrage :

```bash
sudo -u labuse bash -c 'set -a; . /etc/labuse/labuse.env; set +a; \
  /opt/labuse/venv/bin/labuse init-db && /opt/labuse/venv/bin/labuse doctor --json | head'
```

## 8. Lancement via systemd

Poser l'unité (fournie : `deploy/systemd/labuse.service`) :

```bash
install -o root -g root -m 644 /opt/labuse/app/deploy/systemd/labuse.service \
  /etc/systemd/system/labuse.service
systemctl daemon-reload
systemctl enable --now labuse
systemctl status labuse --no-pager
journalctl -u labuse -n 30 --no-pager           # logs via journald (pas de nohup)

# L'app écoute en LOCAL uniquement (127.0.0.1:8000) — vérif :
curl -s http://127.0.0.1:8000/healthz           # {"status":"ok"}
```

## 9. Configuration Nginx (reverse proxy)

Poser le vhost (fourni : `deploy/nginx/labuse.conf`) puis l'activer **d'abord en HTTP** (le temps
d'obtenir le certificat) :

```bash
install -o root -g root -m 644 /opt/labuse/app/deploy/nginx/labuse.conf \
  /etc/nginx/sites-available/labuse.conf
ln -sf /etc/nginx/sites-available/labuse.conf /etc/nginx/sites-enabled/labuse.conf
rm -f /etc/nginx/sites-enabled/default
mkdir -p /var/www/certbot
nginx -t && systemctl reload nginx
```

> Le vhost proxie `app.labuse.immo` → `127.0.0.1:8000`, redirige `labuse.immo` → `app.labuse.immo`,
> pose les en-têtes de sécurité et le support WebSocket (précaution). Les blocs `443 ssl` y figurent
> déjà : ils deviennent valides une fois le certificat émis (étape 10).

## 10. HTTPS avec Let's Encrypt

Pré-requis : les DNS de `labuse.immo`, `www.labuse.immo` et `app.labuse.immo` pointent déjà sur
l'IP du VPS (enregistrements A/AAAA). Puis :

```bash
certbot --nginx -d app.labuse.immo -d labuse.immo -d www.labuse.immo \
  --redirect --agree-tos -m admin@labuse.immo --no-eff-email

# Renouvellement auto déjà installé par le paquet ; tester à blanc :
certbot renew --dry-run
systemctl reload nginx
```

> Après confirmation que tout passe en HTTPS, décommenter la ligne `Strict-Transport-Security`
> (HSTS) dans `deploy/nginx/labuse.conf` puis `nginx -t && systemctl reload nginx`.

## 11. Tests de santé après déploiement

```bash
# Smoke test fourni (process, /healthz, /readyz, DB, PostGIS, 1 parcelle, statut démo)
sudo -u labuse bash -c 'set -a; . /etc/labuse/labuse.env; set +a; \
  /opt/labuse/app/deploy/scripts/smoke_test.sh'

# Depuis l'extérieur (HTTPS public)
curl -sS https://app.labuse.immo/healthz
curl -sS https://app.labuse.immo/readyz          # 200 = schéma + données critiques OK
```

Mettre en place la maintenance + les sauvegardes (cron) :

```bash
# Sauvegarde quotidienne hors dossier applicatif (3h du matin)
( crontab -l -u labuse 2>/dev/null; \
  echo '0 3 * * * /opt/labuse/app/deploy/scripts/backup_postgres.sh >> /var/log/labuse-backup.log 2>&1' \
) | crontab -u labuse -

# Maintenance hebdo (VACUUM ANALYZE + audit tailles) — dimanche 4h
( crontab -l -u labuse 2>/dev/null; \
  echo '0 4 * * 0 /opt/labuse/app/deploy/scripts/db_maintenance.sh >> /var/log/labuse-maint.log 2>&1' \
) | crontab -u labuse -
```

> `labuse` n'ayant pas de shell, exécuter ces scripts via `sudo -u labuse bash -lc '...'` lors des
> tests manuels, ou via cron comme ci-dessus. Le mot de passe DB est lu depuis `~labuse/.pgpass`
> (voir `backup_postgres.sh`) ou depuis `LABUSE_DATABASE_URL`.

---

## 12. Procédure de ROLLBACK

Le rollback repose sur deux invariants : **le code est versionné (git)** et **chaque mise en
production est précédée d'un dump** (étape 5 / sauvegarde). Pour revenir à l'état antérieur :

```bash
# 1) Repli applicatif : revenir au commit/tag précédent
cd /opt/labuse/app
sudo -u labuse git fetch --tags
sudo -u labuse git checkout <tag_ou_commit_precedent>
sudo -u labuse /opt/labuse/venv/bin/pip install -e /opt/labuse/app   # si deps modifiées

# 2) Repli base (UNIQUEMENT si la migration a touché la donnée) :
#    restaurer le dump pris JUSTE AVANT la migration. pg_restore --clean ÉCRASE l'existant.
systemctl stop labuse
sudo -u postgres pg_restore --clean --if-exists --no-owner --role=labuse \
  -d labuse /var/backups/labuse/labuse-labuse-<AVANT_MIGRATION>.dump

# 3) Redémarrer + revérifier
systemctl start labuse
sudo -u labuse bash -lc '/opt/labuse/app/deploy/scripts/smoke_test.sh'
```

> **Avant toute mise à jour** : `labuse backup-db --dir /var/backups/labuse` (ou attendre la
> sauvegarde cron) → on a toujours un point de retour daté. Le rollback ne supprime jamais les
> backups ; il restaure par-dessus.

---

## Annexe — Merge de la branche vers `main` avant déploiement

La branche de travail `claude/brave-davinci-NaRd4` est **en avance sur `main`** : elle doit être
fusionnée avant de déployer (le déploiement clone `main`). Procédure propre :

```bash
git checkout main
git pull --ff-only origin main
git merge --no-ff claude/brave-davinci-NaRd4 -m "Release: pack déploiement + LOT 1-4 + finitions"
# Vérifs avant de pousser :
pytest -q && ruff check src/labuse tests
git tag -a v1.0.0-pilot -m "Pilote Saint-Paul — première mise en production"
git push origin main --tags
```

> Si tu préfères une revue : ouvrir une **Pull Request** `claude/brave-davinci-NaRd4 → main`,
> faire tourner la CI, puis merger. Ne jamais déployer une branche de travail directement.
